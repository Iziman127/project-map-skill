# Story Mode

Story mode traces a real scenario through the codebase. It is not a generic summary.

## When to use it

- The user asks how a request or job flows through the code
- The repo is too large for one diagram to explain behavior
- The interesting part is control flow, not static architecture

## Scenario selection

If the user names a scenario (via `$ARGUMENTS` text after `story`, or by describing it in chat), trace that exact scenario.

If they do not name a scenario:

1. Scan for entry points across these categories:
   - HTTP routes: route registrations, controller decorators, API endpoint definitions
   - CLI commands: subcommand definitions, argument parsers
   - Queue consumers: message handlers, subscriber registrations
   - Scheduled jobs: cron definitions, scheduler registrations
   - Webhook handlers: webhook route registrations
   - Event listeners: event handler registrations

2. Rank the discovered entry points by significance:
   - Prefer user-facing over internal
   - Prefer routes with more middleware or deeper call chains
   - Prefer entry points that touch storage or external services
   - Prefer entry points that cross domain boundaries

3. List the top 5-8 most significant entry points and use `AskUserQuestion`:
   - Question: `Which scenario do you want to trace through the code?`
   - Each option should be a short description of the entry point with its trigger, e.g.:
     1. `POST /api/auth/login` — `User authentication flow through auth service to database`
     2. `processPayment worker` — `Background payment processing from queue to Stripe`
     3. `cli deploy` — `Deployment pipeline from CLI to cloud provider`
   - Include a final option: `Auto-select` — `Let me pick 1-3 representative paths automatically`

4. If the user picks `Auto-select`, or if `AskUserQuestion` is unavailable, fall back to automatic selection: pick 1-3 representative paths such as:
   - a top user-facing request
   - a critical background job
   - an error or retry path

## Trace rules

Start from a real trigger:

- HTTP route
- CLI command
- scheduler entry
- queue consumer
- webhook handler

Then follow the actual path through:

1. entry point
2. validation/auth/middleware
3. orchestration layer
4. domain logic
5. external calls
6. storage writes or emitted events
7. returned result or side effect

## Required evidence

Every step should include:

- file path
- line number or a narrow line range
- function or method name
- what changes at that step

If the path splits, say so. If a hop is inferred, mark it as inferred.

## Output format

```text
SCENARIO: "User logs in and receives a session token"

Entry Point — path/to/file:line
What triggers the flow.

Step 1 — Validate credentials — path/to/file:line
Relevant function names and what happens here.

  ↓

Step 2 — Load user and issue token — path/to/file:line
...

Result
What the caller or system gets.

What could go wrong
- failure mode 1
- failure mode 2
```

## Quality bar

- Prefer 5-9 meaningful steps over noisy detail
- Mention important branches
- Include failures only if they matter to understanding the flow
- Keep the trace faithful to the code, even if it makes the story messier
