# ULTRON

ULTRON is a self-learning terminal-based LangGraph assistant with direct chat, local file tools, web research, Gmail tooling, LinkedIn MCP tooling, and long-term memory through mem0 backed by Qdrant.

## What It Does

| Area | Behavior |
| --- | --- |
| Orchestrator | Answers simple requests directly, calls local file tools, or hands work to a focused subgraph. |
| Memory | Uses `mem0ai` OSS with DeepSeek for memory extraction, Hugging Face embeddings, and Qdrant collection `ultron_memories` for vector storage. |
| Internet | Routes current/recent/source-backed requests to the Tavily-backed internet subgraph. |
| Gmail | Searches Gmail and creates drafts through Gmail OAuth tooling. |
| LinkedIn | Loads selected LinkedIn MCP tools from `mcp_config.json`. |
| Safety | Uses human-in-the-loop approval before risky file and Gmail actions. |
| Terminal UI | Provides Rich-based prompts, run status, responses, approval prompts, and error panels. |

## Architecture

```text
User input
    |
    v
dynamic_agent_selection
    |
    +-- LinkedIn keywords/current route -> linkedin subgraph
    +-- Internet/search/current route   -> internet subgraph
    |
    v
orchestrator
    |
    +-- direct answer
    +-- local file tools
    +-- transfer_to_gmail
    +-- transfer_to_linkedin
    +-- transfer_to_internet
```

The orchestrator retrieves relevant memories before calling the model, injects them into the system prompt, and stores useful direct assistant turns back into mem0/Qdrant.

## Project Structure

```text
.
+-- main.py
+-- mcp_config.json
+-- pyproject.toml
+-- requirements.txt
+-- README.md
+-- skills/
|   +-- internet_search/SKILL.md
|   +-- linkedin/SKILL.md
+-- src/
    +-- agent.py
    +-- memory.py
    +-- state.py
    +-- terminal_ui.py
    +-- middlewares/
    |   +-- HITL.py
    |   +-- context_handoff.py
    |   +-- trim_tool_content.py
    +-- nodes/
    |   +-- dynamic_agent_selection.py
    |   +-- dynamic_prompt.py
    |   +-- swarm.py
    +-- subgraphs/
    |   +-- gmail_agent.py
    |   +-- internet_agent.py
    |   +-- linkedin_agent.py
    +-- tools/
        +-- Gmail.py
        +-- fileManagment.py
        +-- mcp.py
        +-- read_skill.py
        +-- tavily.py
```

## Requirements

- Python `>=3.11`
- `uv`
- Qdrant running on `localhost:6333`
- DeepSeek API key
- Tavily API key for web search
- Gmail OAuth files if Gmail features are used
- LinkedIn MCP setup if LinkedIn features are used

## Setup

Install dependencies:

```bash
uv sync
```

Create `.env`:

```bash
DEEPSEEK_API_KEY=your_deepseek_key
TAVILY_API_KEY=your_tavily_key
```

Start Qdrant locally if it is not already running:

```bash
docker run -p 6333:6333 -v "$(pwd)/qdrant_storage:/qdrant/storage" qdrant/qdrant
```

Optional Gmail files at repo root:

```text
credentials.json
token.json
```

Optional LinkedIn MCP config lives in:

```text
mcp_config.json
```

## Memory

Memory is configured in `src/memory.py`:

```text
provider: mem0 OSS
llm: DeepSeek
embedder: Hugging Face multi-qa-MiniLM-L6-cos-v1
vector store: Qdrant
collection: ultron_memories
dimensions: 384
```

`MEM0_API_KEY` is not required for this local Qdrant-backed setup. That key is for hosted Mem0 Platform usage, not the local OSS `Memory.from_config(...)` path.

First run may download model assets such as Hugging Face embeddings or spaCy resources.

## Run

```bash
uv run main.py
```

or:

```bash
uv run python main.py
```

Exit with:

```text
exit
quit
```

## Example Prompts

```text
hii i am abhishek
remember that i prefer short direct answers
search the web for the latest LangGraph MCP examples
search my gmail for invoices from today
search linkedin for entry level AI jobs in Bengaluru
create a file named notes.md with a short project update
```

## Validation

Compile the app:

```bash
uv run python -m compileall main.py src
```

Check Qdrant connectivity:

```bash
uv run python - <<'PY'
from qdrant_client import QdrantClient

client = QdrantClient(host="localhost", port=6333)
print(client.get_collections())
PY
```

Check the memory collection:

```bash
uv run python - <<'PY'
from qdrant_client import QdrantClient

client = QdrantClient(host="localhost", port=6333)
info = client.get_collection("ultron_memories")
print("points:", info.points_count)
print("vectors:", info.config.params.vectors)
PY
```

## Notes

- `src/nodes/swarm.py` is preserved, but the main entrypoint uses `src/agent.py`.
- `src/middlewares/trim_tool_content.py` is preserved for tool-output trimming.
- Deleted scratch/dead files should stay out of the app path unless they are intentionally reintroduced.
