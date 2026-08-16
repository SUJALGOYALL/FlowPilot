from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import (
    WorkflowDefinition,
    WorkflowRun,
    WorkflowTask,
)
from app.services.workflow_resolver import WorkflowResolver


class WorkflowExecutionService:
    def __init__(
        self,
        workflows_dir: str,
    ):
        self.resolver = WorkflowResolver(workflows_dir)

    async def create_workflow_run(
        self,
        session: AsyncSession,
        employee_id: int,
        job_title: str,
    ) -> WorkflowRun:
        # Resolve the workflow from YAML
        workflow = self.resolver.resolve(job_title)

        # Find the corresponding workflow definition
        # already stored in PostgreSQL.
        result = await session.execute(
            select(WorkflowDefinition).where(
                WorkflowDefinition.job_title == job_title,
                WorkflowDefinition.is_active.is_(True),
            )
        )

        workflow_definition = result.scalar_one_or_none()

        if workflow_definition is None:
            raise ValueError(
                f"No active workflow definition found in database "
                f"for job title: {job_title}"
            )

        # Create the execution record.
        workflow_run = WorkflowRun(
            workflow_definition_id=workflow_definition.id,
            employee_id=employee_id,
            status="pending",
        )

        session.add(workflow_run)

        # Get the generated workflow_run.id
        await session.flush()

        # Create execution records for every task.
        for task in workflow.tasks:
            workflow_task = WorkflowTask(
                workflow_run_id=workflow_run.id,
                task_id=task.id,
                name=task.name,
                task_type=task.type,
                status="pending",
                requires_approval=task.requires_approval,
                approval_role=task.approval_role,
                depends_on=task.depends_on,
            )

            session.add(workflow_task)

        await session.commit()

        await session.refresh(workflow_run)

        return workflow_run

    async def update_workflow_run_status(
        self,
        session: AsyncSession,
        workflow_run_id: int,
    ) -> WorkflowRun:
        result = await session.execute(
            select(WorkflowRun).where(
                WorkflowRun.id == workflow_run_id
            )
        )

        workflow_run = result.scalar_one_or_none()

        if workflow_run is None:
            raise ValueError(
                f"Workflow run '{workflow_run_id}' not found."
            )

        task_result = await session.execute(
            select(WorkflowTask).where(
                WorkflowTask.workflow_run_id == workflow_run_id
            )
        )

        tasks = list(task_result.scalars().all())

        if not tasks:
            return workflow_run

        # Start the workflow once the first execution begins.
        if workflow_run.status == "pending":
            workflow_run.status = "running"
            workflow_run.started_at = datetime.now(timezone.utc)

        # If every task is completed, complete the workflow.
        if all(task.status == "completed" for task in tasks):
            workflow_run.status = "completed"
            workflow_run.completed_at = datetime.now(timezone.utc)

        await session.commit()
        await session.refresh(workflow_run)

        return workflow_run