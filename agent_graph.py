import asyncio
import json
import re
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

# Helper function to dynamically detect the material from the user's query
def detect_material(query: str) -> str:
    query_lower = query.lower()
    if "alumina" in query_lower and "zirconia" not in query_lower:
        return "Alumina Bioceramics"
    elif any(x in query_lower for x in ["steel", "stainless", "316l"]):
        return "316L Stainless Steel"
    return "Y-TZP Zirconia"

# Helper function to detect high fracture toughness requests (e.g. > 6 MPa·m^(1/2) or improved toughness)
def detects_high_toughness_request(query: str) -> bool:
    query_lower = query.lower()
    high_toughness_keywords = ["high toughness", "improved toughness", "increase toughness", "high fracture toughness"]
    if any(k in query_lower for k in high_toughness_keywords):
        return True
    
    # Check for patterns like > 6 or >= 6
    match = re.search(r'(?:toughness|k1c)\s*(?:>|>=|greater\s+than|above)\s*(\d+(?:\.\d+)?)', query_lower)
    if match:
        val = float(match.group(1))
        if val >= 6.0:
            return True
            
    # Direct mentions of > 6
    if "> 6" in query_lower or ">6" in query_lower or "above 6" in query_lower or "greater than 6" in query_lower:
        return True
        
    return False

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

# Helper function to compute the Research Gap Analysis focusing on thermal conflicts
def compute_research_gap_analysis(material: str, high_toughness: bool) -> str:
    gap_text = "## 5. Research Gap Analysis: Thermal Processing-Window Conflicts\n"
    
    if "zirconia" in material.lower():
        gap_text += """
* **Sintering Temperature Incompatibility**: Y-TZP Zirconia densifies optimally around 1500°C. However, adding Alumina ($Al_2O_3$) to improve hydrothermal aging resistance requires higher temperatures (~1550°C - 1600°C) for full densification. Raising the temperature to accommodate alumina leads to rapid grain growth in the Y-TZP matrix, which reduces the transformation toughening capability and makes the zirconia more susceptible to low-temperature degradation (LTD).
* **Atmospheric Sintering Conflicts**: While zirconia requires an oxidizing atmosphere to maintain its oxygen stoichiometry, co-doping with certain elements or metallic components requires vacuum or reducing environments (e.g., hydrogen gas) to prevent oxidation, which in turn causes oxygen vacancies and destabilization of the tetragonal zirconia phase.
"""
        if high_toughness:
            gap_text += """
* **Nanoparticle Burnout vs. Zirconia Sintering**: The injection of Graphene or CNTs for high-toughness requirements introduces a major thermal processing gap. Carbon-based reinforcements burn out in oxidizing atmospheres at temperatures above 450°C. However, sintering zirconia requires oxygen to prevent reduction. Sintering in inert/reducing conditions to preserve CNTs/Graphene yields sub-stoichiometric zirconia ($ZrO_{2-x}$), which exhibits degraded mechanical properties and poor dental aesthetics.
"""
    elif "alumina" in material.lower():
        gap_text += """
* **ZTA Sintering Trade-Offs**: Sintering Alumina Bioceramics requires temperatures of 1600°C. In Zirconia-Toughened Alumina (ZTA), this high thermal energy causes significant grain growth of both the alumina matrix and the zirconia dispersoids. If the zirconia grains exceed the critical size (~1 µm), they undergo spontaneous tetragonal-to-monoclinic transformation upon cooling rather than remaining metastable. This defeats the stress-induced transformation toughening mechanism at room temperature.
"""
    elif "steel" in material.lower() or "stainless" in material.lower():
        gap_text += """
* **Binder Burnout vs. Metal Oxidation**: 316L Stainless Steel printed green bodies require debinding under hydrogen or vacuum to prevent carbon retention (which causes chromium carbide precipitation and sensitizes the steel to corrosion). Ceramics, by contrast, require oxygen for clean binder burnout. Co-processing metals with oxide ceramics is heavily constrained by this atmospheric conflict.
* **Thermal Expansion Mismatch**: 316L Stainless Steel has a high coefficient of thermal expansion (CTE) of approximately $16 \times 10^{-6}/\text{K}$, whereas zirconia and alumina are around $7-10 \times 10^{-6}/\text{K}$. Sintering hybrid materials across these windows causes massive residual stresses during the cooling phase, leading to interfacial delamination and cracking.
"""
    return gap_text

