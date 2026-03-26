#!/usr/bin/env python3
"""Render an architecture map HTML artifact from a canonical model."""

from __future__ import annotations

import argparse
import copy
import html
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


SKILL_DIR = Path(__file__).resolve().parent.parent
INTERACTIVE_TEMPLATE = SKILL_DIR / "template.html"

ALLOWED_CONFIDENCE = {"high", "medium", "low"}
ALLOWED_COMPONENT_KINDS = {
    "input",
    "pipeline",
    "service",
    "library",
    "ui",
    "storage",
    "config",
    "broker",
    "producer",
    "consumer",
    "terminus",
    "microservice",
    "shared",
}
ALLOWED_CONNECTION_KINDS = {
    "main-flow",
    "input",
    "service",
    "storage",
    "config",
    "trigger",
    "frontend",
    "event",
    "internal",
}
KIND_LABELS = {
    "input": "Input",
    "pipeline": "Main Flow",
    "service": "External Service",
    "library": "Library",
    "ui": "UI",
    "storage": "Storage",
    "config": "Config",
    "broker": "Broker",
    "producer": "Producer",
    "consumer": "Consumer",
    "terminus": "Terminus",
    "microservice": "Microservice",
    "shared": "Shared Module",
}
CONNECTION_KIND_LABELS = {
    "main-flow": "Main Flow",
    "input": "Input",
    "service": "External Service",
    "storage": "Storage",
    "config": "Config",
    "trigger": "Trigger",
    "frontend": "Frontend",
    "event": "Event",
    "internal": "Internal",
}
DEFAULT_ICONS = {
    "input": "📥",
    "pipeline": "⚙️",
    "service": "🔌",
    "library": "📚",
    "ui": "🖥️",
    "storage": "🗄️",
    "config": "🔑",
    "broker": "📨",
    "producer": "📤",
    "consumer": "📥",
    "terminus": "◆",
    "microservice": "🧩",
    "shared": "🔧",
}
DEFAULT_COLORS = {
    "input": "#f97316",
    "pipeline": "#3b82f6",
    "service": "#d946ef",
    "library": "#64748b",
    "ui": "#ffffff",
    "storage": "#eab308",
    "config": "#94a3b8",
    "broker": "#ec4899",
    "producer": "#22d3ee",
    "consumer": "#22c55e",
    "terminus": "#22c55e",
    "microservice": "#3b82f6",
    "shared": "#64748b",
}
STAT_COLOR_MAP = {
    "purple": "var(--purple)",
    "accent": "var(--accent)",
    "cyan": "var(--cyan)",
    "orange": "var(--orange)",
    "green": "var(--green)",
    "yellow": "var(--yellow)",
    "red": "var(--red)",
    "white": "var(--text)",
}
RENDER_AS_MAP = {
    "webapp": "webapp",
    "pipeline": "pipeline",
    "event-driven": "event-driven",
    "cli-tool": "pipeline",
    "worker": "pipeline",
    "microservices": "microservices",
    "library": "library",
    "skill": "pipeline",
    "config": "library",
    "docs": "library",
}
NODE_MIN_WIDTH = 200
NODE_MAX_WIDTH = 240
NODE_BASE_HEIGHT = 76
NODE_TAG_ROW_HEIGHT = 24
NODE_PAD = 60
LANE_HEIGHT = 170
MIN_H_GAP = 80
MIN_V_GAP = 50


def estimate_node_size(component: dict[str, Any]) -> dict[str, int]:
    """Estimate rendered pixel size of a node from its content."""
    tags = [str(t) for t in component.get("tags", []) if str(t).strip()]
    tag_rows = 0
    if tags:
        row_chars = 0
        tag_rows = 1
        for tag in tags:
            chars = len(tag) * 8 + 16
            if row_chars + chars > NODE_MAX_WIDTH - 32:
                tag_rows += 1
                row_chars = chars
            else:
                row_chars += chars
    h = NODE_BASE_HEIGHT + tag_rows * NODE_TAG_ROW_HEIGHT
    label = str(component.get("label", ""))
    w = max(NODE_MIN_WIDTH, min(NODE_MAX_WIDTH, len(label) * 9 + 70))
    return {"w": w, "h": h}


