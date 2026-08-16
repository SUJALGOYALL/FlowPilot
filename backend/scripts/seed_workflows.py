import asyncio
from pathlib import Path
from app.models.employee import Employee
from app.models.user import User
from app.db.database import AsyncSessionLocal
from app.services.workflow_registry import WorkflowRegistry


WORKFLOWS_DIR = (
    Path(__file__).resolve().parent.parent
    / "workflows"
    / "engineering"
)


async def seed_workflows() -> None:
    registry = WorkflowRegistry(WORKFLOWS_DIR)

    async with AsyncSessionLocal() as session:
        workflows = await registry.sync_all(session)

        for workflow in workflows:
            print(
                f"Synced workflow: "
                f"{workflow.job_title} "
                f"(version={workflow.version})"
            )


if __name__ == "__main__":
    asyncio.run(seed_workflows())