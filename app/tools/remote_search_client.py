from __future__ import annotations

"""LangChain tools that call the real MCP search server via STDIO.

These tools communicate with the MCP server defined in
`app.mcp_servers.remote_search_server` using the MCP protocol over STDIO.
"""

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Dict

from langchain_core.tools import tool

from app.config import PROJECT_ROOT


def _call_mcp_tool(tool_name: str, arguments: dict) -> str:
    """Call a tool on the remote MCP server via STDIO.

    Returns the text content from the MCP server response.
    """

    script = str(PROJECT_ROOT / "app" / "mcp_servers" / "remote_search_server.py")

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
    # Pass the current environment so the subprocess can access .env variables
    proc = subprocess.Popen(
        [sys.executable, script],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=os.environ.copy()
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

        # Check if we got any response
        if not tool_response_line.strip():
            stderr_output = proc.stderr.read() if proc.stderr else ""
            raise RuntimeError(f"Empty response from MCP server. Stderr: {stderr_output}")

        # Parse the tool response
        try:
            tool_response = json.loads(tool_response_line)
        except json.JSONDecodeError as e:
            stderr_output = proc.stderr.read() if proc.stderr else ""
            raise RuntimeError(f"Invalid JSON from MCP server: {tool_response_line}. Stderr: {stderr_output}") from e

        # Extract the text content from the response
        if "result" in tool_response and "content" in tool_response["result"]:
            content_list = tool_response["result"]["content"]
            if content_list and len(content_list) > 0:
                return content_list[0]["text"]

        raise RuntimeError(f"Unexpected MCP response format: {tool_response}")

    except Exception as exc:
        if proc.poll() is None:
            proc.kill()
        proc.wait()
        raise RuntimeError(f"Error calling MCP tool {tool_name}: {exc}") from exc


@tool("web_search")
def web_search(query: str, num_results: int = 5) -> List[Dict]:
    """Search the web using the remote MCP server.

    Returns a list of {title, url, snippet} dictionaries.
    """

    arguments = {"query": query, "num_results": num_results}
    result_text = _call_mcp_tool("web_search", arguments)

    # Parse the JSON result
    return json.loads(result_text)


@tool("fetch_page")
def fetch_page(url: str) -> Dict:
    """Fetch page content using the remote MCP server.

    Returns {url, title, content}. If there's an error, returns {url, title, content, error}.
    """

    arguments = {"url": url}
    result_text = _call_mcp_tool("fetch_page", arguments)

    # Parse the JSON result
    if not result_text or not result_text.strip():
        raise ValueError(f"Empty response from MCP server for fetch_page with url={url}")

    try:
        result = json.loads(result_text)
        # If there's an error field, we still return the result but the caller can check for it
        return result
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON from fetch_page: {result_text[:200]}") from e

