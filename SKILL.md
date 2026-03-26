---
name: project-map
description: Build evidence-based architecture maps from any project — codebases, skills, config directories, script collections, documentation trees, or any structured set of files. Produces in-chat, interactive HTML, or scenario traces. Adapts classification to the project's actual nature rather than assuming it is a traditional software codebase.
user-invocable: true
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Write, Bash(python *), Task, AskUserQuestion
argument-hint: [chat|html|story [scenario description]]
---

# project-map

`${SKILL_DIR}` refers to the directory containing this SKILL.md file. Resolve it to an absolute path before running any script commands.

Map how any project works — a codebase, a skill, a config tree, a set of scripts, a documentation structure, or any collection of files in the current working directory. Always analyze first, then render from a canonical architecture model. Do not reject a project because it is not a traditional software codebase; adapt the analysis to whatever is there.

## Defaults

- If `$ARGUMENTS` starts with `story`, use **Story mode**. Any text after `story` is the scenario description. If no text follows, scenario selection is interactive (see [references/story-mode.md](references/story-mode.md)).
- If `$ARGUMENTS` contains `html`, use **interactive HTML**.
- If `$ARGUMENTS` contains `chat`, use **in-chat mode**.
- Otherwise, ask the user which mode they want with `AskUserQuestion`:
  - Question: `How do you want to visualize the architecture?`
  - Options:
    1. `HTML (recommended)` — `Interactive React Flow canvas`
    2. `In chat` — `Structured map directly in chat`
    3. `Story` — `Trace one concrete scenario through the code`
- If `AskUserQuestion` is unavailable, fall back to **in-chat mode**.

## Core workflow

### 0. Check for existing model

Before starting analysis, check if `architecture-map.json` exists in the project root.

If it exists:

1. Read and validate it against the model schema in [references/model.md](references/model.md)
2. If validation fails (missing required fields, broken references), discard it and proceed with a fresh analysis from step 1
3. If validation passes, use `AskUserQuestion`:
   - Question: `An existing architecture model was found (architecture-map.json). What do you want to do?`
   - Options:
     1. `Update it` — `Re-scan the codebase for changes and update the existing model`
     2. `Start fresh` — `Full re-analysis from scratch`
     3. `Render as-is` — `Skip analysis and render the existing model immediately`

**If "Update":**

- Load the existing model as the baseline
- Perform a targeted scan:
  1. Check if files referenced in component `evidence` still exist and have the same structure
  2. Look for new entry points, route groups, or services not in the existing model
  3. Check for new or removed dependencies
  4. Verify connections still hold (source and target files still exist and reference each other)
- For each existing component:
  - If its evidence files are unchanged: keep it as-is
  - If its evidence files changed significantly: re-analyze that component, update its description, tags, and evidence
  - If its evidence files are gone: remove the component and note the removal in `open_questions`
- Add newly discovered components with fresh evidence
- Preserve any `position` values from the existing model (the user may have manually adjusted the layout)
- Update `_meta.last_analyzed` with the current ISO 8601 timestamp
- Proceed to step 4 (Classify) to verify the classification still holds, then continue to rendering

**If "Render as-is":**

- Skip all analysis steps (steps 1 through 5)
- Jump directly to step 6 (Choose the renderer)
- Use the existing model for rendering without changes

**If "Start fresh":**

- Ignore the existing file entirely
- Proceed with the normal workflow from step 1

If `AskUserQuestion` is unavailable: proceed with a fresh analysis (current behavior). Do not silently reuse a potentially stale model.

### 1. Detect scope before analysis

Before building the model, do a quick structural scan to determine if the repository is large or a monorepo.

**Check for monorepo markers:**

- Multiple `package.json`, `go.mod`, `Cargo.toml`, or `pyproject.toml` files in different directories
- Workspace configuration (`workspaces` in package.json, `pnpm-workspace.yaml`, Cargo workspace, Go workspace)
- Directories named `services/`, `apps/`, `packages/`, `modules/` containing independent applications
- Multiple Dockerfiles or docker-compose service definitions

