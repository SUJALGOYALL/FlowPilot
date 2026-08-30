from mcp.server.fastmcp import FastMCP


mcp = FastMCP(
    "FlowPilot Provisioning",
    stateless_http=True,
    json_response=True,
)


@mcp.tool()
async def create_company_account(
    employee_id: int,
    job_title: str,
) -> str:
    """Create a company account for an employee."""
    return (
        f"Company account created for employee {employee_id} "
        f"with job title '{job_title}'."
    )


@mcp.tool()
async def provision_slack_access(
    employee_id: int,
) -> str:
    """Provision Slack access for an employee."""
    return (
        f"Slack access provisioned for employee {employee_id}."
    )


@mcp.tool()
async def provision_github_access(
    employee_id: int,
) -> str:
    """Provision GitHub access for an employee."""
    return (
        f"GitHub access provisioned for employee {employee_id}."
    )


@mcp.tool()
async def provision_vpn_access(
    employee_id: int,
) -> str:
    """Provision VPN access for an employee."""
    return (
        f"VPN access provisioned for employee {employee_id}."
    )


@mcp.tool()
async def provision_development_environment(
    employee_id: int,
) -> str:
    """Provision the development environment for an employee."""
    return (
        f"Development environment provisioned for employee "
        f"{employee_id}."
    )


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
    )