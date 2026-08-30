import uvicorn

from mcp_servers.provisioning.server import mcp


if __name__ == "__main__":
    uvicorn.run(
        mcp.streamable_http_app(),
        host="127.0.0.1",
        port=8001,
    )