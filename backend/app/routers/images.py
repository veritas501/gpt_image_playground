from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from app.repositories.image_repo import ImageRepository
from app.utils.file_storage import FileStorage

router = APIRouter(prefix="/api/images", tags=["images"])


@router.get("/{image_id}")
def get_image(image_id: str, request: Request) -> FileResponse:
    return _image_response(image_id, request, as_attachment=False)


@router.get("/{image_id}/download")
def download_image(image_id: str, request: Request) -> FileResponse:
    return _image_response(image_id, request, as_attachment=True)


def _image_response(image_id: str, request: Request, *, as_attachment: bool) -> FileResponse:
    with request.app.state.session_factory() as session:
        image = ImageRepository(session).get(image_id)
        if not image:
            raise HTTPException(status_code=404, detail="image not found")
        storage = FileStorage(request.app.state.settings.images.storage_dir)
        path = storage.resolve(image.file_path)
        if not path.exists():
            raise HTTPException(status_code=404, detail="image file not found")
        filename = path.name if as_attachment else None
        return FileResponse(path, media_type=image.mime_type, filename=filename)
