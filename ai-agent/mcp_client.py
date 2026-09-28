import asyncio
import json

from mcp import Client, StdioServerParameters

# The server_params tell the client:
# "Here's the program you should launch when you need to talk to the MCP server."
# The SDK then starts that process and communicates with it through stdin/stdout. That's the standard stdio transport
server_params = StdioServerParameters(
    command="/Users/mehakbhatia/IdeaProjects/incident-response-platform/mcp-server/.venv/bin/mcp",
    args=[
        "run",
        "/Users/mehakbhatia/IdeaProjects/incident-response-platform/mcp-server/server.py"
    ],
)

# MCP communication is asynchronous, so we're using Python's async/await model.
# await means:
# "Wait for this operation to finish without blocking the entire async application."
async def get_service_health(service: str):
    async with Client(server_params) as client:
        result = await client.call_tool(
            "get_service_health",
            {"service": service}
        )

        if result.is_error:
            raise RuntimeError(result.content)

        # print("MCP result:", result)
        # print("Content:", result.content)
        # print("Structured content:", result.structured_content)

        return json.loads(result.content[0].text)


# temp code for testing
if __name__ == "__main__":
    result = asyncio.run(
        get_service_health("payment-service")
    )

    print(result)