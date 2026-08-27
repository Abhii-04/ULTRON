# ULTRON

ULTRON is a Python LangGraph multi-agent assistant that routes user requests across specialized workflows for general assistance, web research, Gmail, LinkedIn, and local file operations. It uses DeepSeek through the OpenAI-compatible LangChain client, LangGraph state machines, MCP tool sessions, Tavily search, Gmail OAuth tooling, and human-in-the-loop approval for sensitive actions.

```text
User request
    |
    v
Dynamic route selection
    |
    +-- Direct route: LinkedIn / Internet
    |
    v
Orchestrator with file tools and handoff tools
    |
    +-- transfer_to_gmail     -> Gmail OAuth search/draft workflow
    +-- transfer_to_linkedin  -> LinkedIn MCP job/company/post tools
    +-- transfer_to_internet  -> Tavily-backed web research
    +-- transfer_to_assistant -> general reasoning and local skills
```

## Resume Highlights

- Built a LangGraph-based multi-agent orchestrator in Python with custom handoff tools routing task instructions across assistant, internet, Gmail, LinkedIn, and file workflows.
- Implemented human-in-the-loop safety for risky LangChain tools, interrupting create/write/delete file and Gmail draft/send actions until explicit user approval before execution.
- Integrated Tavily, Google Gmail Toolkit, and LinkedIn MCP sessions with structured tools, output compaction, redaction, and resilient provider failure handling.
- Designed custom context handoffs using LangGraph Commands and injected state to transfer control between specialized subgraphs while preserving task instructions.

## Features

| Area | What it does |
| --- | --- |
| Routing | Uses keyword-based pre-routing plus an LLM orchestrator to send requests to focused LangGraph subgraphs. |
| Handoffs | Creates custom LangGraph handoff tools that pass task instructions, preserve state, and transfer control with `Command(goto=...)`. |
| Skills | Agents can load local instructions from `skills/<skill>/SKILL.md` through `read_skill`. |
| Internet | Uses Tavily for current or source-backed web research and filters noisy or inaccessible result content. |
| Gmail | Searches Gmail and creates drafts through Gmail OAuth helpers, compacting results and redacting sensitive snippets. |
| LinkedIn | Loads approved LinkedIn MCP tools from `mcp_config.json`, keeps stdio sessions open, and trims large job-search outputs. |
| Safety | Wraps risky file and Gmail tools with human approval interrupts before execution. |
| Memory | Uses process-local LangGraph checkpointing and in-memory profile storage. |
| Terminal UI | Provides a Rich-powered CLI with setup status, latency summaries, approval prompts, and interrupt handling. |

## Architecture

The main `Agent` builds one top-level `StateGraph` with four compiled subgraphs: `Assistant`, `InternetAgent`, `Gmail_agent`, and `LinkedinAgent`. The graph first applies dynamic route selection for obvious LinkedIn or internet requests. Other requests go through the orchestrator, which can either execute local file tools or call a handoff tool that transfers the task to a specialized subgraph with explicit task instructions.

Each LLM-backed agent binds only the tools needed for its domain. The internet workflow uses Tavily and Headroom compression for long tool outputs. The LinkedIn workflow starts MCP sessions from `mcp_config.json`, filters available MCP tools to job/company/post operations, and compacts search results before returning them to the model. The Gmail workflow uses LangChain Google Community Gmail tools behind thread-safe wrappers and exposes deterministic search and draft nodes.

Sensitive actions are gated by LangGraph interrupts. File creation, file writes, file deletion, Gmail draft creation, and Gmail sending pause execution until the terminal user approves or rejects the operation.

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
    +-- nodes/
    |   +-- context_handoff.py
    |   +-- dynamic_agent_selection.py
    |   +-- dynamic_prompt.py
    |   +-- HITL.py
    +-- tools/
        +-- Gmail.py
        +-- fileManagment.py
        +-- linkedin_tool.py
        +-- mcp.py
        +-- read_skill.py
        +-- tavily.py
```

## Setup

```bash
uv sync
```

Or install with pip:

```bash
pip install -r requirements.txt
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
