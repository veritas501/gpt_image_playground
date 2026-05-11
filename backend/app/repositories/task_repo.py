from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Task


class TaskRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, task: Task) -> Task:
        self.session.add(task)
        self.session.flush()
        return task

    def get(self, task_id: str) -> Task | None:
        return self.session.get(Task, task_id)

    def delete(self, task: Task) -> None:
        self.session.delete(task)

    def list(self, *, status: str | None, q: str | None, page: int, page_size: int) -> tuple[list[Task], int]:
        stmt = select(Task)
        count_stmt = select(func.count()).select_from(Task)
        if status:
            stmt = stmt.where(Task.status == status)
            count_stmt = count_stmt.where(Task.status == status)
        if q:
            pattern = f"%{q}%"
            stmt = stmt.where(Task.prompt.like(pattern))
            count_stmt = count_stmt.where(Task.prompt.like(pattern))
        total = int(self.session.scalar(count_stmt) or 0)
        tasks = list(
            self.session.scalars(
                stmt.order_by(Task.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
            )
        )
        return tasks, total
