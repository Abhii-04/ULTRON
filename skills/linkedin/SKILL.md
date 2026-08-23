---
name: linkedin
description: Use this skill whenever the user asks about LinkedIn job search, saved jobs, job details, company profiles, company research, employer lookup, or hiring-post searches. This skill guides the LinkedInAgent to use the configured LinkedIn MCP tools through the existing LangGraph workflow.
---

# LinkedIn Skill

## Purpose

Use this skill for LinkedIn job and company research. In this project, LinkedIn requests are routed to the `linkedin` subgraph by `src/agent.py`, and the LinkedInAgent can use configured MCP tools loaded from `mcp_config.json`.

Allowed LinkedIn MCP tool names are filtered in `src/tools/mcp.py`:

- `search_jobs`
- `get_job_details`
- `get_saved_jobs`
- `search_companies`
- `get_company_profile`
- `search_posts`

The agent also has `read_skill`.

## When To Use

Use this skill when the request mentions or implies:

- LinkedIn jobs or job search
- saved LinkedIn jobs
- job details for a LinkedIn job ID or URL
- company search, employer research, or company profiles
- hiring posts, recruiter posts, or informal job opportunities on LinkedIn
- comparing LinkedIn job results

If a user asks for general web research about a company without LinkedIn context, use the internet workflow instead.

## Workflow

1. Read the user request and identify the target action: job search, saved jobs, job details, company search, company profile, or hiring posts.
2. Extract constraints such as title, keywords, location, remote/on-site preference, experience level, company, date range, and job ID.
3. Use the most specific LinkedIn MCP tool available.
4. For job details, use job IDs from prior search results when available.
5. Keep results concise and action-oriented.
6. Include apply links or LinkedIn job URLs when the tool result provides them.
7. If the tool does not provide a link, explicitly say the link was not provided.
8. If required input is missing, ask one concise clarification question.

## Tool Selection

Use:

- `search_jobs` for new job searches.
- `get_job_details` when the user provides or selects a job ID.
- `get_saved_jobs` when the user asks for saved jobs.
- `search_companies` when the user wants employer/company discovery.
- `get_company_profile` when the user asks about one company.
- `search_posts` for hiring posts, recruiter posts, or informal opportunities.

Do not describe tool calls or tool syntax in the final answer.

## Result Format

For job search results, include fields when available:

- Title
- Company
- Location
- Job ID
- Apply link or LinkedIn job URL
- Posting date
- Work type
- Experience level

Preferred format:

```text
Found N relevant LinkedIn result(s):

1. Title - Company
   Location: ...
   Job ID: ...
   Link: ...
   Posted: ...
   Work type: ...
   Experience: ...
```

For company research:

```text
Company: ...
LinkedIn profile: ...
Summary: ...
Relevant notes: ...
```

## Boundaries

- Do not use general internet search from this workflow.
- Do not handle Gmail or email tasks.
- Do not claim to operate a browser beyond the configured LinkedIn MCP tools.
- Do not message recruiters, connect with people, apply to jobs, save jobs, or perform account-changing actions unless explicit tools for those actions are added later.
- Do not invent job IDs, links, salaries, dates, or company details.

## Error Handling

If a LinkedIn MCP tool fails:

- State the failure briefly.
- Ask for any missing required input if the error is input-related.
- If the MCP server is unavailable, mention that LinkedIn MCP configuration/session startup should be checked in `mcp_config.json`.

If no LinkedIn tools are available, explain that the LinkedIn MCP server did not expose usable tools and suggest checking MCP setup before retrying.
