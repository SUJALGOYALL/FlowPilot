from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import WorkflowTask


class NotificationTaskExecutor:
    async def execute(
        self,
        session: AsyncSession,
        task: WorkflowTask,
    ) -> WorkflowTask:
        if task.task_type != "notification":
            raise ValueError(
                f"Invalid task type '{task.task_type}' "
                f"for NotificationTaskExecutor."
            )

        task.result = (
            f"Notification task '{task.name}' "
            f"executed successfully."
        )

        return task