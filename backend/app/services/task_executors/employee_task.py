from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import WorkflowTask


class EmployeeTaskExecutor:
    async def execute(
        self,
        session: AsyncSession,
        task: WorkflowTask,
    ) -> WorkflowTask:
        if task.task_type != "employee_task":
            raise ValueError(
                f"Invalid task type '{task.task_type}' "
                f"for EmployeeTaskExecutor."
            )

        task.result = (
            f"Employee task '{task.name}' "
            f"executed successfully."
        )

        return task