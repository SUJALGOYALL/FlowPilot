from sqlalchemy.ext.asyncio import AsyncSession

from app.services.task_execution import TaskExecutionService
from app.services.task_executor import TaskExecutor
from app.services.workflow_execution import WorkflowExecutionService


class WorkflowOrchestrator:
    def __init__(
        self,
        task_service: TaskExecutionService | None = None,
        executor: TaskExecutor | None = None,
        workflow_service: WorkflowExecutionService | None = None,
    ):
        self.task_service = (
            task_service
            if task_service is not None
            else TaskExecutionService()
        )

        self.executor = (
            executor
            if executor is not None
            else TaskExecutor()
        )

        self.workflow_service = (
            workflow_service
            if workflow_service is not None
            else WorkflowExecutionService(
                workflows_dir="workflows",
            )
        )

    async def execute_workflow(
        self,
        session: AsyncSession,
        workflow_run_id: int,
    ):
        executed_tasks = []

        while True:
            ready_tasks = await self.task_service.get_ready_tasks(
                session=session,
                workflow_run_id=workflow_run_id,
            )

            if not ready_tasks:
                break

            progress_made = False

            for task in ready_tasks:
                previous_status = task.status

                completed_task = await self.executor.execute(
                    session=session,
                    task=task,
                )

                executed_tasks.append(completed_task)

                if completed_task.status != previous_status:
                    progress_made = True

            if not progress_made:
                break

        workflow_run = (
            await self.workflow_service.update_workflow_run_status(
                session=session,
                workflow_run_id=workflow_run_id,
            )
        )

        return workflow_run, executed_tasks