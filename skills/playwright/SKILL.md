---
name: playwright
description: Use this skill whenever the user asks for browser automation, UI testing, screenshots, responsive checks, form filling, login flow testing, Playwright scripts, or validating a website in a real browser. In the current ULTRON graph, no Playwright/browser tool is wired into an agent, so this skill guides the assistant to report that limitation or provide non-executing guidance.
---

# Playwright Skill

## Purpose

Use this skill for browser automation and UI testing requests. The current LangGraph code does not wire a Playwright tool or browser automation subgraph into the runtime agents.

Current graph reality:

- The top-level graph routes to `gmail`, `linkedin`, `internet`, or `assistant`.
- The Assistant has `read_skill` only.
- The InternetAgent has `Internet_search` and `read_skill`.
- The LinkedInAgent has LinkedIn MCP tools and `read_skill`.
- No agent currently has a Playwright execution tool.

Because of that, do not claim that browser actions were executed unless a Playwright tool is added to the graph later.

## When To Use

Use this skill when the request mentions or implies:

- Playwright
- browser automation
- screenshots
- page inspection
- checking UI layout or responsive behavior
- filling forms
- testing login flows
- clicking buttons or navigating pages
- checking console errors or network requests
- writing Playwright test code

## Current Runtime Behavior

If the user asks to execute browser automation:

1. Explain that Playwright is not currently connected to any runnable agent tool in this graph.
2. Provide the exact next step needed to enable it, such as adding a Playwright tool or subgraph.
3. If useful, provide Playwright test code or a command the user can run outside the agent.
4. Do not fabricate screenshots, browser observations, console logs, or test results.

If the user asks for Playwright test code:

1. Write code that is directly runnable.
2. Prefer clear locators such as role, label, text, placeholder, or test id.
3. Include assertions for visible user-facing behavior.
4. Keep credentials and secrets out of the test.
5. Mention required environment variables when login or private pages are involved.

## Suggested Test Structure

For Python Playwright:

```python
from playwright.sync_api import Page, expect

def test_example(page: Page):
    page.goto("http://localhost:3000")
    expect(page.get_by_role("heading")).to_be_visible()
```

For TypeScript Playwright:

```ts
import { test, expect } from '@playwright/test';

test('example', async ({ page }) => {
  await page.goto('http://localhost:3000');
  await expect(page.getByRole('heading')).toBeVisible();
});
```

## Browser Testing Guidance

When designing tests:

- Test the user workflow, not implementation details.
- Prefer stable semantic locators over CSS selectors.
- Add waits through assertions instead of fixed sleeps.
- Capture screenshots only when they help debug or verify visual output.
- Check console/network errors when debugging a failing page.
- Test both desktop and mobile viewports for responsive UI changes.

## Boundaries

- Do not claim to open a browser from the current graph.
- Do not claim to take screenshots from the current graph.
- Do not report visual findings that were not actually observed.
- Do not bypass authentication, CAPTCHA, paywalls, or access controls.
- Do not store credentials in test files.

## Error Handling

If the user expected live browser execution, respond with:

```text
Error: Playwright execution is not wired into this ULTRON graph.
Cause: No current agent exposes a browser automation tool.
Solution: Add a Playwright tool/subgraph, then route browser-testing requests to it.
Next step: I can provide the Playwright test code or help wire the Playwright agent into the graph.
```
