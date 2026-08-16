from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import WorkflowTask


class TaskExecutor:
    async def execute(
        self,
        session: AsyncSession,
        task: WorkflowTask,
    ) -> WorkflowTask:
        if task.status != "pending":
            raise ValueError(
                f"Task '{task.task_id}' cannot be executed "
                f"from status '{task.status}'."
            )

        # Approval-required tasks must wait for human approval.
        if task.requires_approval:
            task.status = "waiting_approval"
            task.result = (
                f"Waiting for approval from "
                f"{task.approval_role}."
            )

            await session.commit()
            await session.refresh(task)

            return task

        # Normal task execution.
        task.status = "running"
        task.started_at = datetime.now(timezone.utc)

        await session.flush()

        # Temporary deterministic execution.
        # Real task executors will replace this later.
        task.result = (
            f"Task '{task.name}' executed successfully."
        )

        task.status = "completed"
        task.completed_at = datetime.now(timezone.utc)

        await session.commit()
        await session.refresh(task)

        return task