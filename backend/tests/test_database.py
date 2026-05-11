from pathlib import Path

from sqlalchemy import inspect

from app.database import create_engine_for_path, init_db


def test_init_db_creates_required_tables(tmp_path: Path) -> None:
    engine = create_engine_for_path(tmp_path / "app.db")

    init_db(engine)

    table_names = set(inspect(engine).get_table_names())
    assert {"tasks", "images", "task_images"}.issubset(table_names)
