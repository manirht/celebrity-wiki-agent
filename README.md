# Celebrity Wiki Agent (LLM + Tools + Citations)

This project implements a command-line Celebrity Wiki Agent using:

- **LLM**: Groq Qwen model (qwen/qwen3-32b)
- **Orchestration**: LangChain + LangGraph
- **Web Search**: Tavily API via MCP server
- **Weather API**: Open-Meteo (free, no API key required)
- **File System**: Local MCP-style STDIO server for writing outputs

The agent:

- Reads a CSV of 5 famous people from different domains
- For each person, gathers facts and citations from the web
- Fetches current weather in the person's birth city via a weather API tool
- Generates **two outputs per person**:
  - A structured JSON file containing enriched data + citations
  - A Markdown report with a human-readable summary and citations

## People

The default input CSV (`data/celebrities.csv`) contains:

| Name | Domain |
|------|--------|
| P. V. Sindhu | Sport |
| Leonardo DiCaprio | Movies |
| Dr. A. P. J. Abdul Kalam | Academia/Science |
| Ratan Tata | Business |
| Arijit Singh | Music |

## Prerequisites

- Python 3.10+
- [Groq API Key](https://console.groq.com/) - for the Qwen LLM
- [Tavily API Key](https://tavily.com/) - for web search

## Installation

1. **Clone or extract the project**

2. **Create a virtual environment**
   ```bash
   cd Day-3
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   ```
   Then edit `.env` and add your API keys:
   ```
   GROQ_API_KEY=your_groq_api_key_here
   TAVILY_API_KEY=your_tavily_api_key_here
   ```

## Usage

Run the agent:

```bash
python -m app.main
```

The agent will:
1. Load the celebrities from `data/celebrities.csv`
2. For each person, search the web for biography information
3. Extract facts and birthplace using the LLM
4. Fetch weather for the birth city
5. Generate structured JSON and Markdown reports

## Output

After running, you'll find:

- `outputs/structured/` - JSON files with enriched data
  - Example: `p_v_sindhu.json`, `leonardo_dicaprio.json`
- `outputs/reports/` - Markdown reports with citations
  - Example: `p_v_sindhu.md`, `leonardo_dicaprio.md`

## Project Structure

```
Celebrity Agent/
├── app/
│   ├── __init__.py
│   ├── config.py             # Configuration (API keys, paths)
│   ├── main.py               # CLI entrypoint
│   ├── models.py             # Data models (PersonInput, EnrichedPerson, etc.)
│   ├── formatting/
│   │   └── markdown.py       # Markdown report generator
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── graph_builder.py  # LangGraph workflow builder
│   │   ├── nodes.py          # Graph nodes (enrich, write)
│   │   └── state.py          # Graph state definition
│   ├── mcp_servers/
│   │   ├── __init__.py
│   │   ├── local_fs_stdio_server.py   # File system MCP server
│   │   └── remote_search_server.py    # Web search MCP server
│   └── tools/
│       ├── __init__.py
│       ├── local_fs_client.py      # File system tool client
│       ├── remote_search_client.py # Search tool client
│       └── weather_tool.py         # Weather API tool
├── data/
│   └── celebrities.csv       # Input data
├── outputs/                  # Generated at runtime
│   ├── reports/              # Markdown reports
│   └── structured/           # JSON outputs
├── logs/                     # Log files (created at runtime)
├── .env.example              # Example environment config
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## How It Works

1. **MCP Servers**: The project uses Model Context Protocol (MCP) for tool communication:
   - `remote_search_server.py` - Handles web search via Tavily API
   - `local_fs_stdio_server.py` - Handles file system operations

2. **LangGraph Workflow**: Two-node graph for each person:
   - `enrich` node: Collects sources, extracts facts with LLM, fetches weather
   - `write` node: Generates and saves JSON + Markdown outputs

3. **LLM Processing**: Uses Groq's Qwen3-32B model to:
   - Extract structured facts from web sources
   - Synthesize coherent sections with proper citations

## Troubleshooting

- **"GROQ_API_KEY environment variable is not set"**: Make sure you've created `.env` file with your API key
- **"Error calling Tavily API"**: Check your Tavily API key is valid
- **Weather shows "No city provided"**: The LLM couldn't extract birthplace from sources (this can vary)

## Dependencies

See `requirements.txt`:
- `langchain-core`, `langchain-groq`, `langgraph` - LLM orchestration
- `mcp` - Model Context Protocol SDK
- `httpx`, `beautifulsoup4`, `lxml` - Web scraping
- `tavily-python` - Web search API
- `pydantic` - Data validation
- `python-dotenv` - Environment variables
