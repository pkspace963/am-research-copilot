import asyncio
import json
import sys
from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

# Import hardcoded database structure
try:
    from mfg_data import Y_TZP_DENTAL_DATA
except ImportError as e:
    print(f"Error: Failed to import Y_TZP_DENTAL_DATA from mfg_data.py. Details: {e}", file=sys.stderr)
    sys.exit(1)

# Initialize the MCP Server
server = Server("y-tzp-mfg-server")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List the tools exposed by this MCP server.
    """
    return [
        types.Tool(
            name="get_material_baselines",
            description=(
                "Returns the baseline mechanical properties (fracture toughness, flexural strength) "
                "and recommended DLP print parameters (layer thickness range, sintering temperature profile) "
                "for Y-TZP Zirconia dental applications."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="get_additive_insights",
            description=(
                "Returns the pros, cons, and concentrations for common Y-TZP toughness additives "
                "(Alumina and Ceria)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "additive_name": {
                        "type": "string",
                        "enum": ["Alumina (Al2O3)", "Ceria (CeO2)"],
                        "description": "Optional name of the additive to retrieve. If omitted, returns all additives."
                    }
                },
                "required": []
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict
) -> list[types.TextContent] | types.CallToolResult:
    """
    Execute tool logic based on the requested name and arguments.
    Gracefully handles exceptions and input validation mismatches.
    """
    try:
        if name == "get_material_baselines":
            baselines = {
                "material": Y_TZP_DENTAL_DATA.get("material"),
                "dental_applications": Y_TZP_DENTAL_DATA.get("dental_applications"),
                "baseline_mechanical_properties": Y_TZP_DENTAL_DATA.get("baseline_mechanical_properties"),
                "dlp_print_parameters": Y_TZP_DENTAL_DATA.get("dlp_print_parameters")
            }
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(baselines, indent=2, ensure_ascii=False)
                )
            ]

        elif name == "get_additive_insights":
            additive_name = arguments.get("additive_name")
            additives = Y_TZP_DENTAL_DATA.get("toughness_additives", {})

            if additive_name:
                if additive_name in additives:
                    result_data = {additive_name: additives[additive_name]}
                else:
                    # Attempt a case-insensitive fallback lookup
                    matched_key = None
                    for key in additives:
                        if additive_name.lower() in key.lower():
                            matched_key = key
                            break
                    if matched_key:
                        result_data = {matched_key: additives[matched_key]}
                    else:
                        raise ValueError(
                            f"Additive '{additive_name}' not found. "
                            f"Available options are: {list(additives.keys())}"
                        )
            else:
                result_data = additives

            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(result_data, indent=2, ensure_ascii=False)
                )
            ]

        else:
            raise ValueError(f"Tool '{name}' is not registered on this server.")

    except Exception as e:
        # Return a CallToolResult indicating an error occurred during execution
        return types.CallToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text=f"Error executing tool '{name}': {str(e)}"
                )
            ],
            isError=True
        )

async def main():
    # Diagnostic logs should always go to stderr to prevent stdio protocol corruption
    print("Starting Y-TZP Manufacturing MCP Server...", file=sys.stderr)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
