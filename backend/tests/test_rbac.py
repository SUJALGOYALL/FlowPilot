from datetime import datetime, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.api.routes import auth as auth_routes
from app.api.routes import workflows as workflow_routes
from app.core.config import settings
from app.core.security import create_access_token
from app.db.database import get_db
from app.main import app
from app.services.approval_service import ApprovalService


class FakeResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value

    def scalar_one(self):
        return self.value

    def scalar(self):
        return self.value


def make_task(
    *,
    task_id="vpn_access",
    status="waiting_approval",
    requires_approval=True,
    approval_role="manager",
    workflow_run_id=17,
):
    return SimpleNamespace(
        id=42,
        workflow_run_id=workflow_run_id,
        task_id=task_id,
        status=status,
        requires_approval=requires_approval,
        approval_role=approval_role,
        result="Waiting for approval.",
    )


class RBACApiTests(unittest.TestCase):
    def setUp(self):
        self.previous_overrides = app.dependency_overrides.copy()
        self.user = SimpleNamespace(
            id=101,
            role="employee",
            is_active=True,
            is_verified=True,
            email="user@example.test",
            full_name="Test User",
        )
        self.db = SimpleNamespace(
            execute=AsyncMock(),
            add=Mock(),
            flush=AsyncMock(),
            commit=AsyncMock(),
            refresh=AsyncMock(),
        )

        async def override_db():
            yield self.db

        async def override_current_user():
            return self.user

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_user] = override_current_user
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)

    def test_authenticated_employee_can_view_own_account(self):
        response = self.client.get("/api/v1/auth/me")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], self.user.id)
        self.assertEqual(response.json()["role"], "employee")

    def test_employee_is_denied_employee_creation_and_workflow_start(self):
        employee_response = self.client.post(
            "/api/v1/employees",
            json={
                "user_id": 202,
                "employee_id": "EMP-NEW",
                "department": "Engineering",
                "job_title": "Backend Engineer",
                "joining_date": "2026-10-01",
            },
        )
        workflow_response = self.client.post(
            "/api/v1/workflows/runs",
            json={"employee_id": 9, "job_title": "Backend Engineer"},
        )

        self.assertEqual(employee_response.status_code, 403)
        self.assertEqual(workflow_response.status_code, 403)
        self.db.execute.assert_not_awaited()

    def test_manager_is_denied_hr_workflow_operations(self):
        self.user.role = "manager"

        create_response = self.client.post(
            "/api/v1/workflows/runs",
            json={"employee_id": 9, "job_title": "Backend Engineer"},
        )
        execute_response = self.client.post(
            "/api/v1/workflows/runs/17/execute"
        )

        self.assertEqual(create_response.status_code, 403)
        self.assertEqual(execute_response.status_code, 403)
        self.db.execute.assert_not_awaited()

    def test_hr_and_admin_can_create_employee_profiles(self):
        for role in ("hr", "admin"):
            with self.subTest(role=role):
                self.user.role = role
                self.db.execute = AsyncMock(
                    side_effect=[
                        FakeResult(SimpleNamespace(id=202)),
                        FakeResult(None),
                        FakeResult(None),
                    ]
                )

                async def refresh(employee):
                    employee.id = 303
                    employee.created_at = datetime.now(timezone.utc)

                self.db.refresh = AsyncMock(side_effect=refresh)
                response = self.client.post(
                    "/api/v1/employees",
                    json={
                        "user_id": 202,
                        "employee_id": f"EMP-{role.upper()}",
                        "department": "Engineering",
                        "job_title": "Backend Engineer",
                        "joining_date": "2026-10-01",
                    },
                )

                self.assertEqual(response.status_code, 201)
                self.assertEqual(response.json()["user_id"], 202)
                self.assertEqual(response.json()["id"], 303)

    def test_admin_accesses_hr_admin_privileged_workflow_operation(self):
        self.user.role = "admin"
        employee = SimpleNamespace(id=9, job_title="Backend Engineer")
        workflow_run = SimpleNamespace(
            id=17,
            status="waiting_approval",
            workflow_definition_id=5,
            employee_id=9,
            started_at=None,
            completed_at=None,
            created_at=datetime.now(timezone.utc),
            tasks=[],
        )
        self.db.execute = AsyncMock(
            side_effect=[FakeResult(employee), FakeResult(workflow_run)]
        )
        workflow_service = SimpleNamespace(
            create_workflow_run=AsyncMock(return_value=workflow_run)
        )
        orchestrator = SimpleNamespace(
            execute_workflow=AsyncMock(return_value=(workflow_run, []))
        )
        app.dependency_overrides[
            workflow_routes.get_workflow_execution_service
        ] = lambda: workflow_service
        app.dependency_overrides[
            workflow_routes.get_workflow_orchestrator
        ] = lambda: orchestrator

        response = self.client.post(
            "/api/v1/workflows/runs",
            json={"employee_id": 9, "job_title": "Backend Engineer"},
        )

        self.assertEqual(response.status_code, 201)
        orchestrator.execute_workflow.assert_awaited_once()

    def test_manager_can_read_direct_report_run(self):
        self.user.role = "manager"
        employee = SimpleNamespace(id=11, user_id=303, manager_id=202)
        manager_profile_id = 202
        workflow_run = SimpleNamespace(
            id=17,
            employee_id=11,
            status="running",
            workflow_definition_id=5,
            started_at=None,
            completed_at=None,
            created_at=datetime.now(timezone.utc),
            tasks=[],
        )
        self.db.execute = AsyncMock(
            side_effect=[
                FakeResult(workflow_run),
                FakeResult(employee),
                FakeResult(manager_profile_id),
                FakeResult(workflow_run),
            ]
        )

        response = self.client.get("/api/v1/workflows/runs/17")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["employee_id"], 11)

    def test_manager_cannot_read_unrelated_run_or_task(self):
        self.user.role = "manager"
        workflow_run = SimpleNamespace(
            id=17,
            employee_id=11,
            status="running",
        )
        unrelated_employee = SimpleNamespace(
            id=11,
            user_id=404,
            manager_id=999,
        )
        task = make_task()

        self.db.execute = AsyncMock(
            side_effect=[
                FakeResult(workflow_run),
                FakeResult(unrelated_employee),
                FakeResult(202),
            ]
        )
        run_response = self.client.get("/api/v1/workflows/runs/17")
        self.assertEqual(run_response.status_code, 404)

        self.db.execute = AsyncMock(
            side_effect=[
                FakeResult(task),
                FakeResult(11),
                FakeResult(unrelated_employee),
                FakeResult(202),
            ]
        )
        task_response = self.client.get("/api/v1/workflows/tasks/42")
        self.assertEqual(task_response.status_code, 404)

    def test_manager_without_employee_profile_cannot_read_unassigned_run(self):
        self.user.role = "manager"
        workflow_run = SimpleNamespace(
            id=17,
            employee_id=11,
            status="running",
        )
        unassigned_employee = SimpleNamespace(
            id=11,
            user_id=404,
            manager_id=None,
        )
        self.db.execute = AsyncMock(
            side_effect=[
                FakeResult(workflow_run),
                FakeResult(unassigned_employee),
                FakeResult(None),
            ]
        )

        response = self.client.get("/api/v1/workflows/runs/17")

        self.assertEqual(response.status_code, 404)

    def test_hr_and_admin_can_read_any_run(self):
        run = SimpleNamespace(
            id=17,
            employee_id=808,
            status="running",
            workflow_definition_id=5,
            started_at=None,
            completed_at=None,
            created_at=datetime.now(timezone.utc),
            tasks=[],
        )
        for role in ("hr", "admin"):
            with self.subTest(role=role):
                self.user.role = role
                self.db.execute = AsyncMock(
                    side_effect=[FakeResult(run), FakeResult(run)]
                )
                response = self.client.get("/api/v1/workflows/runs/17")
                self.assertEqual(response.status_code, 200)

    def test_employee_cannot_approve_task(self):
        response = self.client.post("/api/v1/workflows/tasks/42/approve")

        self.assertEqual(response.status_code, 403)
        self.db.execute.assert_not_awaited()

    def test_manager_approval_endpoint_enforces_required_role_and_scope(self):
        self.user.role = "manager"
        task = make_task(approval_role="hr")
        self.db.execute = AsyncMock(return_value=FakeResult(task))
        app.dependency_overrides[
            workflow_routes.get_approval_service
        ] = ApprovalService

        response = self.client.post("/api/v1/workflows/tasks/42/approve")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()["detail"],
            "You do not have permission to approve this task.",
        )

        task.approval_role = "manager"
        employee = SimpleNamespace(id=11, manager_id=999)
        self.db.execute = AsyncMock(
            side_effect=[FakeResult(task), FakeResult(employee), FakeResult(202)]
        )
        response = self.client.post("/api/v1/workflows/tasks/42/approve")
        self.assertEqual(response.status_code, 403)

    def test_hr_admin_override_uses_existing_approval_service(self):
        for role in ("hr", "admin"):
            with self.subTest(role=role):
                self.user.role = role
                task = make_task(approval_role="manager")
                self.db.execute = AsyncMock(return_value=FakeResult(task))
                app.dependency_overrides[
                    workflow_routes.get_approval_service
                ] = ApprovalService
                app.dependency_overrides[
                    workflow_routes.get_workflow_orchestrator
                ] = lambda: SimpleNamespace(
                    execute_workflow=AsyncMock(
                        return_value=(SimpleNamespace(id=17), [task])
                    )
                )

                response = self.client.post(
                    "/api/v1/workflows/tasks/42/approve"
                )

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["status"], "approved")

    def test_approval_service_requires_approval_and_waiting_state(self):
        service = ApprovalService()
        task = make_task(requires_approval=False)

        with self.assertRaisesRegex(ValueError, "does not require approval"):
            self._run(service.approve(self.db, task, approver=self.user))

        task.requires_approval = True
        task.status = "completed"
        with self.assertRaisesRegex(ValueError, "cannot be approved"):
            self._run(service.approve(self.db, task, approver=self.user))

    def test_approval_service_checks_role_and_direct_report(self):
        service = ApprovalService()
        task = make_task(approval_role="hr")
        manager = SimpleNamespace(id=303, role="manager")

        with self.assertRaises(PermissionError):
            self._run(service.approve(self.db, task, approver=manager))
        self.db.execute.assert_not_awaited()

        task.approval_role = "manager"
        employee = SimpleNamespace(id=11, manager_id=202)
        self.db.execute = AsyncMock(
            side_effect=[FakeResult(employee), FakeResult(202)]
        )
        task.status = "waiting_approval"
        result = self._run(
            service.approve(self.db, task, approver=manager)
        )

        self.assertIs(result, task)
        self.assertEqual(task.status, "approved")
        self.db.commit.assert_awaited()

    def test_missing_and_invalid_authentication_return_401(self):
        app.dependency_overrides.pop(get_current_user, None)
        self.db.execute = AsyncMock(
            return_value=FakeResult(self.user)
        )

        missing = self.client.get("/api/v1/auth/me")
        invalid = self.client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid-token"},
        )

        self.assertEqual(missing.status_code, 401)
        self.assertEqual(invalid.status_code, 401)

    def test_jwt_role_claim_cannot_escalate_database_employee_role(self):
        app.dependency_overrides.pop(get_current_user, None)
        database_user = SimpleNamespace(
            id=101,
            role="employee",
            is_active=True,
            is_verified=True,
        )
        self.db.execute = AsyncMock(
            return_value=FakeResult(database_user)
        )
        with patch.object(
            settings,
            "JWT_SECRET_KEY",
            "rbac-unit-test-secret-with-at-least-32-bytes",
        ):
            token = create_access_token(user_id=101, role="admin")
            response = self.client.post(
                "/api/v1/workflows/runs",
                headers={"Authorization": f"Bearer {token}"},
                json={"employee_id": 9, "job_title": "Backend Engineer"},
            )

        self.assertEqual(response.status_code, 403)

    def test_registration_cannot_choose_a_privileged_role(self):
        created_users = []
        self.db.execute = AsyncMock(return_value=FakeResult(None))
        self.db.add = Mock(side_effect=created_users.append)

        with (
            patch.object(auth_routes, "store_otp", new=AsyncMock()),
            patch.object(auth_routes, "send_email", new=AsyncMock()),
        ):
            response = self.client.post(
                "/api/v1/auth/register",
                json={
                    "email": "new-user@example.com",
                    "full_name": "New User",
                    "password": "secure-test-password",
                    "role": "admin",
                },
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(created_users[0].role, "employee")

    @staticmethod
    def _run(awaitable):
        import asyncio

        return asyncio.run(awaitable)


if __name__ == "__main__":
    unittest.main()
