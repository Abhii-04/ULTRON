# Mem0 + Qdrant Orchestrator Fix Report

Date: 2026-08-29

## Goal

Use mem0 as the memory/db layer for ULTRON and store long-term user preferences in local Qdrant.

That means the orchestrator should use:

```python
Memory.from_config(...)
```

not:

```python
MemoryClient(...)
```

`MemoryClient` is for the hosted Mem0 API. Your target is local OSS mem0 writing vectors into Qdrant.

## Current State

Qdrant is reachable on:

```text
localhost:6333
```

The Qdrant collection already exists:

```text
collection: ultron_memories
points: 0
vector size: 384
distance: cosine
sparse vector slot: bm25
```

So the DB layer is partly working: `src/memory.py` successfully initializes mem0 and creates the Qdrant collection. The problem is that the orchestrator is not using that configured local memory object correctly.

## Main Cause

In `src/memory.py`, you correctly create the local Qdrant-backed mem0 object:

```python
memory = Memory.from_config(memory_config)
```

But in `src/agent.py`, you import it and then ignore it:

```python
from src.memory import memory

load_dotenv(override=True)
mem0 = MemoryClient(api_key=os.getenv("MEM0_API_KEY"))
```

Then `orchestrator()` calls `mem0.search(...)` and `mem0.add(...)`, which means it is using `MemoryClient`, not the Qdrant-backed `Memory` from `src/memory.py`.

For your goal, the orchestrator should use the `memory` object from `src.memory` as the only mem0 backend.

## Current Runtime Crash

The pasted `BadRequestError` is not a Qdrant connection failure. It is caused by malformed `SystemMessage.content` in `src/agent.py`.

Current code:

```python
system_messsage = SystemMessage(
    content = {
        f"{prompt_modifier(state)}\n\n"
        f"Relevant long term user memories: \n{memory_context}"
    }
)
```

The `{ ... }` around the f-string creates a Python `set`, not a string. Chat model message content must be a string or a valid list of content blocks. DeepSeek receives a malformed first message and rejects it with:

```text
messages[0]: invalid type
```

Fix shape:

```python
system_message = SystemMessage(
    content=(
        f"{prompt_modifier(state)}\n\n"
        f"Relevant long term user memories:\n{memory_context}"
    )
)
```

Also fix the variable spelling so the invoke call uses the same name:

```python
response = self.orchestrator_agent.invoke([system_message, *messages])
```

There is another typo below it:

```python
if not getattr(response, "tool_call", None):
```

LangChain messages use `tool_calls`, plural:

```python
if not getattr(response, "tool_calls", None):
```

Without this, the condition will always behave as if there are no tool calls, so the orchestrator may save tool-routing responses into memory.

## Required Fixes

### 1. Wire the orchestrator to local Qdrant-backed mem0

Replace the hosted-client wiring in `src/agent.py`.

Current shape:

```python
from mem0 import MemoryClient
from src.memory import memory

mem0 = MemoryClient(api_key=os.getenv("MEM0_API_KEY"))
```

Target shape:

```python
from src.memory import memory as mem0
```

After this, `mem0.add(...)` and `mem0.search(...)` inside the orchestrator will hit your local `ultron_memories` Qdrant collection.

Also remove the now-unused `MemoryClient` import from `src/agent.py`.

### 2. Keep `src/memory.py` as the single db-layer config

Your `src/memory.py` should be the one place that defines:

```python
memory_config = {
    "llm": {
        "provider": "deepseek",
        "config": {
            "api_key": os.getenv("DEEPSEEK_API_KEY"),
            "model": "deepseek-v4-flash",
            "temperature": 0.2,
        },
    },
    "embedder": {
        "provider": "huggingface",
        "config": {
            "model": "multi-qa-MiniLM-L6-cos-v1",
        },
    },
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "collection_name": "ultron_memories",
            "host": "localhost",
            "port": 6333,
            "embedding_model_dims": 384,
        },
    },
}
```

This matches your local setup:

- Hugging Face `multi-qa-MiniLM-L6-cos-v1` produces 384-dimensional embeddings.
- Qdrant collection `ultron_memories` is already 384-dimensional.
- mem0's Qdrant adapter accepts `collection_name`, `host`, `port`, and `embedding_model_dims`.

### 3. Fix memory retrieval formatting

Current orchestrator code:

```python
context = "relevant information from previous conversations:\n"
for memory in memory_list:
    context += f"-{['memory']}\n"
```

This appends the literal text `['memory']`. It never appends the actual memory content.

Target shape:

```python
memory_context = "\n".join(
    f"- {item['memory']}"
    for item in memory_list
    if item.get("memory")
)
```

### 4. Actually put memories into the orchestrator prompt

Current code builds `context`, then throws it away:

```python
system_message = SystemMessage(content=prompt_modifier(state))
response = self.orchestrator_agent.invoke([system_message, *state["messages"]])
```

Target shape:

```python
system_message = SystemMessage(
    content=(
        f"{prompt_modifier(state)}\n\n"
        f"Relevant long-term user memories:\n{memory_context}"
    )
)

response = self.orchestrator_agent.invoke([system_message, *messages])
```

Without this, mem0 can store/search perfectly and the model still will not use the memories.

### 5. Save only useful assistant turns

Your current save shape is basically right:

