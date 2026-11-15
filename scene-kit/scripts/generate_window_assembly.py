#!/usr/bin/env python3
"""Generate a parametric divided-light window inside Blender.

The generated component contains three material meshes:
- stone surround, head and projecting sill;
- timber outer frame and glazing bars;
- inset glass panes.

Pure parameter validation runs outside Blender. Geometry creation requires bpy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _number(value: Any, name: str, minimum: float | None = None) -> float:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(float(value))
    ):
        raise ValueError(f"{name} must be a finite number")
    result = float(value)
    if minimum is not None and result < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return result


def _integer(value: Any, name: str, minimum: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{name} must be an integer")
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return value


def resolve_parameters(parameters: dict[str, Any]) -> dict[str, Any]:
    opening_width = _number(
        parameters.get("opening_width_m"),
        "opening_width_m",
        0.2,
    )
    opening_height = _number(
        parameters.get("opening_height_m"),
        "opening_height_m",
        0.2,
    )
    clearance = _number(
        parameters.get("installation_clearance_m", 0.012),
        "installation_clearance_m",
        0.0,
    )
    stone_border = _number(
        parameters.get("stone_border_m", 0.06),
        "stone_border_m",
        0.01,
    )
    stone_depth = _number(
        parameters.get("stone_depth_m", 0.24),
        "stone_depth_m",
        0.02,
    )
    sill_projection = _number(
        parameters.get("sill_projection_m", 0.08),
        "sill_projection_m",
        0.0,
    )
    sill_thickness = _number(
        parameters.get("sill_thickness_m", 0.06),
        "sill_thickness_m",
        0.01,
    )
    frame_thickness = _number(
        parameters.get("frame_thickness_m", 0.055),
        "frame_thickness_m",
        0.01,
    )
    frame_depth = _number(
        parameters.get("frame_depth_m", 0.165),
        "frame_depth_m",
        0.01,
    )
    bar_width = _number(
        parameters.get("bar_width_m", 0.024),
        "bar_width_m",
        0.005,
    )
    glass_depth = _number(
        parameters.get("glass_depth_m", 0.025),
        "glass_depth_m",
        0.002,
    )
    rows = _integer(parameters.get("rows", 4), "rows", 1)
    major_sections = _integer(
        parameters.get("major_vertical_sections", 3),
        "major_vertical_sections",
        1,
    )
    central_split = parameters.get("central_split") or {}
    if not isinstance(central_split, dict):
        raise ValueError("central_split must be an object")
    split_enabled = bool(central_split.get("enabled", False))
    split_columns = _integer(
        central_split.get("sub_columns", 2),
        "central_split.sub_columns",
        1,
    )
    columns = (
        major_sections - 1 + split_columns
        if split_enabled
        else major_sections
    )
    ratios = parameters.get("column_ratios")
    if ratios is None:
        ratios = (
            [1.3] + [0.8] * (columns - 2) + [1.3]
            if columns >= 3
            else [1.0] * columns
        )
    if not isinstance(ratios, list) or len(ratios) != columns:
        raise ValueError("column_ratios length must equal resolved columns")
    ratios = [
        _number(value, f"column_ratios[{index}]", 0.01)
        for index, value in enumerate(ratios)
    ]

    frame_outer_width = opening_width - 2.0 * clearance
    frame_outer_height = opening_height - 2.0 * clearance
    frame_inner_width = frame_outer_width - 2.0 * frame_thickness
    frame_inner_height = frame_outer_height - 2.0 * frame_thickness
    if frame_inner_width <= 0.02 or frame_inner_height <= 0.02:
        raise ValueError("frame thickness leaves no usable opening")
    ratio_sum = sum(ratios)
    total_muntin_width = bar_width * (columns - 1)
    usable_width = frame_inner_width - total_muntin_width
    if usable_width <= 0.02:
        raise ValueError("vertical glazing bars leave no pane width")
    column_widths = [
        usable_width * value / ratio_sum for value in ratios
    ]
    total_horizontal_bar = bar_width * (rows - 1)
    usable_height = frame_inner_height - total_horizontal_bar
    if usable_height <= 0.02:
        raise ValueError("horizontal glazing bars leave no pane height")
    row_height = usable_height / rows

    outer_width = opening_width + 2.0 * stone_border
    outer_height = opening_height + 2.0 * stone_border
    overall_depth = stone_depth + sill_projection
    return {
        "opening_width_m": opening_width,
        "opening_height_m": opening_height,
        "installation_clearance_m": clearance,
        "stone_border_m": stone_border,
        "stone_depth_m": stone_depth,
        "sill_projection_m": sill_projection,
        "sill_thickness_m": sill_thickness,
        "frame_thickness_m": frame_thickness,
        "frame_depth_m": frame_depth,
        "bar_width_m": bar_width,
        "glass_depth_m": glass_depth,
        "rows": rows,
        "major_vertical_sections": major_sections,
        "central_split": {
            "enabled": split_enabled,
            "sub_columns": split_columns if split_enabled else 0,
        },
        "columns": columns,
        "pane_count": columns * rows,
        "column_ratios": ratios,
        "column_widths_m": column_widths,
        "row_height_m": row_height,
        "frame_outer_width_m": frame_outer_width,
        "frame_outer_height_m": frame_outer_height,
        "frame_inner_width_m": frame_inner_width,
        "frame_inner_height_m": frame_inner_height,
        "overall_width_m": outer_width,
        "overall_height_m": outer_height,
        "overall_depth_m": overall_depth,
    }


def validate_parameters(parameters: dict[str, Any]) -> dict[str, Any]:
    resolved = resolve_parameters(parameters)
    if resolved["pane_count"] <= 0:
        raise ValueError("pane count must be positive")
    if (
        resolved["frame_outer_width_m"]
        >= resolved["opening_width_m"]
        or resolved["frame_outer_height_m"]
        >= resolved["opening_height_m"]
    ):
        raise ValueError("window frame must fit inside the rough opening")
    return {"status": "pass", **resolved}


def _move_to_collection(obj: Any, collection: Any) -> None:
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    collection.objects.link(obj)


def _join_objects(objects: list[Any], name: str) -> Any:
    import bpy

    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    joined = objects[0]
    joined.name = name
    bpy.context.scene.cursor.location = (0.0, 0.0, 0.0)
    bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
    return joined


def build_window(
    parameters: dict[str, Any],
    materials: dict[str, str],
    prefix: str = "SK_tall_window_parametric_v1",
    collection_name: str = "SK_COL_AI",
    replace_existing: bool = True,
) -> dict[str, Any]:
    import bpy

    checked = validate_parameters(parameters)
    material_values = {}
    for role in ("stone", "wood", "glass"):
        name = materials.get(role)
        if not isinstance(name, str) or not name:
            raise ValueError(f"materials.{role} must be provided")
        material = bpy.data.materials.get(name)
        if material is None:
            raise ValueError(f"Material not found: {name}")
        material_values[role] = material

    collection = bpy.data.collections.get(collection_name)
    if collection is None:
        collection = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(collection)
    if replace_existing:
        for obj in list(bpy.data.objects):
            if obj.name.startswith(prefix):
                bpy.data.objects.remove(obj, do_unlink=True)

    def box(
        center: tuple[float, float, float],
        size: tuple[float, float, float],
        material: Any,
    ) -> Any:
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
        obj.dimensions = size
        bpy.ops.object.transform_apply(
            location=False,
            rotation=False,
            scale=True,
        )
        _move_to_collection(obj, collection)
        obj.data.materials.append(material)
        return obj

    opening_w = checked["opening_width_m"]
    opening_h = checked["opening_height_m"]
    border = checked["stone_border_m"]
    stone_depth = checked["stone_depth_m"]
    sill_projection = checked["sill_projection_m"]
    sill_thickness = checked["sill_thickness_m"]
    stone_y = 0.0
    outer_h = checked["overall_height_m"]
    stone_objects = []
    stone_objects.append(
        box(
            (-(opening_w + border) / 2.0, stone_y, outer_h / 2.0),
            (border, stone_depth, outer_h),
            material_values["stone"],
        )
    )
    stone_objects.append(
        box(
            ((opening_w + border) / 2.0, stone_y, outer_h / 2.0),
            (border, stone_depth, outer_h),
            material_values["stone"],
        )
    )
    stone_objects.append(
        box(
            (0.0, stone_y, outer_h - border / 2.0),
            (opening_w, stone_depth, border),
            material_values["stone"],
        )
    )
    stone_objects.append(
        box(
            (
                0.0,
                -sill_projection / 2.0,
                sill_thickness / 2.0,
            ),
            (
                opening_w + 2.0 * border,
                stone_depth + sill_projection,
                sill_thickness,
            ),
            material_values["stone"],
        )
    )
    stone = _join_objects(stone_objects, f"{prefix}_stone")

    clearance = checked["installation_clearance_m"]
    frame_w = checked["frame_outer_width_m"]
    frame_h = checked["frame_outer_height_m"]
    frame_thickness = checked["frame_thickness_m"]
    frame_depth = checked["frame_depth_m"]
    bar_width = checked["bar_width_m"]
    frame_front = -stone_depth / 2.0 + 0.02
    frame_center_y = frame_front + frame_depth / 2.0
    frame_bottom = border + clearance
    frame_center_z = frame_bottom + frame_h / 2.0
    wood_objects = []
    wood_objects.extend(
        [
            box(
                (
                    -(frame_w - frame_thickness) / 2.0,
                    frame_center_y,
                    frame_center_z,
                ),
                (frame_thickness, frame_depth, frame_h),
                material_values["wood"],
            ),
            box(
                (
                    (frame_w - frame_thickness) / 2.0,
                    frame_center_y,
                    frame_center_z,
                ),
                (frame_thickness, frame_depth, frame_h),
                material_values["wood"],
            ),
            box(
                (
                    0.0,
                    frame_center_y,
                    frame_bottom + frame_h - frame_thickness / 2.0,
                ),
                (frame_w - 2.0 * frame_thickness, frame_depth, frame_thickness),
                material_values["wood"],
            ),
            box(
                (
                    0.0,
                    frame_center_y,
                    frame_bottom + frame_thickness / 2.0,
                ),
                (frame_w - 2.0 * frame_thickness, frame_depth, frame_thickness),
                material_values["wood"],
            ),
        ]
    )

    inner_w = checked["frame_inner_width_m"]
    inner_h = checked["frame_inner_height_m"]
    inner_left = -inner_w / 2.0
    inner_bottom = frame_bottom + frame_thickness
    column_edges = [inner_left]
    for width in checked["column_widths_m"]:
        column_edges.append(column_edges[-1] + width + bar_width)
    for boundary in column_edges[1:-1]:
        bar_x = boundary - bar_width / 2.0
        wood_objects.append(
            box(
                (bar_x, frame_center_y, frame_center_z),
                (bar_width, frame_depth, inner_h),
                material_values["wood"],
            )
        )
    row_height = checked["row_height_m"]
    for index in range(1, checked["rows"]):
        bar_z = (
            inner_bottom
            + index * row_height
            + (index - 0.5) * bar_width
        )
        wood_objects.append(
            box(
                (0.0, frame_center_y, bar_z),
                (inner_w, frame_depth, bar_width),
                material_values["wood"],
            )
        )
    wood = _join_objects(wood_objects, f"{prefix}_wood")

    glass_objects = []
    glass_depth = checked["glass_depth_m"]
    glass_y = frame_front + frame_depth * 0.72
    pane_x = inner_left
    for column_index, pane_width in enumerate(
        checked["column_widths_m"]
    ):
        for row_index in range(checked["rows"]):
            pane_center_x = pane_x + pane_width / 2.0
            pane_center_z = (
                inner_bottom
                + row_index * (row_height + bar_width)
                + row_height / 2.0
            )
            glass_objects.append(
                box(
                    (pane_center_x, glass_y, pane_center_z),
                    (pane_width, glass_depth, row_height),
                    material_values["glass"],
                )
            )
        pane_x += pane_width + bar_width
    glass = _join_objects(glass_objects, f"{prefix}_glass")

    for obj in (stone, wood, glass):
        for polygon in obj.data.polygons:
            polygon.material_index = 0
        while len(obj.data.materials) > 1:
            obj.data.materials.pop(index=len(obj.data.materials) - 1)
        bpy.context.view_layer.objects.active = obj
        bevel = obj.modifiers.new("EDGE_SOFTENING", "BEVEL")
        bevel.width = 0.004
        bevel.segments = 2
        bevel.limit_method = "ANGLE"
        bpy.ops.object.modifier_apply(modifier=bevel.name)
        obj["part_id"] = "tall_window_assembly"
        obj["parameters_hash"] = hashlib.sha256(
            json.dumps(
                checked,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

    root = bpy.data.objects.new(f"{prefix}_ROOT", None)
    collection.objects.link(root)
    for obj in (stone, wood, glass):
        obj.parent = root
    return {
        "status": "generated",
        "root": root.name,
        "objects": [stone.name, wood.name, glass.name],
        "dimensions_m": [
            checked["overall_width_m"],
            checked["overall_depth_m"],
            checked["overall_height_m"],
        ],
        "columns": checked["columns"],
        "rows": checked["rows"],
        "pane_count": checked["pane_count"],
        "parameters_hash": hashlib.sha256(
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
    parser.add_argument("--stone-material", required=True)
    parser.add_argument("--wood-material", required=True)
    parser.add_argument("--glass-material", required=True)
    parser.add_argument("--prefix", default="SK_tall_window_parametric_v1")
    parser.add_argument("--collection", default="SK_COL_AI")
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
    parameters = _read_json(parameter_path)
    checked = validate_parameters(parameters)
    if args.validate_only:
        print(json.dumps(checked, ensure_ascii=False, indent=2))
        return 0
    try:
        result = build_window(
            parameters,
            {
                "stone": args.stone_material,
                "wood": args.wood_material,
                "glass": args.glass_material,
            },
            prefix=args.prefix,
            collection_name=args.collection,
        )
    except ImportError as exc:
        print(f"Window generation must run inside Blender: {exc}", file=sys.stderr)
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
