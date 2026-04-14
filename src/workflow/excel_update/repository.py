from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from src.workflow.excel_update.models import ExcelUpdateOperation, ExcelUpdateTask


class ExcelUpdateTaskRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_task(self, task: ExcelUpdateTask) -> ExcelUpdateTask:
        self.db.add(task)
        self.db.commit()
        return self.get_task(task.task_id) or task

    def list_tasks(self) -> list[ExcelUpdateTask]:
        statement = select(ExcelUpdateTask).order_by(ExcelUpdateTask.created_at.desc())
        return list(self.db.execute(statement).scalars().all())

    def get_task(self, task_id: str) -> ExcelUpdateTask | None:
        statement = (
            select(ExcelUpdateTask)
            .options(selectinload(ExcelUpdateTask.operations))
            .where(ExcelUpdateTask.task_id == task_id)
        )
        return self.db.execute(statement).scalar_one_or_none()

    def add_operation(self, task: ExcelUpdateTask, operation: ExcelUpdateOperation) -> ExcelUpdateOperation:
        task.operations.append(operation)
        self.db.add(task)
        self.db.commit()
        refreshed_task = self.get_task(task.task_id)
        if refreshed_task is None:
            return operation
        for item in refreshed_task.operations:
            if item.operation_id == operation.operation_id:
                return item
        return operation
