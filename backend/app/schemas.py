from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

TaskStatus = Literal["queued", "running", "succeeded", "failed"]
TaskMode = Literal["generate", "edit"]


class TaskCreateResponse(BaseModel):
    request_id: str
    status: TaskStatus
    created_at: str


class TaskDetail(BaseModel):
    request_id: str
    prompt: str
    mode: str
    params: dict[str, Any]
    status: str
    error: str | None = None
    api_mode: str | None = None
    api_model: str | None = None
    elapsed_ms: int | None = None
    actual_params: dict[str, Any] | None = None
    revised_prompt: str | None = None
    input_image_ids: list[str] = Field(default_factory=list)
    mask_image_id: str | None = None
    output_image_ids: list[str] = Field(default_factory=list)
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
