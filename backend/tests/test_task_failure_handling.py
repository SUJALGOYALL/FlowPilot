import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from mcp.types import CallToolResult, TextContent

from app.services.task_executor import TaskExecutor
from app.services.task_executors.provisioning import (
    ProvisioningTaskExecutor,
)
from app.services.workflow_execution import WorkflowExecutionService
from app.services.workflow_orchestrator import WorkflowOrchestrator


class TaskExecutorTests(unittest.IsolatedAsyncioTestCase):
    def make_session(self):
        return SimpleNamespace(
            flush=AsyncMock(),
            commit=AsyncMock(),
            refresh=AsyncMock(),
            rollback=AsyncMock(),
        )

    def make_task(self, **overrides):
        values = {
            "workflow_run_id": 1,
            "task_id": "slack_access",
            "task_type": "provisioning",
            "status": "pending",
            "requires_approval": False,
            "approval_role": None,
            "result": None,
            "started_at": None,
            "completed_at": None,
        }
        values.update(overrides)
        return SimpleNamespace(**values)

    async def test_successful_task_is_completed(self):
        session = self.make_session()
        session.execute = AsyncMock(
            side_effect=[
                SimpleNamespace(
                    scalar_one=lambda: SimpleNamespace(employee_id=7)
                ),
                SimpleNamespace(
                    scalar_one=lambda: SimpleNamespace(
                        id=7,
                        job_title="Backend Engineer",
                    )
                ),
            ]
        )
        task = self.make_task()
        executor = TaskExecutor()
        executor.executors["provisioning"] = ProvisioningTaskExecutor()
        mcp_success = CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text="Slack access provisioned",
                )
            ],
            isError=False,
        )

        with patch(
            "app.services.task_executors.provisioning.MCPClient.call_tool",
            new=AsyncMock(return_value=mcp_success),
        ) as call_tool:
            result = await executor.execute(session, task)

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.result, "Slack access provisioned")
        self.assertIsNotNone(result.started_at)
        self.assertIsNotNone(result.completed_at)
        call_tool.assert_awaited_once_with(
            tool_name="provision_slack_access",
            arguments={"employee_id": 7},
        )
        session.commit.assert_awaited_once()

    async def test_company_account_includes_job_title_argument(self):
        session = self.make_session()
        session.execute = AsyncMock(
            side_effect=[
                SimpleNamespace(
                    scalar_one=lambda: SimpleNamespace(employee_id=7)
                ),
                SimpleNamespace(
                    scalar_one=lambda: SimpleNamespace(
                        id=7,
                        job_title="Backend Engineer",
                    )
                ),
            ]
        )
        task = self.make_task(task_id="company_account")
        executor = TaskExecutor()
        executor.executors["provisioning"] = ProvisioningTaskExecutor()
        result = CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text="Company account created",
                )
            ],
            isError=False,
        )

        with patch(
            "app.services.task_executors.provisioning.MCPClient.call_tool",
            new=AsyncMock(return_value=result),
        ) as call_tool:
            completed_task = await executor.execute(session, task)

        self.assertEqual(completed_task.status, "completed")
        call_tool.assert_awaited_once_with(
            tool_name="create_company_account",
            arguments={
                "employee_id": 7,
                "job_title": "Backend Engineer",
            },
        )

    async def test_executor_exception_persists_failed_task(self):
        session = self.make_session()
        task = self.make_task()

        class FailingExecutor:
            async def execute(self, session, task):
                raise RuntimeError(
                    "Slack provisioning service unavailable; "
                    "api_key=secret123"
                )

        executor = TaskExecutor()
        executor.executors["provisioning"] = FailingExecutor()

        result = await executor.execute(session, task)

        self.assertEqual(result.status, "failed")
        self.assertIn(
            "Slack provisioning service unavailable",
            result.result,
        )
        self.assertIn("[REDACTED]", result.result)
        self.assertNotIn("secret123", result.result)
        self.assertIsNotNone(result.started_at)
        self.assertIsNone(result.completed_at)
        session.rollback.assert_awaited_once()
        session.commit.assert_awaited_once()

    async def test_mcp_error_result_persists_failed_task(self):
        session = self.make_session()
        session.execute = AsyncMock(
            side_effect=[
                SimpleNamespace(
                    scalar_one=lambda: SimpleNamespace(employee_id=7)
                ),
                SimpleNamespace(
                    scalar_one=lambda: SimpleNamespace(
                        id=7,
                        job_title="Backend Engineer",
                    )
                ),
            ]
        )
        task = self.make_task()
        mcp_error = CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text="Slack provisioning service unavailable",
                )
            ],
            isError=True,
        )
        executor = TaskExecutor()
        executor.executors["provisioning"] = ProvisioningTaskExecutor()

        with patch(
            "app.services.task_executors.provisioning.MCPClient.call_tool",
            new=AsyncMock(return_value=mcp_error),
        ):
            result = await executor.execute(session, task)

        self.assertEqual(result.status, "failed")
        self.assertIn("MCP provisioning failed", result.result)
        self.assertIn("Slack provisioning service unavailable", result.result)
        self.assertIsNone(result.completed_at)
        session.rollback.assert_awaited_once()
        session.commit.assert_awaited_once()

    async def test_approval_waits_then_executes_successfully(self):
        session = self.make_session()
        task = self.make_task(
            requires_approval=True,
            approval_role="manager",
        )

        class SuccessfulExecutor:
            async def execute(self, session, task):
                task.result = "Provisioned after approval"
                return task

        executor = TaskExecutor()
        executor.executors["provisioning"] = SuccessfulExecutor()

        waiting_task = await executor.execute(session, task)
        self.assertEqual(waiting_task.status, "waiting_approval")
        self.assertIn("manager", waiting_task.result)
        self.assertIsNone(waiting_task.started_at)

        waiting_task.status = "approved"
        completed_task = await executor.execute(session, waiting_task)

        self.assertEqual(completed_task.status, "completed")
        self.assertEqual(
            completed_task.result,
            "Provisioned after approval",
        )


