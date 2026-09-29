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

@mcp.tool()
def get_recent_logs(service: str) -> list:
    """Get recent application logs for a service."""

    return [
        {
            "timestamp": "2026-09-28T10:15:21",
            "level": "ERROR",
            "message": "Connection timeout to payment provider"
        },
        {
            "timestamp": "2026-09-28T10:15:24",
            "level": "ERROR",
            "message": "Payment provider request failed"
        },
        {
            "timestamp": "2026-09-28T10:15:27",
            "level": "ERROR",
            "message": "Retry limit exceeded"
        }
    ]


@mcp.tool()
def get_metrics(service: str) -> dict:
    """Get current monitoring metrics for a service."""

    return {
        "service": service,
        "errorRate": 98.4,
        "latencyMs": 4200,
        "requestsPerMinute": 120
    }

# We're deliberately simulating the restart. The portfolio project shouldn't actually restart a machine/container.
@mcp.tool()
def restart_service(service: str) -> dict:
    """Simulate restarting a service."""
    return {
        "service": service,
        "action": "restart",
        "status": "simulated",
        "message": f"Simulated restart of {service}"
    }

if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=8001
    )


    #                  MCP Server
    #                      │
    #           ┌──────────┴──────────┐
    #           │                     │
    #        AI Agent           Remediation Executor
    #           │                     │
    #    health/logs/metrics      restart_service


    # HTTP over stdio isn't about Python vs. Java.
    #
    # It's about:
    # Do we want MCP to be an independently running service that multiple clients can connect to?
    # For our architecture, yes.