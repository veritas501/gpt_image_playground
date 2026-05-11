from pathlib import Path

import pytest

from app.utils.file_storage import FileStorage, InvalidImageKind


def test_save_and_read_file_by_kind(tmp_path: Path) -> None:
    storage = FileStorage(tmp_path)

    saved = storage.save_bytes(kind="input", content=b"abc", filename="source.PNG")

    assert saved.image_id
    assert saved.mime_type == "image/png"
    assert saved.relative_path.startswith("inputs/")
    assert saved.absolute_path.read_bytes() == b"abc"
    assert storage.resolve(saved.relative_path) == saved.absolute_path


def test_invalid_kind_is_rejected(tmp_path: Path) -> None:
    storage = FileStorage(tmp_path)

    with pytest.raises(InvalidImageKind):
        storage.save_bytes(kind="bad", content=b"abc", filename="x.png")
