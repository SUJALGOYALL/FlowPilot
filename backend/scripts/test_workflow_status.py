import asyncio

import app.models

from app.db.database import AsyncSessionLocal
from app.services.workflow_execution import WorkflowExecutionService


WORKFLOW_RUN_ID = 2


async def test_workflow_status() -> None:
    async with AsyncSessionLocal() as session:
        service = WorkflowExecutionService(
            workflows_dir="workflows"
        )

        workflow_run = await service.update_workflow_run_status(
            session=session,
            workflow_run_id=WORKFLOW_RUN_ID,
        )

        print("\nWORKFLOW RUN STATUS")
        print("=" * 40)
        print(f"id={workflow_run.id}")
        print(f"status={workflow_run.status}")
        print(f"started_at={workflow_run.started_at}")
        print(f"completed_at={workflow_run.completed_at}")


if __name__ == "__main__":
    asyncio.run(test_workflow_status())