class WorkflowFailureTests(unittest.IsolatedAsyncioTestCase):
    def make_status_session(self, workflow_run, tasks):
        first_result = SimpleNamespace(
            scalar_one_or_none=lambda: workflow_run
        )
        second_result = SimpleNamespace(
            scalars=lambda: SimpleNamespace(all=lambda: tasks)
        )
        return SimpleNamespace(
            execute=AsyncMock(side_effect=[first_result, second_result]),
            commit=AsyncMock(),
            refresh=AsyncMock(),
        )

    async def test_failed_task_fails_workflow(self):
        workflow_run = SimpleNamespace(
            status="running",
            started_at=None,
            completed_at=None,
        )
        failed_task = SimpleNamespace(status="failed")
        session = self.make_status_session(workflow_run, [failed_task])
        service = WorkflowExecutionService(workflows_dir="workflows")

        result = await service.update_workflow_run_status(session, 1)

        self.assertEqual(result.status, "failed")
        session.commit.assert_awaited_once()

    async def test_all_completed_tasks_complete_workflow(self):
        workflow_run = SimpleNamespace(
            status="running",
            started_at=None,
            completed_at=None,
        )
        tasks = [SimpleNamespace(status="completed")]
        session = self.make_status_session(workflow_run, tasks)
        service = WorkflowExecutionService(workflows_dir="workflows")

        result = await service.update_workflow_run_status(session, 1)

        self.assertEqual(result.status, "completed")
        self.assertIsNotNone(result.completed_at)

    async def test_orchestrator_stops_after_failed_task(self):
        task = SimpleNamespace(status="pending")
        workflow_run = SimpleNamespace(status="running")

        class TaskService:
            calls = 0

            async def get_ready_tasks(self, session, workflow_run_id):
                self.calls += 1
                return [task]

        class FailingExecutor:
            async def execute(self, session, task):
                task.status = "failed"
                return task

        class WorkflowService:
            async def get_workflow_run(self, session, workflow_run_id):
                return workflow_run

            async def update_workflow_run_status(
                self,
                session,
                workflow_run_id,
            ):
                workflow_run.status = "failed"
                return workflow_run

        task_service = TaskService()
        orchestrator = WorkflowOrchestrator(
            task_service=task_service,
            executor=FailingExecutor(),
            workflow_service=WorkflowService(),
        )

        result, executed_tasks = await orchestrator.execute_workflow(
            session=object(),
            workflow_run_id=1,
        )

        self.assertEqual(result.status, "failed")
        self.assertEqual(task_service.calls, 1)
        self.assertEqual(executed_tasks, [task])


if __name__ == "__main__":
    unittest.main()