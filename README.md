# Ultron Agent Capabilities

Ultron is a multi-agent assistant that routes each user request to the agent best suited for the task.

## Orchestrator

The orchestrator reads the latest user request and chooses one route:

- `internet` for web, current-information, source-backed, URL, search, or email-related work.
- `assistant` for general reasoning, writing, editing, planning, summarizing, and non-web help.

The orchestrator can also read a user-scoped in-memory profile from LangGraph `InMemoryStore` and include that profile as routing context.

## Internet Agent

The internet agent handles tasks that require external information or connected account actions.

Capabilities:

- Search the internet for current, recent, external, or source-backed information.
- Research web topics and summarize findings.
- Prefer authoritative or recent sources when search results conflict.
- Use Gmail tools for email tasks such as searching, reading, drafting, or sending Gmail messages.
- Return tool errors in normal language instead of crashing the CLI.

Boundaries:

- It does not perform browser interaction.
- It does not edit local files.
- It does not run shell commands.
- It should ask for explicit confirmation before sending email or making external account changes.

## Assistant Agent

The assistant agent handles non-web, general-purpose help.

Capabilities:

- Answer general questions using conversation context and model knowledge.
- Help with writing, editing, summarizing, planning, brainstorming, and explanations.
- Break unclear or complex requests into practical steps.
- Ask concise clarification questions when a request cannot be handled safely from available context.

Boundaries:

- It does not browse the web.
- It does not operate a browser.
- It does not run shell commands.
- It does not read or edit local files.
- It does not send email or access accounts.

## Memory

The top-level agent uses two in-memory LangGraph components:

- `InMemorySaver` for graph checkpoints and conversation continuity during the process lifetime.
- `InMemoryStore` for user-scoped profile memory during the process lifetime.

This memory is process-local and is cleared when the Python process exits.
