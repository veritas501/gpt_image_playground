from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Image, TaskImage


class ImageRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, image: Image, *, role: str, sort_order: int) -> Image:
        self.session.add(image)
        self.session.add(
            TaskImage(
                task_id=image.task_id,
                image_id=image.id,
                role=role,
                sort_order=sort_order,
            )
        )
        self.session.flush()
        return image

    def get(self, image_id: str) -> Image | None:
        return self.session.get(Image, image_id)

    def ids_for_task(self, task_id: str, role: str) -> list[str]:
        stmt = (
            select(TaskImage.image_id)
            .where(TaskImage.task_id == task_id, TaskImage.role == role)
            .order_by(TaskImage.sort_order.asc())
        )
        return list(self.session.scalars(stmt))

    def images_for_task(self, task_id: str, role: str) -> list[Image]:
        stmt = (
            select(Image)
            .join(TaskImage, Image.id == TaskImage.image_id)
            .where(TaskImage.task_id == task_id, TaskImage.role == role)
            .order_by(TaskImage.sort_order.asc())
        )
        return list(self.session.scalars(stmt))

    def all_images_for_task(self, task_id: str) -> list[Image]:
        stmt = (
            select(Image)
            .join(TaskImage, Image.id == TaskImage.image_id)
            .where(TaskImage.task_id == task_id)
            .order_by(TaskImage.sort_order.asc())
        )
        return list(self.session.scalars(stmt))

    def delete_links_for_task(self, task_id: str) -> None:
        for link in self.session.scalars(select(TaskImage).where(TaskImage.task_id == task_id)):
            self.session.delete(link)

    def delete_images_for_task(self, task_id: str) -> None:
        for image in self.session.scalars(select(Image).where(Image.task_id == task_id)):
            self.session.delete(image)
