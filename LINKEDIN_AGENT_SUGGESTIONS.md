# LinkedIn Agent Suggestions

## Current Direction

The LinkedIn workflow is better as a separate agent with the same broad structure as `internet_agent.py`: an LLM bound to MCP tools, a `ToolNode`, and a loop back to the agent after tool execution.

This is preferable to the Gmail-style deterministic parser because LinkedIn job search has richer filters and more varied user phrasing.

## Suggested Improvements

- Keep LinkedIn MCP tools out of `internet_agent.py` so web research and LinkedIn account-backed search remain separate workflows.
- Keep the LinkedIn agent prompt strict about returning job links. Search responses should include apply links or LinkedIn job URLs whenever the MCP result provides them.
- Ask the model to include basic job fields in every search result: title, company, location, job ID, apply/job link, posting date, work type, and experience level when available.
- Add a result formatter later if MCP output is too verbose or inconsistent. That formatter can preserve links and IDs while trimming noisy raw metadata.
- Add a small routing test for top-level LinkedIn prompts if routing becomes unreliable.
- Consider adding prompt examples for common searches such as remote AI jobs, entry-level roles, jobs posted this week, and Easy Apply roles.
- If the LinkedIn MCP server exposes apply/save/connect/message tools later, require explicit user confirmation before any account-changing action.

## Testing Notes

- Unit tests can validate graph routing without calling the live LinkedIn MCP server.
- Live testing should verify that the server returns job URLs or apply links for `search_jobs`.
- If search results only return job IDs, the agent should call `get_job_details` before finalizing when the user asks for actionable links.
