#!/usr/bin/env python3
"""Generate mirrored porch railing runs around a central stair opening."""

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


def _number(
    value: Any,
    name: str,
    minimum: float | None = None,
) -> float:
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


def validate_parameters(parameters: dict[str, Any]) -> dict[str, Any]:
    total_width = _number(
        parameters.get("total_width_m"),
        "total_width_m",
        1.2,
    )
    opening = _number(
        parameters.get("center_opening_m"),
        "center_opening_m",
        0.6,
    )
    height = _number(parameters.get("height_m"), "height_m", 0.6)
    platform_top = _number(
        parameters.get("platform_top_z_m"),
        "platform_top_z_m",
        0.0,
    )
    front_y = _number(
        parameters.get("front_y_m"),
        "front_y_m",
    )
    outer_inset = _number(
        parameters.get("outer_inset_m"),
        "outer_inset_m",
        0.0,
    )
    post_width = _number(
        parameters.get("post_width_m"),
        "post_width_m",
        0.04,
    )
    post_cap_height = _number(
        parameters.get("post_cap_height_m"),
        "post_cap_height_m",
        0.01,
    )
    top_rail_height = _number(
        parameters.get("top_rail_height_m"),
        "top_rail_height_m",
        0.04,
    )
    top_rail_depth = _number(
        parameters.get("top_rail_depth_m"),
        "top_rail_depth_m",
        0.04,
    )
    bottom_rail_height = _number(
        parameters.get("bottom_rail_height_m"),
        "bottom_rail_height_m",
        0.03,
    )
    bottom_rail_depth = _number(
        parameters.get("bottom_rail_depth_m"),
        "bottom_rail_depth_m",
        0.03,
    )
    bottom_rail_z = _number(
        parameters.get("bottom_rail_z_m"),
        "bottom_rail_z_m",
        0.05,
    )
    baluster_width = _number(
        parameters.get("baluster_width_m"),
        "baluster_width_m",
        0.015,
    )
    spacing = _number(
        parameters.get("baluster_spacing_m"),
        "baluster_spacing_m",
        0.05,
    )
    if opening + outer_inset * 2 >= total_width:
        raise ValueError("center opening leaves no side railing bay")
    bay_length = (total_width - opening) / 2.0 - outer_inset
    if bay_length <= post_width * 2 + baluster_width:
        raise ValueError("side railing bay is too short")
    if bottom_rail_z + bottom_rail_height / 2.0 >= height - top_rail_height:
        raise ValueError("bottom rail is too high for the selected railing")
    if spacing <= baluster_width * 1.5:
        raise ValueError("baluster spacing is too tight")
    if platform_top + bottom_rail_z - bottom_rail_height / 2.0 <= 0:
        raise ValueError("bottom rail is below the mounting surface")
    material = parameters.get("material")
    if not isinstance(material, dict):
        raise ValueError("material must be an object")
    scale = material.get("wood_mapping_scale")
    physical = material.get("physical_texture_dimensions_m")
    for name, values in (
        ("wood_mapping_scale", scale),
        ("physical_texture_dimensions_m", physical),
    ):
        if (
            not isinstance(values, list)
            or len(values) not in {2, 3}
            or not all(
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and value > 0
                for value in values
            )
        ):
            raise ValueError(f"material.{name} contains invalid values")
    return {
        "status": "pass",
        "total_width_m": total_width,
        "center_opening_m": opening,
        "height_m": height,
        "platform_top_z_m": platform_top,
        "front_y_m": front_y,
        "outer_inset_m": outer_inset,
        "post_width_m": post_width,
        "post_cap_height_m": post_cap_height,
        "top_rail_height_m": top_rail_height,
        "top_rail_depth_m": top_rail_depth,
        "bottom_rail_height_m": bottom_rail_height,
        "bottom_rail_depth_m": bottom_rail_depth,
        "bottom_rail_z_m": bottom_rail_z,
        "baluster_width_m": baluster_width,
        "baluster_spacing_m": spacing,
        "bay_length_m": bay_length,
        "overall_dimensions_m": [
            total_width
            - outer_inset * 2.0
            + post_width * 1.35,
            max(
                top_rail_depth,
                bottom_rail_depth,
                post_width * 1.6,
            ),
            height + post_cap_height,
        ],
        "material": material,
    }


class MeshBuilder:
    def __init__(self) -> None:
        self.vertices: list[tuple[float, float, float]] = []
        self.faces: list[tuple[int, ...]] = []

    def add_box(
        self,
        center: tuple[float, float, float],
        size: tuple[float, float, float],
    ) -> None:
        cx, cy, cz = center
        hx, hy, hz = (value / 2.0 for value in size)
        offset = len(self.vertices)
        self.vertices.extend(
            [
                (cx - hx, cy - hy, cz - hz),
                (cx + hx, cy - hy, cz - hz),
                (cx + hx, cy + hy, cz - hz),
                (cx - hx, cy + hy, cz - hz),
                (cx - hx, cy - hy, cz + hz),
                (cx + hx, cy - hy, cz + hz),
                (cx + hx, cy + hy, cz + hz),
                (cx - hx, cy + hy, cz + hz),
            ]
        )
        self.faces.extend(
            tuple(offset + index for index in face)
            for face in (
                (0, 3, 2, 1),
                (4, 5, 6, 7),
                (0, 1, 5, 4),
                (1, 2, 6, 5),
                (2, 3, 7, 6),
                (3, 0, 4, 7),
            )
        )


