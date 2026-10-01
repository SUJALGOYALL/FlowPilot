from pathlib import Path
import unittest

from app.services.task_executor import TaskExecutor
from app.services.task_executors.provisioning import (
    ProvisioningTaskExecutor,
)
from app.services.workflow_resolver import WorkflowResolver
from mcp_servers.provisioning.server import mcp


WORKFLOWS_DIR = Path(__file__).resolve().parents[1] / "workflows"

EXPECTED_MAPPINGS = {
    "company_account": "create_company_account",
    "slack_access": "provision_slack_access",
    "github_access": "provision_github_access",
    "vpn_access": "provision_vpn_access",
    "backend_environment": "provision_development_environment",
    "frontend_environment": "provision_frontend_environment",
    "package_registry": "provision_package_registry",
    "ml_environment": "provision_ml_environment",
    "gpu_access": "provision_gpu_access",
    "model_registry": "provision_model_registry",
    "cloud_environment": "provision_cloud_environment",
    "infrastructure_access": "provision_infrastructure_access",
    "deployment_access": "provision_deployment_access",
}

WORKFLOW_TASKS = {
    "Backend Engineer": {
        "company_account": "create_company_account",
        "slack_access": "provision_slack_access",
        "github_access": "provision_github_access",
        "vpn_access": "provision_vpn_access",
        "backend_environment": "provision_development_environment",
    },
    "Frontend Engineer": {
        "company_account": "create_company_account",
        "slack_access": "provision_slack_access",
        "github_access": "provision_github_access",
        "vpn_access": "provision_vpn_access",
        "frontend_environment": "provision_frontend_environment",
        "package_registry": "provision_package_registry",
    },
    "AI/ML Engineer": {
        "company_account": "create_company_account",
        "slack_access": "provision_slack_access",
        "github_access": "provision_github_access",
        "vpn_access": "provision_vpn_access",
        "ml_environment": "provision_ml_environment",
        "gpu_access": "provision_gpu_access",
        "model_registry": "provision_model_registry",
    },
    "DevOps Engineer": {
        "company_account": "create_company_account",
        "slack_access": "provision_slack_access",
        "github_access": "provision_github_access",
        "vpn_access": "provision_vpn_access",
        "cloud_environment": "provision_cloud_environment",
        "infrastructure_access": "provision_infrastructure_access",
        "deployment_access": "provision_deployment_access",
    },
}

EXPECTED_APPROVALS = {
    "Backend Engineer": {"vpn_access"},
    "Frontend Engineer": {"vpn_access"},
    "AI/ML Engineer": {"vpn_access", "gpu_access", "model_registry"},
    "DevOps Engineer": {
        "vpn_access",
        "cloud_environment",
        "infrastructure_access",
        "deployment_access",
    },
}


class ProvisioningWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.resolver = WorkflowResolver(WORKFLOWS_DIR)
        self.provisioning_executor = ProvisioningTaskExecutor()
        self.registered_tools = {
            tool.name for tool in mcp._tool_manager.list_tools()
        }

    def test_backend_provisioning_mapping(self):
        self.assert_workflow_mappings("Backend Engineer")

    def test_frontend_provisioning_mapping(self):
        self.assert_workflow_mappings("Frontend Engineer")

    def test_ai_ml_provisioning_mapping(self):
        self.assert_workflow_mappings("AI/ML Engineer")

    def test_devops_provisioning_mapping(self):
        self.assert_workflow_mappings("DevOps Engineer")

    def test_every_mapped_tool_is_registered_by_server(self):
        mapped_tools = {
            self.provisioning_executor._get_tool_name(task_id)
            for task_id in self.provisioning_executor.TOOL_MAPPING
        }

        self.assertEqual(mapped_tools, set(EXPECTED_MAPPINGS.values()))
        self.assertTrue(mapped_tools.issubset(self.registered_tools))

    def test_explicit_mapping_matches_workflow_inventory(self):
        self.assertEqual(
            self.provisioning_executor.TOOL_MAPPING,
            EXPECTED_MAPPINGS,
        )

    def test_every_workflow_definition_is_valid_and_fully_mapped(self):
        task_executor = TaskExecutor()

        for job_title, expected_tasks in WORKFLOW_TASKS.items():
            with self.subTest(workflow=job_title):
                workflow = self.resolver.resolve(job_title)
                task_ids = {task.id for task in workflow.tasks}
                tasks_by_id = {task.id: task for task in workflow.tasks}
                provisioning_ids = {
                    task.id
                    for task in workflow.tasks
                    if task.type == "provisioning"
                }

                self.assertEqual(provisioning_ids, set(expected_tasks))
                self.assertEqual(
                    {
                        task_id: self.provisioning_executor._get_tool_name(
                            task_id
                        )
                        for task_id in provisioning_ids
                    },
                    expected_tasks,
                )

                for task in workflow.tasks:
                    self.assertIn(task.type, task_executor.executors)
                    self.assertTrue(set(task.depends_on).issubset(task_ids))

                self.assertEqual(
                    {
                        task.id
                        for task in workflow.tasks
                        if task.requires_approval
                    },
                    EXPECTED_APPROVALS[job_title],
                )

                self.assertTrue(
                    {
                        expected_tasks[task_id]
                        for task_id in provisioning_ids
                    }.issubset(self.registered_tools)
                )

                for task_id in EXPECTED_APPROVALS[job_title]:
                    self.assertTrue(tasks_by_id[task_id].approval_role)

    def test_unknown_task_id_has_clear_error(self):
        with self.assertRaisesRegex(
            ValueError,
            "No provisioning MCP tool configured for task 'unknown_task'",
        ):
            self.provisioning_executor._get_tool_name("unknown_task")

    def assert_workflow_mappings(self, job_title):
        workflow = self.resolver.resolve(job_title)
        actual_mappings = {
            task.id: self.provisioning_executor._get_tool_name(task.id)
            for task in workflow.tasks
            if task.type == "provisioning"
        }

        self.assertEqual(actual_mappings, WORKFLOW_TASKS[job_title])


if __name__ == "__main__":
    unittest.main()