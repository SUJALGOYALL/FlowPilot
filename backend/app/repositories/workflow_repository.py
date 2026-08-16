from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import (
    WorkflowDefinition,
    WorkflowRun,
    WorkflowTask,
)


class WorkflowRepository:
    """
    Handles database operations related to workflow definitions,
    workflow runs, and runtime workflow tasks.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_active_definition(
        self,
        job_title: str,
    ) -> WorkflowDefinition | None:
        """
        Get the active workflow definition for a job title.
        """

        result = await self.session.execute(
            select(WorkflowDefinition)
            .where(
                WorkflowDefinition.job_title == job_title,
                WorkflowDefinition.is_active.is_(True),
            )
        )

        return result.scalar_one_or_none()

    async def get_run(
        self,
        run_id: int,
    ) -> WorkflowRun | None:
        """
        Get a workflow run by its ID.
        """

        result = await self.session.execute(
            select(WorkflowRun)
            .where(WorkflowRun.id == run_id)
        )

        return result.scalar_one_or_none()

    async def create_run(
        self,
        workflow_definition_id: int,
        employee_id: int,
    ) -> WorkflowRun:
        """
        Create a new workflow execution instance.
        """

        workflow_run = WorkflowRun(
            workflow_definition_id=workflow_definition_id,
            employee_id=employee_id,
            status="pending",
        )

        self.session.add(workflow_run)

        await self.session.flush()

        return workflow_run

    async def create_tasks(
        self,
        workflow_run: WorkflowRun,
    ) -> list[WorkflowTask]:
        """
        Create runtime WorkflowTask records from the
        workflow's task definitions.
        """

        tasks = []

        for definition in workflow_run.workflow_definition.task_definitions:
            task = WorkflowTask(
                workflow_run_id=workflow_run.id,
                task_id=definition.task_key,
                name=definition.name,
                task_type=definition.task_type,
                status="pending",
                requires_approval=definition.requires_approval,
                approval_role=definition.approval_role,
                depends_on=definition.depends_on,
            )

            self.session.add(task)
            tasks.append(task)

        await self.session.flush()

        return tasks

    async def get_tasks(
        self,
        workflow_run_id: int,
    ) -> list[WorkflowTask]:
        """
        Get all runtime tasks belonging to a workflow run.
        """

        result = await self.session.execute(
            select(WorkflowTask)
            .where(
                WorkflowTask.workflow_run_id == workflow_run_id
            )
            .order_by(WorkflowTask.id)
        )

        return list(result.scalars().all())

    async def update_run_status(
        self,
        workflow_run: WorkflowRun,
        status: str,
    ) -> WorkflowRun:
        """
        Update the status of a workflow run.
        """

        workflow_run.status = status

        await self.session.flush()

        return workflow_run

    async def update_task_status(
        self,
        task: WorkflowTask,
        status: str,
        result: str | None = None,
    ) -> WorkflowTask:
        """
        Update the status and optional result of a runtime task.
        """

        task.status = status

        if result is not None:
            task.result = result

        await self.session.flush()

        return task