from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import WorkflowTask


class TaskExecutionService:
    async def get_ready_tasks(
        self,
        session: AsyncSession,
        workflow_run_id: int,
    ) -> list[WorkflowTask]:
        result = await session.execute(
            select(WorkflowTask)
            .where(
                WorkflowTask.workflow_run_id == workflow_run_id,
                WorkflowTask.status.in_(["pending", "approved"]),
            )
            .order_by(WorkflowTask.id)
        )

        tasks = list(result.scalars().all())

        if not tasks:
            return []

        # Get all tasks belonging to this workflow run.
        all_result = await session.execute(
            select(WorkflowTask)
            .where(
                WorkflowTask.workflow_run_id == workflow_run_id,
            )
        )

        all_tasks = list(all_result.scalars().all())

        status_by_task_id = {
            task.task_id: task.status
            for task in all_tasks
        }

        ready_tasks: list[WorkflowTask] = []

        for task in tasks:
            dependencies_satisfied = all(
                status_by_task_id.get(dependency) == "completed"
                for dependency in task.depends_on
            )

            if dependencies_satisfied:
                ready_tasks.append(task)

        return ready_tasks
    