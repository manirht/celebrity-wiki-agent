#!/usr/bin/env python3
"""Real MCP server for web search and content fetching using official MCP SDK.

This server implements the Model Context Protocol (MCP) specification using
the official Python SDK. It exposes two tools:
- web_search: Search the web using Tavily API
- fetch_page: Fetch and extract readable content from a web page

The server communicates via STDIO using the MCP protocol.
Run with: python -m app.mcp_servers.remote_search_server
"""

import asyncio
import json
import os
from typing import Any

import httpx
from bs4 import BeautifulSoup
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from tavily import TavilyClient

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


# Initialize MCP server
app = Server("remote-search-server")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="web_search",
            description="Search the web using Tavily API. Returns a list of search results with title, URL, and snippet.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query string",
                    },
                    "num_results": {
                        "type": "integer",
                        "description": "Number of results to return (default: 5)",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="fetch_page",
            description="Fetch a web page and extract readable text content. Returns the page title and cleaned text content.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL of the page to fetch",
                    },
                },
                "required": ["url"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls."""

    if name == "web_search":
        return await handle_web_search(arguments)
    elif name == "fetch_page":
        return await handle_fetch_page(arguments)
    else:
        raise ValueError(f"Unknown tool: {name}")


async def handle_web_search(arguments: dict) -> list[TextContent]:
    """Handle web_search tool call."""

    query = arguments.get("query", "")
    num_results = arguments.get("num_results", 5)

    tavily_key = os.environ.get("TAVILY_API_KEY", "")
    if not tavily_key:
        return [TextContent(
            type="text",
            text="Error: TAVILY_API_KEY environment variable not set"
        )]

    try:
        # Initialize Tavily client
        client = TavilyClient(api_key=tavily_key)

        # Perform search in executor (Tavily client is synchronous)
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.search(
                query=query,
                max_results=num_results,
                include_answer=False,
                include_raw_content=False
            )
        )

        # Parse results
        results = []
        for item in response.get("results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("content", ""),  # Tavily uses "content" for snippet
            })

        # Return as JSON string
        return [TextContent(
            type="text",
            text=json.dumps(results, ensure_ascii=False, indent=2)
        )]

    except Exception as exc:
        return [TextContent(
            type="text",
            text=f"Error calling Tavily API: {exc}"
        )]


async def handle_fetch_page(arguments: dict) -> list[TextContent]:
    """Handle fetch_page tool call."""

    url = arguments.get("url", "")
    if not url:
        # Return JSON error
        error_result = {"url": "", "title": "", "content": "", "error": "URL is required"}
        return [TextContent(
            type="text",
            text=json.dumps(error_result, ensure_ascii=False, indent=2)
        )]

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            html = resp.text
        except Exception as exc:
            # Return JSON error
            error_result = {
                "url": url,
                "title": "",
                "content": "",
                "error": f"Error fetching page: {exc}"
            }
            return [TextContent(
                type="text",
                text=json.dumps(error_result, ensure_ascii=False, indent=2)
            )]

    # Extract text using BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")

    # Remove script and style elements
    for script_or_style in soup(["script", "style", "noscript"]):
        script_or_style.decompose()

    # Get title
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else ""

    # Get text
    text = " ".join(soup.stripped_strings)

    # Limit content length
    max_chars = 10000
    if len(text) > max_chars:
        text = text[:max_chars] + "\n... (truncated)"

    # Return as JSON
    result = {
        "url": url,
        "title": title,
        "content": text
    }

    return [TextContent(
        type="text",
        text=json.dumps(result, ensure_ascii=False, indent=2)
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

