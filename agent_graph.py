import asyncio
import json
import sys
from typing import Any, Optional
from pydantic import BaseModel

from google.adk.workflow import Workflow, START, node
from google.adk.events.event import Event
from google.adk.agents.context import Context
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# 1. Define the shared state class tracking research session data
class ResearchState(BaseModel):
    user_query: str
    domain_valid: Optional[bool] = None
    research_notes: Optional[str] = None
    materials_chosen: Optional[str] = None
    experimental_matrix: Optional[str] = None
    final_report: Optional[str] = None

# Helper function to extract query string from various node_input types
def get_text_from_input(node_input: Any) -> str:
    if isinstance(node_input, str):
        return node_input
    if hasattr(node_input, 'parts') and node_input.parts:
        return node_input.parts[0].text
    if isinstance(node_input, dict) and 'user_query' in node_input:
        return node_input['user_query']
    if isinstance(node_input, dict) and 'text' in node_input:
        return node_input['text']
    return str(node_input)

# Helper function to invoke tools from the MCP server
async def call_mcp_tool(tool_name: str, arguments: dict = None) -> str:
    """
    Spawns the local MCP server as a subprocess and invokes the specified tool.
    """
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["d:/capstone/mcp_server.py"]
    )
    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            response = await session.call_tool(tool_name, arguments or {})
            if response.isError:
                raise ValueError(response.content[0].text)
            return response.content[0].text

# 2. Define the Agent Nodes

@node
def guardrail_node(ctx: Context, node_input: Any) -> Event:
    """
    Checks if the user query is related to manufacturing or materials.
    Sets 'domain_valid' in the shared state.
    """
    query = get_text_from_input(node_input)
    
    # Manufacturing, zirconia, or materials keywords
    keywords = [
        "zirconia", "y-tzp", "ceramic", "sintering", "debinding", 
        "dlp", "print", "manufacturing", "additive", "mfg", 
        "material", "properties", "toughness", "flexural", "alumina", "ceria"
    ]
    
    domain_valid = any(kw in query.lower() for kw in keywords)
    
    return Event(
        output=query,
        state={
            "user_query": query,
            "domain_valid": domain_valid
        }
    )

@node
async def research_node(ctx: Context, node_input: Any) -> Event:
    """
    Retrieves baseline mechanical properties and DLP print parameters
    if the query is verified as domain-valid.
    """
    domain_valid = ctx.state.get("domain_valid", False)
    
    if domain_valid:
        try:
            # Query the baseline properties from the MCP server
            baselines = await call_mcp_tool("get_material_baselines")
            return Event(
                output=baselines,
                state={"research_notes": baselines}
            )
        except Exception as e:
            error_msg = f"Failed to retrieve material baselines: {str(e)}"
            return Event(
                output=error_msg,
                state={"research_notes": f"Error: {error_msg}"}
            )
    else:
        return Event(
            output="Query out-of-domain. Baseline research skipped.",
            state={"research_notes": "Skipped (out of domain)"}
        )

@node
async def materials_node(ctx: Context, node_input: Any) -> Event:
    """
    Retrieves pros, cons, and typical concentration ranges of common
    toughness additives using the MCP server to aid material selection.
    """
    domain_valid = ctx.state.get("domain_valid", False)
    
    if domain_valid:
        try:
            # Query the additive insights from the MCP server
            additives = await call_mcp_tool("get_additive_insights")
            return Event(
                output=additives,
                state={"materials_chosen": additives}
            )
        except Exception as e:
            error_msg = f"Failed to retrieve additive insights: {str(e)}"
            return Event(
                output=error_msg,
                state={"materials_chosen": f"Error: {error_msg}"}
            )
    else:
        return Event(
            output="Query out-of-domain. Material selection skipped.",
            state={"materials_chosen": "Skipped (out of domain)"}
        )

@node
def planner_node(ctx: Context, node_input: Any) -> Event:
    """
    Creates a Design of Experiments (DoE) test matrix for evaluating additives.
    """
    domain_valid = ctx.state.get("domain_valid", False)
    
    if not domain_valid:
        return Event(
            output="Query out-of-domain. Sintering/DLP planning skipped.",
            state={"experimental_matrix": "Skipped (out of domain)"}
        )
        
    doe_matrix = """
### Proposed Design of Experiments (DoE) Matrix

To evaluate the influence of additive type, concentration, layer thickness, and sintering temperature:

| Run | Additive Type | Concentration | Layer Thickness (µm) | Sintering Temp (°C) | Dwell Time (min) | Primary Objective |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1 (Control)** | None | 0.0 wt% | 30 | 1500 | 120 | Establish baseline properties |
| **2** | Alumina (Al2O3) | 0.05 wt% | 20 | 1500 | 120 | Optimize fine feature resolution |
| **3** | Alumina (Al2O3) | 0.25 wt% | 50 | 1550 | 120 | Investigate high-concentration limit |
| **4** | Ceria (CeO2) | 8.0 mol% | 20 | 1450 | 120 | Test low-temperature sintering |
| **5** | Ceria (CeO2) | 12.0 mol% | 50 | 1500 | 120 | Maximize transformation toughening |
| **6** | Alumina + Ceria | 0.1% + 10% | 30 | 1500 | 120 | Test synergistic co-doping effects |
"""
    return Event(
        output=doe_matrix,
        state={"experimental_matrix": doe_matrix}
    )

