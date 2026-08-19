# ULTRON

Although still in development but still quite useful for my day to day need and yess the readme file is AI generated ;)
ULTRON is a Python multi-agent assistant built with LangGraph. It routes each request to the right specialist workflow, then lets that workflow use the tools it is allowed to use.

The current build includes:

- A top-level orchestrator that routes between agents.
- A general assistant for writing, planning, summarizing, and reasoning.
- An internet research agent powered by Tavily.
- A Gmail workflow for search and draft creation through Gmail OAuth.
- A LinkedIn job research agent that loads LinkedIn MCP tools from `mcp_config.json`.
- Process-local conversation checkpoints and user profile memory through LangGraph.
- Unit tests for routing, LinkedIn agent behavior, and MCP result trimming.

If you want a small, hackable base for personal agents, tool-using subagents, and MCP-backed workflows, this repo is meant to be easy to fork and extend.

## Why This Exists

Most assistant projects start as one big agent with every tool attached. That gets messy quickly: the model uses the wrong tool, account actions bleed into research tasks, and prompts become hard to reason about.

ULTRON keeps the system split into focused subagents:

```text
User request
    |
    v
Orchestrator
    |
    +-- Gmail Agent       -> Gmail OAuth tools
    +-- LinkedIn Agent    -> LinkedIn MCP tools
    +-- Internet Agent    -> Tavily search
    +-- Assistant Agent   -> no external tools
```

Each subagent has its own prompt, boundaries, tools, graph, and tests.

## Features

| Area | What it does |
| --- | --- |
| Routing | Sends Gmail, LinkedIn, internet, and general requests to separate workflows. |
| LangGraph | Uses `StateGraph`, checkpointing, subgraphs, and tool nodes. |
| MCP | Loads MCP server definitions from `mcp_config.json` and exposes approved tools to agents. |
| Gmail | Searches Gmail, formats compact results, and creates drafts. The Gmail tool wrapper also includes read/thread/send helpers for future workflow nodes. |
| LinkedIn | Searches jobs, job details, saved jobs, companies, profiles, and hiring posts through MCP tools. |
| Internet | Uses Tavily for source-backed or current web research. |
| Memory | Uses `InMemorySaver` and `InMemoryStore` for process-local continuity. |
| Tests | Covers deterministic routing, LinkedIn tool routing, and MCP output trimming. |

## Project Structure

```text
.
+-- main.py                         # CLI entrypoint
+-- mcp_config.json                 # MCP server configuration
+-- pyproject.toml                  # Python dependencies
+-- src/
|   +-- agent.py                    # Top-level orchestrator graph
|   +-- state.py                    # Shared graph state
|   +-- tools/
|   |   +-- Gmail.py                # Gmail tool wrappers
|   |   +-- mcp.py                  # MCP loading, filtering, and LinkedIn result trimming
|   |   +-- tavily.py               # Internet search tool
|   |   +-- bash.py                 # Local shell tool placeholder
|   |   +-- filetools.py            # Local file tool placeholder
|   +-- subgraphs/
|       +-- assistant.py            # General assistant graph
|       +-- gmail_agent.py          # Gmail workflow graph
|       +-- internet_agent.py       # Web research graph
|       +-- linkedin_agent.py       # LinkedIn MCP graph
|       +-- subgraph_template.py    # Starting point for new subagents
+-- tests/
    +-- test_agent_routing.py
    +-- test_linkedin_agent.py
    +-- test_mcp_tools.py
```

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/<your-username>/Ultron.git
cd Ultron
uv sync
```

This project uses Python `>=3.11`.

### 2. Create your environment file

Create a `.env` file:

```bash
DEEPSEEK_API_KEY=your_deepseek_key
TAVILY_API_KEY=your_tavily_key
```

The current model configuration is in `src/agent.py` and the subagents:

```python
ChatOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    model="deepseek-v4-flash",
    base_url="https://api.deepseek.com",
)
```

You can replace this with any OpenAI-compatible provider supported by `langchain-openai`.

### 3. Optional: set up Gmail

For Gmail features, add Google OAuth files at the repo root:

```text
credentials.json
token.json
```

`credentials.json` comes from your Google Cloud OAuth client. `token.json` is created after the first authorization flow. Make sure the Gmail API is enabled for the Google Cloud project.

### 4. Optional: set up LinkedIn MCP

LinkedIn tools are loaded from `mcp_config.json`. The default config starts `mcp-server-linkedin` through `uvx` under `Xvfb`:

```json
{
  "mcpServers": {
    "mcp-server-linkedin": {
      "command": "bash",
      "args": ["-lc", "... uvx mcp-server-linkedin@latest ..."]
    }
  }
}
```

Install any system dependencies required by that MCP server, such as `Xvfb`, before using the LinkedIn workflow.

### 5. Run ULTRON

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

Exit with:

```text
quit
```

## Run Tests

```bash
uv run python -m unittest discover -s tests
```

## How Routing Works

The top-level graph lives in `src/agent.py`.

1. The orchestrator reads the latest user message.
2. Simple deterministic rules catch obvious Gmail and LinkedIn requests.
3. If no rule matches, the routing LLM returns one route word:
   - `gmail`
   - `linkedin`
   - `internet`
   - `assistant`
4. The selected subgraph runs and returns the final message.

This keeps account-specific actions away from general reasoning and web research.

## How To Add A New Tool

Tools can be simple Python functions or LangChain `StructuredTool` objects.

### 1. Create a tool file

Add a file under `src/tools/`, for example `src/tools/weather.py`:

```python
def get_weather(city: str) -> dict:
    """Get weather for a city."""
    return {
        "city": city,
        "summary": "Sunny",
    }
