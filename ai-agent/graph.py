import os
# We need this because the API key is stored as an environment variable, rather than putting the secret directly into our source code.

import json
import asyncio

from langgraph.graph import StateGraph, START, END
from typing import TypedDict
from mcp import Client, StdioServerParameters
from rag import initialize_rag, retrieve_runbook

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
    runbooks: list
    final_analysis: dict

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

            health_result = await client.call_tool(
                "get_service_health",
                {"service": incident["service"]}
            )

            logs_result = await client.call_tool(
                "get_recent_logs",
                {"service": incident["service"]}
            )

            metrics_result = await client.call_tool(
                "get_metrics",
                {"service": incident["service"]}
            )

            if health_result.is_error:
                raise RuntimeError(health_result.content)

            if logs_result.is_error:
                raise RuntimeError(logs_result.content)

            if metrics_result.is_error:
                raise RuntimeError(metrics_result.content)

            return {
                "health": json.loads(health_result.content[0].text),
                "logs": json.loads(logs_result.content[0].text),
                "metrics": json.loads(metrics_result.content[0].text)
            }

    investigation = asyncio.run(call_mcp())

    print("Investigation:", investigation)

    return {
        "investigation": investigation
    }


# Its job is to connect LangGraph → RAG.
def retrieve_incident_runbook(state: IncidentState):

    incident = state["incident"]

    # gets your MCP results:
    investigation = state["investigation"]

    # We're combining the information we already know about the incident into one piece of text.
    # This becomes the RAG search query.
    query = f"""
    Service: {incident["service"]}
    Error: {incident["error"]}

    Investigation:
    {json.dumps(investigation)}
    """

    # this line is the actual RAG retrieval
    # We're calling the function from rag.py
    runbooks = retrieve_runbook(query)

    print("Relevant runbooks:", runbooks)

    return {
        "runbooks": runbooks
    }


def analyze_evidence(state: IncidentState):
    incident = state["incident"]
    investigation = state["investigation"]
    runbooks = state["runbooks"]

    prompt = f"""
Re-analyze this production incident using the investigation evidence.

Incident:
Service: {incident["service"]}
Severity: {incident["severity"]}
Error: {incident["error"]}

Investigation evidence:
{json.dumps(investigation, indent=2)}

Relevant runbooks:
{json.dumps(runbooks, indent=2)}

Based on the incident, investigation evidence, and relevant runbooks,
provide a refined diagnosis.

Important:
- Clearly distinguish observed evidence from inference.
- Do not assume that requests are payment transactions unless the evidence explicitly says so.
- Use the provided metrics exactly as reported.
- Do not invent facts that are not present in the incident, investigation, or runbooks.

Return your analysis as JSON with exactly these fields:

{{
  "rootCause": "string",
  "impact": "string",
  "recommendedActions": ["string", "string", "string"]
}}
"""

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

    analysis_text = (
        response.content[0].text
        .replace("```json", "")
        .replace("```", "")
        .strip()
    )

    final_analysis = json.loads(analysis_text)

    print("Evidence-based analysis:", final_analysis)

    return {
        "final_analysis": final_analysis
    }


initialize_rag()
# Create a graph whose state follows IncidentState
graph_builder = StateGraph(IncidentState)

graph_builder.add_node("analyze", analyze_incident)
graph_builder.add_node("investigate", investigate_incident)
graph_builder.add_node("retrieve_runbook", retrieve_incident_runbook)
graph_builder.add_node("analyze_evidence", analyze_evidence)

graph_builder.add_edge(START, "analyze")
graph_builder.add_edge("analyze", "investigate")
graph_builder.add_edge("investigate", "retrieve_runbook")
graph_builder.add_edge("retrieve_runbook", "analyze_evidence")
graph_builder.add_edge("analyze_evidence", END)

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
        "investigation": {},
        "runbooks":[],
        "final_analysis": {}
    })

    print(result)

# Runbook = human-written operational knowledge/instructions.
# Chroma = stores and searches that knowledge semantically.
# RAG = retrieves relevant knowledge and gives it to the LLM as context.
# rag.py = your implementation of the retrieval layer.
# retrieve_incident_runbook() = the LangGraph node that takes the current incident/evidence and asks the RAG layer for relevant knowledge.
# Claude = uses the retrieved knowledge + actual MCP evidence to produce the diagnosis.



#                 INCIDENT
#                    │
#                    ▼
#              LangGraph
#                    │
#                    ▼
#            MCP Investigation
#                    │
#         ┌──────────┼──────────┐
#         │          │          │
#       health      logs      metrics
#         │          │          │
#         └──────────┼──────────┘
#                    │
#                    ▼
#         retrieve_incident_runbook()
#                    │
#                    ▼
#              Create query
#                    │
#                    ▼
#               retrieve_runbook()
#                    │
#                    ▼
#                 Chroma
#                    │
#              semantic search
#                    │
#                    ▼
#         ┌─────────────────────┐
#         │ Relevant Runbooks   │
#         │                     │
#         │ Provider Timeout    │
#         │ Service Down        │
#         └──────────┬──────────┘
#                    │
#                    ▼
#             LangGraph state
#                    │
#                    ▼
#             Claude + evidence
#                    │
#                    ▼
#           Refined diagnosis