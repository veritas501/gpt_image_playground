from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from app.config import Settings, load_config
from app.database import create_engine_for_path, create_session_factory, init_db
from app.routers import app as app_router
from app.routers import images as images_router
from app.routers import tasks as tasks_router
from app.services.upstream import UpstreamClient

PUBLIC_API_PATHS = {"/api/health"}
NON_CACHEABLE_API_PREFIXES = ("/api/app", "/api/tasks")


def create_app(
    settings: Settings | None = None,
    *,
    upstream_client: UpstreamClient | None = None,
    run_tasks_inline: bool = False,
) -> FastAPI:
    settings = settings or load_config()
    settings.images.storage_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine_for_path(_database_path(settings))
    init_db(engine)

    app = FastAPI(title=settings.app.app_name)
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    app.state.upstream_client = upstream_client or UpstreamClient(settings)
    app.state.run_tasks_inline = run_tasks_inline

    @app.middleware("http")
    async def access_token_middleware(request: Request, call_next: Callable):
        if request.url.path.startswith("/api/") and request.url.path not in PUBLIC_API_PATHS:
            token = request.headers.get("X-Access-Token")
            if token != settings.security.access_token:
                return JSONResponse(status_code=403, content={"detail": "invalid access token"})
        response = await call_next(request)
        _apply_no_store_headers(request, response)
        return response

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(app_router.router)
    app.include_router(tasks_router.router)
    app.include_router(images_router.router)

    if settings.app.static_dir.exists():
        app.mount("/", StaticFiles(directory=settings.app.static_dir, html=True), name="static")
    return app


def _apply_no_store_headers(request: Request, response: Response) -> None:
    if not request.url.path.startswith(NON_CACHEABLE_API_PREFIXES):
        return
    response.headers["Cache-Control"] = "no-store, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"


def _database_path(settings: Settings) -> Path:
    env_path = os.getenv("IMAGE2_GEN_DB_PATH")
    if env_path:
        return Path(env_path).expanduser().resolve()
    return settings.project_root / "app.db"
