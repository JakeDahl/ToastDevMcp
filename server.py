#!/usr/bin/env python3
import asyncio
import json
import logging
from typing import Any
import requests
import yaml
from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("toast-api-server")

# Toast API specification URLs
TOAST_SPECS = {
    "reporting": "https://doc.toasttab.com/toast-api-specifications/toast-reporting-api.yaml",
    "authentication": "https://doc.toasttab.com/toast-api-specifications/toast-authentication-api.yaml",
    "cashmgmt": "https://doc.toasttab.com/toast-api-specifications/toast-cashmgmt-api.yaml",
    "config": "https://doc.toasttab.com/toast-api-specifications/toast-config-api.yaml",
    "ccpartner": "https://doc.toasttab.com/toast-api-specifications/toast-ccpartner-api.yaml",
    "kitchen": "https://doc.toasttab.com/openapi/kitchen/overview/",
    "labor": "https://doc.toasttab.com/openapi/labor/overview/",
    "menus": "https://doc.toasttab.com/openapi/menus/overview/",
    "menus-v3": "https://doc.toasttab.com/toast-api-specifications/toast-menus-api-v3.yaml",
    "ordermgmt-config": "https://doc.toasttab.com/toast-api-specifications/toast-ordermgmt-config-api-docs.yaml",
    "orders": "https://doc.toasttab.com/toast-api-specifications/toast-orders-api.yaml",
    "packaging": "https://doc.toasttab.com/openapi/packaging/overview/",
    "partners": "https://doc.toasttab.com/openapi/partners/overview/",
    "rx-availability": "https://doc.toasttab.com/openapi/rx.availability.service/overview/",
    "restaurants": "https://doc.toasttab.com/toast-api-specifications/toast-restaurants-api.yaml",
    "stock": "https://doc.toasttab.com/toast-api-specifications/toast-stock-api.yaml",
    "giftcard-integration": "https://doc.toasttab.com/toast-api-specifications/toast-integrations-giftcard-api.yaml",
    "loyalty-integration": "https://doc.toasttab.com/toast-api-specifications/toast-integrations-loyalty-api.yaml",
    "tender-integration": "https://doc.toasttab.com/toast-api-specifications/toast-tender-api.yaml",
}

# Cache for specifications
specs_cache = {}

def fetch_yaml_spec(spec_name: str) -> dict:
    """Fetch and parse a YAML specification from Toast documentation."""
    if spec_name in specs_cache:
        return specs_cache[spec_name]
        
    if spec_name not in TOAST_SPECS:
        raise ValueError(f"Unknown spec: {spec_name}. Available specs: {', '.join(TOAST_SPECS.keys())}")
    
    url = TOAST_SPECS[spec_name]
    logger.info(f"Fetching YAML spec from {url}")
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        spec_data = yaml.safe_load(response.text)
        specs_cache[spec_name] = spec_data
        return spec_data
    except requests.RequestException as e:
        raise Exception(f"Failed to fetch spec from {url}: {str(e)}")
    except yaml.YAMLError as e:
        raise Exception(f"Failed to parse YAML from {url}: {str(e)}")

# Create the server
app = Server("toast-api-server")

