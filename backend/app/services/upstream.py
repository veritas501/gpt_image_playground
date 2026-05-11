from __future__ import annotations

import base64
import json
import mimetypes
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from app.config import Settings


@dataclass(frozen=True)
class UpstreamImage:
    content: bytes
    mime_type: str
    filename: str = "output.png"


@dataclass(frozen=True)
class UpstreamResult:
    images: list[UpstreamImage]
    actual_params: dict[str, Any] = field(default_factory=dict)
    revised_prompt: str | None = None


class UpstreamClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def run_image_task(
        self,
        *,
        prompt: str,
        mode: str,
        params: dict[str, Any],
        input_paths: list[Path],
        mask_path: Path | None,
    ) -> UpstreamResult:
        if self.settings.app.api_mode == "responses":
            return self._responses(prompt=prompt, params=params, input_paths=input_paths, mask_path=mask_path)
        if mode == "edit":
            return self._edit(prompt=prompt, params=params, input_paths=input_paths, mask_path=mask_path)
        return self._generate(prompt=prompt, params=params)

    def _generate(self, *, prompt: str, params: dict[str, Any]) -> UpstreamResult:
        payload = self._base_payload(prompt, params)
        response = self._client().post(f"{self.settings.upstream.base_url}/images/generations", json=payload)
        self._raise_for_status(response)
        return self._parse_response(response.json(), params)

    def _edit(self, *, prompt: str, params: dict[str, Any], input_paths: list[Path], mask_path: Path | None) -> UpstreamResult:
        data = self._base_payload(prompt, params)
        files: list[tuple[str, tuple[str, bytes, str]]] = []
        for path in input_paths:
            files.append(("image", (path.name, path.read_bytes(), self._mime_type_for_path(path))))
        if mask_path:
            files.append(("mask", (mask_path.name, mask_path.read_bytes(), self._mime_type_for_path(mask_path))))
        response = self._client().post(f"{self.settings.upstream.base_url}/images/edits", data=data, files=files)
        self._raise_for_status(response)
        return self._parse_response(response.json(), params)

    def _responses(
        self,
        *,
        prompt: str,
        params: dict[str, Any],
        input_paths: list[Path],
        mask_path: Path | None,
    ) -> UpstreamResult:
        payload = {
            "model": self.settings.upstream.default_model,
            "input": self._responses_input(prompt, input_paths),
            "tools": [self._responses_tool(params, is_edit=bool(input_paths), mask_path=mask_path)],
            "tool_choice": "required",
        }
        response = self._client().post(f"{self.settings.upstream.base_url}/responses", json=payload)
        self._raise_for_status(response)
        return self._parse_responses_response(response.json())

    def _client(self) -> httpx.Client:
        return httpx.Client(
            timeout=self.settings.upstream.timeout_seconds,
            headers={"Authorization": f"Bearer {self.settings.upstream.api_key}"},
        )

    def _base_payload(self, prompt: str, params: dict[str, Any]) -> dict[str, Any]:
        payload = dict(params)
        payload.setdefault("model", self.settings.upstream.default_model)
        payload["prompt"] = prompt
        return payload

    def _responses_input(self, prompt: str, input_paths: list[Path]) -> str | list[dict[str, Any]]:
        guarded_prompt = f"Use the following text as the complete prompt. Do not rewrite it:\n{prompt}"
        if not input_paths:
            return guarded_prompt
        return [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": guarded_prompt},
                    *[
                        {
                            "type": "input_image",
                            "image_url": self._file_to_data_url(path),
                        }
                        for path in input_paths
                    ],
                ],
            }
        ]

    def _responses_tool(self, params: dict[str, Any], *, is_edit: bool, mask_path: Path | None) -> dict[str, Any]:
        tool: dict[str, Any] = {
            "type": "image_generation",
            "action": "edit" if is_edit else "generate",
            "size": params.get("size"),
            "output_format": params.get("output_format"),
        }
        if params.get("quality") is not None:
            tool["quality"] = params["quality"]
        if params.get("output_compression") is not None:
            tool["output_compression"] = params["output_compression"]
        if mask_path:
            tool["input_image_mask"] = {"image_url": self._file_to_data_url(mask_path)}
        return tool

    def _file_to_data_url(self, path: Path) -> str:
        payload = base64.b64encode(path.read_bytes()).decode("ascii")
        mime = self._mime_type_for_path(path)
        return f"data:{mime};base64,{payload}"

    def _mime_type_for_path(self, path: Path) -> str:
        return mimetypes.guess_type(path.name)[0] or "application/octet-stream"

    def _raise_for_status(self, response: httpx.Response) -> None:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = self._extract_error_message(response)
            if detail:
                raise RuntimeError(detail) from exc
            raise

    def _extract_error_message(self, response: httpx.Response) -> str | None:
        try:
            payload = response.json()
        except (ValueError, json.JSONDecodeError):
            text = response.text.strip()
            return text or None
        if not isinstance(payload, dict):
            return None
        error = payload.get("error")
        if isinstance(error, dict):
            message = error.get("message")
            if isinstance(message, str) and message.strip():
                return message.strip()
        detail = payload.get("detail")
        if isinstance(detail, str) and detail.strip():
            return detail.strip()
        return None

    def _parse_response(self, payload: dict[str, Any], params: dict[str, Any]) -> UpstreamResult:
        images: list[UpstreamImage] = []
        revised_prompt: str | None = None
        for index, item in enumerate(payload.get("data", [])):
            if item.get("revised_prompt"):
                revised_prompt = item["revised_prompt"]
            if item.get("b64_json"):
                images.append(
                    UpstreamImage(
                        content=base64.b64decode(item["b64_json"]),
                        mime_type="image/png",
                        filename=f"output-{index}.png",
                    )
                )
            elif item.get("url"):
                url = item["url"]
                fetched = self._client().get(url)
                fetched.raise_for_status()
                images.append(
                    UpstreamImage(
                        content=fetched.content,
                        mime_type=fetched.headers.get("content-type", "image/png"),
                        filename=f"output-{index}.png",
                    )
                )
        return UpstreamResult(
            images=images,
            actual_params=dict(params),
            revised_prompt=revised_prompt,
        )

    def _parse_responses_response(self, payload: dict[str, Any]) -> UpstreamResult:
        images: list[UpstreamImage] = []
        revised_prompt: str | None = None
        actual_params: dict[str, Any] = {}

        for index, item in enumerate(payload.get("output", [])):
            if item.get("type") != "image_generation_call":
                continue
            if item.get("revised_prompt"):
                revised_prompt = item["revised_prompt"]
            if item.get("size"):
                actual_params["size"] = item["size"]

            result = item.get("result")
            if isinstance(result, str) and result:
                images.append(
                    UpstreamImage(
                        content=base64.b64decode(result),
                        mime_type="image/png",
                        filename=f"output-{index}.png",
                    )
                )
                continue
            if isinstance(result, dict):
                b64_value = result.get("b64_json") or result.get("image") or result.get("data")
                if isinstance(b64_value, str) and b64_value:
                    images.append(
                        UpstreamImage(
                            content=base64.b64decode(b64_value),
                            mime_type="image/png",
                            filename=f"output-{index}.png",
                        )
                    )

        return UpstreamResult(
            images=images,
            actual_params=actual_params,
            revised_prompt=revised_prompt,
        )
