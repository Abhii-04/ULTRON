# Gmail Workflow Fix Implemented

## Issue

The top-level agent was routing Gmail requests to the Gmail workflow, but the workflow did not execute a Gmail action from a normal user message.

Observed earlier:

```text
User: Search Gmail for messages newer_than:1d
Route selected: gmail
Final output: Search Gmail for messages newer_than:1d
```

The route was correct, but the Gmail workflow router had no `gmail_action`, so it returned `END`.

## Root Cause

The orchestrator only returns a route word:

```text
gmail
internet
assistant
```

It does not create Gmail workflow fields such as:

```python
gmail_action = "search_gmail"
query = "newer_than:1d"
```

The Gmail workflow expected those fields to already exist. When invoked from the top-level agent, it only received the normal message state.

## Fix Applied

The fix was kept inside `src/subgraphs/gmail_agent.py`.

No new Gmail-specific fields were added to global `src/state.py`.

The workflow now has an internal prep node:

```python
prepare_gmail_state
```

That node reads the latest user message and fills local Gmail workflow fields before routing.

Example:

```text
"Search Gmail for messages newer_than:1d"
-> gmail_action = "search_gmail"
-> query = "newer_than:1d"
```

The graph flow is now:

```text
START
-> prepare_gmail_state
-> gmail_router
-> search_gmail / draft_message
-> END
```

## Why This Fix Fits The Codebase

- The orchestrator still only chooses the workflow.
- Gmail-specific parsing stays inside the Gmail workflow.
- Global `State` does not need to carry Gmail-only fields like `query`, `to`, `subject`, `cc`, or `bcc`.
- The existing `GmailState` remains local to `gmail_agent.py`.
- The Gmail workflow remains a workflow, not a separate tool-calling chat agent.

## Tests Run

### Compile

```text
python -m compileall src/subgraphs/gmail_agent.py
PASS
```

### Direct Gmail Workflow Test With Fake Gmail Search

Input:

```text
Search Gmail for messages newer_than:1d
```

Result:

```text
direct workflow: PASS
calls: [{'query': 'newer_than:1d'}]
final: [{'id': 'msg-1', 'query': 'newer_than:1d'}]
```

This proves the Gmail workflow can now derive `gmail_action` and `query` from a normal message.

### Top-Level Graph Route Test With Fake Orchestrator And Fake Gmail Search

Result:

```text
top-level graph: PASS
next: gmail
calls: [{'query': 'newer_than:1d'}]
final: [{'id': 'msg-1', 'query': 'newer_than:1d'}]
```

This proves the parent graph can route to the Gmail workflow and the Gmail workflow can prepare its own local state.

## Remaining Limitation

Real Gmail execution can still fail if the environment is missing Gmail auth dependencies.

Earlier failure:

```text
ImportError: Could not import google_auth_oauthlib.flow python package.
Please install it with `pip install google-auth-oauthlib`.
```

That is an environment/dependency issue, not a graph-routing issue.

## Current Scope

The implemented prep logic is intentionally minimal.

It handles Gmail search prompts such as:

```text
Search Gmail for messages newer_than:1d
```

Draft execution still expects structured fields like:

```python
message
to
subject
```

If a plain-text draft request should be supported later, the Gmail workflow needs a small draft parser or a user-confirmation step. That should be a separate change.