def _mesh_object(
    name: str,
    builder: MeshBuilder,
    material: Any,
    collection: Any,
) -> Any:
    import bmesh
    import bpy

    mesh = bpy.data.meshes.new(f"MESH_{name}")
    mesh.from_pydata(builder.vertices, [], builder.faces)
    mesh.update()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj


def _add_bay(
    builder: MeshBuilder,
    checked: dict[str, Any],
    side: int,
) -> dict[str, Any]:
    opening_half = checked["center_opening_m"] / 2.0
    outer_inset = checked["outer_inset_m"]
    total_half = checked["total_width_m"] / 2.0
    post_width = checked["post_width_m"]
    inner_x = side * (
        opening_half + post_width * 0.675
    )
    outer_x = side * (total_half - outer_inset)
    x0, x1 = sorted((inner_x, outer_x))
    center_x = (x0 + x1) / 2.0
    bay_length = x1 - x0
    platform = checked["platform_top_z_m"]
    height = checked["height_m"]
    front_y = checked["front_y_m"]
    for x in (x0, x1):
        builder.add_box(
            (
                x,
                front_y,
                platform + height / 2.0,
            ),
            (post_width, post_width, height),
        )
        builder.add_box(
            (
                x,
                front_y,
                platform + height + checked["post_cap_height_m"] / 2.0,
            ),
            (
                post_width * 1.3,
                post_width * 1.3,
                checked["post_cap_height_m"],
            ),
        )
        builder.add_box(
            (
                x,
                front_y,
                platform + 0.025,
            ),
            (
                post_width * 1.35,
                post_width * 1.6,
                0.05,
            ),
        )
    builder.add_box(
        (
            center_x,
            front_y,
            platform + height - checked["top_rail_height_m"] / 2.0,
        ),
        (
            bay_length,
            checked["top_rail_depth_m"],
            checked["top_rail_height_m"],
        ),
    )
    builder.add_box(
        (
            center_x,
            front_y,
            platform + checked["bottom_rail_z_m"],
        ),
        (
            bay_length,
            checked["bottom_rail_depth_m"],
            checked["bottom_rail_height_m"],
        ),
    )
    span_start = x0 + post_width / 2.0 + checked["baluster_width_m"]
    span_end = x1 - post_width / 2.0 - checked["baluster_width_m"]
    count = max(
        1,
        int(
            (span_end - span_start)
            / checked["baluster_spacing_m"]
        )
        + 1,
    )
    baluster_bottom = (
        platform
        + checked["bottom_rail_z_m"]
        + checked["bottom_rail_height_m"] / 2.0
    )
    baluster_top = (
        platform
        + height
        - checked["top_rail_height_m"]
    )
    for index in range(count):
        fraction = (
            index / (count - 1)
            if count > 1
            else 0.5
        )
        x = span_start + fraction * (span_end - span_start)
        builder.add_box(
            (
                x,
                front_y,
                (baluster_bottom + baluster_top) / 2.0,
            ),
            (
                checked["baluster_width_m"],
                checked["baluster_width_m"],
                baluster_top - baluster_bottom,
            ),
        )
    return {
        "side": "left" if side < 0 else "right",
        "inner_x_m": inner_x,
        "outer_x_m": outer_x,
        "bay_length_m": bay_length,
        "baluster_count": count,
    }


def build_railing(
    parameters: dict[str, Any],
    material_name: str,
    prefix: str = "SK_porch_railing_primary_v1",
    collection_name: str = "SK_COL_Structure",
    replace_existing: bool = True,
) -> dict[str, Any]:
    import bpy

    checked = validate_parameters(parameters)
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
    builder = MeshBuilder()
    bays = [
        _add_bay(builder, checked, -1),
        _add_bay(builder, checked, 1),
    ]
    obj = _mesh_object(
        f"{prefix}_wood",
        builder,
        material,
        collection,
    )
    root = bpy.data.objects.new(f"{prefix}_ROOT", None)
    collection.objects.link(root)
    obj.parent = root
    parameters_hash = hashlib.sha256(
        json.dumps(
            checked,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    obj["part_id"] = "porch_railing_primary"
    obj["parameters_hash"] = parameters_hash
    return {
        "status": "generated",
        "root": root.name,
        "objects": [obj.name],
        "dimensions_m": checked["overall_dimensions_m"],
        "bays": bays,
        "parameters_hash": parameters_hash,
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
    parser.add_argument("--material-name", required=True)
    parser.add_argument("--prefix", default="SK_porch_railing_primary_v1")
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
    parameters = _read_json(parameter_path)
    checked = validate_parameters(parameters)
    if args.validate_only:
        print(json.dumps(checked, ensure_ascii=False, indent=2))
        return 0
    try:
        result = build_railing(
            parameters,
            args.material_name,
            prefix=args.prefix,
            collection_name=args.collection,
        )
    except ImportError as exc:
        print(f"Railing generation must run inside Blender: {exc}", file=sys.stderr)
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