**Estimate scale:**

- Count top-level source directories with entry points
- If more than 3 independently deployable units or more than 500 source files are detected, treat as large

**If large repo or monorepo detected**, use `AskUserQuestion`:

- Question: `This looks like a large repository. What scope do you want to map?`
- Options:
  1. `Entire repository` — `High-level service map showing how services connect`
  2. `A specific service or app` — `Focused map of one deployable unit`
  3. `A specific flow` — `Trace one scenario through the code (switches to story mode)`

Handling each choice:

- **Entire repository**: set scope to full repo. The Monorepo row in layouts.md applies (10-18 nodes, apps/services only). Set `project.scope` to `null`.
- **A specific service or app**: if more than one candidate was detected, use a follow-up `AskUserQuestion` listing the detected services/apps. If only one candidate exists or `AskUserQuestion` is unavailable for the follow-up, use the most prominent candidate. Then restrict all subsequent analysis to that directory subtree. Set `project.scope` to the chosen path (e.g., `"services/auth-api"`). Mention the scope in `project.summary`.
- **A specific flow**: switch mode to story and proceed to the story mode flow.

**If small repo** (fewer than 3 deployable units and fewer than 500 source files): skip this step entirely. Analyze the whole repository.

**If `AskUserQuestion` is unavailable**: skip this step. Analyze the entire repository and let the compression rules in layouts.md handle scale.

### 2. Build the canonical architecture model

Read [references/model.md](references/model.md) first. Then read [references/analysis.md](references/analysis.md).

Your first deliverable is a structured model of the codebase. Treat every later output as a render of that model.

For `html`, write the model to `architecture-map.json` in the project root before rendering.

If a scope was set in step 1, restrict all file scanning and analysis to the chosen subtree.

### 3. Analyze with evidence, not vibes

Identify:

- Entry points and triggers
- Main execution flow or route groups
- Internal business domains or service boundaries
- External dependencies and outbound calls
- Storage systems, caches, queues, file stores
- Config sources and secret usage
- UI or operational surfaces
- Unknowns, ambiguities, and probable-but-unproven components

Every component and connection in the model must include:

- `confidence`: `high`, `medium`, or `low`
- `evidence`: one or more concrete references explaining why it exists

If you cannot support a component with evidence, do one of these instead:

- Leave it out
- Put it in `open_questions`
- Mark it explicitly as a hypothesis with `confidence: low`

### 4. Classify before you render

Set:

- `classification.primary`
- `classification.secondary`
- `classification.render_as`

Supported `primary` types:

- `webapp`
- `pipeline`
- `event-driven`
- `cli-tool`
- `worker`
- `microservices`
- `library`
- `skill` — Claude Code skill, prompt-driven tool, or agent definition
- `config` — configuration tree, infrastructure-as-code, dotfiles
- `docs` — documentation structure, knowledge base, content tree

`render_as` should normally be one of:

- `webapp`
- `pipeline`
- `event-driven`
- `microservices`
- `library`

Use these mappings unless the project clearly needs something else:

- `cli-tool` -> `pipeline`
- `worker` -> `pipeline`
- `skill` -> `pipeline` (prompt flow from invocation to output)
- `config` -> `library` (modules and references)
- `docs` -> `library` (content tree with cross-references)

### 5. Compress large repos before rendering

Read [references/layouts.md](references/layouts.md) when you are ready to render.

Use the size rules there to decide whether to show:

- exact components
- grouped domains
- grouped services
- only the top-level execution path

Do not dump every file, route, or helper into the map. The map should explain the system, not mirror the tree.

### 6. Choose the renderer

#### In-chat

Use the relevant layout section in [references/layouts.md](references/layouts.md).

Always include:

- project type and why you classified it that way
- a compact architecture map
- a short `Confidence & Unknowns` section
- exact file references for all major components

#### HTML

Interactive React Flow page. Use this only when external browser assets are acceptable.

Steps:

1. Write `architecture-map.json`
2. Render:

   ```bash
   python ${SKILL_DIR}/scripts/render_map.py \
     --model architecture-map.json \
     --output project-map.html
   ```

