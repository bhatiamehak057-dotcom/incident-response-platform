from mcp.server import MCPServer

mcp = MCPServer("Incident Response Tools")

# The official SDK uses @mcp.tool() to expose a Python function as an MCP tool.
# The function's type hints and docstring are used to describe the tool to MCP clients.
# Make this Python function available as a tool that an MCP client can discover and call.
@mcp.tool()
def get_service_health(service: str) -> dict:
    """Get the current health status of a service."""

    return {
        "service": service,
        "status": "DOWN",
        "message": "Service is experiencing connectivity issues"
    }