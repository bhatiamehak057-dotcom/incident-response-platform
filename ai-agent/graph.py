import os
# We need this because the API key is stored as an environment variable, rather than putting the secret directly into our source code.

import json
import asyncio

from langgraph.graph import StateGraph, START, END
from typing import TypedDict
from mcp import Client
# from mcp import StdioServerParameters
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
    remediation: dict

# creates an Anthropic client.
# Think of client as our connection/interface to Claude.
# The Anthropic object gives your Python code methods for communicating with Claude
client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# We don't need below code anymore because the MCP server is already running independently on port 8001.
# server_params = StdioServerParameters(
#     command="/Users/mehakbhatia/IdeaProjects/incident-response-platform/mcp-server/.venv/bin/mcp",
#     args=[
#         "run",
#         "/Users/mehakbhatia/IdeaProjects/incident-response-platform/mcp-server/server.py"
#     ],
# )

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

# LangGraph passes the state to MCP investigation node.
# This node calls three MCP tools
def investigate_incident(state: IncidentState):
    incident = state["incident"]

    # async def call_mcp():
    #     async with Client(server_params) as client:

    # This is an important improvement because the MCP server is now an independent service, rather than something the AI agent owns as a subprocess.
    async def call_mcp():
        async with Client("http://localhost:8001/mcp") as client:

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
# giving Claude access to existing operational knowledge
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

# This is the second Claude call, and this is the response you should consider your evidence-based diagnosis
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


# look at:
# final_analysis
# and determine whether a remediation action should be proposed.
# Node where Claude decides whether automation is appropriate, eg:
# Given the evidence, should we propose restarting the service
def decide_remediation(state: IncidentState):

    incident = state["incident"]
    final_analysis = state["final_analysis"]

    prompt = f"""
Based on the following production incident and evidence-based analysis,
determine whether a remediation action should be proposed.

Incident:
{json.dumps(incident, indent=2)}

Evidence-based analysis:
{json.dumps(final_analysis, indent=2)}

Available remediation actions:

1. restart_service
   - Restarts the affected service.
   - This is currently a simulated remediation.

Only propose a remediation if it is appropriate based on the evidence.

Return JSON with exactly these fields:

{{
  "action": "restart_service" or "none",
  "service": "string",
  "reason": "string",
  "requiresApproval": true or false
}}

Set requiresApproval to:
- true if action is "restart_service"
- false if action is "none"

Do not execute any remediation.
Only propose the action.
"""

    # if claude returns action as none, it means, Don't execute any of the currently available automated remediation actions.
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    remediation_text = (
        response.content[0].text
        .replace("```json", "")
        .replace("```", "")
        .strip()
    )

    remediation = json.loads(remediation_text)

    print("Remediation proposal:", remediation)

    return {
        "remediation": remediation
    }

# will only execute after human approval

initialize_rag()
# Create a graph whose state follows IncidentState
graph_builder = StateGraph(IncidentState)

graph_builder.add_node("analyze", analyze_incident)
graph_builder.add_node("investigate", investigate_incident)
graph_builder.add_node("retrieve_runbook", retrieve_incident_runbook)
graph_builder.add_node("analyze_evidence", analyze_evidence)
graph_builder.add_node("decide_remediation", decide_remediation)

graph_builder.add_edge(START, "analyze")
graph_builder.add_edge("analyze", "investigate")
graph_builder.add_edge("investigate", "retrieve_runbook")
graph_builder.add_edge("retrieve_runbook", "analyze_evidence")
graph_builder.add_edge("analyze_evidence", "decide_remediation")
graph_builder.add_edge("decide_remediation", END)

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
        "final_analysis": {},
        "remediation": {}
    })

    # print(result)

    analysis = result["analysis"]
final_analysis = result["final_analysis"]
investigation = result["investigation"]
remediation = result["remediation"]

print("\n=== INCIDENT ===")
print(result["incident"])

print("\n=== INITIAL ANALYSIS ===")
print("Root cause:", analysis["rootCause"])
print("Impact:", analysis["impact"])
print("Recommended actions:")
for action in analysis["recommendedActions"]:
    print(f"- {action}")

print("\n=== INVESTIGATION ===")
print("Health:", investigation["health"])
print("Logs:", investigation["logs"])
print("Metrics:", investigation["metrics"])

print("\n=== RUNBOOKS ===")
for runbook in result["runbooks"]:
    print(runbook.split("\n")[0])

print("\n=== EVIDENCE-BASED ANALYSIS ===")
print("Root cause:", final_analysis["rootCause"])
print("Impact:", final_analysis["impact"])
print("Recommended actions:")
for action in final_analysis["recommendedActions"]:
    print(f"- {action}")

print("\n=== REMEDIATION DECISION ===")
print("Action:", remediation["action"])
print("Service:", remediation["service"])
print("Reason:", remediation["reason"])
print("Requires approval:", remediation["requiresApproval"])

# analysis = Claude's initial hypothesis;
# investigation = MCP's observed system data;
# runbooks = Chroma/RAG's retrieved knowledge;
# final_analysis = Claude's evidence-based diagnosis;
# remediation = Claude's decision about whether an available automated action should be proposed.

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





# START
#   ↓
# Initial Claude Analysis
#   ↓
# MCP Investigation
#   ↓
# RAG Retrieval
#   ↓
# Evidence-Based Claude Analysis
#   ↓
# Remediation Decision
#   ↓
# END




#                  LangGraph
#                     │
#                     ▼
#             decide_remediation
#                     │
#              action = restart
#                     │
#              requiresApproval
#                     │
#                     ▼
#               SAVE / PAUSE
#                     │
#                     │
#                     ▼
#               React Dashboard
#                     │
#              ┌──────┴──────┐
#              ▼             ▼
#           Approve        Reject
#              │             │
#              └──────┬──────┘
#                     ▼
#                   Kafka
#                     │
#                     ▼
#               Resume workflow
#                     │
#               ┌─────┴─────┐
#               ▼           ▼
#            execute       END
#            MCP