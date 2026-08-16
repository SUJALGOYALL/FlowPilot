import asyncio

import app.models

from app.db.database import AsyncSessionLocal
from app.models.workflow import WorkflowTask
from app.services.approval_service import ApprovalService


WORKFLOW_RUN_ID = 2
TASK_ID = "vpn_access"


async def test_approval() -> None:
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select

        result = await session.execute(
            select(WorkflowTask).where(
                WorkflowTask.workflow_run_id == WORKFLOW_RUN_ID,
                WorkflowTask.task_id == TASK_ID,
            )
        )

        task = result.scalar_one_or_none()

        if task is None:
            print(f"Task '{TASK_ID}' not found.")
            return

        print("\nBEFORE APPROVAL")
        print("=" * 40)
        print(
            f"id={task.id} | "
            f"task_id={task.task_id} | "
            f"status={task.status}"
        )
        print(f"result={task.result}")

        approval_service = ApprovalService()

        approved_task = await approval_service.approve(
            session=session,
            task=task,
        )

        print("\nAFTER APPROVAL")
        print("=" * 40)
        print(
            f"id={approved_task.id} | "
            f"task_id={approved_task.task_id} | "
            f"status={approved_task.status}"
        )
        print(f"result={approved_task.result}")


if __name__ == "__main__":
    asyncio.run(test_approval())