```

### 2. Attach the tool to a subagent

In the subagent that should use it:

```python
from src.tools.weather import get_weather

def setup(self):
    self.tools = [get_weather]
    self.memory = InMemorySaver()
    self.assistant_llm = llm().bind_tools(self.tools)
```

If the subagent uses a `ToolNode`, make sure the graph includes the tools node:

```python
graph_builder.add_node("tools", ToolNode(self.tools, handle_tool_errors=handle_tool_error))
graph_builder.add_conditional_edges(
    "agent",
    self.agent_router,
    {
        "tools": "tools",
        END: END,
    },
)
graph_builder.add_edge("tools", "agent")
```

### 3. Update the agent prompt

Add a short tool policy to the subagent system message:

```text
Use the weather tool only when the user asks for weather.
If required fields are missing, ask for them.
Do not invent weather data.
```

### 4. Add a focused test

At minimum, test routing and error handling. Keep the test small and tied to the behavior you changed.

## How To Add An MCP Server

Add the server to `mcp_config.json`:

```json
{
  "mcpServers": {
    "my-server": {
      "command": "uvx",
      "args": ["my-mcp-server@latest"],
      "env": {
        "MY_API_KEY": "value"
      }
    }
  }
}
```

MCP servers are loaded in `src/tools/mcp.py`.

By default, ULTRON filters MCP tools so only approved LinkedIn job tools are exposed:

```python
LINKEDIN_JOB_TOOL_NAMES = {
    "search_jobs",
    "get_job_details",
    "get_saved_jobs",
    "search_companies",
    "get_company_profile",
    "search_posts",
}
```

To expose more MCP tools:

1. Add the tool names to the allowlist.
2. Decide which subagent should receive them.
3. Update that subagent prompt with clear boundaries.
4. Add tests for the new routing/tool behavior.

## How To Add A New Subagent

Use the existing subgraphs as the pattern. `src/subgraphs/linkedin_agent.py` is the best example for a tool-calling agent. `src/subgraphs/gmail_agent.py` is the best example for a deterministic workflow.

### 1. Create a new subgraph

Create `src/subgraphs/calendar_agent.py`:

```python
import os

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from src.state import State


def llm():
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("api_key not found")
    return ChatOpenAI(
        api_key=api_key,
        model="deepseek-v4-flash",
        base_url="https://api.deepseek.com",
    )