# 2. Define the Agent Nodes

@node
def guardrail_node(ctx: Context, node_input: Any) -> Event:
    """
    Checks if the user query is related to manufacturing or materials.
    Sets 'domain_valid' in the shared state.
    """
    query = get_text_from_input(node_input)
    
    # Manufacturing, zirconia, metals, or general materials keywords
    keywords = [
        "zirconia", "y-tzp", "ceramic", "sintering", "debinding", 
        "dlp", "print", "manufacturing", "additive", "mfg", 
        "material", "properties", "toughness", "flexural", "alumina", "ceria",
        "steel", "stainless", "316l", "metal", "alloy", "bioceramic"
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
    user_query = ctx.state.get("user_query", "")
    
    if domain_valid:
        try:
            # Determine targeted material dynamically
            material_name = detect_material(user_query)
            # Query the baseline properties from the MCP server
            baselines = await call_mcp_tool("get_material_baselines", {"material_name": material_name})
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
    Appends Graphene/CNT composite reinforcement if high toughness is requested.
    """
    domain_valid = ctx.state.get("domain_valid", False)
    user_query = ctx.state.get("user_query", "")
    
    if domain_valid:
        try:
            # Determine targeted material dynamically
            material_name = detect_material(user_query)
            # Query the additive insights from the MCP server
            additives_raw = await call_mcp_tool("get_additive_insights", {"material_name": material_name})
            
            try:
                additives = json.loads(additives_raw)
            except Exception:
                additives = {}
            
            # Adaptive Routing: Inject advanced composite parameters for high fracture toughness requests
            if detects_high_toughness_request(user_query):
                additives["Graphene Nanoplatelets (GNPs) / Carbon Nanotubes (CNTs)"] = {
                    "typical_concentration_range": "0.1 wt% - 1.0 wt%",
                    "pros": [
                        "Provides extraordinary fracture toughness via crack bridging, pull-out, and crack deflection mechanisms",
                        "Introduces electrical conductivity, enabling structural health monitoring",
                        "Improves wear resistance and hardness"
                    ],
                    "cons": [
                        "Drastically reduces translucency, resulting in a dark, opaque gray/black appearance (unsuitable for aesthetic dental restorations)",
                        "High risk of agglomeration, requiring advanced dispersion techniques (ultrasonication, surfactants)",
                        "Anisotropic mechanical properties depending on alignment during the printing process"
                    ],
                    "reinforcement_alignment": "Requires magnetic or electric field alignment during DLP print layer exposure to align CNTs perpendicular to crack propagation plane."
                }
            
            additives_json = json.dumps(additives, indent=2, ensure_ascii=False)
            return Event(
                output=additives_json,
                state={"materials_chosen": additives_json}
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
    user_query = ctx.state.get("user_query", "")
    
    if not domain_valid:
        return Event(
            output="Query out-of-domain. Sintering/DLP planning skipped.",
            state={"experimental_matrix": "Skipped (out of domain)"}
        )
        
    material_name = detect_material(user_query)
    high_toughness = detects_high_toughness_request(user_query)
    
    # Customize the DoE matrix depending on the material and toughness requirement
    if "zirconia" in material_name.lower():
        doe_matrix = f"""
### Proposed Design of Experiments (DoE) Matrix (Y-TZP Zirconia)

To evaluate the influence of additive type, concentration, layer thickness, and sintering temperature:

| Run | Additive Type | Concentration | Layer Thickness (µm) | Sintering Temp (°C) | Dwell Time (min) | Primary Objective |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1 (Control)** | None | 0.0 wt% | 30 | 1500 | 120 | Establish baseline properties |
| **2** | Alumina (Al2O3) | 0.05 wt% | 20 | 1500 | 120 | Optimize fine feature resolution |
| **3** | Alumina (Al2O3) | 0.25 wt% | 50 | 1550 | 120 | Investigate high-concentration limit |
| **4** | Ceria (CeO2) | 8.0 mol% | 20 | 1450 | 120 | Test low-temperature sintering |
| **5** | Ceria (CeO2) | 12.0 mol% | 50 | 1500 | 120 | Maximize transformation toughening |
"""
        if high_toughness:
            doe_matrix += """| **6** | Graphene/CNTs | 0.5 wt% | 30 | 1500 (Argon/Inert) | 120 | Evaluate carbon composite reinforcement & alignment |
"""
        else:
            doe_matrix += """| **6** | Alumina + Ceria | 0.1% + 10% | 30 | 1500 | 120 | Test synergistic co-doping effects |
"""
            
    elif "alumina" in material_name.lower():
        doe_matrix = """
### Proposed Design of Experiments (DoE) Matrix (Alumina Bioceramics)

Evaluating Zirconia-Toughened Alumina (ZTA) parameters:

| Run | Additive Type | Concentration | Layer Thickness (µm) | Sintering Temp (°C) | Dwell Time (min) | Primary Objective |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1 (Control)** | None | 0.0 wt% | 40 | 1600 | 120 | Pure alumina baseline |
| **2** | Zirconia (ZrO2) | 10.0 wt% | 30 | 1600 | 120 | ZTA toughness evaluation |
| **3** | Zirconia (ZrO2) | 20.0 wt% | 50 | 1550 | 180 | Evaluate lower temp / longer dwell ZTA |
"""
    else:  # Stainless steel
        doe_matrix = """
### Proposed Design of Experiments (DoE) Matrix (316L Stainless Steel)

Evaluating metal printing and sintering under vacuum/hydrogen parameters:

| Run | Additive Type | Concentration | Layer Thickness (µm) | Sintering Temp (°C) | Atmosphere | Primary Objective |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1 (Control)** | None | 0.0 wt% | 50 | 1360 | High Vacuum | Baseline printed steel density |
| **2** | Nickel (Ni) | 12.0 wt% | 30 | 1360 | Dry Hydrogen | Austenitic stability evaluation |
| **3** | Nickel (Ni) | 14.0 wt% | 50 | 1340 | Argon Shield | Evaluate alternative sintering gas |
"""

    return Event(
        output=doe_matrix,
        state={"experimental_matrix": doe_matrix}
    )

@node
def report_node(ctx: Context, node_input: Any) -> Event:
    """
    Compiles all gathered information and tables into a clean markdown report.
    Autonomously computes and appends a Research Gap Analysis section.
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

*The submitted query does not relate to manufacturing, ceramics, or metallic materials application. Execution halted by guardrails.*
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

    material_name = baselines.get("material", "Unknown Material")
    mech_props = baselines.get("baseline_mechanical_properties", {})
    ft = mech_props.get("fracture_toughness", {})
    fs = mech_props.get("flexural_strength", {})
    dlp = baselines.get("dlp_print_parameters", {})
    lt = dlp.get("layer_thickness", {})
    sintering = dlp.get("sintering_temperature_profile", {})

    high_toughness = detects_high_toughness_request(user_query)

    # Generate the formatted Markdown report
    report_content = f"""# Advanced Manufacturing & Sintering Analysis Report

**Original Query:** {user_query}
**Domain Verification Status:** PASSED ({material_name} Applications)

---

## 1. Baseline Mechanical Properties ({material_name})
* **Fracture Toughness:** {ft.get('value_range', [3.0, 10.0])[0]} - {ft.get('value_range', [3.0, 10.0])[1]} {ft.get('unit', 'MPa·m^(1/2)')}
  * *Test Method:* {ft.get('method', 'N/A')}
* **Flexural Strength:** {fs.get('value_range', [400, 1200])[0]} - {fs.get('value_range', [400, 1200])[1]} {fs.get('unit', 'MPa')}
  * *Test Method:* {fs.get('method', 'N/A')}

---

## 2. Recommended DLP Print Parameters
* **Layer Thickness Range:** {lt.get('range', [20, 75])[0]} - {lt.get('range', [20, 75])[1]} {lt.get('unit', 'microns')}
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

    report_content += "\n---\n\n## 3. Toughness Additives & Modification Analysis\n"
    for name, details in additives.items():
        pros_list = "\n".join(f"  * {p}" for p in details.get("pros", []))
        cons_list = "\n".join(f"  * {c}" for c in details.get("cons", []))
        align = details.get("reinforcement_alignment")
        
        report_content += f"""
### {name}
* **Typical Concentration:** {details.get('typical_concentration_range')}
* **Pros:**
{pros_list}
* **Cons:**
{cons_list}
"""
        if align:
            report_content += f"* **Alignment requirements:** {align}\n"

    report_content += f"""
---

## 4. Proposed Design of Experiments (DoE)
{experimental_matrix}

---

{compute_research_gap_analysis(material_name, high_toughness)}
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
