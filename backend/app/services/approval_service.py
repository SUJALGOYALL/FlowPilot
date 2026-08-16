from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import WorkflowTask


class ApprovalService:
    async def approve(
        self,
        session: AsyncSession,
        task: WorkflowTask,
    ) -> WorkflowTask:
        if task.status != "waiting_approval":
            raise ValueError(
                f"Task '{task.task_id}' cannot be approved "
                f"from status '{task.status}'."
            )

        task.status = "approved"
        task.result = "Task approved."

        await session.commit()
        await session.refresh(task)

        return task