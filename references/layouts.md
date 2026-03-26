# Layouts And Rendering

Use this reference only after the canonical model exists.

## Node budget and aggregation

Aim for a readable map, not exhaustive coverage.

| Scope | Target nodes | Hard ceiling | Strategy |
|---|---|---|---|
| Small app | 8-14 | 18 | show concrete components |
| Medium app | 12-20 | 26 | group trivial helpers |
| Large app | 14-24 | 30 | group by domain/service boundary |
| Monorepo | 10-18 | 24 | show apps/services only |

If you exceed the ceiling:

1. merge helper libraries into one supporting node
2. merge route files into route groups or domains
3. merge storage replicas into one storage node unless the distinction matters
4. cut speculative nodes before concrete ones

## Affinity grouping

If two components exist primarily to serve one another, give them the same `affinity` key so the renderer aligns them vertically.

Good uses:

- preview UI + asset server
- upload worker + object storage
- API gateway + auth middleware

## Render shapes

Use `classification.render_as` to pick the layout.

### `webapp`

- Top: UI or operator surfaces
- Upper middle: external services
- Center: route groups or business domains
- Lower middle: shared libraries
- Bottom: storage and config
- Left edge: inbound client/input surfaces

### `pipeline`

- Left to right main flow
- Inputs on the far left
- External services above the stage that calls them
- Libraries below the stage that uses them
- Storage/config at the bottom
- Terminus on the far right, on the same row as the main flow

### `event-driven`

- Producers on the left
- Broker/hub in the center
- Consumers on the right
- Shared services/config above
- Storage and DLQs below

### `microservices`

- Gateway/input on the left
- Service boundaries across the center
- Shared infra and third-party services above
- Datastores below the owning service when possible
- Shared config and platform services at the bottom-left or top-left

### `library`

- Public API or entry modules on the left
- Core modules in the center
- Adapters/integrations above
- Examples, fixtures, or storage-like artifacts below

## Edge styles

Map connection kinds like this:

| Kind | Style intent |
|---|---|
| `main-flow` | animated, thick |
| `input` | animated |
| `service` | dashed, source-colored |
| `storage` | solid smooth path |
| `config` | gray dashed |
| `trigger` | dashed, labeled when useful |
| `frontend` | animated |
| `event` | dashed or animated hub link |
| `internal` | solid, understated |

## Chat output shape

Always start with a compact header:

```text
PROJECT_NAME — System Architecture Map
Type: PRIMARY (rendered as RENDER_AS)
Why: short classification reason
```

Then use the relevant structure:

### `webapp`

- `Frontend / Entry`
- `Main Flow`
- `External Services`
- `Storage & Config`
- `Confidence & Unknowns`

### `pipeline`

- `Main Flow`
- `External Services`
- `Resources & Libs`
- `Storage & Config`
- `Entry / UI`
- `Confidence & Unknowns`

### `event-driven`

- `Event Flow`
- `Producers`
- `Consumers`
- `Shared Services`
- `Storage & Config`
- `Confidence & Unknowns`

### `microservices`

- `Ingress`
- `Service Boundaries`
- `Shared Infra`
- `Storage & Config`
- `Confidence & Unknowns`

### `library`

- `Public Surface`
- `Core Modules`
- `Adapters`
- `State / Fixtures`
- `Confidence & Unknowns`

## HTML guidance

Prefer the renderer over manual editing:

```bash
python ${SKILL_DIR}/scripts/render_map.py \
  --model architecture-map.json \
  --output project-map.html
```

The renderer will:

- validate required fields
- auto-place nodes unless `position` is provided
- add the pipeline lane for pipeline-like layouts
- style edges from connection kinds
- surface evidence and confidence in the details panel

## Failure modes

If the rendered map is crowded or misleading:

1. reduce node count in the model
2. increase grouping
3. remove low-confidence nodes
4. fall back to in-chat mode if the environment cannot open a browser
