import asyncio
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal
from app.models.employee import Employee
from app.models.user import User
from app.models.workflow import (
    WorkflowDefinition,
    WorkflowTaskDefinition,
    WorkflowRun,
    WorkflowTask,
)
from app.services.task_execution import TaskExecutionService
import app.models
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal
from app.services.task_execution import TaskExecutionService

import asyncio

import app.models

from app.db.database import AsyncSessionLocal
from app.services.task_execution import TaskExecutionService
from app.services.task_executor import TaskExecutor


WORKFLOW_RUN_ID = 1
TASK_ID_TO_EXECUTE = "vpn_access"

async def test_task_execution() -> None:
    async with AsyncSessionLocal() as session:
        task_service = TaskExecutionService()
        executor = TaskExecutor()

        ready_tasks = await task_service.get_ready_tasks(
            session=session,
            workflow_run_id=WORKFLOW_RUN_ID,
        )

        print("\nREADY TASKS")
        print("=" * 40)

        for task in ready_tasks:
            print(
                f"id={task.id} | "
                f"task_id={task.task_id} | "
                f"name={task.name}"
            )

        selected_task = next(
            (
                task
                for task in ready_tasks
                if task.task_id == TASK_ID_TO_EXECUTE
            ),
            None,
        )

        if selected_task is None:
            print(
                f"\nTask '{TASK_ID_TO_EXECUTE}' "
                f"is not currently ready."
            )
            return

        print("\nEXECUTING TASK")
        print("=" * 40)
        print(f"task_id={selected_task.task_id}")

        completed_task = await executor.execute(
            session=session,
            task=selected_task,
        )

        print("\nTASK RESULT")
        print("=" * 40)
        print(
            f"id={completed_task.id} | "
            f"task_id={completed_task.task_id} | "
            f"status={completed_task.status}"
        )
        print(f"result={completed_task.result}")


if __name__ == "__main__":
    asyncio.run(test_task_execution())