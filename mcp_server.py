import asyncio
import json
import sys
from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

# Import hardcoded database structure
try:
    from mfg_data import MATERIALS_DB
except ImportError as e:
    try:
        from mfg_data import Y_TZP_DENTAL_DATA
        MATERIALS_DB = {"Y-TZP Zirconia": Y_TZP_DENTAL_DATA}
    except Exception as inner_e:
        print(f"Error: Failed to import data from mfg_data.py. Details: {inner_e}", file=sys.stderr)
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
                "for a specified material."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "material_name": {
                        "type": "string",
                        "enum": ["Y-TZP Zirconia", "Alumina Bioceramics", "316L Stainless Steel"],
                        "default": "Y-TZP Zirconia",
                        "description": "The name of the material to query."
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="get_additive_insights",
            description=(
                "Returns the pros, cons, and concentrations for common toughness additives "
                "associated with the specified material."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "material_name": {
                        "type": "string",
                        "enum": ["Y-TZP Zirconia", "Alumina Bioceramics", "316L Stainless Steel"],
                        "default": "Y-TZP Zirconia",
                        "description": "The material for which you are querying additives."
                    },
                    "additive_name": {
                        "type": "string",
                        "description": "Optional name of the specific additive to retrieve. If omitted, returns all additives."
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
        # Determine the targeted material (defaulting to Zirconia)
        material_name = arguments.get("material_name", "Y-TZP Zirconia")
        if material_name not in MATERIALS_DB:
            # Fallback fuzzy match
            matched_material = None
            for key in MATERIALS_DB:
                if material_name.lower() in key.lower():
                    matched_material = key
                    break
            if matched_material:
                material_name = matched_material
            else:
                raise ValueError(
                    f"Material '{material_name}' not found. "
                    f"Available options are: {list(MATERIALS_DB.keys())}"
                )

        material_data = MATERIALS_DB[material_name]

        if name == "get_material_baselines":
            baselines = {
                "material": material_data.get("material"),
                "dental_applications": material_data.get("dental_applications"),
                "baseline_mechanical_properties": material_data.get("baseline_mechanical_properties"),
                "dlp_print_parameters": material_data.get("dlp_print_parameters")
            }
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(baselines, indent=2, ensure_ascii=False)
                )
            ]

        elif name == "get_additive_insights":
            additive_name = arguments.get("additive_name")
            additives = material_data.get("toughness_additives", {})

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
                            f"Additive '{additive_name}' not found for '{material_name}'. "
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
