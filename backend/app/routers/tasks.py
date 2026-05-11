from __future__ import annotations

import json
import threading
from typing import Annotated, Any

from fastapi import APIRouter, FastAPI, File, Form, HTTPException, Request, UploadFile

from app.services.task_service import TaskInputError, TaskNotFoundError, TaskService

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.post("", status_code=201)
async def create_task(
    request: Request,
    prompt: Annotated[str, Form()],
    mode: Annotated[str, Form()],
    params: Annotated[str, Form()] = "{}",
    input_images: Annotated[list[UploadFile], File()] = [],
    mask: Annotated[UploadFile | None, File()] = None,
    mask_target_index: Annotated[int | None, Form()] = None,
    n: Annotated[int | None, Form()] = None,
    size: Annotated[str | None, Form()] = None,
    quality: Annotated[str | None, Form()] = None,
    output_format: Annotated[str | None, Form()] = None,
    output_compression: Annotated[int | None, Form()] = None,
    moderation: Annotated[str | None, Form()] = None,
) -> dict[str, Any]:
    parsed_params = _parse_params(params)
    _merge_form_params(
        parsed_params,
        {
            "mask_target_index": mask_target_index,
            "n": n,
            "size": size,
            "quality": quality,
            "output_format": output_format,
            "output_compression": output_compression,
            "moderation": moderation,
        },
    )
    input_file_data = [
        (upload.filename or "input.bin", await upload.read(), upload.content_type or "application/octet-stream")
        for upload in input_images
    ]
    mask_file_data = None
    if mask:
        mask_file_data = (
            mask.filename or "mask.bin",
            await mask.read(),
            mask.content_type or "application/octet-stream",
        )

    with request.app.state.session_factory() as session:
        service = TaskService(session, request.app.state.settings)
        try:
            created = service.create_task(
                prompt=prompt,
                mode=mode,
                params=parsed_params,
                input_files=input_file_data,
                mask_file=mask_file_data,
            )
        except TaskInputError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    if request.app.state.run_tasks_inline:
        _execute_task(request, created.request_id)
    else:
        _spawn_task_worker(request.app, created.request_id)
    return created.model_dump()


@router.get("/{request_id}")
def get_task(request_id: str, request: Request) -> dict[str, Any]:
    return _get_task_detail(request_id, request)


@router.post("/{request_id}")
def post_task_detail(request_id: str, request: Request) -> dict[str, Any]:
    return _get_task_detail(request_id, request)


def _get_task_detail(request_id: str, request: Request) -> dict[str, Any]:
    with request.app.state.session_factory() as session:
        service = TaskService(session, request.app.state.settings)
        try:
            return service.get_task(request_id).model_dump()
        except TaskNotFoundError as exc:
            raise HTTPException(status_code=404, detail="task not found") from exc


@router.post("/{request_id}/retry", status_code=201)
def retry_task(request_id: str, request: Request) -> dict[str, Any]:
    with request.app.state.session_factory() as session:
        service = TaskService(session, request.app.state.settings)
        try:
            created = service.retry_task(request_id)
        except TaskNotFoundError as exc:
            raise HTTPException(status_code=404, detail="task not found") from exc

    if request.app.state.run_tasks_inline:
        _execute_task(request, created.request_id)
    else:
        _spawn_task_worker(request.app, created.request_id)
    return created.model_dump()


@router.delete("/{request_id}")
def delete_task(request_id: str, request: Request, keep_images: bool = False) -> dict[str, bool]:
    with request.app.state.session_factory() as session:
        service = TaskService(session, request.app.state.settings)
        try:
            service.delete_task(request_id, keep_images=keep_images)
        except TaskNotFoundError as exc:
            raise HTTPException(status_code=404, detail="task not found") from exc
    return {"deleted": True}


def _execute_task(request: Request, task_id: str) -> None:
    with request.app.state.session_factory() as session:
        service = TaskService(session, request.app.state.settings)
        service.execute_task(task_id, request.app.state.upstream_client)


def _execute_task_for_app(app: FastAPI, task_id: str) -> None:
    with app.state.session_factory() as session:
        service = TaskService(session, app.state.settings)
        service.execute_task(task_id, app.state.upstream_client)


def _spawn_task_worker(app: FastAPI, task_id: str) -> None:
    worker = threading.Thread(
        target=_execute_task_for_app,
        args=(app, task_id),
        daemon=True,
        name=f"image2-gen-task-{task_id[:8]}",
    )
    worker.start()


def _parse_params(raw: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="params must be a JSON object") from exc
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=400, detail="params must be a JSON object")
    return parsed


def _merge_form_params(params: dict[str, Any], values: dict[str, Any]) -> None:
    for key, value in values.items():
        if value is not None:
            params[key] = value
