from __future__ import annotations

"""LangChain tools for the local STDIO filesystem MCP server.

These tools spawn the `local_fs_stdio_server` script as a subprocess and
communicate with it via STDIO using the official MCP protocol.

For the purposes of this assignment, starting a fresh process per call is
acceptable and keeps the implementation straightforward.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict

from langchain_core.tools import tool

from app.config import PROJECT_ROOT


def _call_mcp_tool(tool_name: str, arguments: dict) -> str:
    """Call a tool on the local filesystem MCP server via STDIO.

    Returns the text content from the MCP server response.
    """

    script = str(PROJECT_ROOT / "app" / "mcp_servers" / "local_fs_stdio_server.py")

    # Create the MCP protocol messages
    # 1. Initialize request
    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "celebrity-wiki-agent",
                "version": "1.0.0"
            }
        }
    }

    # 2. Tool call request
    tool_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }

    # Run the MCP server as a subprocess
    proc = subprocess.Popen(
        [sys.executable, script],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        assert proc.stdin and proc.stdout

        # Send initialize request
        proc.stdin.write(json.dumps(init_request) + "\n")
        proc.stdin.flush()

        # Read initialize response
        init_response = proc.stdout.readline()

        # Send tool call request
        proc.stdin.write(json.dumps(tool_request) + "\n")
        proc.stdin.flush()

        # Read tool call response
        tool_response_line = proc.stdout.readline()

        # Close and wait
        proc.stdin.close()
        proc.wait(timeout=30)

        # Parse the tool response
        tool_response = json.loads(tool_response_line)

        # Extract the text content from the response
        if "result" in tool_response and "content" in tool_response["result"]:
            content_list = tool_response["result"]["content"]
            if content_list and len(content_list) > 0:
                return content_list[0]["text"]

        raise RuntimeError(f"Unexpected MCP response format: {tool_response}")

    except Exception as exc:
        proc.kill()
        proc.wait()
        raise RuntimeError(f"Error calling MCP tool {tool_name}: {exc}") from exc


def _abs_path(relative: str) -> str:
    return str((PROJECT_ROOT / relative).resolve())


@tool("fs_mkdir")
def fs_mkdir(path: str) -> Dict:
    """Create a directory (and parents) under the project root via STDIO FS tool."""

    abs_path = _abs_path(path)
    result_text = _call_mcp_tool("fs_mkdir", {"path": abs_path})

    # Parse the JSON result
    return json.loads(result_text)


@tool("fs_write_file")
def fs_write_file(path: str, content: str) -> Dict:
    """Write a file under the project root via STDIO FS tool.

    The directory is created if needed. Existing files are overwritten.
    """

    abs_path = _abs_path(path)
    result_text = _call_mcp_tool("fs_write_file", {"path": abs_path, "content": content})

    # Parse the JSON result
    return json.loads(result_text)