def build_sizes(components: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    """Build a size lookup for all components."""
    return {c["id"]: estimate_node_size(c) for c in components}


def max_h(items: list[dict[str, Any]], sizes: dict[str, dict[str, int]]) -> int:
    """Max height among a list of components."""
    if not items:
        return NODE_BASE_HEIGHT
    return max(sizes.get(item["id"], {"h": NODE_BASE_HEIGHT})["h"] for item in items)


def max_w(items: list[dict[str, Any]], sizes: dict[str, dict[str, int]]) -> int:
    """Max width among a list of components."""
    if not items:
        return NODE_MAX_WIDTH
    return max(sizes.get(item["id"], {"w": NODE_MAX_WIDTH})["w"] for item in items)


class ValidationError(Exception):
    pass


def load_model(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Invalid JSON in {path}: {exc}") from exc


def validate_model(model: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    errors: list[str] = []

    if not isinstance(model, dict):
        raise ValidationError("Model must be a JSON object.")

    project = model.get("project")
    if not isinstance(project, dict):
        errors.append("Missing object: project")
    else:
        if not project.get("name"):
            errors.append("Missing project.name")
        if not project.get("summary"):
            warnings.append("project.summary is empty; renderer will use a generic summary.")

    classification = model.get("classification")
    if not isinstance(classification, dict):
        errors.append("Missing object: classification")
    else:
        primary = classification.get("primary")
        if primary not in RENDER_AS_MAP:
            errors.append(
                "classification.primary must be one of "
                + ", ".join(sorted(RENDER_AS_MAP))
            )

    components = model.get("components")
    if not isinstance(components, list) or not components:
        errors.append("components must be a non-empty array")
        components = []

    component_ids: set[str] = set()
    allowed_component_kinds = ", ".join(sorted(ALLOWED_COMPONENT_KINDS))
    for index, component in enumerate(components):
        label = f"components[{index}]"
        if not isinstance(component, dict):
            errors.append(f"{label} must be an object")
            continue
        cid = component.get("id")
        if not cid:
            errors.append(f"{label} missing id")
        elif cid in component_ids:
            errors.append(f"Duplicate component id: {cid}")
        else:
            component_ids.add(cid)

        kind = component.get("kind")
        if not kind:
            errors.append(f"{label} missing kind")
        elif kind not in ALLOWED_COMPONENT_KINDS:
            errors.append(f"{label} kind must be one of: {allowed_component_kinds}")
        if not component.get("label"):
            errors.append(f"{label} missing label")
        if not component.get("desc"):
            errors.append(f"{label} missing desc")
        if component.get("confidence") not in ALLOWED_CONFIDENCE:
            errors.append(f"{label} confidence must be high|medium|low")
        if not normalize_evidence(component.get("evidence")):
            errors.append(f"{label} must include evidence")

        position = component.get("position")
        if position is not None:
            if not isinstance(position, dict):
                errors.append(f"{label}.position must be an object with x and y")
            else:
                for axis in ("x", "y"):
                    if axis not in position:
                        errors.append(f"{label}.position missing {axis}")
                        continue
                    value = position[axis]
                    if isinstance(value, bool):
                        errors.append(f"{label}.position.{axis} must be an integer")
                        continue
                    try:
                        int(value)
                    except (TypeError, ValueError):
                        errors.append(f"{label}.position.{axis} must be an integer")

    connections = model.get("connections", [])
    if not isinstance(connections, list):
        errors.append("connections must be an array")
        connections = []

    allowed_connection_kinds = ", ".join(sorted(ALLOWED_CONNECTION_KINDS))
    for index, connection in enumerate(connections):
        label = f"connections[{index}]"
        if not isinstance(connection, dict):
            errors.append(f"{label} must be an object")
            continue
        source = connection.get("source")
        target = connection.get("target")
        if not source or source not in component_ids:
            errors.append(f"{label} has unknown source: {source}")
        if not target or target not in component_ids:
            errors.append(f"{label} has unknown target: {target}")
        kind = connection.get("kind")
        if not kind:
            errors.append(f"{label} missing kind")
        elif kind not in ALLOWED_CONNECTION_KINDS:
            errors.append(f"{label} kind must be one of: {allowed_connection_kinds}")
        if connection.get("confidence") not in ALLOWED_CONFIDENCE:
            errors.append(f"{label} confidence must be high|medium|low")
        if not normalize_evidence(connection.get("evidence")):
            errors.append(f"{label} must include evidence")

    if len(component_ids) > 30:
        warnings.append(
            f"Model has {len(component_ids)} components. Consider grouping before rendering."
        )

    if errors:
        raise ValidationError("\n".join(errors))
    return warnings


def normalize_evidence(evidence: Any) -> list[str]:
    if not evidence:
        return []
    normalized: list[str] = []
    if isinstance(evidence, list):
        for item in evidence:
            if isinstance(item, str) and item.strip():
                normalized.append(item.strip())
            elif isinstance(item, dict):
                file_part = str(item.get("file", "")).strip()
                lines_part = str(item.get("lines", "")).strip()
                reason_part = str(item.get("reason", "")).strip()
                bits = [part for part in [file_part, lines_part] if part]
                prefix = ":".join(bits) if bits else ""
                if prefix and reason_part:
                    normalized.append(f"{prefix} — {reason_part}")
                elif prefix:
                    normalized.append(prefix)
                elif reason_part:
                    normalized.append(reason_part)
    return normalized


def parse_position(position: Any) -> dict[str, int] | None:
    if not isinstance(position, dict):
        return None
    if "x" not in position or "y" not in position:
        return None
    x = position["x"]
    y = position["y"]
    if isinstance(x, bool) or isinstance(y, bool):
        return None
    try:
        return {"x": int(x), "y": int(y)}
    except (TypeError, ValueError):
        return None


def render_as_for(model: dict[str, Any]) -> str:
    classification = model.get("classification", {})
    explicit = classification.get("render_as")
    if explicit in {"webapp", "pipeline", "event-driven", "microservices", "library"}:
        return explicit
    return RENDER_AS_MAP.get(classification.get("primary"), "webapp")


def sort_components(components: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        components,
        key=lambda item: (
            item.get("order", 9999),
            str(item.get("label", "")).lower(),
            str(item.get("id", "")).lower(),
        ),
    )


def build_related_lookup(
    components: dict[str, dict[str, Any]], connections: list[dict[str, Any]]
) -> dict[str, str]:
    preferred_targets = {
        "pipeline",
        "microservice",
        "producer",
        "consumer",
        "broker",
        "terminus",
    }
    related: dict[str, str] = {}
    for cid, component in components.items():
        if component.get("related_to") in components:
            related[cid] = component["related_to"]
            continue
        for connection in connections:
            src = connection.get("source")
            dst = connection.get("target")
            if src == cid and dst in components and components[dst].get("kind") in preferred_targets:
                related[cid] = dst
                break
            if dst == cid and src in components and components[src].get("kind") in preferred_targets:
                related[cid] = src
                break
    return related


def group_by_kind(components: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for component in components:
        groups[component.get("kind", "pipeline")].append(component)
    for key, items in list(groups.items()):
        groups[key] = sort_components(items)
    return groups


def assign_positions(model: dict[str, Any]) -> list[dict[str, Any]]:
    components = [copy.deepcopy(component) for component in model.get("components", [])]
    sizes = build_sizes(components)
    by_id = {component["id"]: component for component in components}
    related_lookup = build_related_lookup(by_id, model.get("connections", []))
    grouped = group_by_kind(components)
    layout = render_as_for(model)
    positions: dict[str, dict[str, int]] = {}
    manual_positions: dict[str, dict[str, int]] = {}

    for component in components:
        parsed_position = parse_position(component.get("position"))
        if parsed_position is not None:
            manual_positions[component["id"]] = parsed_position

    if len(manual_positions) == len(components):
        positions = dict(manual_positions)
    elif layout == "pipeline":
        positions = layout_pipeline(grouped, related_lookup, sizes)
    elif layout == "event-driven":
        positions = layout_event_driven(grouped, related_lookup, sizes)
    elif layout == "microservices":
        positions = layout_microservices(grouped, related_lookup, sizes)
    elif layout == "library":
        positions = layout_library(grouped, related_lookup, sizes)
    else:
        positions = layout_webapp(grouped, related_lookup, sizes)

    # Fallback: place any component that the layout function did not handle.
    # This covers kinds like broker/producer/consumer in non-event-driven layouts.
    unplaced = [c for c in components if c["id"] not in positions and c["id"] not in manual_positions]
    if unplaced:
        all_y = [pos["y"] for pos in positions.values()] or [0]
        fallback_y = max(all_y) + NODE_BASE_HEIGHT + MIN_V_GAP
        fallback_step = max_w(unplaced, sizes) + MIN_H_GAP
        for idx, comp in enumerate(unplaced):
            positions[comp["id"]] = {"x": idx * fallback_step, "y": fallback_y}

    apply_affinity_alignment(components, positions, locked_ids=set(manual_positions))
    resolve_collisions(positions, sizes, locked_ids=set(manual_positions))
    positions.update(manual_positions)

    for component in components:
        cid = component["id"]
        component["position"] = positions[cid]

    lane_node = build_lane_node(layout, components, sizes)
    render_nodes = [lane_node] if lane_node else []
    render_nodes.extend(build_render_node(component, sizes) for component in components)
    normalize_positions(render_nodes)
    return render_nodes


def layout_webapp(grouped: dict[str, list[dict[str, Any]]], related: dict[str, str], sizes: dict[str, dict[str, int]]) -> dict[str, dict[str, int]]:
    positions: dict[str, dict[str, int]] = {}
    flow = grouped.get("pipeline", []) or grouped.get("microservice", [])
    h_step = max_w(flow, sizes) + MIN_H_GAP
    inputs = grouped.get("input", [])
    ui = grouped.get("ui", [])
    services = grouped.get("service", [])
    libraries = grouped.get("library", []) + grouped.get("shared", [])
    storage = grouped.get("storage", [])
    config = grouped.get("config", [])
    terminus = grouped.get("terminus", [])

    flow_y = 0
    flow_x = place_row(flow, start_x=440, y=flow_y, positions=positions, sizes=sizes)
    place_column(inputs, x=0, start_y=flow_y, positions=positions, sizes=sizes)

    service_y = flow_y - max_h(flow, sizes) - MIN_V_GAP
    place_related_row(services, y=service_y, fallback_x=440, positions=positions, related=related, sizes=sizes)

    ui_y = service_y - max_h(services, sizes) - MIN_V_GAP
    place_row_centered(ui, y=ui_y, anchor_x=average(flow_x) or 660, positions=positions, sizes=sizes)

    library_y = flow_y + max_h(flow, sizes) + MIN_V_GAP
    place_related_row(libraries, y=library_y, fallback_x=380, positions=positions, related=related, sizes=sizes)

    storage_y = library_y + max_h(libraries, sizes) + MIN_V_GAP
    place_related_row(storage, y=storage_y, fallback_x=500, positions=positions, related=related, sizes=sizes)

    config_start = (min(flow_x) - 400) if flow_x else 120
    place_related_row(config, y=storage_y, fallback_x=config_start, positions=positions, related=related, sizes=sizes)

    terminus_anchor = (max(flow_x) + h_step) if flow_x else 1100
    place_row_centered(terminus, y=flow_y, anchor_x=terminus_anchor, positions=positions, centered=False, sizes=sizes)
    return positions


def layout_pipeline(grouped: dict[str, list[dict[str, Any]]], related: dict[str, str], sizes: dict[str, dict[str, int]]) -> dict[str, dict[str, int]]:
    positions: dict[str, dict[str, int]] = {}
    flow = grouped.get("pipeline", [])
    inputs = grouped.get("input", [])
    services = grouped.get("service", [])
    ui = grouped.get("ui", [])
    libraries = grouped.get("library", []) + grouped.get("shared", [])
    storage = grouped.get("storage", [])
    config = grouped.get("config", [])
    terminus = grouped.get("terminus", [])
    h_step = max_w(flow, sizes) + MIN_H_GAP

    flow_y = 0
    flow_x = place_row(flow, start_x=0, y=flow_y, positions=positions, sizes=sizes)
    place_column(inputs, x=-360, start_y=flow_y - 40, positions=positions, sizes=sizes)

    terminus_start = (max(flow_x) + h_step) if flow_x else h_step
    place_row_centered(terminus, y=flow_y, anchor_x=terminus_start, positions=positions, centered=False, sizes=sizes)

    service_y = flow_y - max_h(flow, sizes) - MIN_V_GAP
    place_related_row(services, y=service_y, fallback_x=0, positions=positions, related=related, sizes=sizes)

    ui_y = service_y - max_h(services, sizes) - MIN_V_GAP
    place_related_row(ui, y=ui_y, fallback_x=440, positions=positions, related=related, sizes=sizes)

    library_y = flow_y + max_h(flow, sizes) + MIN_V_GAP
    place_related_row(libraries, y=library_y, fallback_x=0, positions=positions, related=related, sizes=sizes)

    storage_y = library_y + max_h(libraries, sizes) + MIN_V_GAP
    place_related_row(storage, y=storage_y, fallback_x=40, positions=positions, related=related, sizes=sizes)
    place_related_row(config, y=storage_y, fallback_x=-360, positions=positions, related=related, sizes=sizes)
    return positions


def layout_event_driven(grouped: dict[str, list[dict[str, Any]]], related: dict[str, str], sizes: dict[str, dict[str, int]]) -> dict[str, dict[str, int]]:
    del related
    positions: dict[str, dict[str, int]] = {}
    producers = grouped.get("producer", []) + grouped.get("input", [])
    broker = grouped.get("broker", []) or grouped.get("pipeline", [])
    consumers = grouped.get("consumer", [])
    services = grouped.get("service", []) + grouped.get("ui", []) + grouped.get("config", [])
    storage = grouped.get("storage", []) + grouped.get("shared", [])
    terminus = grouped.get("terminus", [])

    flow_y = 0
    place_column(producers, x=0, start_y=flow_y, positions=positions, sizes=sizes)
    col_gap = max_w(producers, sizes) + MIN_H_GAP
    broker_x = col_gap + max_w(producers, sizes)
    place_column(broker, x=broker_x, start_y=flow_y + 100, positions=positions, sizes=sizes)
    consumer_x = broker_x + max_w(broker, sizes) + MIN_H_GAP + max_w(consumers, sizes)
    place_column(consumers, x=consumer_x, start_y=flow_y, positions=positions, sizes=sizes)

    all_cols = producers + broker + consumers
    service_y = flow_y - max_h(all_cols, sizes) - MIN_V_GAP
    place_related_row(services, y=service_y, fallback_x=400, positions=positions, related={}, sizes=sizes)

    storage_y = flow_y + max_h(all_cols, sizes) + MIN_V_GAP
    place_related_row(storage, y=storage_y, fallback_x=400, positions=positions, related={}, sizes=sizes)

    place_related_row(terminus, y=flow_y + 100, fallback_x=consumer_x + max_w(consumers, sizes) + MIN_H_GAP, positions=positions, related={}, sizes=sizes)
    return positions


def layout_microservices(grouped: dict[str, list[dict[str, Any]]], related: dict[str, str], sizes: dict[str, dict[str, int]]) -> dict[str, dict[str, int]]:
    positions: dict[str, dict[str, int]] = {}
    inputs = grouped.get("input", [])
    services_row = grouped.get("microservice", []) or grouped.get("pipeline", [])
    ui = grouped.get("ui", [])
    ext_services = grouped.get("service", [])
    libraries = grouped.get("library", []) + grouped.get("shared", [])
    storage = grouped.get("storage", [])
    config = grouped.get("config", [])
    terminus = grouped.get("terminus", [])
    h_step = max_w(services_row, sizes) + MIN_H_GAP

    flow_y = 0
    place_column(inputs, x=0, start_y=flow_y, positions=positions, sizes=sizes)
    service_x = place_row(services_row, start_x=440, y=flow_y, positions=positions, sizes=sizes)

    ext_y = flow_y - max_h(services_row, sizes) - MIN_V_GAP
    place_related_row(ext_services, y=ext_y, fallback_x=440, positions=positions, related=related, sizes=sizes)

    ui_y = ext_y - max_h(ext_services, sizes) - MIN_V_GAP
    place_row_centered(ui, y=ui_y, anchor_x=average(service_x) or 660, positions=positions, sizes=sizes)

    library_y = flow_y + max_h(services_row, sizes) + MIN_V_GAP
    place_related_row(libraries, y=library_y, fallback_x=440, positions=positions, related=related, sizes=sizes)

    storage_y = library_y + max_h(libraries, sizes) + MIN_V_GAP
    place_related_row(storage, y=storage_y, fallback_x=440, positions=positions, related=related, sizes=sizes)
    place_related_row(config, y=storage_y, fallback_x=40, positions=positions, related=related, sizes=sizes)

    terminus_anchor = (max(service_x) + h_step) if service_x else 1200
    place_row_centered(terminus, y=flow_y, anchor_x=terminus_anchor, positions=positions, centered=False, sizes=sizes)
    return positions


def layout_library(grouped: dict[str, list[dict[str, Any]]], related: dict[str, str], sizes: dict[str, dict[str, int]]) -> dict[str, dict[str, int]]:
    positions: dict[str, dict[str, int]] = {}
    inputs = grouped.get("input", []) + grouped.get("ui", [])
    core = grouped.get("pipeline", []) + grouped.get("library", [])
    services = grouped.get("service", [])
    shared = grouped.get("shared", [])
    storage = grouped.get("storage", []) + grouped.get("config", [])
    terminus = grouped.get("terminus", [])
    h_step = max_w(core, sizes) + MIN_H_GAP

    flow_y = 0
    place_column(inputs, x=0, start_y=flow_y, positions=positions, sizes=sizes)
    core_x = place_row(core, start_x=440, y=flow_y, positions=positions, sizes=sizes)

    service_y = flow_y - max_h(core, sizes) - MIN_V_GAP
    place_related_row(services, y=service_y, fallback_x=440, positions=positions, related=related, sizes=sizes)

    shared_y = flow_y + max_h(core, sizes) + MIN_V_GAP
    place_related_row(shared, y=shared_y, fallback_x=440, positions=positions, related=related, sizes=sizes)

    storage_y = shared_y + max_h(shared, sizes) + MIN_V_GAP
    place_related_row(storage, y=storage_y, fallback_x=340, positions=positions, related=related, sizes=sizes)

    terminus_anchor = (max(core_x) + h_step) if core_x else 1200
    place_row_centered(terminus, y=flow_y, anchor_x=terminus_anchor, positions=positions, centered=False, sizes=sizes)
    return positions


def place_row(
    items: list[dict[str, Any]],
    *,
    start_x: int,
    y: int,
    positions: dict[str, dict[str, int]],
    sizes: dict[str, dict[str, int]],
    step: int | None = None,
) -> list[int]:
    if step is None:
        step = max_w(items, sizes) + MIN_H_GAP
    xs: list[int] = []
    for index, item in enumerate(items):
        x = start_x + index * step
        positions[item["id"]] = {"x": x, "y": y}
        xs.append(x)
    return xs


def place_column(
    items: list[dict[str, Any]],
    *,
    x: int,
    start_y: int,
    positions: dict[str, dict[str, int]],
    sizes: dict[str, dict[str, int]],
    step: int | None = None,
) -> None:
    if step is None:
        step = max_h(items, sizes) + MIN_V_GAP
    for index, item in enumerate(items):
        positions[item["id"]] = {"x": x, "y": start_y + index * step}


def place_row_centered(
    items: list[dict[str, Any]],
    *,
    y: int,
    anchor_x: int,
    positions: dict[str, dict[str, int]],
    sizes: dict[str, dict[str, int]],
    centered: bool = True,
    step: int | None = None,
) -> None:
    if not items:
        return
    if step is None:
        step = max_w(items, sizes) + MIN_H_GAP
    start_x = anchor_x - ((len(items) - 1) * step // 2) if centered else anchor_x
    for index, item in enumerate(items):
        positions[item["id"]] = {"x": start_x + index * step, "y": y}


def place_related_row(
    items: list[dict[str, Any]],
    *,
    y: int,
    fallback_x: int,
    positions: dict[str, dict[str, int]],
    related: dict[str, str],
    sizes: dict[str, dict[str, int]],
) -> None:
    step = max_w(items, sizes) + MIN_H_GAP
    next_x = fallback_x
    grouped_by_anchor: dict[int | None, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        anchor = related.get(item["id"])
        anchor_x = positions[anchor]["x"] if anchor and anchor in positions else None
        grouped_by_anchor[anchor_x].append(item)

    for anchor_x, bucket in grouped_by_anchor.items():
        if anchor_x is None:
            for item in bucket:
                positions[item["id"]] = {"x": next_x, "y": y}
                next_x += step
            continue

        spread = max_w(bucket, sizes) + MIN_H_GAP
        start_x = anchor_x - ((len(bucket) - 1) * spread // 2)
        for index, item in enumerate(bucket):
            positions[item["id"]] = {"x": start_x + index * spread, "y": y}


def resolve_collisions(
    positions: dict[str, dict[str, int]],
    sizes: dict[str, dict[str, int]],
    *,
    locked_ids: set[str] | None = None,
    pad_x: int = 60,
    pad_y: int = 40,
) -> None:
    """Nudge overlapping nodes apart. Locked nodes are not moved."""
    locked = locked_ids or set()
    ids = list(positions)
    changed = True
    iterations = 0
    while changed and iterations < 50:
        changed = False
        iterations += 1
        for i in range(len(ids)):
            a = ids[i]
            if a in locked or a not in positions:
                continue
            ax, ay = positions[a]["x"], positions[a]["y"]
            a_w = sizes.get(a, {"w": NODE_MAX_WIDTH})["w"]
            a_h = sizes.get(a, {"h": NODE_BASE_HEIGHT})["h"]
            for j in range(i + 1, len(ids)):
                b = ids[j]
                if b not in positions:
                    continue
                bx, by = positions[b]["x"], positions[b]["y"]
                b_w = sizes.get(b, {"w": NODE_MAX_WIDTH})["w"]
                b_h = sizes.get(b, {"h": NODE_BASE_HEIGHT})["h"]
                overlap_x = (max(a_w, b_w) + pad_x) - abs(ax - bx)
                overlap_y = (max(a_h, b_h) + pad_y) - abs(ay - by)
                if overlap_x <= 0 or overlap_y <= 0:
                    continue
                if overlap_x < overlap_y:
                    shift = (overlap_x // 2) + 1
                    if b not in locked:
                        if ax <= bx:
                            positions[b]["x"] += shift
                            if a not in locked:
                                positions[a]["x"] -= shift
                        else:
                            positions[b]["x"] -= shift
                            if a not in locked:
                                positions[a]["x"] += shift
                    elif a not in locked:
                        if ax <= bx:
                            positions[a]["x"] -= overlap_x
                        else:
                            positions[a]["x"] += overlap_x
                else:
                    shift = (overlap_y // 2) + 1
                    if b not in locked:
                        if ay <= by:
                            positions[b]["y"] += shift
                            if a not in locked:
                                positions[a]["y"] -= shift
                        else:
                            positions[b]["y"] -= shift
                            if a not in locked:
                                positions[a]["y"] += shift
                    elif a not in locked:
                        if ay <= by:
                            positions[a]["y"] -= overlap_y
                        else:
                            positions[a]["y"] += overlap_y
                changed = True


def apply_affinity_alignment(
    components: list[dict[str, Any]],
    positions: dict[str, dict[str, int]],
    *,
    locked_ids: set[str] | None = None,
) -> None:
    locked = locked_ids or set()
    groups: dict[str, list[str]] = defaultdict(list)
    for component in components:
        affinity = component.get("affinity")
        if affinity:
            groups[str(affinity)].append(component["id"])
    for ids in groups.values():
        if len(ids) < 2:
            continue
        anchor_id = next((cid for cid in ids if cid in positions), None)
        if not anchor_id:
            continue
        anchor_x = positions[anchor_id]["x"]
        anchor_y = positions[anchor_id]["y"]
        for cid in ids:
            if cid == anchor_id or cid in locked:
                continue
            if cid not in positions:
                continue
            if positions[cid]["y"] == anchor_y:
                continue
            positions[cid]["x"] = anchor_x


def build_lane_node(layout: str, components: list[dict[str, Any]], sizes: dict[str, dict[str, int]]) -> dict[str, Any] | None:
    if layout != "pipeline":
        return None
    flow_nodes = [component for component in components if component.get("kind") in {"pipeline", "terminus"}]
    if not flow_nodes:
        return None
    min_x = min(component["position"]["x"] for component in flow_nodes)
    max_x = max(component["position"]["x"] for component in flow_nodes)
    last_node_w = sizes.get(flow_nodes[-1]["id"], {"w": NODE_MAX_WIDTH})["w"]
    width = max((max_x - min_x) + last_node_w + 120, 500)
    lane_y = min(component["position"]["y"] for component in flow_nodes) - NODE_PAD
    return {
        "id": "lane",
        "type": "lane",
        "position": {"x": min_x - 60, "y": lane_y},
        "data": {"width": width, "height": LANE_HEIGHT},
        "width": width,
        "height": LANE_HEIGHT,
    }


def build_render_node(component: dict[str, Any], sizes: dict[str, dict[str, int]]) -> dict[str, Any]:
    kind = component.get("kind", "pipeline")
    tags = [str(tag) for tag in component.get("tags", []) if str(tag).strip()]
    confidence = component.get("confidence", "medium")
    node_size = sizes.get(component["id"], {"w": NODE_MAX_WIDTH, "h": NODE_BASE_HEIGHT})
    return {
        "id": component["id"],
        "type": "engine",
        "position": component["position"],
        "width": node_size["w"],
        "height": node_size["h"],
        "data": {
            "label": component.get("label", component["id"]),
            "icon": component.get("icon") or DEFAULT_ICONS.get(kind, "•"),
            "color": component.get("color") or DEFAULT_COLORS.get(kind, "#3b82f6"),
            "sub": component.get("sub") or KIND_LABELS.get(kind, kind.title()),
            "desc": component.get("desc", ""),
            "file": component.get("file", ""),
            "tags": tags,
            "kindLabel": KIND_LABELS.get(kind, kind.replace("-", " ").title()),
            "confidence": confidence,
            "evidence": normalize_evidence(component.get("evidence")),
        },
    }


def normalize_positions(render_nodes: list[dict[str, Any]]) -> None:
    if not render_nodes:
        return
    min_x = min(node["position"]["x"] for node in render_nodes)
    min_y = min(node["position"]["y"] for node in render_nodes)
    shift_x = 120 - min_x if min_x < 120 else 0
    shift_y = 120 - min_y if min_y < 120 else 0
    for node in render_nodes:
        node["position"]["x"] += shift_x
        node["position"]["y"] += shift_y


def build_render_edges(
    model: dict[str, Any], render_nodes: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    node_lookup = {node["id"]: node for node in render_nodes}
    edges: list[dict[str, Any]] = []
    for index, connection in enumerate(model.get("connections", [])):
        source = connection["source"]
        target = connection["target"]
        if source not in node_lookup or target not in node_lookup:
            continue
        edge = {
            "id": connection.get("id") or f"e-{index}-{source}-{target}",
            "source": source,
            "target": target,
            "kind": connection.get("kind", "internal"),
            "kindLabel": CONNECTION_KIND_LABELS.get(
                connection.get("kind", "internal"),
                str(connection.get("kind", "internal")).replace("-", " ").title(),
            ),
            "sourceLabel": node_lookup[source]["data"]["label"],
            "targetLabel": node_lookup[target]["data"]["label"],
        }
        style = style_for_connection(connection, node_lookup[source]["data"]["color"])
        edge.update(style)
        if connection.get("label"):
            edge["label"] = connection["label"]
            edge["labelShowBg"] = True
            edge["labelBgPadding"] = [8, 4]
            edge["labelBgBorderRadius"] = 8
            edge["labelBgStyle"] = {"fill": "rgba(8, 15, 24, 0.92)", "stroke": "rgba(255, 255, 255, 0.08)"}
            edge["labelStyle"] = {"fill": "#e2e8f0", "fontSize": 11, "fontWeight": 700}
        edge["confidence"] = connection.get("confidence", "medium")
        edge["evidence"] = normalize_evidence(connection.get("evidence"))
        edges.append(edge)
    return edges


def style_for_connection(connection: dict[str, Any], source_color: str) -> dict[str, Any]:
    kind = connection.get("kind")
    if kind == "main-flow":
        return {"animated": True, "style": {"strokeWidth": 3}, "strokeWidth": 3}
    if kind == "input":
        return {"animated": True}
    if kind == "service":
        return {
            "type": "smoothstep",
            "style": {"stroke": source_color, "strokeDasharray": "5 5"},
            "stroke": source_color,
            "dasharray": "5 5",
        }
    if kind == "storage":
        return {"type": "smoothstep"}
    if kind == "config":
        return {
            "type": "smoothstep",
            "style": {"stroke": "#94a3b8", "strokeDasharray": "3 3"},
            "stroke": "#94a3b8",
            "dasharray": "3 3",
        }
    if kind == "trigger":
        return {
            "type": "smoothstep",
            "style": {"stroke": "#ffffff", "strokeDasharray": "8 4"},
            "stroke": "#ffffff",
            "dasharray": "8 4",
        }
    if kind == "event":
        return {
            "type": "smoothstep",
            "style": {"stroke": source_color, "strokeDasharray": "7 5"},
            "stroke": source_color,
            "dasharray": "7 5",
        }
    if kind == "frontend":
        return {"animated": True}
    return {"type": "smoothstep"}


def average(values: list[int]) -> int | None:
    if not values:
        return None
    return sum(values) // len(values)


def summarize_model(model: dict[str, Any], render_nodes: list[dict[str, Any]]) -> dict[str, str]:
    project = model.get("project", {})
    classification = model.get("classification", {})
    primary = classification.get("primary", "unknown")
    render_as = render_as_for(model)
    secondary = classification.get("secondary") or []
    summary = project.get("summary") or "Evidence-based architecture map generated from the repository."
    reason = classification.get("reason") or "Classification reason not provided."
    subtitle = f"Type: {primary}"
    if secondary:
        subtitle += f" · Secondary: {', '.join(secondary)}"
    subtitle += f" · Rendered as: {render_as}"
    node_count = len(render_nodes) - (1 if render_nodes and render_nodes[0]["id"] == "lane" else 0)
    footer = f"{render_as} · {node_count} nodes"

    # Build bullet list from summary (split on " • " or use as single bullet)
    bullets = _split_summary_bullets(summary)
    # Append classification reason as a bullet
    if reason and reason != "Classification reason not provided.":
        bullets.append(reason)

    return {
        "project_name": project.get("name", "Project"),
        "subtitle": subtitle,
        "overview_bullets": bullets,
        "footer": footer,
    }


def _split_summary_bullets(summary: str) -> list[str]:
    """Split a summary string into bullet items.

    Supports three formats:
    - Bullet-separated: "• item1 • item2 • item3"
    - Newline-separated: "item1\\nitem2\\nitem3"
    - Single paragraph (returned as one bullet)
    """
    # Try bullet separator first
    if " • " in summary or summary.startswith("• "):
        parts = [p.strip().lstrip("• ").strip() for p in summary.split("•") if p.strip()]
        if len(parts) > 1:
            return parts
    # Try newline separator
    lines = [line.strip().lstrip("- ").lstrip("* ").strip() for line in summary.splitlines() if line.strip()]
    if len(lines) > 1:
        return lines
    # Single paragraph — return as-is
    return [summary] if summary else []


def build_stats(model: dict[str, Any], render_nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    stats = model.get("stats")
    if isinstance(stats, list) and stats:
        normalized = []
        for item in stats[:4]:
            if not isinstance(item, dict):
                continue
            normalized.append(
                {
                    "label": str(item.get("label", "Stat")),
                    "value": str(item.get("value", "0")),
                    "color": item.get("color", "accent"),
                }
            )
        if not any(stat["label"].lower() in {"nodes", "components"} for stat in normalized):
            normalized = normalized[:3] + [
                {
                    "label": "Components",
                    "value": str(
                        sum(1 for node in render_nodes if node.get("id") != "lane")
                    ),
                    "color": "orange",
                }
            ]
        return normalized[:4]

    components = model.get("components", [])
    by_kind = defaultdict(int)
    for component in components:
        by_kind[component.get("kind", "pipeline")] += 1
    return [
        {"label": "Main Flow", "value": str(by_kind["pipeline"] + by_kind["microservice"]), "color": "purple"},
        {"label": "3rd-Party APIs", "value": str(by_kind["service"]), "color": "accent"},
        {"label": "Data Stores", "value": str(by_kind["storage"] + by_kind["config"]), "color": "cyan"},
        {
            "label": "Components",
            "value": str(sum(1 for node in render_nodes if node.get("id") != "lane")),
            "color": "orange",
        },
    ]


def format_project_title(name: str) -> str:
    words = name.split()
    if len(words) < 2:
        return html.escape(name)
    first = html.escape(words[0])
    second = html.escape(words[1])
    rest = " ".join(html.escape(word) for word in words[2:])
    if rest:
        return f"{first} <span style=\"color:var(--accent)\">{second}</span> {rest}"
    return f"{first} <span style=\"color:var(--accent)\">{second}</span>"


def render_stats_cards(stats: list[dict[str, Any]]) -> str:
    cards: list[str] = []
    for item in stats:
        color = STAT_COLOR_MAP.get(str(item.get("color")), str(item.get("color")))
        label = html.escape(str(item.get("label", "Stat")))
        value = html.escape(str(item.get("value", "0")))
        cards.append(
            "<div class=\"mini-card\">"
            f"<div class=\"val\" style=\"color:{color}\">{value}</div>"
            f"<div class=\"lbl\">{label}</div>"
            "</div>"
        )
    return "\n".join(cards)


def render_overview_bullets(bullets: list[str]) -> str:
    """Render a list of bullet strings as <li> elements for the template."""
    return "\n".join(f"                    <li>{html.escape(b)}</li>" for b in bullets)


def render_template(
    template_path: Path,
    *,
    model: dict[str, Any],
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> str:
    template = template_path.read_text(encoding="utf-8")
    summary = summarize_model(model, nodes)
    stats_cards = render_stats_cards(build_stats(model, nodes))
    replacements = {
        "{{PROJECT_NAME}}": html.escape(summary["project_name"]),
        "{{PROJECT_TITLE_HTML}}": format_project_title(summary["project_name"]),
        "{{PROJECT_SUBTITLE}}": html.escape(summary["subtitle"]),
        "{{OVERVIEW_BULLETS}}": render_overview_bullets(summary["overview_bullets"]),
        "{{STATS_CARDS}}": stats_cards,
        "{{DETAILS_DEFAULT_TITLE}}": "Select a node or edge",
        "{{DETAILS_DEFAULT_BODY}}": html.escape("Click a node or edge to inspect its role and evidence."),
        "{{FOOTER_NOTE}}": html.escape(summary["footer"]),
        "{{NODES_JSON}}": json.dumps(nodes, ensure_ascii=False, indent=4),
        "{{EDGES_JSON}}": json.dumps(edges, ensure_ascii=False, indent=4),
    }
    for needle, replacement in replacements.items():
        template = template.replace(needle, replacement)
    return template


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, type=Path, help="Path to architecture-map.json")
    parser.add_argument("--output", required=True, type=Path, help="Output HTML file")
    args = parser.parse_args()

    try:
        model = load_model(args.model)
        warnings = validate_model(model)
        nodes = assign_positions(model)
        edges = build_render_edges(model, nodes)

        rendered = render_template(
            INTERACTIVE_TEMPLATE,
            model=model,
            nodes=nodes,
            edges=edges,
        )
        args.output.write_text(rendered, encoding="utf-8")
    except (ValidationError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
