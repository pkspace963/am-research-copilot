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

# Helper function to call the Google GenAI SDK (Gemini) with exponential backoff
def generate_content_gemini(prompt: str) -> str:
    import time
    from google import genai
    from google.genai.errors import APIError
    
    max_retries = 3
    delay = 2.0
    client = genai.Client()
    
    for attempt in range(max_retries):
        try:
            # Using gemini-2.5-flash which is the active high-quota model in this workspace
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            return response.text.strip()
        except APIError as e:
            # Retry on rate limits (429) or transient server errors (503)
            if e.code in [429, 503] and attempt < max_retries - 1:
                # If 429 rate limit is encountered on the first attempt, sleep 35s to reset the quota window
                current_delay = 35.0 if (e.code == 429 and attempt == 0) else delay
                print(f"Transient Gemini API error {e.code} (attempt {attempt+1}/{max_retries}). Retrying in {current_delay}s...", file=sys.stderr)
                time.sleep(current_delay)
                delay = current_delay * 2
            else:
                print(f"Gemini API Error: {e}", file=sys.stderr)
                raise e
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Generic error (attempt {attempt+1}/{max_retries}). Retrying in {delay}s...", file=sys.stderr)
                time.sleep(delay)
                delay *= 2
            else:
                print(f"Gemini API Error: {e}", file=sys.stderr)
                raise e


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

# 2. Define the Agent Nodes using live Gemini SDK generation

@node
def guardrail_node(ctx: Context, node_input: Any) -> Event:
    """
    Checks if the user query is related to manufacturing or materials.
    Sets 'domain_valid' in the shared state using Gemini validation.
    """
    query = get_text_from_input(node_input)
    
    prompt = f"""
    You are an expert manufacturing guardrail. Determine if the user query is about advanced manufacturing, materials science (ceramics, metals, polymers), 3D printing, sintering, or dental applications.
    User Query: "{query}"
    
    Respond with ONLY 'TRUE' or 'FALSE'. Do not add any other text.
    """
    try:
        ans = generate_content_gemini(prompt)
        domain_valid = "TRUE" in ans.upper()
    except Exception:
        # Fallback to simple keyword check if API fails
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
    if the query is verified as domain-valid, utilizing Gemini to formulate research notes.
    """
    domain_valid = ctx.state.get("domain_valid", False)
    user_query = ctx.state.get("user_query", "")
    
    if domain_valid:
        try:
            # Determine targeted material dynamically
            material_name = detect_material(user_query)
            # Query the baseline properties from the MCP server
            baselines_raw = await call_mcp_tool("get_material_baselines", {"material_name": material_name})
            
            prompt = f"""
            You are a materials science researcher. Given the user query: "{user_query}" and the following verified database baseline properties:
            {baselines_raw}
            
            Dynamically generate a detailed research summary of the baseline mechanical properties (flexural strength, fracture toughness) and Recommended DLP printing/sintering parameters. Do not hallucinate any values outside the provided data.
            """
            research_notes = generate_content_gemini(prompt)
            return Event(
                output=research_notes,
                state={"research_notes": research_notes}
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
    toughness additives using the MCP server to aid material selection,
    utilizing Gemini to analyze the trade-offs.
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
            
            high_toughness = detects_high_toughness_request(user_query)
            # Adaptive Routing: Inject advanced composite parameters for high fracture toughness requests
            if high_toughness:
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
            
            prompt = f"""
            You are a materials selection agent. Given the user query: "{user_query}" and the additive insights from our database:
            {json.dumps(additives, indent=2)}
            
            Dynamically generate a comparative analysis of the additives, their concentration ranges, and their pros/cons for this material application. If high toughness is requested, synthesize the trade-offs of using Graphene/CNT composite reinforcement and field alignment.
            """
            materials_analysis = generate_content_gemini(prompt)
            return Event(
                output=materials_analysis,
                state={"materials_chosen": materials_analysis}
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
    Creates a Design of Experiments (DoE) test matrix for evaluating additives using Gemini.
    """
    domain_valid = ctx.state.get("domain_valid", False)
    research_notes = ctx.state.get("research_notes", "")
    materials_chosen = ctx.state.get("materials_chosen", "")
    
    if not domain_valid:
        return Event(
            output="Query out-of-domain. Sintering/DLP planning skipped.",
            state={"experimental_matrix": "Skipped (out of domain)"}
        )
        
    prompt = f"""
    You are an experimental planning agent. Given the material research notes:
    "{research_notes}"
    
    And materials chosen/analyzed:
    "{materials_chosen}"
    
    Compose a unique Design of Experiments (DoE) matrix in a clean markdown table. The DoE should test variables like layer thickness, sintering temperature, and additives. Return ONLY the markdown table. Do not add introductory or concluding text.
    """
    try:
        doe_matrix = generate_content_gemini(prompt)
    except Exception as e:
        doe_matrix = f"Error generating DoE matrix: {e}"

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

    prompt = f"""
    You are a principal engineer compiling a final research report.
    User Query: {user_query}
    Research Notes: {research_notes}
    Additives Chosen: {materials_chosen}
    DoE Matrix: {experimental_matrix}
    
    Compile everything into a beautiful, detailed, professional markdown report. You MUST include a dedicated section titled '## 5. Research Gap Analysis: Thermal Processing-Window Conflicts' that analyzes the specific thermodynamic/sintering conflicts for this material and its additives (e.g., grain growth vs. densification temperatures, oxidation of carbon reinforcements, or thermal expansion mismatch). Structure the report professionally.
    """
    try:
        report_content = generate_content_gemini(prompt)
    except Exception as e:
        report_content = f"Error compiling final report: {e}"

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

# 4. Expose a LangGraph-compatible compile().invoke() wrapper for automated tools/checkers
class CompiledGraph:
    def __init__(self, workflow):
        self.workflow = workflow
    def invoke(self, inputs: dict) -> dict:
        from google.adk.apps import App
        from google.adk.runners import InMemoryRunner
        from google.genai import types
        
        async def _run():
            app = App(name="app", root_agent=self.workflow)
            runner = InMemoryRunner(app=app)
            session = await runner.session_service.create_session(app_name="app", user_id="cli_user")
            new_message = types.Content(
                role="user",
                parts=[types.Part.from_text(text=inputs.get("user_query", ""))]
            )
            async for _ in runner.run_async(
                user_id="cli_user",
                session_id=session.id,
                new_message=new_message
            ):
                pass
            updated_session = await runner.session_service.get_session(
                app_name="app", user_id="cli_user", session_id=session.id
            )
            return updated_session.state
        return asyncio.run(_run())

class GraphWrapper:
    def __init__(self, workflow):
        self.workflow = workflow
    def compile(self):
        return CompiledGraph(self.workflow)
    def invoke(self, inputs: dict) -> dict:
        return self.compile().invoke(inputs)

workflow = GraphWrapper(root_agent)
graph = workflow.compile()



