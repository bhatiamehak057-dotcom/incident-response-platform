import os
# We need this because the API key is stored as an environment variable, rather than putting the secret directly into our source code.

import json
import asyncio

from langgraph.graph import StateGraph, START, END
from typing import TypedDict
from mcp import Client, StdioServerParameters

# importing anthropic sdk, This gives our Python application access to Anthropic's API.
from anthropic import Anthropic

# Node → a step in the workflow
# State → information passed between steps
# Edge → determines what happens next
# Tool → something the agent can actually call
# MCP → standardized way of exposing those tools

# A node is simply a function that does one piece of work.
# A graph connects those functions together.


# The state is the information that travels through the graph.
class IncidentState(TypedDict):
    incident: dict
    analysis: dict
    investigation: dict

# creates an Anthropic client.
# Think of client as our connection/interface to Claude.
# The Anthropic object gives your Python code methods for communicating with Claude
client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

server_params = StdioServerParameters(
    command="/Users/mehakbhatia/IdeaProjects/incident-response-platform/mcp-server/.venv/bin/mcp",
    args=[
        "run",
        "/Users/mehakbhatia/IdeaProjects/incident-response-platform/mcp-server/server.py"
    ],
)

# This is a LangGraph node. - It's just a Python function.
# The node:
# Gets the incident from the graph state.
# Builds the Claude prompt.
# Calls Claude.
# Parses the response.
# Returns the analysis back into the graph state.
def analyze_incident(state: IncidentState):
    incident = state["incident"]

    # This is Python f-string syntax.
    # The f means Python will substitute the values from the dictionary.
    # f-strings are useful for your AI project.
    # because we're dynamically constructing a prompt from the incident data
    # A single { means "evaluate Python code," so {{ tells Python to output a literal {
    # Eventually, we'll make the Python service actually parse and validate that JSON rather than trusting Claude's output.
    prompt = f"""
Analyze this production incident:

Service: {incident["service"]}
Severity: {incident["severity"]}
Error: {incident["error"]}

Return your analysis as JSON with exactly these fields:

{{
  "rootCause": "string",
  "impact": "string",
  "recommendedActions": ["string", "string", "string"]
}}
"""

    # "Send this message to Claude and give me the response."
    # Tells Anthropic which Claude model should process the request.
    # max tok = Limits how much Claude can generate. - keeping it small as we're just doing incident analysis
    # messages = the conversation we're sending to Claude.
    # The role is "user" because we're giving Claude a user-style request.
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    # extracting claude's response and storing it in analysis_text
    analysis_text = response.content[0].text

    analysis_text = (
        analysis_text
        .replace("```json", "")
        .replace("```", "")
        .strip()
    )

    # making analysis a python dict
    analysis = json.loads(analysis_text)

    print("Claude analysis:", analysis)

    return {
        "analysis": analysis
    }


def investigate_incident(state: IncidentState):
    incident = state["incident"]

    async def call_mcp():
        async with Client(server_params) as client:
            result = await client.call_tool(
                "get_service_health",
                {"service": incident["service"]}
            )

            if result.is_error:
                raise RuntimeError(result.content)

            return json.loads(result.content[0].text)

    investigation = asyncio.run(call_mcp())

    print("Investigation:", investigation)

    return {
        "investigation": investigation
    }


# Create a graph whose state follows IncidentState
graph_builder = StateGraph(IncidentState)

graph_builder.add_node("analyze", analyze_incident)
graph_builder.add_node("investigate", investigate_incident)

graph_builder.add_edge(START, "analyze")
graph_builder.add_edge("analyze", "investigate")
graph_builder.add_edge("investigate", END)

# turns the graph definition into an executable graph
graph = graph_builder.compile()


# below code was to just run graph.py using python graph.py, this code is already in main which calls graph.py
if __name__ == "__main__":
    result = graph.invoke({
        "incident": {
            "service": "payment-service",
            "severity": "CRITICAL",
            "error": "payment provider unavailable"
        },
        "analysis": {},
        "investigation": {}
    })

    print(result)