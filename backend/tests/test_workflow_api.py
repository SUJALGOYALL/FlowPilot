from datetime import datetime, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.api.routes import workflows as workflow_routes
from app.db.database import get_db
from app.main import app


JOB_TITLES = (
    "Backend Engineer",
    "Frontend Engineer",
    "AI/ML Engineer",
    "DevOps Engineer",
)


def make_task(
    task_id="vpn_access",
    *,
    task_pk=42,
    status="waiting_approval",
    requires_approval=True,
    result="Waiting for approval from manager.",
):
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=task_pk,
        workflow_run_id=17,
        task_id=task_id,
        name=f"Provision {task_id}",
        task_type="provisioning",
        status=status,
        requires_approval=requires_approval,
        approval_role="manager" if requires_approval else None,
        depends_on=["security_training"],
        result=result,
        started_at=now if status in {"running", "completed", "failed"} else None,
        completed_at=now if status == "completed" else None,
        created_at=now,
    )


def make_run(status="waiting_approval", tasks=None):
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=17,
        workflow_definition_id=5,
        employee_id=9,
        status=status,
        started_at=now,
        completed_at=now if status == "completed" else None,
        created_at=now,
        tasks=list(tasks or []),
    )


class WorkflowApiTests(unittest.TestCase):
    def setUp(self):
        self.role = "hr"
        self.employee = SimpleNamespace(id=9, job_title="Backend Engineer")
        self.run = make_run(tasks=[make_task()])
        self.db = SimpleNamespace(
            execute=AsyncMock(),
            refresh=AsyncMock(),
        )
        self.workflow_service = SimpleNamespace(
            create_workflow_run=AsyncMock(return_value=self.run),
        )
        self.orchestrator = SimpleNamespace(
            execute_workflow=AsyncMock(return_value=(self.run, [])),
        )
        self.approval_service = SimpleNamespace(
            approve=AsyncMock(),
        )

        async def override_db():
            yield self.db

        async def override_current_user():
            return SimpleNamespace(role=self.role)

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_user] = override_current_user
        app.dependency_overrides[
            workflow_routes.get_workflow_execution_service
        ] = lambda: self.workflow_service
        app.dependency_overrides[
            workflow_routes.get_workflow_orchestrator
        ] = lambda: self.orchestrator
        app.dependency_overrides[
            workflow_routes.get_approval_service
        ] = lambda: self.approval_service
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()

    def execute_result(self, *, one_or_none=None, one=None):
        return SimpleNamespace(
            scalar_one_or_none=lambda: one_or_none,
            scalar_one=lambda: one,
        )

    def test_start_workflows_for_each_supported_job_title(self):
        for job_title in JOB_TITLES:
            with self.subTest(job_title=job_title):
                self.employee.job_title = job_title
                self.run.status = "waiting_approval"
                self.db.execute = AsyncMock(
                    side_effect=[
                        self.execute_result(one_or_none=self.employee),
                        self.execute_result(one=self.run),
                    ]
                )
                self.workflow_service.create_workflow_run = AsyncMock(
                    return_value=self.run
                )
                self.orchestrator.execute_workflow = AsyncMock(
                    return_value=(self.run, [])
                )

                response = self.client.post(
                    "/api/v1/workflows/runs",
                    json={"employee_id": 9, "job_title": job_title},
                )

                self.assertEqual(response.status_code, 201)
                self.assertEqual(response.json()["status"], "waiting_approval")
                self.workflow_service.create_workflow_run.assert_awaited_once_with(
                    session=self.db,
                    employee_id=9,
                    job_title=job_title,
                )
                self.orchestrator.execute_workflow.assert_awaited_once_with(
                    session=self.db,
                    workflow_run_id=17,
                )
                self.workflow_service.create_workflow_run.reset_mock()
                self.orchestrator.execute_workflow.reset_mock()

    def test_start_returns_failed_state_from_execution(self):
        failed_task = make_task(
            status="failed",
            result="MCP provisioning failed: service unavailable",
        )
        self.run.status = "failed"
        self.run.tasks = [failed_task]
        self.db.execute = AsyncMock(
            side_effect=[
                self.execute_result(one_or_none=self.employee),
                self.execute_result(one=self.run),
            ]
        )
        self.orchestrator.execute_workflow = AsyncMock(
            return_value=(self.run, [failed_task])
        )

        response = self.client.post(
            "/api/v1/workflows/runs",
            json={
                "employee_id": 9,
                "job_title": "Backend Engineer",
            },
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "failed")
        self.assertEqual(response.json()["tasks"][0]["status"], "failed")
        self.assertIn(
            "service unavailable",
            response.json()["tasks"][0]["result"],
        )

    def test_start_rejects_missing_employee_and_job_title_mismatch(self):
        self.db.execute = AsyncMock(
            return_value=self.execute_result(one_or_none=None)
        )
        response = self.client.post(
            "/api/v1/workflows/runs",
            json={"employee_id": 999, "job_title": "Backend Engineer"},
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Employee not found.")

        self.db.execute = AsyncMock(
            return_value=self.execute_result(one_or_none=self.employee)
        )
        response = self.client.post(
            "/api/v1/workflows/runs",
            json={"employee_id": 9, "job_title": "Frontend Engineer"},
        )
        self.assertEqual(response.status_code, 400)
        self.workflow_service.create_workflow_run.assert_not_awaited()

    def test_start_maps_unknown_workflow_to_not_found(self):
        self.employee.job_title = "Unconfigured Engineer"
        self.db.execute = AsyncMock(
            return_value=self.execute_result(one_or_none=self.employee)
        )
        self.workflow_service.create_workflow_run = AsyncMock(
            side_effect=ValueError("No onboarding workflow configured")
        )

        response = self.client.post(
            "/api/v1/workflows/runs",
            json={
                "employee_id": 9,
                "job_title": "Unconfigured Engineer",
            },
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json()["detail"],
            "No onboarding workflow configured",
        )
        self.orchestrator.execute_workflow.assert_not_awaited()

    def test_get_run_includes_task_state_results_and_timestamps(self):
        completed_task = make_task(
            status="completed",
            result="VPN access provisioned for employee 9.",
        )
        self.run.status = "completed"
        self.run.tasks = [completed_task]
        self.db.execute = AsyncMock(
            side_effect=[
                self.execute_result(one_or_none=self.run),
                self.execute_result(one_or_none=self.run),
            ]
        )

        response = self.client.get("/api/v1/workflows/runs/17")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "completed")
        self.assertEqual(body["tasks"][0]["status"], "completed")
        self.assertEqual(
            body["tasks"][0]["result"],
            "VPN access provisioned for employee 9.",
        )
        self.assertIsNotNone(body["tasks"][0]["completed_at"])

    def test_get_task_exposes_waiting_approval_state(self):
        task = make_task()
        self.db.execute = AsyncMock(
            return_value=self.execute_result(one_or_none=task)
        )

        response = self.client.get("/api/v1/workflows/tasks/42")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "waiting_approval")
        self.assertTrue(response.json()["requires_approval"])
        self.assertEqual(response.json()["approval_role"], "manager")

    def test_get_unknown_run_and_task_return_not_found(self):
        self.db.execute = AsyncMock(
            return_value=self.execute_result(one_or_none=None)
        )
        run_response = self.client.get("/api/v1/workflows/runs/999")
        task_response = self.client.get("/api/v1/workflows/tasks/999")

        self.assertEqual(run_response.status_code, 404)
        self.assertEqual(task_response.status_code, 404)

    def test_approval_uses_service_resumes_and_returns_final_task_state(self):
        task = make_task()
        self.db.execute = AsyncMock(
            return_value=self.execute_result(one_or_none=task)
        )

        async def approve(*, session, task, approver):
            task.status = "approved"
            task.result = "Task approved."
            return task

        async def resume(*, session, workflow_run_id):
            task.status = "completed"
            task.result = "VPN access provisioned for employee 9."
            return self.run, [task]

        self.approval_service.approve = AsyncMock(side_effect=approve)
        self.orchestrator.execute_workflow = AsyncMock(side_effect=resume)

        response = self.client.post("/api/v1/workflows/tasks/42/approve")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "completed")
        self.assertEqual(
            response.json()["result"],
            "VPN access provisioned for employee 9.",
        )
        self.approval_service.approve.assert_awaited_once_with(
            session=self.db,
            task=task,
            approver=SimpleNamespace(role="hr"),
        )
        self.orchestrator.execute_workflow.assert_awaited_once_with(
            session=self.db,
            workflow_run_id=17,
        )
        self.db.refresh.assert_awaited_once_with(task)

    def test_approval_rejects_non_approval_task_and_invalid_state(self):
        non_approval_task = make_task(requires_approval=False)
        self.db.execute = AsyncMock(
            return_value=self.execute_result(one_or_none=non_approval_task)
        )
        self.approval_service.approve = AsyncMock(
            side_effect=ValueError(
                "Task 'vpn_access' does not require approval."
            )
        )
        response = self.client.post("/api/v1/workflows/tasks/42/approve")
        self.assertEqual(response.status_code, 409)
        self.approval_service.approve.assert_awaited_once()

        waiting_task = make_task(status="completed")
        self.db.execute = AsyncMock(
            return_value=self.execute_result(one_or_none=waiting_task)
        )
        self.approval_service.approve = AsyncMock(
            side_effect=ValueError("cannot be approved from status 'completed'")
        )
        response = self.client.post("/api/v1/workflows/tasks/42/approve")
        self.assertEqual(response.status_code, 409)
        self.assertIn("cannot be approved", response.json()["detail"])
        self.orchestrator.execute_workflow.assert_not_awaited()

    def test_approval_requires_authorized_role(self):
        self.role = "employee"

        response = self.client.post("/api/v1/workflows/tasks/42/approve")

        self.assertEqual(response.status_code, 403)
        self.approval_service.approve.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