class CalendarAgent:
    def __init__(self):
        self.calendar_llm = None
        self.tools = []
        self.memory = None
        self.graph = None

    async def setup(self, _state=None):
        self.memory = InMemorySaver()
        self.tools = []
        self.calendar_llm = llm().bind_tools(self.tools)

    def calendar_agent(self, state: State):
        messages = [
            SystemMessage(content="You are a calendar assistant."),
            *state["messages"],
        ]
        response = self.calendar_llm.invoke(messages)
        return {"messages": [response]}

    def router(self, state: State):
        if getattr(state["messages"][-1], "tool_calls", None):
            return "tools"
        return END

    async def build_graph(self):
        if self.memory is None:
            await self.setup()

        graph_builder = StateGraph(State)
        graph_builder.add_node("calendar_agent", self.calendar_agent)
        graph_builder.add_node("tools", ToolNode(self.tools))
        graph_builder.add_edge(START, "calendar_agent")
        graph_builder.add_conditional_edges(
            "calendar_agent",
            self.router,
            {"tools": "tools", END: END},
        )
        graph_builder.add_edge("tools", "calendar_agent")
        self.graph = graph_builder.compile(checkpointer=self.memory)

    async def run_superstep(self, message, _history):
        result = await self.graph.ainvoke({
            "messages": [HumanMessage(content=message)],
        })
        print(result["messages"][-1].content)
        return result
```

### 2. Register it in the top-level agent

In `src/agent.py`:

```python
from src.subgraphs.calendar_agent import CalendarAgent
```

Add instance fields:

```python
self.calendar_graph = None
self.calendar_agent = None
```

Build it during setup:

```python
calendar = CalendarAgent()
await calendar.build_graph()
self.calendar_graph = calendar.graph
self.calendar_agent = calendar
```

Add the node:

```python
graph_builder.add_node("calendar", self.calendar_graph)
graph_builder.add_edge("calendar", END)
```

### 3. Teach the orchestrator the new route

Update the deterministic routing, router prompt, valid route list, and conditional edges in `src/agent.py`.

For example:

```python
if "calendar" in latest_text or "meeting" in latest_text:
    return "calendar"
```

Then include `calendar` in:

- The system prompt route list.
- The `route not in (...)` validation.
- `orchestrator_router`.
- `add_conditional_edges`.

### 4. Test the route

Add a test in `tests/test_agent_routing.py`:

```python
def test_routes_calendar_prompt_to_calendar(self):
    self.assertEqual(
        _deterministic_route_from_text("show my calendar meetings today"),
        "calendar",
    )
```

## Extension Checklist

When adding tools or agents, keep this checklist tight:

- Add the tool or subagent in the smallest focused file.
- Bind only the tools that subagent actually needs.
- Write clear prompt boundaries for account-changing actions.
- Ask for explicit confirmation before sending, posting, applying, deleting, or modifying external accounts.
- Add routing tests for new request types.
- Add tool-output tests when you trim, transform, or normalize external data.
- Run `uv run python -m unittest discover -s tests`.

## Environment Variables

| Variable | Required for | Notes |
| --- | --- | --- |
| `DEEPSEEK_API_KEY` | All LLM workflows | Used by the OpenAI-compatible DeepSeek endpoint. |
| `TAVILY_API_KEY` | Internet agent | Required by `src/tools/tavily.py`. |

Gmail also requires `credentials.json` and `token.json` at the repo root.

## Current Boundaries

ULTRON is intentionally local and hackable:

- Memory is process-local and clears when the process exits.
- The CLI is the primary interface.
- Gmail and LinkedIn require your own account/API/MCP setup.
- External account-changing actions should require explicit user confirmation.
- The assistant subagent does not browse, run shell commands, or edit files unless you attach those tools yourself.

## Contributing

Useful contributions:

- New subagents with narrow responsibilities.
- More MCP integrations.
- Better routing tests.
- Safer account-action confirmation flows.
- A richer CLI or web UI.
- Persistent memory beyond `InMemoryStore`.
- More compact output formatters for noisy tool results.

Before opening a PR:

```bash
uv sync
uv run python -m unittest discover -s tests
```

Keep contributions focused. One new tool, one new subagent, or one workflow improvement per PR is easiest to review.

## License

Add a license before publishing widely so contributors know how they can use the project.
