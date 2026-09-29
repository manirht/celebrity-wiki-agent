#!/usr/bin/env python3
"""Real MCP server for filesystem operations using official MCP SDK.

This server implements the Model Context Protocol (MCP) specification using
the official Python SDK. It exposes two tools:
- fs_mkdir: Create a directory
- fs_write_file: Write content to a file

The server communicates via STDIO using the MCP protocol.
Run with: python -m app.mcp_servers.local_fs_stdio_server
"""

import asyncio
import json
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent


# Initialize MCP server
app = Server("local-fs-server")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="fs_mkdir",
            description="Create a directory (and any necessary parent directories).",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The directory path to create",
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="fs_write_file",
            description="Write content to a file. Creates parent directories if needed.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The file path to write to",
                    },
                    "content": {
                        "type": "string",
                        "description": "The content to write to the file",
                    },
                },
                "required": ["path", "content"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls."""

    if name == "fs_mkdir":
        return await handle_mkdir(arguments)
    elif name == "fs_write_file":
        return await handle_write_file(arguments)
    else:
        raise ValueError(f"Unknown tool: {name}")


async def handle_mkdir(arguments: dict) -> list[TextContent]:
    """Handle fs_mkdir tool call."""

    path_str = arguments.get("path", "")
    if not path_str:
        return [TextContent(
            type="text",
            text="Error: path is required"
        )]

    try:
        path = Path(path_str)
        path.mkdir(parents=True, exist_ok=True)

        result = {
            "status": "ok",
            "message": f"Created directory: {path}",
            "path": str(path)
        }

        return [TextContent(
            type="text",
            text=json.dumps(result, ensure_ascii=False, indent=2)
        )]
    except Exception as exc:
        return [TextContent(
            type="text",
            text=f"Error creating directory: {exc}"
        )]


async def handle_write_file(arguments: dict) -> list[TextContent]:
    """Handle fs_write_file tool call."""

    path_str = arguments.get("path", "")
    content = arguments.get("content", "")

    if not path_str:
        return [TextContent(
            type="text",
            text="Error: path is required"
        )]

    try:
        path = Path(path_str)
        # Create parent directories if needed
        path.parent.mkdir(parents=True, exist_ok=True)
        # Write the file
        path.write_text(content, encoding="utf-8")

        result = {
            "status": "ok",
            "message": f"Wrote file: {path}",
            "path": str(path),
            "bytes_written": len(content.encode("utf-8"))
        }

        return [TextContent(
            type="text",
            text=json.dumps(result, ensure_ascii=False, indent=2)
        )]
    except Exception as exc:
        return [TextContent(
            type="text",
            text=f"Error writing file: {exc}"
        )]


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())

