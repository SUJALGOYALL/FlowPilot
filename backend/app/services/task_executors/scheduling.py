from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import WorkflowTask


class SchedulingTaskExecutor:
    async def execute(
        self,
        session: AsyncSession,
        task: WorkflowTask,
    ) -> WorkflowTask:
        if task.task_type != "scheduling":
            raise ValueError(
                f"Invalid task type '{task.task_type}' "
                f"for SchedulingTaskExecutor."
            )

        task.result = (
            f"Scheduling task '{task.name}' "
            f"executed successfully."
        )

        return task