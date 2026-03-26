# Analysis Workflow

Use this reference while building the canonical model. This applies to any project — codebases, skills, config trees, documentation, script collections, or any structured set of files.

## 1. Classify the project

Look for the dominant shape first, then note secondary patterns. Not every project is a traditional software codebase — adapt to whatever is actually in the directory.

### Common signals

| Signal | Likely type |
|---|---|
| HTTP routes, controllers, frontend + backend, CRUD | `webapp` |
| Sequential orchestration, ETL, automation, content generation | `pipeline` |
| Topics, queues, subscribers, webhook fan-out | `event-driven` |
| Command tree, subcommands, argument parsers | `cli-tool` |
| Scheduled jobs, background processors, workers | `worker` |
| Multiple deployable services or service directories | `microservices` |
| Mostly exported modules/adapters with no central runtime | `library` |
| SKILL.md or prompt definition with references, scripts, templates | `skill` |
| Config files, IaC, dotfiles, settings trees | `config` |
| Markdown/text structure, knowledge base, content hierarchy | `docs` |

Mixed projects are common. Set `primary` to the dominant shape, put the rest in `secondary`, and choose `render_as` for the clearest visual explanation.

### Non-code projects

For projects that are not traditional codebases, adapt the analysis vocabulary:

- **Entry points** become: main definition file (SKILL.md), root config, index document
- **Routes/handlers** become: sections, reference files, sub-documents
- **External services** become: external tools, CDN assets, referenced systems
- **Storage** becomes: output files, templates, generated artifacts
- **Config** stays config but may be the primary content, not supporting infrastructure

Do not reject a project or ask the user to switch to a "real codebase". Map whatever is there.

## 2. Gather evidence in this order

1. Entry points
2. Trigger surfaces
3. Main execution flow
4. Storage and state
5. External dependencies
6. Internal boundaries
7. Config and secrets
8. UI or operator surfaces

Do not start by scanning every file. Start from real execution surfaces and move inward.

## 3. Useful search patterns

### Entry points and triggers

- `main.py`, `app.py`, `server.py`, `index.ts`, `main.go`
- `if __name__ == "__main__"`
- `app.listen`
- `createServer`
- `func main()`
- command registration such as `argparse`, `click`, `commander`, `cobra`
- schedulers such as `cron`, `APScheduler`, `Bull`, `Celery`

### Route and handler discovery

- `app.get`, `app.post`, `app.put`, `app.delete`
- `router.`
- `@app.route`
- `urlpatterns`
- `FastAPI(`, `APIRouter(`

### Storage and models

- `BaseModel`, `@dataclass`, ORM entities, Prisma models
- `CREATE TABLE`
- connection setup for Postgres, MySQL, Redis, MongoDB, S3, filesystem storage

### External services

- `fetch(`, `axios`, `requests.`, `httpx`, `HttpClient`
- `openai`, `anthropic`, `gemini`
- `stripe`, `paypal`
- `sendgrid`, `ses`, `smtp`
- `Kafka`, `RabbitMQ`, `SQS`, `SNS`, `PubSub`

### Config

- `.env*`, `config/*`, `settings.*`
- `process.env`, `os.getenv`, `os.environ`, `System.getenv`

## 4. Build an evidence table while reading

Use a quick working table before you finalize the model.

| Item | Candidate type | Evidence | Confidence | Keep? |
|---|---|---|---|---|
| `src/routes/auth.ts` | route group | registered in `app.ts` | high | yes |
| `lib/cache.ts` | utility or service? | imported widely, wraps Redis | medium | maybe |

This step prevents pretty-but-false maps.

## 5. Confidence rules

Upgrade confidence when you have:

- direct registration
- concrete call chain
- config plus implementation
- schema plus read/write path

Downgrade confidence when you only have:

- dependency manifests
- naming conventions
- dead code
- generated files with no runtime path

## 6. Treat unknowns as output, not failure

Examples:

- "Worker trigger is external; no scheduler found in-repo."
- "There are Prisma models, but no obvious API route owning them."
- "Frontend assets exist, but no build or runtime entry was found."

Put these in `open_questions`.

## 7. Guardrails

- Do not infer a message broker from a single client package dependency.
- Do not infer a database from an ORM package alone.
- Do not infer a frontend from shared component files alone.
- Do not infer microservices just because the repo has many folders.
- Do not model every helper or DTO as a component.

## 8. Monorepo handling

If a scope was selected during the scope detection step (step 1 in SKILL.md), restrict all analysis to that scope. Only scan files within the chosen subtree. Cross-boundary references (imports from outside the scope) should be noted as external dependencies rather than fully traced. Set `project.scope` to the path prefix that was analyzed.

For large repos, first find:

- deployable apps
- packages used by multiple apps
- shared infrastructure modules

Then decide whether the map should show:

- the whole monorepo at service/domain level
- one application only
- one request or worker path only

Be explicit about the scope in `project.summary`.
