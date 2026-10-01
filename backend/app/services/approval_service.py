from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee import Employee
from app.models.user import User
from app.models.workflow import WorkflowRun, WorkflowTask


class ApprovalService:
    async def approve(
        self,
        session: AsyncSession,
        task: WorkflowTask,
        approver: User,
    ) -> WorkflowTask:
        if not task.requires_approval:
            raise ValueError(
                f"Task '{task.task_id}' does not require approval."
            )

        if task.status != "waiting_approval":
            raise ValueError(
                f"Task '{task.task_id}' cannot be approved "
                f"from status '{task.status}'."
            )

        if approver.role not in {"hr", "admin"}:
            if approver.role != task.approval_role:
                raise PermissionError(
                    "User is not authorized to approve this task."
                )

            if approver.role == "manager":
                result = await session.execute(
                    select(Employee).join(
                        WorkflowRun,
                        WorkflowRun.employee_id == Employee.id,
                    ).where(
                        WorkflowRun.id == task.workflow_run_id
                    )
                )
                employee = result.scalar_one_or_none()

                manager_result = await session.execute(
                    select(Employee.id).where(
                        Employee.user_id == approver.id
                    )
                )
                manager_employee_id = (
                    manager_result.scalar_one_or_none()
                )

                if (
                    employee is None
                    or manager_employee_id is None
                    or employee.manager_id != manager_employee_id
                ):
                    raise PermissionError(
                        "User is not authorized to approve this task."
                    )

        task.status = "approved"
        task.result = "Task approved."

        await session.commit()
        await session.refresh(task)

        return task