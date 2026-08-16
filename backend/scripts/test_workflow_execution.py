import asyncio
from pathlib import Path
import app.models
from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.models.employee import Employee
from app.models.user import User

from app.services.workflow_execution import WorkflowExecutionService


WORKFLOWS_DIR = (
    Path(__file__).resolve().parent.parent
    / "workflows"
    / "engineering"
)


async def test_workflow_execution() -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Employee)
            .where(Employee.employee_id == "EMP-TEST-001")
        )

        employee = result.scalar_one_or_none()

        if employee is None:
            raise ValueError(
                "Test employee EMP-TEST-001 was not found."
            )

        service = WorkflowExecutionService(
            str(WORKFLOWS_DIR)
        )

        workflow_run = await service.create_workflow_run(
            session=session,
            employee_id=employee.id,
            job_title=employee.job_title,
        )

        print(
            f"Created workflow run: "
            f"id={workflow_run.id}, "
            f"employee_id={employee.id}, "
            f"job_title={employee.job_title}, "
            f"status={workflow_run.status}"
        )


if __name__ == "__main__":
    asyncio.run(test_workflow_execution())