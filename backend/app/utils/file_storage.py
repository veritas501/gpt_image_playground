from __future__ import annotations

import mimetypes
import uuid
from dataclasses import dataclass
from pathlib import Path


class InvalidImageKind(ValueError):
    pass


@dataclass(frozen=True)
class SavedFile:
    image_id: str
    relative_path: str
    absolute_path: Path
    mime_type: str


class FileStorage:
    _DIR_BY_KIND = {
        "input": "inputs",
        "mask": "masks",
        "output": "outputs",
    }

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def save_bytes(self, *, kind: str, content: bytes, filename: str | None = None) -> SavedFile:
        directory = self._directory_for(kind)
        image_id = uuid.uuid4().hex
        extension = self._extension_for(filename)
        relative_path = f"{directory}/{image_id}{extension}"
        absolute_path = self.resolve(relative_path)
        absolute_path.parent.mkdir(parents=True, exist_ok=True)
        absolute_path.write_bytes(content)
        return SavedFile(
            image_id=image_id,
            relative_path=relative_path,
            absolute_path=absolute_path,
            mime_type=self._mime_type_for(extension),
        )

    def resolve(self, relative_path: str) -> Path:
        path = (self.root / relative_path).resolve()
        if self.root not in path.parents and path != self.root:
            raise ValueError("path escapes storage root")
        return path

    def delete(self, relative_path: str) -> None:
        path = self.resolve(relative_path)
        if path.exists():
            path.unlink()

    def _directory_for(self, kind: str) -> str:
        try:
            return self._DIR_BY_KIND[kind]
        except KeyError as exc:
            raise InvalidImageKind(f"invalid image kind: {kind}") from exc

    def _extension_for(self, filename: str | None) -> str:
        if not filename:
            return ".bin"
        suffix = Path(filename).suffix.lower()
        if suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
            return suffix
        return ".bin"

    def _mime_type_for(self, extension: str) -> str:
        if extension == ".bin":
            return "application/octet-stream"
        return mimetypes.types_map.get(extension, "application/octet-stream")