```python
interaction = [
    {"role": "user", "content": messages[-1].content},
    {"role": "assistant", "content": response.content},
]

result = mem0.add(interaction, user_id=user_id)
```

For mem0 OSS, `add()` accepts `user_id` as a top-level argument. `search()` requires identity scope inside `filters`.

Correct:

```python
mem0.add(interaction, user_id=user_id)
mem0.search(query, filters={"user_id": user_id})
```

Wrong:

```python
mem0.search(query, user_id=user_id)
```

### 6. Fix the memory failure fallback

Current fallback:

```python
except Exception as e:
    print(f"Error retrieving :{e}")
    response = self.orchestrator_agent.invoke(state)
```

Problems:

- It does not return `{"messages": [response]}`.
- It passes the whole LangGraph state dict into the model instead of a message list.

Target shape:

```python
except Exception as e:
    print(f"Error retrieving memory: {type(e).__name__}: {e}")
    system_message = SystemMessage(content=prompt_modifier(state))
    response = self.orchestrator_agent.invoke([system_message, *messages])
    return {"messages": [response]}
```

## Minimal Orchestrator Shape

This is the practical target for `Agent.orchestrator()`:

```python
def orchestrator(self, state: State, store: BaseStore) -> dict[str, Any]:
    messages = state["messages"]
    user_id = state.get("user_id", "default")
    user_text = messages[-1].content

    try:
        memories = mem0.search(user_text, filters={"user_id": user_id}, top_k=5)
        memory_list = memories.get("results", [])
    except Exception as e:
        print(f"Error retrieving memory: {type(e).__name__}: {e}")
        memory_list = []

    memory_context = "\n".join(
        f"- {item['memory']}"
        for item in memory_list
        if item.get("memory")
    )

    system_message = SystemMessage(
        content=(
            f"{prompt_modifier(state)}\n\n"
            f"Relevant long-term user memories:\n{memory_context}"
        )
    )

    response = self.orchestrator_agent.invoke([system_message, *messages])

    if not getattr(response, "tool_calls", None):
        try:
            interaction = [
                {"role": "user", "content": user_text},
                {"role": "assistant", "content": response.content},
            ]
            result = mem0.add(interaction, user_id=user_id)
            print(f"memory saved: {len(result.get('results', []))} memories added")
        except Exception as e:
            print(f"Error saving memory: {type(e).__name__}: {e}")

    return {"messages": [response]}
```

Important detail: this skips saving tool-call-only orchestrator responses. Those responses usually contain routing/tool metadata, not useful user preferences.

## Validation Commands

### Confirm orchestrator uses local mem0

```bash
python - <<'PY'
from src.agent import mem0
print(type(mem0).__name__)
PY
```

Expected:

```text
Memory
```

If it prints `MemoryClient`, the orchestrator is still not using Qdrant-backed mem0.

### Confirm Qdrant collection exists

```bash
python - <<'PY'
from qdrant_client import QdrantClient
client = QdrantClient(host="localhost", port=6333)
info = client.get_collection("ultron_memories")
print("points:", info.points_count)
print("vectors:", info.config.params.vectors)
print("sparse:", info.config.params.sparse_vectors)
PY
```

### Confirm mem0 writes into Qdrant

Use this only after wiring `src.agent.mem0` to `src.memory.memory`.

```bash
python - <<'PY'
from src.agent import mem0

user_id = "debug_user"

result = mem0.add(
    [{"role": "user", "content": "I prefer short direct answers."}],
    user_id=user_id,
)
print("add:", result)

found = mem0.search(
    "How should I answer this user?",
    filters={"user_id": user_id},
    top_k=5,
)
print("search:", found)
PY
```

Then check Qdrant point count:

```bash
python - <<'PY'
from qdrant_client import QdrantClient
client = QdrantClient(host="localhost", port=6333)
print(client.get_collection("ultron_memories").points_count)
PY
```

Expected: point count should increase from `0`.

## Non-Obvious Notes

### `MEM0_API_KEY` is not needed for local Qdrant mode

For this architecture, you need:

```text
DEEPSEEK_API_KEY
Qdrant running on localhost:6333
```

You do not need:

```text
MEM0_API_KEY
OPENAI_API_KEY
```

because your config uses DeepSeek as the memory extraction LLM and Hugging Face locally for embeddings.

### Qdrant stores vectors, mem0 decides what to store

With `infer=True`, mem0 calls the configured LLM to extract durable facts before writing vectors. That is what you want for preferences like:

```text
User prefers concise answers.
User likes Python examples.
User wants casual tone.
```

If you use `infer=False`, mem0 stores raw messages instead. That is useful for debugging Qdrant writes, but worse for long-term assistant memory.

### Existing `src/nodes/mem0.py` is not the right integration point

That node is not wired into the main graph and also has:

```python
SystemMessage(context=...)
```

It should be `content=...`, but the cleaner fix is to keep memory inside `Agent.orchestrator()` first. Do not add another graph node until the simple path works.

## Sources

- Official mem0 OSS overview: https://docs.mem0.ai/open-source/overview
- Official mem0 OSS configuration: https://docs.mem0.ai/open-source/configuration
- Official mem0 Qdrant guide: https://docs.mem0.ai/components/vectordbs/dbs/qdrant
- Installed package source inspected locally: `mem0ai==2.0.19`
