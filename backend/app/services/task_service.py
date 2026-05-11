from __future__ import annotations

import json
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Image, Task
from app.repositories.image_repo import ImageRepository
from app.repositories.task_repo import TaskRepository
from app.schemas import TaskCreateResponse, TaskDetail
from app.services.upstream import UpstreamClient
from app.utils.file_storage import FileStorage, SavedFile


class TaskInputError(ValueError):
    pass


class TaskNotFoundError(LookupError):
    pass


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


class TaskService:
    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.tasks = TaskRepository(session)
        self.images = ImageRepository(session)
        self.storage = FileStorage(settings.images.storage_dir)

    def create_task(
        self,
        *,
        prompt: str,
        mode: str,
        params: dict[str, Any],
        input_files: list[tuple[str, bytes, str]],
        mask_file: tuple[str, bytes, str] | None,
    ) -> TaskCreateResponse:
        if mode not in {"generate", "edit"}:
            raise TaskInputError("mode must be generate or edit")
        task = Task(
            id=uuid.uuid4().hex,
            prompt=prompt,
            mode=mode,
            params_json=json.dumps(params, ensure_ascii=False),
            status="queued",
            api_mode=self.settings.app.api_mode,
            api_model=self.settings.upstream.default_model,
            created_at=utc_now(),
        )
        self.tasks.add(task)
        for index, (filename, content, mime_type) in enumerate(input_files):
            saved = self.storage.save_bytes(kind="input", content=content, filename=filename)
            self._add_image(task.id, saved, kind="input", role="input", sort_order=index, mime_type=mime_type)
        if mask_file:
            filename, content, mime_type = mask_file
            saved = self.storage.save_bytes(kind="mask", content=content, filename=filename)
            self._add_image(task.id, saved, kind="mask", role="mask", sort_order=0, mime_type=mime_type)
        self.session.commit()
        return TaskCreateResponse(request_id=task.id, status="queued", created_at=task.created_at)

    def execute_task(self, task_id: str, upstream_client: UpstreamClient) -> None:
        task = self.tasks.get(task_id)
        if not task:
            raise TaskNotFoundError(task_id)
        start = time.monotonic()
        task.status = "running"
        task.started_at = utc_now()
        self.session.commit()
        try:
            params = self._params_for(task)
            input_paths = [self.storage.resolve(image.file_path) for image in self.images.images_for_task(task.id, "input")]
            mask_images = self.images.images_for_task(task.id, "mask")
            mask_path = self.storage.resolve(mask_images[0].file_path) if mask_images else None
            result = upstream_client.run_image_task(
                prompt=task.prompt,
                mode=task.mode,
                params=params,
                input_paths=input_paths,
                mask_path=mask_path,
            )
            for index, output in enumerate(result.images):
                saved = self.storage.save_bytes(kind="output", content=output.content, filename=output.filename)
                self._add_image(task.id, saved, kind="output", role="output", sort_order=index, mime_type=output.mime_type)
            task.status = "succeeded"
            task.actual_params_json = json.dumps(result.actual_params, ensure_ascii=False)
            task.revised_prompt = result.revised_prompt
        except Exception as exc:  # noqa: BLE001 - 任务失败必须落库，避免后台异常丢失。
            task.status = "failed"
            task.error = str(exc)
        finally:
            task.elapsed_ms = int((time.monotonic() - start) * 1000)
            task.finished_at = utc_now()
            self.session.commit()

    def get_task(self, task_id: str) -> TaskDetail:
        task = self.tasks.get(task_id)
        if not task:
            raise TaskNotFoundError(task_id)
        return self._detail_for(task)

    def retry_task(self, task_id: str) -> TaskCreateResponse:
        task = self.tasks.get(task_id)
        if not task:
            raise TaskNotFoundError(task_id)
        input_files = [
            (
                Path(image.file_path).name,
                self.storage.resolve(image.file_path).read_bytes(),
                image.mime_type,
            )
            for image in self.images.images_for_task(task.id, "input")
        ]
        mask_images = self.images.images_for_task(task.id, "mask")
        mask_file = None
        if mask_images:
            mask_image = mask_images[0]
            mask_file = (
                Path(mask_image.file_path).name,
                self.storage.resolve(mask_image.file_path).read_bytes(),
                mask_image.mime_type,
            )
        return self.create_task(
            prompt=task.prompt,
            mode=task.mode,
            params=self._params_for(task),
            input_files=input_files,
            mask_file=mask_file,
        )

    def delete_task(self, task_id: str, *, keep_images: bool) -> None:
        task = self.tasks.get(task_id)
        if not task:
            raise TaskNotFoundError(task_id)
        images = self.images.all_images_for_task(task.id)
        if not keep_images:
            for image in images:
                self.storage.delete(image.file_path)
        self.images.delete_links_for_task(task.id)
        self.images.delete_images_for_task(task.id)
        self.tasks.delete(task)
        self.session.commit()

    def _add_image(self, task_id: str, saved: SavedFile, *, kind: str, role: str, sort_order: int, mime_type: str) -> None:
        self.images.add(
            Image(
                id=saved.image_id,
                task_id=task_id,
                kind=kind,
                file_path=saved.relative_path,
                mime_type=mime_type or saved.mime_type,
                created_at=utc_now(),
            ),
            role=role,
            sort_order=sort_order,
        )

    def _detail_for(self, task: Task) -> TaskDetail:
        mask_ids = self.images.ids_for_task(task.id, "mask")
        return TaskDetail(
            request_id=task.id,
            prompt=task.prompt,
            mode=task.mode,
            params=self._params_for(task),
            status=task.status,
            error=task.error,
            api_mode=task.api_mode,
            api_model=task.api_model,
            elapsed_ms=task.elapsed_ms,
            actual_params=self._json_or_none(task.actual_params_json),
            revised_prompt=task.revised_prompt,
            input_image_ids=self.images.ids_for_task(task.id, "input"),
            mask_image_id=mask_ids[0] if mask_ids else None,
            output_image_ids=self.images.ids_for_task(task.id, "output"),
            created_at=task.created_at,
            started_at=task.started_at,
            finished_at=task.finished_at,
        )

    def _params_for(self, task: Task) -> dict[str, Any]:
        value = json.loads(task.params_json)
        return value if isinstance(value, dict) else {}

    def _json_or_none(self, value: str | None) -> dict[str, Any] | None:
        if not value:
            return None
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else None