@app.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools."""
    return [
        types.Tool(
            name="list_toast_specs",
            description="List all available Toast API specifications",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="get_toast_spec",
            description="Get the full YAML specification for a Toast API. Available specs: reporting, authentication, cashmgmt, config, ccpartner, kitchen, labor, menus, menus-v3, ordermgmt-config, orders, packaging, partners, rx-availability, restaurants, stock, giftcard-integration, loyalty-integration, tender-integration",
            inputSchema={
                "type": "object",
                "properties": {
                    "spec_name": {
                        "type": "string",
                        "description": "The name of the spec to retrieve. Use list_toast_specs to see all available specs."
                    }
                },
                "required": ["spec_name"]
            }
        ),
        types.Tool(
            name="get_toast_endpoints",
            description="Get all endpoints/paths from a Toast API specification",
            inputSchema={
                "type": "object",
                "properties": {
                    "spec_name": {
                        "type": "string",
                        "description": "The name of the spec. Use list_toast_specs to see all available specs."
                    }
                },
                "required": ["spec_name"]
            }
        ),
        types.Tool(
            name="get_toast_endpoint_details",
            description="Get detailed information about a specific endpoint in a Toast API",
            inputSchema={
                "type": "object",
                "properties": {
                    "spec_name": {
                        "type": "string",
                        "description": "The name of the spec. Use list_toast_specs to see all available specs."
                    },
                    "endpoint_path": {
                        "type": "string",
                        "description": "The path of the endpoint (e.g., /v2/reports)"
                    }
                },
                "required": ["spec_name", "endpoint_path"]
            }
        ),
        types.Tool(
            name="search_toast_spec",
            description="Search for specific content within a Toast API specification",
            inputSchema={
                "type": "object",
                "properties": {
                    "spec_name": {
                        "type": "string",
                        "description": "The name of the spec. Use list_toast_specs to see all available specs."
                    },
                    "search_term": {
                        "type": "string",
                        "description": "The term to search for in the specification"
                    }
                },
                "required": ["spec_name", "search_term"]
            }
        )
    ]

@app.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool calls."""
    try:
        if name == "list_toast_specs":
            specs_list = [
                {"name": spec_name, "url": url}
                for spec_name, url in TOAST_SPECS.items()
            ]
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(specs_list, indent=2)
                )
            ]
        
        elif name == "get_toast_spec":
            spec_name = arguments.get("spec_name")
            spec_data = fetch_yaml_spec(spec_name)
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(spec_data, indent=2)
                )
            ]
        
        elif name == "get_toast_endpoints":
            spec_name = arguments.get("spec_name")
            spec_data = fetch_yaml_spec(spec_name)
            
            endpoints = []
            if "paths" in spec_data:
                for path, methods in spec_data["paths"].items():
                    for method, details in methods.items():
                        if isinstance(details, dict):
                            endpoints.append({
                                "path": path,
                                "method": method.upper(),
                                "summary": details.get("summary", ""),
                                "description": details.get("description", "")
                            })
            
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(endpoints, indent=2)
                )
            ]
        
        elif name == "get_toast_endpoint_details":
            spec_name = arguments.get("spec_name")
            endpoint_path = arguments.get("endpoint_path")
            spec_data = fetch_yaml_spec(spec_name)
            
            if "paths" not in spec_data or endpoint_path not in spec_data["paths"]:
                raise ValueError(f"Endpoint {endpoint_path} not found in {spec_name} specification")
            
            endpoint_data = spec_data["paths"][endpoint_path]
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(endpoint_data, indent=2)
                )
            ]
        
        elif name == "search_toast_spec":
            spec_name = arguments.get("spec_name")
            search_term = arguments.get("search_term", "").lower()
            spec_data = fetch_yaml_spec(spec_name)
            
            def search_recursive(obj, path=""):
                results = []
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        current_path = f"{path}.{key}" if path else key
                        if search_term in str(key).lower() or search_term in str(value).lower():
                            results.append({
                                "path": current_path,
                                "key": key,
                                "value": value if not isinstance(value, (dict, list)) else f"<{type(value).__name__}>"
                            })
                        if isinstance(value, (dict, list)):
                            results.extend(search_recursive(value, current_path))
                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        current_path = f"{path}[{i}]"
                        if search_term in str(item).lower():
                            results.append({
                                "path": current_path,
                                "value": item if not isinstance(item, (dict, list)) else f"<{type(item).__name__}>"
                            })
                        if isinstance(item, (dict, list)):
                            results.extend(search_recursive(item, current_path))
                return results
            
            search_results = search_recursive(spec_data)
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(search_results[:50], indent=2) + 
                         (f"\n\n... and {len(search_results) - 50} more results" if len(search_results) > 50 else "")
                )
            ]
        
        else:
            raise ValueError(f"Unknown tool: {name}")
    
    except Exception as e:
        logger.error(f"Error executing tool {name}: {str(e)}")
        raise

async def main():
    logger.info("Starting Toast API MCP Server")
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
