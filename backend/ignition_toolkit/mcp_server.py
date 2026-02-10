"""
Ignition Toolbox MCP Server

Exposes Ignition Toolbox capabilities to Claude Code and Claude Desktop
via the Model Context Protocol (MCP) over stdio transport.

This is a thin bridge that proxies requests to the running FastAPI backend.

Usage:
    python -m ignition_toolkit.mcp_server

Configuration:
    TOOLBOX_API_URL - Backend URL (default: http://localhost:5000)

Add to claude_desktop_config.json or .mcp.json:
    {
        "mcpServers": {
            "ignition-toolbox": {
                "command": "python",
                "args": ["-m", "ignition_toolkit.mcp_server"]
            }
        }
    }
"""

import asyncio
import json
import logging
import os
from typing import Any
from urllib.parse import quote

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Resource, TextContent, Tool

logger = logging.getLogger(__name__)

# Backend URL (configurable via environment variable)
TOOLBOX_API_URL = os.environ.get("TOOLBOX_API_URL", "http://localhost:5000")

# HTTP client timeout
HTTP_TIMEOUT = 30.0


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

async def _request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Make an HTTP request to the Toolbox backend and return parsed JSON."""
    url = f"{TOOLBOX_API_URL}{path}"
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            resp = await client.request(method, url, params=params, json=json_body)
            resp.raise_for_status()
            return resp.json()
    except httpx.ConnectError:
        return {"error": f"Cannot connect to Toolbox backend at {TOOLBOX_API_URL}. Is it running?"}
    except httpx.HTTPStatusError as exc:
        try:
            detail = exc.response.json()
        except Exception:
            detail = exc.response.text
        return {"error": f"HTTP {exc.response.status_code}", "detail": detail}
    except Exception as exc:
        return {"error": str(exc)}


async def _get(path: str, **params: Any) -> dict[str, Any]:
    filtered = {k: v for k, v in params.items() if v is not None}
    return await _request("GET", path, params=filtered or None)


async def _post(path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    return await _request("POST", path, json_body=body)


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

TOOLS: list[Tool] = [
    Tool(
        name="list_playbooks",
        description="List all available playbooks in the Ignition Toolbox",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="get_playbook",
        description="Get detailed information about a specific playbook including its steps",
        inputSchema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Playbook path (e.g. 'gateway/check-gateway-status.yaml')"},
            },
            "required": ["path"],
        },
    ),
    Tool(
        name="run_playbook",
        description="Execute a playbook against an Ignition Gateway",
        inputSchema={
            "type": "object",
            "properties": {
                "playbook_path": {"type": "string", "description": "Path to the playbook file"},
                "credential_name": {"type": "string", "description": "Name of stored credential to use"},
                "gateway_url": {"type": "string", "description": "Gateway URL (e.g. http://localhost:8088)"},
                "parameters": {"type": "object", "description": "Playbook parameters (key-value pairs)"},
                "debug": {"type": "boolean", "description": "Enable debug mode", "default": False},
            },
            "required": ["playbook_path"],
        },
    ),
    Tool(
        name="list_executions",
        description="List playbook execution history",
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max results to return", "default": 20},
                "status": {"type": "string", "description": "Filter by status (running, completed, failed, cancelled)"},
            },
            "required": [],
        },
    ),
    Tool(
        name="get_execution",
        description="Get detailed status and step results for a specific execution",
        inputSchema={
            "type": "object",
            "properties": {
                "execution_id": {"type": "string", "description": "Execution ID"},
            },
            "required": ["execution_id"],
        },
    ),
    Tool(
        name="cancel_execution",
        description="Cancel a running playbook execution",
        inputSchema={
            "type": "object",
            "properties": {
                "execution_id": {"type": "string", "description": "Execution ID to cancel"},
            },
            "required": ["execution_id"],
        },
    ),
    Tool(
        name="get_system_health",
        description="Get detailed system health status including component-level information",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="get_logs",
        description="Get recent backend logs with optional filtering",
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max log entries (1-1000)", "default": 100},
                "level": {"type": "string", "description": "Filter by level: DEBUG, INFO, WARNING, ERROR"},
                "logger_filter": {"type": "string", "description": "Filter by logger name (substring match)"},
            },
            "required": [],
        },
    ),
    Tool(
        name="search_logs",
        description="Search logs by logger name pattern",
        inputSchema={
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Logger name pattern to search for"},
                "limit": {"type": "integer", "description": "Max results", "default": 100},
                "level": {"type": "string", "description": "Filter by level: DEBUG, INFO, WARNING, ERROR"},
            },
            "required": ["pattern"],
        },
    ),
    Tool(
        name="list_credentials",
        description="List stored credentials (names and metadata only, no secrets exposed)",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="test_gateway",
        description="Test connectivity to an Ignition Gateway",
        inputSchema={
            "type": "object",
            "properties": {
                "gateway_url": {"type": "string", "description": "Gateway URL (e.g. http://localhost:8088)"},
                "api_key_name": {"type": "string", "description": "Name of stored API key for authentication"},
            },
            "required": ["gateway_url"],
        },
    ),
    Tool(
        name="gateway_request",
        description="Execute a raw API request against an Ignition Gateway",
        inputSchema={
            "type": "object",
            "properties": {
                "gateway_url": {"type": "string", "description": "Gateway URL (e.g. http://localhost:8088)"},
                "method": {"type": "string", "description": "HTTP method", "default": "GET"},
                "path": {"type": "string", "description": "API path (e.g. /data/api/v1/gateway-info)"},
                "api_key_name": {"type": "string", "description": "Name of stored API key for authentication"},
                "headers": {"type": "object", "description": "Additional request headers"},
                "query_params": {"type": "object", "description": "Query parameters"},
                "body": {"description": "Request body (for POST/PUT)"},
            },
            "required": ["gateway_url", "path"],
        },
    ),
]


# ---------------------------------------------------------------------------
# Tool dispatch
# ---------------------------------------------------------------------------

async def _handle_tool(name: str, arguments: dict[str, Any]) -> str:
    """Dispatch a tool call to the appropriate backend endpoint."""

    if name == "list_playbooks":
        result = await _get("/api/playbooks")

    elif name == "get_playbook":
        encoded_path = quote(arguments["path"], safe="")
        result = await _get(f"/api/playbooks/{encoded_path}")

    elif name == "run_playbook":
        body = {
            "playbook_path": arguments["playbook_path"],
            "parameters": arguments.get("parameters", {}),
        }
        if arguments.get("credential_name"):
            body["credential_name"] = arguments["credential_name"]
        if arguments.get("gateway_url"):
            body["gateway_url"] = arguments["gateway_url"]
        if arguments.get("debug"):
            body["debug_mode"] = arguments["debug"]
        result = await _post("/api/executions", body)

    elif name == "list_executions":
        result = await _get(
            "/api/executions",
            limit=arguments.get("limit", 20),
            status=arguments.get("status"),
        )

    elif name == "get_execution":
        result = await _get(f"/api/executions/{arguments['execution_id']}")

    elif name == "cancel_execution":
        result = await _post(f"/api/executions/{arguments['execution_id']}/cancel")

    elif name == "get_system_health":
        result = await _get("/health/detailed")

    elif name == "get_logs":
        result = await _get(
            "/api/logs",
            limit=arguments.get("limit", 100),
            level=arguments.get("level"),
            logger_filter=arguments.get("logger_filter"),
        )

    elif name == "search_logs":
        result = await _get(
            "/api/logs",
            limit=arguments.get("limit", 100),
            level=arguments.get("level"),
            logger_filter=arguments["pattern"],
        )

    elif name == "list_credentials":
        result = await _get("/api/credentials")

    elif name == "test_gateway":
        body = {"gateway_url": arguments["gateway_url"]}
        if arguments.get("api_key_name"):
            body["api_key_name"] = arguments["api_key_name"]
        result = await _post("/api/explorer/test-connection", body)

    elif name == "gateway_request":
        body: dict[str, Any] = {
            "gateway_url": arguments["gateway_url"],
            "method": arguments.get("method", "GET"),
            "path": arguments["path"],
        }
        for key in ("api_key_name", "headers", "query_params", "body"):
            if arguments.get(key) is not None:
                body[key] = arguments[key]
        result = await _post("/api/explorer/request", body)

    else:
        result = {"error": f"Unknown tool: {name}"}

    return json.dumps(result, indent=2, default=str)


# ---------------------------------------------------------------------------
# MCP Server setup
# ---------------------------------------------------------------------------

def create_server() -> Server:
    """Create and configure the MCP server."""
    server = Server("ignition-toolbox")

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        return TOOLS

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict[str, Any] | None) -> list[TextContent]:
        text = await _handle_tool(name, arguments or {})
        return [TextContent(type="text", text=text)]

    @server.list_resources()
    async def handle_list_resources() -> list[Resource]:
        return [
            Resource(
                uri="playbook://{path}",
                name="Playbook",
                description="Get playbook details by path (e.g. playbook://gateway/check-gateway-status.yaml)",
                mimeType="application/json",
            ),
            Resource(
                uri="execution://{id}",
                name="Execution",
                description="Get execution status and results by ID",
                mimeType="application/json",
            ),
        ]

    @server.read_resource()
    async def handle_read_resource(uri: str) -> str:
        uri_str = str(uri)
        if uri_str.startswith("playbook://"):
            path = uri_str[len("playbook://"):]
            encoded_path = quote(path, safe="")
            result = await _get(f"/api/playbooks/{encoded_path}")
            return json.dumps(result, indent=2, default=str)

        elif uri_str.startswith("execution://"):
            execution_id = uri_str[len("execution://"):]
            result = await _get(f"/api/executions/{execution_id}")
            return json.dumps(result, indent=2, default=str)

        else:
            return json.dumps({"error": f"Unknown resource URI: {uri_str}"})

    return server


async def main() -> None:
    """Run the MCP server with stdio transport."""
    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
