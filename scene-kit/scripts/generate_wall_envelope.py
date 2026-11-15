#!/usr/bin/env python3
"""Generate a parametric wall envelope from a facade/opening layout.

Pure layout validation and deterministic opening selection can run outside
Blender. Geometry creation runs inside Blender:

    blender --background model.blend --python generate_wall_envelope.py -- \
      --project <project> --parameters internal/wall_variant.json \
      --output-blend out/wall_variant.blend
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
from pathlib import Path
from typing import Any


FACADES = {"front", "back", "left", "right"}
DEFAULT_MIN_EDGE_M = 0.15
DEFAULT_MIN_GAP_M = 0.10


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _number(value: Any, name: str) -> float:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(float(value))
    ):
        raise ValueError(f"{name} must be a finite number")
    return float(value)


def resolve_layout(layout: dict[str, Any]) -> dict[str, Any]:
    """Resolve explicit openings and deterministic slot-pool choices."""
    basis = layout.get("basis")
    if not isinstance(basis, dict):
        raise ValueError("layout.basis must be an object")
    width = _number(basis.get("footprint_width_m"), "basis.footprint_width_m")
    depth = _number(basis.get("footprint_depth_m"), "basis.footprint_depth_m")
    height = _number(basis.get("wall_height_m"), "basis.wall_height_m")
    thickness = _number(basis.get("wall_thickness_m"), "basis.wall_thickness_m")
    if min(width, depth, height, thickness) <= 0:
        raise ValueError("wall dimensions and thickness must be positive")

    openings: list[dict[str, Any]] = []
    explicit = layout.get("openings") or []
    if not isinstance(explicit, list):
        raise ValueError("layout.openings must be an array")
    for item in explicit:
        if not isinstance(item, dict):
            raise ValueError("Each opening must be an object")
        opening = dict(item)
        opening.setdefault("enabled", True)
        opening["source"] = "explicit"
        openings.append(opening)

    slot_pool = layout.get("slot_pool") or []
    if not isinstance(slot_pool, list):
        raise ValueError("layout.slot_pool must be an array")
    random_config = layout.get("random") or {}
    seed = int(random_config.get("seed", 0))
    rng = random.Random(seed)
    keep_probability = float(
        random_config.get("keep_probability", 1.0)
    )
    if not 0.0 <= keep_probability <= 1.0:
        raise ValueError("random.keep_probability must be between 0 and 1")
    for item in slot_pool:
        if not isinstance(item, dict):
            raise ValueError("Each slot-pool item must be an object")
        slot = dict(item)
        slot["source"] = "slot_pool"
        if slot.get("kind") == "door" or slot.get("locked") is True:
            slot["enabled"] = bool(slot.get("enabled", True))
        elif "enabled" in slot:
            slot["enabled"] = bool(slot["enabled"])
        else:
            weight = float(slot.get("weight", 1.0))
            slot["enabled"] = rng.random() < min(
                1.0,
                max(0.0, keep_probability * weight),
            )
        openings.append(slot)

    return {
        "basis": {
            "footprint_width_m": width,
            "footprint_depth_m": depth,
            "wall_height_m": height,
            "wall_thickness_m": thickness,
        },
        "openings": openings,
        "seed": seed,
        "keep_probability": keep_probability,
    }


def validate_layout(layout: dict[str, Any]) -> dict[str, Any]:
    """Validate facade bounds, door contact, and opening overlap."""
    resolved = resolve_layout(layout)
    basis = resolved["basis"]
    width = basis["footprint_width_m"]
    depth = basis["footprint_depth_m"]
    height = basis["wall_height_m"]
    min_edge = float(
        (layout.get("constraints") or {}).get(
            "minimum_edge_m",
            DEFAULT_MIN_EDGE_M,
        )
    )
    min_gap = float(
        (layout.get("constraints") or {}).get(
            "minimum_opening_gap_m",
            DEFAULT_MIN_GAP_M,
        )
    )
    if min_edge < 0 or min_gap < 0:
        raise ValueError("minimum edge and gap must be non-negative")

    by_facade: dict[str, list[dict[str, Any]]] = {
        facade: [] for facade in FACADES
    }
    for index, opening in enumerate(resolved["openings"]):
        opening_id = str(opening.get("id", f"opening_{index}"))
        facade = opening.get("facade")
        if facade not in FACADES:
            raise ValueError(f"{opening_id}.facade is invalid")
        if opening.get("enabled") is False:
            continue
        along_name = "offset_m"
        offset = _number(opening.get(along_name), f"{opening_id}.offset_m")
        bottom = _number(opening.get("bottom_m"), f"{opening_id}.bottom_m")
        opening_width = _number(
            opening.get("width_m"),
            f"{opening_id}.width_m",
        )
        opening_height = _number(
            opening.get("height_m"),
            f"{opening_id}.height_m",
        )
        if min(opening_width, opening_height) <= 0:
            raise ValueError(f"{opening_id} dimensions must be positive")
        span = width if facade in {"front", "back"} else depth
        half = opening_width / 2.0
        if offset - half < -span / 2.0 + min_edge:
            raise ValueError(f"{opening_id} violates facade edge margin")
        if offset + half > span / 2.0 - min_edge:
            raise ValueError(f"{opening_id} violates facade edge margin")
        if bottom < -1.0e-9:
            raise ValueError(f"{opening_id}.bottom_m must be non-negative")
        if bottom + opening_height > height + 1.0e-9:
            raise ValueError(f"{opening_id} exceeds wall height")
        if opening.get("kind") == "door" and bottom > 1.0e-9:
            raise ValueError(f"{opening_id} door must start at ground")
        record = {
            "id": opening_id,
            "facade": facade,
            "kind": opening.get("kind", "window"),
            "offset_m": offset,
            "bottom_m": bottom,
            "width_m": opening_width,
            "height_m": opening_height,
            "enabled": True,
        }
        by_facade[facade].append(record)

    for facade, items in by_facade.items():
        ordered = sorted(items, key=lambda item: item["offset_m"])
        for first, second in zip(ordered, ordered[1:]):
            first_right = first["offset_m"] + first["width_m"] / 2.0
            second_left = second["offset_m"] - second["width_m"] / 2.0
            horizontal_gap = second_left - first_right
            vertical_gap = max(
                first["bottom_m"]
                - (second["bottom_m"] + second["height_m"]),
                second["bottom_m"]
                - (first["bottom_m"] + first["height_m"]),
            )
            if (
                horizontal_gap < min_gap - 1.0e-9
                and vertical_gap < min_gap - 1.0e-9
            ):
                raise ValueError(
                    f"{facade} openings {first['id']} and {second['id']} "
                    "are too close or overlap"
                )

    return {
        "status": "pass",
        "basis": basis,
        "seed": resolved["seed"],
        "keep_probability": resolved["keep_probability"],
        "openings": [item for items in by_facade.values() for item in items],
        "counts": {
            facade: len(items) for facade, items in by_facade.items()
        },
        "minimum_edge_m": min_edge,
        "minimum_opening_gap_m": min_gap,
    }


def layout_hash(layout_path: Path) -> str:
    return hashlib.sha256(layout_path.read_bytes()).hexdigest()


def _move_to_collection(obj: Any, collection: Any) -> None:
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    collection.objects.link(obj)


def build_wall(
    layout: dict[str, Any],
    material_name: str,
    prefix: str = "SK_wall_envelope_v1",
    collection_name: str = "SK_COL_Structure",
    replace_existing: bool = True,
) -> dict[str, Any]:
    """Build the wall inside the currently open Blender scene."""
    import bpy

    checked = validate_layout(layout)
    material = bpy.data.materials.get(material_name)
    if material is None:
        raise ValueError(f"Material not found: {material_name}")
    collection = bpy.data.collections.get(collection_name)
    if collection is None:
        collection = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(collection)

    if replace_existing:
        for obj in list(bpy.data.objects):
            if obj.name.startswith(prefix):
                bpy.data.objects.remove(obj, do_unlink=True)

    basis = checked["basis"]
    width = basis["footprint_width_m"]
    depth = basis["footprint_depth_m"]
    height = basis["wall_height_m"]
    thickness = basis["wall_thickness_m"]

    def box(name: str, center: tuple[float, float, float], size: tuple[float, float, float], material_value: Any) -> Any:
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=center)
        obj = bpy.context.view_layer.objects.active
        if obj is None or obj.type != "MESH":
            selected = [
                item
                for item in bpy.context.selected_objects
                if item.type == "MESH"
            ]
            if not selected:
                raise RuntimeError("Primitive cube was not created")
            obj = selected[-1]
        obj.name = name
        obj.dimensions = size
        bpy.ops.object.transform_apply(
            location=False,
            rotation=False,
            scale=True,
        )
        _move_to_collection(obj, collection)
        obj.data.materials.append(material_value)
        return obj

    y_outer = depth / 2.0
    x_outer = width / 2.0
    front_center = -y_outer + thickness / 2.0
    back_center = y_outer - thickness / 2.0
    side_depth = max(0.01, depth - 2.0 * thickness)
    walls = {
        "front": box(
            f"{prefix}_front",
            (0.0, front_center, height / 2.0),
            (width, thickness, height),
            material,
        ),
        "back": box(
            f"{prefix}_back",
            (0.0, back_center, height / 2.0),
            (width, thickness, height),
            material,
        ),
        "left": box(
            f"{prefix}_left",
            (-x_outer + thickness / 2.0, 0.0, height / 2.0),
            (thickness, side_depth, height),
            material,
        ),
        "right": box(
            f"{prefix}_right",
            (x_outer - thickness / 2.0, 0.0, height / 2.0),
            (thickness, side_depth, height),
            material,
        ),
    }

    cutters = []
    for opening in checked["openings"]:
        facade = opening["facade"]
        bottom = opening["bottom_m"]
        opening_height = opening["height_m"]
        z = bottom + opening_height / 2.0
        cutter_depth = thickness * 4.0
        if facade == "front":
            center = (
                opening["offset_m"],
                front_center,
                z,
            )
            size = (
                opening["width_m"],
                cutter_depth,
                opening_height,
            )
        elif facade == "back":
            center = (
                opening["offset_m"],
                back_center,
                z,
            )
            size = (
                opening["width_m"],
                cutter_depth,
                opening_height,
            )
        elif facade == "left":
            center = (
                -x_outer + thickness / 2.0,
                opening["offset_m"],
                z,
            )
            size = (
                cutter_depth,
                opening["width_m"],
                opening_height,
            )
        else:
            center = (
                x_outer - thickness / 2.0,
                opening["offset_m"],
                z,
            )
            size = (
                cutter_depth,
                opening["width_m"],
                opening_height,
            )
        cutters.append(
            (
                facade,
                box(
                    f"CUT_{prefix}_{opening['id']}",
                    center,
                    size,
                    material,
                ),
                opening["id"],
            )
        )

    for facade, cutter, _ in cutters:
        wall = walls[facade]
        bpy.context.view_layer.objects.active = wall
        modifier = wall.modifiers.new(
            f"OPENING_{len(wall.modifiers)}",
            "BOOLEAN",
        )
        modifier.operation = "DIFFERENCE"
        modifier.solver = "EXACT"
        modifier.object = cutter
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    for _, cutter, _ in cutters:
        bpy.data.objects.remove(cutter, do_unlink=True)

    for wall in walls.values():
        for polygon in wall.data.polygons:
            polygon.material_index = 0
        while len(wall.data.materials) > 1:
            wall.data.materials.pop(index=len(wall.data.materials) - 1)
        bpy.context.view_layer.objects.active = wall
        bevel = wall.modifiers.new("EDGE_SOFTENING", "BEVEL")
        bevel.width = 0.008
        bevel.segments = 2
        bevel.limit_method = "ANGLE"
        bpy.ops.object.modifier_apply(modifier=bevel.name)
        wall["part_id"] = "wall_envelope"
        wall["parameters_hash"] = hashlib.sha256(
            json.dumps(
                checked,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

    root = bpy.data.objects.new(f"{prefix}_ROOT", None)
    collection.objects.link(root)
    for wall in walls.values():
        wall.parent = root
    return {
        "status": "generated",
        "root": root.name,
        "objects": [wall.name for wall in walls.values()],
        "facade_counts": checked["counts"],
        "opening_count": len(checked["openings"]),
        "parameters_resolved_hash": hashlib.sha256(
            json.dumps(
                checked,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest(),
    }


def _argument_argv(argv: list[str] | None) -> list[str]:
    if argv is not None:
        return argv
    if "--" in sys.argv:
        return sys.argv[sys.argv.index("--") + 1 :]
    return sys.argv[1:]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path)
    parser.add_argument("--parameters", type=Path, required=True)
    parser.add_argument("--material-name", type=str, required=True)
    parser.add_argument("--prefix", default="SK_wall_envelope_v1")
    parser.add_argument("--collection", default="SK_COL_Structure")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--output-blend", type=Path)
    args = parser.parse_args(_argument_argv(argv))
    project = (
        args.project.expanduser().resolve()
        if args.project
        else Path.cwd()
    )
    parameter_path = args.parameters
    if not parameter_path.is_absolute():
        parameter_path = project / parameter_path
    layout = _read_json(parameter_path)
    checked = validate_layout(layout)
    if args.validate_only:
        print(json.dumps(checked, ensure_ascii=False, indent=2))
        return 0
    try:
        result = build_wall(
            layout,
            args.material_name,
            prefix=args.prefix,
            collection_name=args.collection,
        )
    except ImportError as exc:
        print(f"Wall generation must run inside Blender: {exc}", file=sys.stderr)
        return 2
    if args.output_blend:
        import bpy

        output = args.output_blend
        if not output.is_absolute():
            output = project / output
        output.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(output))
        result["blend_path"] = str(output)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
