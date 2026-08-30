from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


class MCPClient:
    def __init__(self, server_url: str):
        self.server_url = server_url.rstrip("/") + "/mcp"

    async def list_tools(self) -> list[dict[str, Any]]:
        async with streamable_http_client(
            self.server_url
        ) as (
            read_stream,
            write_stream,
            _,
        ):
            async with ClientSession(
                read_stream,
                write_stream,
            ) as session:
                await session.initialize()

                result = await session.list_tools()

                return [
                    {
                        "name": tool.name,
                        "description": tool.description,
                    }
                    for tool in result.tools
                ]

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> Any:
        async with streamable_http_client(
            self.server_url
        ) as (
            read_stream,
            write_stream,
            _,
        ):
            async with ClientSession(
                read_stream,
                write_stream,
            ) as session:
                await session.initialize()

                result = await session.call_tool(
                    tool_name,
                    arguments=arguments,
                )

                return result