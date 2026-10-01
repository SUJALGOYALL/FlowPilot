import re
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import WorkflowTask
from app.services.task_executors.employee_task import (
    EmployeeTaskExecutor,
)
from app.services.task_executors.notification import (
    NotificationTaskExecutor,
)
from app.services.task_executors.provisioning import (
    ProvisioningTaskExecutor,
)
from app.services.task_executors.scheduling import (
    SchedulingTaskExecutor,
)


class TaskExecutor:
    def __init__(self):
        self.executors = {
            "notification": NotificationTaskExecutor(),
            "provisioning": ProvisioningTaskExecutor(),
            "scheduling": SchedulingTaskExecutor(),
            "employee_task": EmployeeTaskExecutor(),
        }

    async def execute(
        self,
        session: AsyncSession,
        task: WorkflowTask,
    ) -> WorkflowTask:
        if task.status not in {"pending", "approved"}:
            raise ValueError(
                f"Task '{task.task_id}' cannot be executed "
                f"from status '{task.status}'."
            )

        # Approval-required tasks must wait for human approval
        # before their first execution.
        if task.status == "pending" and task.requires_approval:
            task.status = "waiting_approval"
            task.result = (
                f"Waiting for approval from "
                f"{task.approval_role}."
            )

            await session.commit()
            await session.refresh(task)

            return task

        started_at = datetime.now(timezone.utc)
        task.status = "running"
        task.started_at = started_at

        try:
            await session.flush()

            executor = self.executors.get(task.task_type)

            if executor is None:
                raise ValueError(
                    f"No executor registered for task type "
                    f"'{task.task_type}'."
                )

            task = await executor.execute(
                session=session,
                task=task,
            )

            task.status = "completed"
            task.completed_at = datetime.now(timezone.utc)

            await session.commit()
            await session.refresh(task)

            return task

        except Exception as exc:
            await session.rollback()
            await session.refresh(task)

            task.status = "failed"
            task.started_at = started_at
            task.completed_at = None
            task.result = self._failure_message(exc)

            await session.commit()
            await session.refresh(task)

        return task

    def _failure_message(self, error: Exception) -> str:
        message = str(error).strip() or type(error).__name__
        message = re.sub(
            r"(?i)\b(password|passwd|token|access[_-]?token|"
            r"refresh[_-]?token|api[_-]?key|secret|credential)"
            r"(\s*[:=]\s*)(\"[^\"]*\"|'[^']*'|[^\s,;]+)",
            r"\1\2[REDACTED]",
            message,
        )
        message = re.sub(
            r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+",
            "Bearer [REDACTED]",
            message,
        )
        message = re.sub(
            r"(://[^:/\s]+:)[^@/\s]+@",
            r"\1[REDACTED]@",
            message,
        )

        if message.lower().startswith("mcp provisioning failed:"):
            return message

        return f"Task execution failed: {message}"