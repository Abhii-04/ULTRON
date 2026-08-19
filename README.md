# Ultron Agent Capabilities

Ultron is a multi-agent assistant that routes each user request to the agent best suited for the task.

## Orchestrator

The orchestrator reads the latest user request and chooses one route:

- `gmail` for Gmail search, reading, threads, drafts, and sending email.
- `internet` for web, current-information, source-backed, URL, search, LinkedIn job-search, or MCP-backed connected-service work.
- `assistant` for general reasoning, writing, editing, planning, summarizing, and non-web help.

The orchestrator can also read a user-scoped in-memory profile from LangGraph `InMemoryStore` and include that profile as routing context.

## Internet Agent

The internet agent handles tasks that require external information or connected account actions.

Capabilities:

- Search the internet for current, recent, external, or source-backed information.
- Research web topics and summarize findings.
- Prefer authoritative or recent sources when search results conflict.
- Use configured LinkedIn MCP job tools from `mcp_config.json`.
- Return tool errors in normal language instead of crashing the CLI.

Boundaries:

- It does not perform browser interaction.
- It does not edit local files.
- It does not run shell commands.
- It does not handle Gmail or email tasks. The Gmail workflow handles those.
- It should ask for explicit confirmation before making external account changes.

## Gmail Agent

The Gmail agent handles Gmail-specific account actions.

Capabilities:

- Search Gmail with natural language requests such as "mails I received today" or "mails I received in the last 24 hours".
- Convert common relative-date requests into Gmail search syntax, including `after:YYYY/MM/DD before:YYYY/MM/DD` for today and `newer_than:1d` for the last 24 hours.
- Return compact, readable search summaries with subject, sender, snippet, and message ID.
- Decode MIME-encoded subjects and HTML entities in compact Gmail output.
- Read Gmail messages or threads by ID.
- Create Gmail drafts and send Gmail messages through the configured Gmail OAuth credentials.

Setup notes:

- Gmail OAuth uses `credentials.json` and writes/reads `token.json`.
- Required Gmail dependencies include `langchain-google-community`, `google-auth-oauthlib`, and `beautifulsoup4`.
- If the Gmail API is disabled for the Google Cloud project behind `credentials.json`, enable the Gmail API in Google Cloud Console and retry after propagation.

Boundaries:

- It should ask for explicit confirmation before sending email.
- It does not browse the web.
- It does not operate LinkedIn or other MCP-backed services.

## MCP Servers

ULTRON loads MCP server definitions from `mcp_config.json` and adds their tools to the internet agent. See `docs/LANGGRAPH_MCP_SERVERS.md` for the LangGraph integration pattern and instructions for adding more MCP servers.

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



so i am trying to import tools from linkedin mcp in mcp.py file and then i want to use those tools in linkedin_agent.py just like gmail_agent so i have already laid the structure
 
  so import the tools from mcp and then use them as a node in linkedin_agent so complete the linkedin agent file and test it, after completion write a report on the changes made by
 
  you and save it in a .md file