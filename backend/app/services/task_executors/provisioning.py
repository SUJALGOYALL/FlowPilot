from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import WorkflowTask


class ProvisioningTaskExecutor:
    async def execute(
        self,
        session: AsyncSession,
        task: WorkflowTask,
    ) -> WorkflowTask:
        if task.task_type != "provisioning":
            raise ValueError(
                f"Invalid task type '{task.task_type}' "
                f"for ProvisioningTaskExecutor."
            )

        task.result = (
            f"Provisioning task '{task.name}' "
            f"executed successfully."
        )

        return task