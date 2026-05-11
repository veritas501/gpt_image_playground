from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    params_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    error: Mapped[str | None] = mapped_column(Text)
    api_mode: Mapped[str | None] = mapped_column(String(32))
    api_model: Mapped[str | None] = mapped_column(Text)
    elapsed_ms: Mapped[int | None] = mapped_column(Integer)
    actual_params_json: Mapped[str | None] = mapped_column(Text)
    revised_prompt: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[str | None] = mapped_column(Text)
    finished_at: Mapped[str | None] = mapped_column(Text)


class Image(Base):
    __tablename__ = "images"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    task_id: Mapped[str] = mapped_column(Text, ForeignKey("tasks.id"), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str] = mapped_column(Text, nullable=False)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


class TaskImage(Base):
    __tablename__ = "task_images"

    task_id: Mapped[str] = mapped_column(Text, ForeignKey("tasks.id"), primary_key=True)
    image_id: Mapped[str] = mapped_column(Text, ForeignKey("images.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String(32), primary_key=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
