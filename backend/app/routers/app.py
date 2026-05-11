from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/app", tags=["app"])


@router.get("/config")
def get_public_config(request: Request) -> dict[str, object]:
    settings = request.app.state.settings
    return {
        "app_name": settings.app.app_name,
        "default_model": settings.upstream.default_model,
        "api_mode": settings.app.api_mode,
        "supported_sizes": settings.app.supported_sizes,
        "default_params": settings.app.default_params,
    }