@node
def report_node(ctx: Context, node_input: Any) -> Event:
    """
    Compiles all gathered information and tables into a clean markdown report.
    """
    user_query = ctx.state.get("user_query", "")
    domain_valid = ctx.state.get("domain_valid", False)
    research_notes = ctx.state.get("research_notes", "")
    materials_chosen = ctx.state.get("materials_chosen", "")
    experimental_matrix = ctx.state.get("experimental_matrix", "")

    if not domain_valid:
        report_content = f"""# Manufacturing Research Report (Out of Domain)

**Original Query:** {user_query}
**Domain Verification Status:** FAILED

*The submitted query does not relate to manufacturing, zirconia, or dental materials application. Execution halted by guardrails.*
"""
        return Event(
            output=report_content,
            state={"final_report": report_content}
        )

    # Parse baseline properties data
    try:
        baselines = json.loads(research_notes)
    except Exception:
        baselines = {}

    # Parse additive details
    try:
        additives = json.loads(materials_chosen)
    except Exception:
        additives = {}

    mech_props = baselines.get("baseline_mechanical_properties", {})
    ft = mech_props.get("fracture_toughness", {})
    fs = mech_props.get("flexural_strength", {})
    dlp = baselines.get("dlp_print_parameters", {})
    lt = dlp.get("layer_thickness", {})
    sintering = dlp.get("sintering_temperature_profile", {})

    # Generate the formatted Markdown report
    report_content = f"""# Zirconia Manufacturing & Sintering Analysis Report

**Original Query:** {user_query}
**Domain Verification Status:** PASSED (Zirconia Dental Applications)

---

## 1. Baseline Mechanical Properties (Y-TZP Zirconia)
* **Fracture Toughness:** {ft.get('value_range', [5.0, 10.0])[0]} - {ft.get('value_range', [5.0, 10.0])[1]} {ft.get('unit', 'MPa·m^(1/2)')}
  * *Test Method:* {ft.get('method', 'N/A')}
* **Flexural Strength:** {fs.get('value_range', [900, 1200])[0]} - {fs.get('value_range', [900, 1200])[1]} {fs.get('unit', 'MPa')}
  * *Test Method:* {fs.get('method', 'N/A')}

---

## 2. Recommended DLP Print Parameters
* **Layer Thickness Range:** {lt.get('range', [20, 50])[0]} - {lt.get('range', [20, 50])[1]} {lt.get('unit', 'microns')}
* **Recommended Thickness:** {lt.get('recommended', 30)} {lt.get('unit', 'microns')}

### Sintering Temperature Profile
"""
    for stage in sintering.get("stages", []):
        report_content += f"""
### Stage: {stage.get('stage_name')}
* **Ramp Rate:** {stage.get('ramp_rate')} {stage.get('ramp_rate_unit')}
* **Target Temp:** {stage.get('target_temperature')}{stage.get('temperature_unit')}
* **Dwell Time:** {stage.get('dwell_time')} {stage.get('dwell_time_unit')}
* *Purpose/Details:* {stage.get('description')}
"""

    report_content += "\n---\n\n## 3. Toughness Additives Analysis\n"
    for name, details in additives.items():
        pros_list = "\n".join(f"  * {p}" for p in details.get("pros", []))
        cons_list = "\n".join(f"  * {c}" for c in details.get("cons", []))
        report_content += f"""
### {name}
* **Typical Concentration:** {details.get('typical_concentration_range')}
* **Pros:**
{pros_list}
* **Cons:**
{cons_list}
"""

    report_content += f"""
---

## 4. Proposed Design of Experiments (DoE)
{experimental_matrix}
"""

    return Event(
        output=report_content,
        state={"final_report": report_content}
    )

# 3. Define and construct the graph workflow
root_agent = Workflow(
    name="zirconia_research_workflow",
    edges=[
        (START, guardrail_node),
        (guardrail_node, research_node),
        (research_node, materials_node),
        (materials_node, planner_node),
        (planner_node, report_node)
    ],
    state_schema=ResearchState
)
