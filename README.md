# /project-map

A Claude Code skill that generates evidence-based architecture maps from any project. Point it at a codebase, a set of scripts, a config directory, or even a documentation tree — it analyzes the structure and produces a visual map of how everything connects.

## Installation

```bash
git clone https://github.com/Iziman127/project-map-skill.git ~/.claude/skills/project-map
```

Restart Claude Code. The `/project-map` command is now available in any project.

## Quick start

```
/project-map html
```

That's it. The skill scans your project, builds a canonical model, and renders an interactive HTML map you can explore in your browser.

## Output modes

| Command | What you get |
|---|---|
| `/project-map html` | Interactive React Flow canvas in your browser |
| `/project-map chat` | Structured architecture map directly in chat |
| `/project-map story` | Step-by-step trace of a specific scenario through the code |

If you run `/project-map` without arguments, it asks which mode you prefer.

## What it maps

- Entry points and triggers
- Route groups and business domains
- External service dependencies
- Storage systems and databases
- Config sources and secrets
- UI or operator surfaces
- Internal boundaries and shared libraries

Every component on the map is backed by **evidence** — real file references, line numbers, and concrete reasons. No guesswork.

## How it works

1. **Analyze** — Scans the project starting from entry points, not by reading every file
2. **Model** — Builds a structured JSON model (`architecture-map.json`) with components, connections, confidence scores, and evidence
3. **Classify** — Determines the project type (webapp, pipeline, microservices, library, CLI tool, etc.)
4. **Render** — Produces the output in your chosen format

## Supported project types

- Web applications (frontend + backend, APIs, CRUD)
- Data pipelines and ETL workflows
- Event-driven systems (queues, pub/sub)
- CLI tools and workers
- Microservice architectures
- Libraries and SDK packages
- Claude Code skills and prompt tools
- Config trees and infrastructure-as-code
- Documentation structures

## Features

- **Incremental updates** — If an `architecture-map.json` already exists, you can update it instead of re-analyzing from scratch
- **Monorepo support** — Detects large repos and lets you scope the map to a specific service
- **Confidence scoring** — Every node is marked high/medium/low confidence so you know what's proven vs. inferred
- **Post-render refinement** — Zoom in on a domain, trace a scenario, or adjust the map after delivery
- **Story mode** — Walk through a concrete request or job flow step by step with exact file paths and line numbers

## Requirements

- Python 3 (for the HTML renderer)
- A browser (for the interactive HTML output — falls back to in-chat mode if unavailable)

## File structure

```
project-map/
  SKILL.md              # Skill definition and workflow
  template.html         # React Flow HTML template
  scripts/
    render_map.py       # Model validator + HTML renderer
    open_html.py        # Browser launcher with headless detection
  references/
    model.md            # Canonical model schema
    analysis.md         # Analysis workflow guide
    layouts.md          # Layout rules and node budgets
    story-mode.md       # Story mode trace rules
```
