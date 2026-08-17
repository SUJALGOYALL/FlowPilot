from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.db.database import get_db
from app.models.employee import Employee
from app.models.user import User
from app.models.workflow import WorkflowRun, WorkflowTask
from app.schemas.workflow import (
    TaskApprovalResponse,
    WorkflowRunCreate,
    WorkflowRunResponse,
    WorkflowTaskResponse,
)
from app.services.approval_service import ApprovalService
from app.services.task_execution import TaskExecutionService
from app.services.task_executor import TaskExecutor
from app.services.workflow_execution import WorkflowExecutionService


router = APIRouter(
    prefix="/workflows",
    tags=["Workflows"],
)


# ---------------------------------------------------------
# Service dependencies
# ---------------------------------------------------------


def get_workflow_execution_service() -> WorkflowExecutionService:
    return WorkflowExecutionService(
        workflows_dir="workflows",
    )


def get_task_execution_service() -> TaskExecutionService:
    return TaskExecutionService()


def get_task_executor() -> TaskExecutor:
    return TaskExecutor()


def get_approval_service() -> ApprovalService:
    return ApprovalService()


# ---------------------------------------------------------
# Create workflow run
# ---------------------------------------------------------


@router.post(
    "/runs",
    response_model=WorkflowRunResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_workflow_run(
    data: WorkflowRunCreate,
    current_user: User = Depends(
        require_role("hr", "admin")
    ),
    db: AsyncSession = Depends(get_db),
    workflow_service: WorkflowExecutionService = Depends(
        get_workflow_execution_service
    ),
):
    # 1. Verify employee exists
    result = await db.execute(
        select(Employee).where(
            Employee.id == data.employee_id
        )
    )

    employee = result.scalar_one_or_none()

    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found.",
        )

    # 2. Make sure the requested job title matches
    # the employee's actual job title.
    if employee.job_title != data.job_title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Job title does not match the employee's "
                "job title."
            ),
        )

    # 3. Create workflow execution
    try:
        workflow_run = await workflow_service.create_workflow_run(
            session=db,
            employee_id=employee.id,
            job_title=data.job_title,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    # 4. Load tasks for response
    result = await db.execute(
        select(WorkflowTask)
        .where(
            WorkflowTask.workflow_run_id
            == workflow_run.id
        )
        .order_by(WorkflowTask.id)
    )

    workflow_run.tasks = list(
        result.scalars().all()
    )

    return workflow_run


# ---------------------------------------------------------
# Get workflow run
# ---------------------------------------------------------


@router.get(
    "/runs/{workflow_run_id}",
    response_model=WorkflowRunResponse,
)
async def get_workflow_run(
    workflow_run_id: int,
    current_user: User = Depends(
        require_role("hr", "admin", "manager")
    ),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WorkflowRun).where(
            WorkflowRun.id == workflow_run_id
        )
    )

    workflow_run = result.scalar_one_or_none()

    if workflow_run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow run not found.",
        )

    task_result = await db.execute(
        select(WorkflowTask)
        .where(
            WorkflowTask.workflow_run_id
            == workflow_run_id
        )
        .order_by(WorkflowTask.id)
    )

    workflow_run.tasks = list(
        task_result.scalars().all()
    )

    return workflow_run


# ---------------------------------------------------------
# Execute task
# ---------------------------------------------------------


@router.post(
    "/tasks/{task_id}/execute",
    response_model=WorkflowTaskResponse,
)
async def execute_task(
    task_id: int,
    current_user: User = Depends(
        require_role("hr", "admin")
    ),
    db: AsyncSession = Depends(get_db),
    task_service: TaskExecutionService = Depends(
        get_task_execution_service
    ),
    executor: TaskExecutor = Depends(
        get_task_executor
    ),
    workflow_service: WorkflowExecutionService = Depends(
        get_workflow_execution_service
    ),
):
    # 1. Find task
    result = await db.execute(
        select(WorkflowTask).where(
            WorkflowTask.id == task_id
        )
    )

    task = result.scalar_one_or_none()

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found.",
        )

    # 2. Check whether task is currently ready
    ready_tasks = await task_service.get_ready_tasks(
        session=db,
        workflow_run_id=task.workflow_run_id,
    )

    selected_task = next(
        (
            ready_task
            for ready_task in ready_tasks
            if ready_task.id == task.id
        ),
        None,
    )

    if selected_task is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Task '{task.task_id}' is not currently ready."
            ),
        )

    # 3. Execute task
    try:
        completed_task = await executor.execute(
            session=db,
            task=selected_task,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    # 4. Recalculate workflow status
    await workflow_service.update_workflow_run_status(
        session=db,
        workflow_run_id=task.workflow_run_id,
    )

    return completed_task


# ---------------------------------------------------------
# Approve task
# ---------------------------------------------------------


@router.post(
    "/tasks/{task_id}/approve",
    response_model=TaskApprovalResponse,
)
async def approve_task(
    task_id: int,
    current_user: User = Depends(
        require_role("manager", "hr", "admin")
    ),
    db: AsyncSession = Depends(get_db),
    approval_service: ApprovalService = Depends(
        get_approval_service
    ),
    workflow_service: WorkflowExecutionService = Depends(
        get_workflow_execution_service
    ),
):
    # 1. Find task
    result = await db.execute(
        select(WorkflowTask).where(
            WorkflowTask.id == task_id
        )
    )

    task = result.scalar_one_or_none()

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found.",
        )

    # 2. Approve task
    try:
        approved_task = await approval_service.approve(
            session=db,
            task=task,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    # 3. Recalculate workflow status
    await workflow_service.update_workflow_run_status(
        session=db,
        workflow_run_id=task.workflow_run_id,
    )

    return approved_task