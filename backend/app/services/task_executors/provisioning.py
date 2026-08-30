from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.employee import Employee
from app.models.workflow import WorkflowRun, WorkflowTask
from app.services.mcp_client import MCPClient


class ProvisioningTaskExecutor:
    async def execute(
        self,
        session: AsyncSession,
        task: WorkflowTask,
    ) -> WorkflowTask:
        # Get the employee associated with this workflow.
        result = await session.execute(
            select(WorkflowRun).where(
                WorkflowRun.id == task.workflow_run_id
            )
        )

        workflow_run = result.scalar_one()

        result = await session.execute(
            select(Employee).where(
                Employee.id == workflow_run.employee_id
            )
        )

        employee = result.scalar_one()

        # Create the generic MCP client.
        client = MCPClient(
            settings.PROVISIONING_MCP_URL
        )

        # Map our workflow task IDs to MCP tool names.
        tool_name = self._get_tool_name(task.task_id)

        arguments = {
            "employee_id": employee.id,
        }

        # The company-account MCP tool also needs the job title.
        if task.task_id == "company_account":
            arguments["job_title"] = employee.job_title

        # Call the actual MCP tool.
        result = await client.call_tool(
            tool_name=tool_name,
            arguments=arguments,
        )

        task.result = self._extract_result(result)

        return task

    def _get_tool_name(
        self,
        task_id: str,
    ) -> str:
        tool_mapping = {
            "company_account": "create_company_account",
            "slack_access": "provision_slack_access",
            "github_access": "provision_github_access",
            "vpn_access": "provision_vpn_access",
            "backend_environment": (
                "provision_development_environment"
            ),
        }

        tool_name = tool_mapping.get(task_id)

        if tool_name is None:
            raise ValueError(
                f"No provisioning MCP tool configured "
                f"for task '{task_id}'."
            )

        return tool_name

    def _extract_result(self, result) -> str:
        if hasattr(result, "content"):
            parts = []

            for item in result.content:
                if hasattr(item, "text"):
                    parts.append(item.text)

            if parts:
                return "\n".join(parts)

        return str(result)
