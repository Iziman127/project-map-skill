# Canonical Architecture Model

Build this model before generating chat, HTML, or story outputs.

## Required top-level shape

```json
{
  "project": {
    "name": "Project Name",
    "root": ".",
    "summary": "2-3 sentence system summary",
    "scope": "services/auth-api"
  },
  "classification": {
    "primary": "webapp",
    "secondary": ["worker"],
    "render_as": "webapp",
    "reason": "Why this classification fits the repo"
  },
  "stats": [
    { "label": "API Routes", "value": 18, "color": "purple" },
    { "label": "3rd-Party APIs", "value": 6, "color": "accent" },
    { "label": "DB Tables", "value": 3, "color": "cyan" },
    { "label": "Components", "value": 14, "color": "orange" }
  ],
  "components": [],
  "connections": [],
  "open_questions": [],
  "assumptions": [],
  "_meta": {
    "last_analyzed": "2026-03-26T14:30:00Z",
    "skill_version": "1.1",
    "scope": null
  }
}
```

### project.scope (optional)

Set when the user chose to map a specific part of the repository during scope detection. Contains the path prefix that was analyzed (e.g., `"services/auth-api"`). Omit or set to `null` for full-repo maps. Mention the scope in `project.summary` when set.

### _meta (optional)

Internal metadata for incremental updates. The renderer ignores this field entirely.

- `last_analyzed`: ISO 8601 timestamp of the last analysis run.
- `skill_version`: version of the skill that produced this model.
- `scope`: mirrors `project.scope` for quick access during incremental re-runs.

Do not rely on `_meta` for rendering or classification. It exists only to support incremental re-runs.

## Component schema

Each component must be an architectural unit, not an arbitrary file.

```json
{
  "id": "p-auth",
  "kind": "pipeline",
  "label": "Auth",
  "icon": "🔐",
  "color": "#3b82f6",
  "sub": "Route group",
  "desc": "Handles login, logout, and token refresh.",
  "file": "src/routes/auth.ts",
  "tags": ["FASTIFY", "7 ENDPOINTS"],
  "order": 2,
  "related_to": "p-api",
  "affinity": "auth-stack",
  "confidence": "high",
  "evidence": [
    {
      "file": "src/routes/auth.ts",
      "lines": "12-88",
      "reason": "Registers auth routes and token handlers"
    }
  ]
}
```

### Required component fields

- `id`
- `kind`
- `label`
- `desc`
- `confidence`
- `evidence`

### Allowed `kind` values

- `input`
- `pipeline`
- `service`
- `library`
- `ui`
- `storage`
- `config`
- `broker`
- `producer`
- `consumer`
- `terminus`
- `microservice`
- `shared`

### Optional component fields

- `icon`
- `color`
- `sub`
- `file`
- `tags`
- `order`
- `related_to`
- `affinity`
- `position`

Use `position` only when you have a deliberate manual override. The renderer should otherwise place nodes automatically.

## Connection schema

```json
{
  "id": "e-auth-db",
  "source": "p-auth",
  "target": "db-main",
  "kind": "storage",
  "label": "Reads/Writes",
  "confidence": "high",
  "evidence": [
    {
      "file": "src/services/auth-service.ts",
      "lines": "44-91",
      "reason": "Persists sessions through the repository"
    }
  ]
}
```

### Required connection fields

- `source`
- `target`
- `kind`
- `confidence`
- `evidence`

### Allowed connection `kind` values

- `main-flow`
- `input`
- `service`
- `storage`
- `config`
- `trigger`
- `frontend`
- `event`
- `internal`

## Confidence scoring

- `high`: direct registration, explicit constructor wiring, concrete call site, real config, real schema
- `medium`: multiple strong hints but one hop inferred
- `low`: plausible but incomplete; keep these rare

If many nodes are `low`, the map is too speculative.

## Evidence rules

Every evidence item should answer: "Why should this node or edge exist?"

Good evidence:

- route registration
- imports plus actual call sites
- ORM model definitions plus usage
- queue/topic declarations
- config keys consumed in the relevant module
- concrete CLI command registration

Weak evidence:

- filename alone
- dependency in `package.json` with no code usage
- a vague utility import with no business effect

## Open questions and assumptions

Use `open_questions` for things you could not prove.

```json
[
  "No explicit scheduler found; worker trigger may be external.",
  "A React frontend is likely, but only shared UI components were visible."
]
```

Use `assumptions` sparingly and keep them explicit.

## Stats guidelines

The `stats` array drives the 4 headline numbers shown on the rendered map. Choose labels that communicate what the system does, not renderer internals.

Good labels:
- `API Routes` or `REST Endpoints` instead of `Endpoints`
- `Components` instead of `Nodes`
- `3rd-Party APIs` instead of `Services`
- `Data Stores` or `DB Tables` instead of `Storage`
- `Entry Points` or `Triggers` instead of `Sources`

Rules:
- Use domain-specific terms the reader already knows.
- Prefer concrete nouns (`DB Tables`, `Queue Topics`) over abstract ones (`Storage`, `Sources`).
- The renderer always appends a `Components` stat (total rendered count) if none of the 4 stats has label `Nodes` or `Components`. Prefer labelling it `Components`.
- Keep labels short (1-2 words). The mini-cards have limited space.

## Minimal quality checklist

Before rendering, verify:

- every component has evidence
- every connection points to real component IDs
- `classification.reason` is specific
- storage and config are separate when they play separate roles
- the map contains all major execution boundaries
- trivial helpers have been grouped or omitted
