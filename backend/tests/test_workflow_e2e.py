from datetime import date
import os
from pathlib import Path
import unittest
from uuid import uuid4
from unittest.mock import patch

from sqlalchemy import delete, select

from app.core.config import settings
from app.db.database import AsyncSessionLocal, engine
from app.models.employee import Employee
from app.models.user import User
from app.models.workflow import WorkflowRun, WorkflowTask
from app.services.approval_service import ApprovalService
from app.services.mcp_client import MCPClient
from app.services.task_executors.provisioning import (
    ProvisioningTaskExecutor,
)
from app.services.workflow_execution import WorkflowExecutionService
from app.services.workflow_orchestrator import WorkflowOrchestrator


BACKEND_DIR = Path(__file__).resolve().parents[1]
WORKFLOWS_DIR = BACKEND_DIR / "workflows"
MCP_ENDPOINT = "http://127.0.0.1:8001"
E2E_FLAG = "FLOWPILOT_RUN_E2E"
EMPLOYEE_ID = "EMP-TEST-001"

PROVISIONING_RESULTS = {
    "company_account": "Company account created",
    "slack_access": "Slack access provisioned",
    "github_access": "GitHub access provisioned",
    "vpn_access": "VPN access provisioned",
    "backend_environment": "Development environment provisioned",
    "frontend_environment": "Frontend development environment provisioned",
    "package_registry": "Package registry access provisioned",
    "ml_environment": "Machine learning development environment provisioned",
    "gpu_access": "GPU access provisioned",
    "model_registry": "Model registry access provisioned",
    "cloud_environment": "Cloud environment provisioned",
    "infrastructure_access": "Infrastructure access provisioned",
    "deployment_access": "Deployment access provisioned",
}


