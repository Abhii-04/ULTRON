---
name: internet_search
description: Use this skill whenever the user asks for web research, current or recent information, source-backed facts, URLs, online documentation, news, product availability, prices, schedules, laws, APIs, package behavior, or anything likely to have changed. This skill guides the InternetAgent to use the Internet_search tool through the existing LangGraph workflow.
---

# Internet Search Skill

## Purpose

Use this skill to answer questions that need current, external, or source-backed information. In this project, those requests are routed to the `internet` subgraph by `src/agent.py`, and the InternetAgent can use:

- `Internet_search`
- `read_skill`

The graph does not provide full browser control to this agent. Treat search results as the available source material.

## When To Use

Use this skill when the request mentions or implies:

- latest, current, recent, today, now, this week, or this year
- web, internet, online, URL, website, source, search, lookup, browse, or documentation
- news, prices, schedules, laws, product availability, package behavior, API examples, or troubleshooting errors
- comparing options using external sources
- verifying a fact that may have changed

When unsure whether external information is needed, prefer using the internet workflow.

## Workflow

1. Identify the concrete question the user needs answered.
2. Build a focused search query with the important nouns, dates, versions, locations, and constraints.
3. Call `Internet_search` before making claims about current or external facts.
4. If the first result set is weak, search again with a narrower or more authoritative query.
5. Synthesize the findings instead of listing raw snippets.
6. Mention source names or URLs when the tool result includes them.
7. If sources conflict, say what conflicts and prefer the more authoritative or more recent source.
8. If the results are insufficient, say what is missing instead of guessing.

## Tool Use

Call `Internet_search` with:

- `query`: A clear search string.
- `max_results`: Usually 3 to 5. Use more only when comparison is required.
- `topic`: Use `"news"` for news-style requests; otherwise use `"general"`.
- `included_raw_content`: Keep `false` unless the user needs deeper source text and the tool supports it.

Do not describe tool calls or tool syntax in the final answer.

## Boundaries

- Do not claim to operate a browser or click through websites.
- Do not claim to read local files, run code, use Gmail, or access LinkedIn MCP tools.
- Do not perform account-changing actions.
- Do not invent citations, URLs, prices, dates, or quotes.
- Do not answer from memory when the user asked for current or source-backed information.

## Response Format

For normal answers:

1. Give the answer directly.
2. Add the key supporting details.
3. Include source names or URLs if available.
4. Call out uncertainty or missing data briefly.

For research summaries, prefer:

```text
Short answer: ...

Key findings:
- ...
- ...

Sources:
- ...
```

## Error Handling

If `Internet_search` fails:

- State the error plainly.
- Explain whether the failure is missing API configuration, a tool/runtime failure, or insufficient search results.
- Offer a next step, such as setting `TAVILY_API_KEY`, retrying with a narrower query, or asking for a URL/source from the user.

If this skill was loaded but the request belongs to Gmail, LinkedIn, or general reasoning, say which workflow should handle it.
