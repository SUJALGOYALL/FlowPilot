from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import (
    WorkflowDefinition,
    WorkflowTaskDefinition,
)
from app.services.workflow_resolver import WorkflowResolver


class WorkflowRegistry:
    """
    Synchronizes workflow YAML definitions into PostgreSQL.

    YAML is the source of truth for workflow configuration.
    PostgreSQL stores the synchronized workflow definitions and
    task definitions used by the execution engine.
    """

    def __init__(self, workflows_dir: str | Path):
        self.workflows_dir = Path(workflows_dir)
        self.resolver = WorkflowResolver(self.workflows_dir)

    async def sync_workflow(
        self,
        session: AsyncSession,
        job_title: str,
    ) -> WorkflowDefinition:
        workflow = self.resolver.resolve(job_title)

        result = await session.execute(
            select(WorkflowDefinition).where(
                WorkflowDefinition.job_title == job_title
            )
        )

        db_workflow = result.scalar_one_or_none()

        yaml_path = str(
            self.workflows_dir
            / self.resolver.WORKFLOW_FILES[job_title]
        )

        if db_workflow is None:
            db_workflow = WorkflowDefinition(
                name=workflow.name,
                version=workflow.version,
                description=workflow.description,
                yaml_path=yaml_path,
                department=workflow.trigger.department,
                job_title=workflow.trigger.job_title,
                is_active=True,
            )

            session.add(db_workflow)
            await session.flush()

        else:
            db_workflow.name = workflow.name
            db_workflow.version = workflow.version
            db_workflow.description = workflow.description
            db_workflow.yaml_path = yaml_path
            db_workflow.department = workflow.trigger.department
            db_workflow.job_title = workflow.trigger.job_title
            db_workflow.is_active = True

            await session.execute(
                delete(WorkflowTaskDefinition).where(
                    WorkflowTaskDefinition.workflow_definition_id
                    == db_workflow.id
                )
            )

            await session.flush()

        for task_order, task in enumerate(
            workflow.tasks,
            start=1,
        ):
            task_definition = WorkflowTaskDefinition(
                workflow_definition_id=db_workflow.id,
                task_key=task.id,
                name=task.name,
                task_type=task.type,
                requires_approval=task.requires_approval,
                approval_role=task.approval_role,
                depends_on=task.depends_on,
                task_order=task_order,
            )

            session.add(task_definition)

        await session.flush()

        return db_workflow

    async def sync_all(
        self,
        session: AsyncSession,
    ) -> list[WorkflowDefinition]:
        workflows: list[WorkflowDefinition] = []

        try:
            for job_title in self.resolver.WORKFLOW_FILES:
                workflow = await self.sync_workflow(
                    session=session,
                    job_title=job_title,
                )

                workflows.append(workflow)

            await session.commit()

        except Exception:
            await session.rollback()
            raise

        return workflows