class WorkflowE2EBase(unittest.IsolatedAsyncioTestCase):
    job_title = ""
    fixture_code = ""
    use_existing_employee = False

    def setUp(self):
        if os.environ.get(E2E_FLAG) != "1":
            self.skipTest(
                f"Set {E2E_FLAG}=1 to run database and MCP E2E tests."
            )

    async def asyncSetUp(self):
        self.workflow_run_ids: list[int] = []
        self.created_employee_pk: int | None = None
        self.created_user_pk: int | None = None
        self.employee_pk: int | None = None

        tools = await MCPClient(MCP_ENDPOINT).list_tools()
        registered_tools = {tool["name"] for tool in tools}
        missing_tools = (
            set(ProvisioningTaskExecutor.TOOL_MAPPING.values())
            - registered_tools
        )
        self.assertFalse(
            missing_tools,
            f"Local MCP server is missing tools: {sorted(missing_tools)}",
        )

        async with AsyncSessionLocal() as session:
            if self.use_existing_employee:
                result = await session.execute(
                    select(Employee).where(
                        Employee.employee_id == EMPLOYEE_ID
                    )
                )
                employee = result.scalar_one_or_none()

                if employee is None:
                    self.fail(
                        f"Required existing employee {EMPLOYEE_ID} was not found."
                    )

                self.employee_pk = employee.id
                return

            employee_identifier = (
                f"EMP-E2E-{self.fixture_code}-{uuid4().hex[:8]}"
            )
            user = User(
                email=(
                    f"{employee_identifier.lower()}@e2e.flowpilot.invalid"
                ),
                full_name=f"FlowPilot E2E {self.fixture_code} Fixture",
                hashed_password="not-used-by-e2e",
                role="employee",
                is_active=True,
                is_verified=True,
            )
            session.add(user)
            await session.flush()

            employee = Employee(
                user_id=user.id,
                employee_id=employee_identifier,
                department="Engineering",
                job_title=self.job_title,
                joining_date=date(2026, 10, 1),
                employment_type="full_time",
                location="E2E fixture",
            )
            session.add(employee)
            await session.commit()
            await session.refresh(employee)

            self.created_user_pk = user.id
            self.created_employee_pk = employee.id
            self.employee_pk = employee.id

    async def asyncTearDown(self):
        try:
            async with AsyncSessionLocal() as session:
                if self.workflow_run_ids:
                    await session.execute(
                        delete(WorkflowTask).where(
                            WorkflowTask.workflow_run_id.in_(
                                self.workflow_run_ids
                            )
                        )
                    )
                    await session.execute(
                        delete(WorkflowRun).where(
                            WorkflowRun.id.in_(self.workflow_run_ids)
                        )
                    )

                if self.created_employee_pk is not None:
                    await session.execute(
                        delete(Employee).where(
                            Employee.id == self.created_employee_pk
                        )
                    )

                if self.created_user_pk is not None:
                    await session.execute(
                        delete(User).where(
                            User.id == self.created_user_pk
                        )
                    )

                await session.commit()
        finally:
            await engine.dispose()

    async def run_workflow_to_completion(self):
        workflow_service = WorkflowExecutionService(
            workflows_dir=str(WORKFLOWS_DIR)
        )
        workflow = workflow_service.resolver.resolve(self.job_title)
        self.assertEqual(workflow.trigger.job_title, self.job_title)

        orchestrator = WorkflowOrchestrator(
            workflow_service=workflow_service
        )
        declared_approvals = {
            task.id
            for task in workflow.tasks
            if task.requires_approval
        }
        observed_approvals: set[str] = set()
        executor = ProvisioningTaskExecutor()

        with patch.object(settings, "PROVISIONING_MCP_URL", MCP_ENDPOINT):
            async with AsyncSessionLocal() as session:
                workflow_run = await workflow_service.create_workflow_run(
                    session=session,
                    employee_id=self.employee_pk,
                    job_title=self.job_title,
                )
                self.workflow_run_ids.append(workflow_run.id)

                task_result = await session.execute(
                    select(WorkflowTask).where(
                        WorkflowTask.workflow_run_id == workflow_run.id
                    )
                )
                created_tasks = list(task_result.scalars().all())
                self.assertEqual(
                    {task.task_id for task in created_tasks},
                    {task.id for task in workflow.tasks},
                )

                workflow_run, _ = await orchestrator.execute_workflow(
                    session=session,
                    workflow_run_id=workflow_run.id,
                )
                self.assertEqual(
                    workflow_run.status,
                    "waiting_approval",
                )

                for _ in range(len(declared_approvals) + 1):
                    if workflow_run.status == "completed":
                        break

                    waiting_result = await session.execute(
                        select(WorkflowTask)
                        .where(
                            WorkflowTask.workflow_run_id == workflow_run.id,
                            WorkflowTask.status == "waiting_approval",
                        )
                        .order_by(WorkflowTask.id)
                    )
                    waiting_tasks = list(waiting_result.scalars().all())
                    self.assertTrue(
                        waiting_tasks,
                        "Workflow stalled without a ready approval task.",
                    )

                    for waiting_task in waiting_tasks:
                        self.assertTrue(waiting_task.requires_approval)
                        self.assertIn(
                            waiting_task.task_id,
                            declared_approvals,
                        )
                        observed_approvals.add(waiting_task.task_id)

                        approved_task = await ApprovalService().approve(
                            session=session,
                            task=waiting_task,
                            approver=User(
                                id=0,
                                role="hr",
                            ),
                        )
                        self.assertEqual(approved_task.status, "approved")

                    workflow_run, _ = await orchestrator.execute_workflow(
                        session=session,
                        workflow_run_id=workflow_run.id,
                    )

                self.assertEqual(
                    workflow_run.status,
                    "completed",
                )
                self.assertEqual(observed_approvals, declared_approvals)

                final_result = await session.execute(
                    select(WorkflowTask)
                    .where(
                        WorkflowTask.workflow_run_id == workflow_run.id
                    )
                    .order_by(WorkflowTask.id)
                )
                final_tasks = list(final_result.scalars().all())

                self.assertTrue(final_tasks)
                self.assertTrue(
                    all(task.status == "completed" for task in final_tasks),
                    {
                        task.task_id: task.status
                        for task in final_tasks
                    },
                )

                tasks_by_id = {
                    task.task_id: task for task in final_tasks
                }
                for task in final_tasks:
                    self.assertIsNotNone(task.started_at)
                    self.assertIsNotNone(task.completed_at)

                    for dependency_id in task.depends_on:
                        dependency = tasks_by_id[dependency_id]
                        self.assertLessEqual(
                            dependency.completed_at,
                            task.started_at,
                            f"{task.task_id} started before "
                            f"dependency {dependency_id} completed.",
                        )

                    if task.task_type == "provisioning":
                        self.assertIn(task.task_id, executor.TOOL_MAPPING)
                        self.assertTrue(
                            task.result.startswith(
                                PROVISIONING_RESULTS[task.task_id]
                            ),
                            f"Unexpected MCP result for {task.task_id}: "
                            f"{task.result}",
                        )

                print(
                    f"{self.job_title} E2E run {workflow_run.id}: "
                    + ", ".join(
                        f"{task.task_id}={task.status}"
                        for task in final_tasks
                    )
                )


class BackendWorkflowE2ETests(WorkflowE2EBase):
    job_title = "Backend Engineer"
    use_existing_employee = True

    async def test_backend_workflow_regression(self):
        await self.run_workflow_to_completion()


class FrontendWorkflowE2ETests(WorkflowE2EBase):
    job_title = "Frontend Engineer"
    fixture_code = "FRONTEND"

    async def test_frontend_workflow(self):
        await self.run_workflow_to_completion()


class AiMlWorkflowE2ETests(WorkflowE2EBase):
    job_title = "AI/ML Engineer"
    fixture_code = "AIML"

    async def test_ai_ml_workflow(self):
        await self.run_workflow_to_completion()


class DevOpsWorkflowE2ETests(WorkflowE2EBase):
    job_title = "DevOps Engineer"
    fixture_code = "DEVOPS"

    async def test_devops_workflow(self):
        await self.run_workflow_to_completion()