3. Open only if it makes sense:

   ```bash
   python ${SKILL_DIR}/scripts/open_html.py project-map.html
   ```

If Python is missing, the environment is headless, or browser launch fails, fall back to **in-chat mode**.

#### Story

Use [references/story-mode.md](references/story-mode.md). Trace an actual scenario through the code with exact functions, files, and line numbers.

If the user invoked story mode without naming a specific scenario, follow the interactive scenario selection process described in [references/story-mode.md](references/story-mode.md) before beginning the trace.

## Model quality bar

- Do not invent databases, queues, services, or route groups.
- Do not call a tiny helper module a "service" unless it behaves like one.
- Do not force a sequential pipeline onto asynchronous workers or fan-out systems.
- Do not hide uncertainty. Surface it.
- Prefer grouped nodes over unreadable graphs once the node budget is exceeded.
- If the repo is mixed-mode, keep the real `primary` type and use `secondary` plus `render_as` to explain the compromise.

## Suggested reference loading order

Load only what you need:

1. [references/model.md](references/model.md) — also used in step 0 to validate an existing model
2. [references/analysis.md](references/analysis.md)
3. [references/layouts.md](references/layouts.md) only when rendering
4. [references/story-mode.md](references/story-mode.md) only for `story` — note that scenario selection may trigger an `AskUserQuestion` interaction

## Deliverables by mode

### `chat`

- Return the final architecture map directly in chat.
- Mention major assumptions and unknowns.

### `html`

- Produce `architecture-map.json`
- Produce `project-map.html`

### `story`

- Return one or more scenario traces in chat.

## Post-render refinement

After delivering the output for any mode, offer the user a chance to iterate.

Use `AskUserQuestion`:

- Question: `Architecture map delivered. Want to refine it?`
- Options:
  1. `Zoom in` — `Focus on a specific component or domain with more detail`
  2. `Trace a scenario` — `Switch to story mode and walk through a specific flow`
  3. `Adjust the map` — `Add, remove, or regroup components`
  4. `Done` — `The map looks good`

### Handling each choice

**Zoom in:**

1. Use `AskUserQuestion` to ask which component or domain to zoom into, listing the top-level components or domains from the current model as options
2. Re-analyze that area with a lower node budget threshold: show concrete components instead of grouped domains, expose individual routes or handlers instead of route groups
3. Re-render using the same mode but scoped to the chosen area
4. Return to the refinement prompt

**Trace a scenario:**

1. Switch to story mode with the canonical model already built — do not re-analyze the overall architecture
2. Follow the story mode scenario selection flow from [references/story-mode.md](references/story-mode.md)
3. After the trace is delivered, return to the refinement prompt

**Adjust the map:**

1. Use `AskUserQuestion` to ask what to change:
   - `Merge components` — `Combine related components into one node`
   - `Split a component` — `Break a grouped node into its parts`
   - `Add a component` — `I know something is missing`
   - `Remove a component` — `Drop a node that is not useful`
   - `Change grouping` — `Reorganize how components are clustered`
2. Apply the requested change to the model
3. If html mode: rewrite `architecture-map.json` and re-run the renderer. Preserve existing `position` values for unchanged components so the user does not lose their mental map of the layout
4. If chat mode: re-output the updated map
5. Return to the refinement prompt

**Done:**

End the skill execution.

### Refinement limits

- Maximum 3 refinement iterations. After the third, deliver the final output and stop.
- Each iteration should mention which iteration it is: "Refinement 1/3", "Refinement 2/3", "Refinement 3/3".
- If `AskUserQuestion` is unavailable, skip the entire refinement loop. Deliver the output and stop.

## General rules

- Be concrete: use real files, symbols, and line numbers when you have them.
- Be honest: confidence and unknowns are first-class outputs.
- Be compact: if the repo is large, aggregate.
- Be deterministic: the same evidence should produce the same model.
- Fix validation errors from the renderer instead of forcing a broken output through.
