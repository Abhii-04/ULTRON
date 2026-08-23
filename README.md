# ULTRON

ULTRON is a small LangGraph multi-agent assistant. The top-level graph routes each user request to one focused workflow:

```text
User request
    |
    v
Orchestrator
    |
    +-- Gmail Agent     -> Gmail OAuth search/draft workflow
    +-- LinkedIn Agent  -> LinkedIn MCP tools
    +-- Internet Agent  -> Tavily search
    +-- Assistant Agent -> general reasoning and local skills
```

## Features

| Area | What it does |
| --- | --- |
| Routing | Sends Gmail, LinkedIn, internet, and general requests to separate subgraphs. |
| Skills | Agents can load local instructions from `skills/<skill>/SKILL.md` through `read_skill`. |
| Internet | Uses Tavily for current or source-backed web research. |
| Gmail | Searches Gmail and creates drafts through Gmail OAuth helpers. |
| LinkedIn | Loads approved LinkedIn MCP tools from `mcp_config.json`. |
| Memory | Uses process-local LangGraph checkpointing and profile storage. |

## Project Structure

```text
.
+-- main.py
+-- mcp_config.json
+-- pyproject.toml
+-- skills/
|   +-- internet_search/SKILL.md
|   +-- linkedin/SKILL.md
|   +-- playwright/SKILL.md
+-- src/
    +-- agent.py
    +-- state.py
    +-- subgraphs/
    |   +-- assistant.py
    |   +-- gmail_agent.py
    |   +-- internet_agent.py
    |   +-- linkedin_agent.py
    +-- tools/
        +-- Gmail.py
        +-- mcp.py
        +-- read_skill.py
        +-- tavily.py
```

## Setup

```bash
uv sync
```

Create `.env`:

```bash
DEEPSEEK_API_KEY=your_deepseek_key
TAVILY_API_KEY=your_tavily_key
```

Optional Gmail files at the repo root:

```text
credentials.json
token.json
```

Optional LinkedIn MCP setup is configured in `mcp_config.json`.

## Run

```bash
uv run python main.py
```

Example prompts:

```text
search the web for the latest LangGraph MCP examples
search my gmail for invoices from today
search linkedin for entry level AI jobs in Bengaluru
write a short project update for this repo
```

Exit with `quit` or `exit`.

## Validation

There is no committed test suite in the cleaned repo. Basic validation:

```bash
python -m compileall main.py src
```

For graph-level smoke testing, instantiate `Agent`, attach stub subgraphs, and call `build_graph()` without external services.
