#!/usr/bin/env python3
"""Generate alternating corner quoin blocks around all four wall corners."""

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
    width = _number(
        parameters.get("footprint_width_m"),
        "footprint_width_m",
        1.0,
    )
    depth = _number(
        parameters.get("footprint_depth_m"),
        "footprint_depth_m",
        1.0,
    )
    bottom = _number(
        parameters.get("bottom_z_m"),
        "bottom_z_m",
        0.0,
    )
    top = _number(
        parameters.get("top_z_m"),
        "top_z_m",
        bottom + 0.27,
    )
    block_height = _number(
        parameters.get("block_height_m"),
        "block_height_m",
        0.12,
    )
    long_length = _number(
        parameters.get("long_length_m"),
        "long_length_m",
        0.15,
    )
    short_length = _number(
        parameters.get("short_length_m"),
        "short_length_m",
        0.1,
    )
    projection = _number(
        parameters.get("projection_m"),
        "projection_m",
        0.02,
    )
    embed_depth = _number(
        parameters.get("embed_depth_m"),
        "embed_depth_m",
        0.02,
    )
    if long_length <= short_length:
        raise ValueError("long_length_m must exceed short_length_m")
    if long_length >= min(width, depth) * 0.25:
        raise ValueError("quoin blocks are too long for the facade")
    if top <= bottom + block_height:
        raise ValueError("quoin vertical range is too short")
    row_count = int(round((top - bottom) / block_height))
    actual_top = bottom + row_count * block_height
    material = parameters.get("material")
    if not isinstance(material, dict):
        raise ValueError("material must be an object")
    scale = material.get("stone_mapping_scale")
    if (
        not isinstance(scale, list)
        or len(scale) != 3
        or not all(
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and value > 0
            for value in scale
        )
    ):
        raise ValueError("material.stone_mapping_scale must have 3 positive numbers")
    return {
        "status": "pass",
        "footprint_width_m": width,
        "footprint_depth_m": depth,
        "bottom_z_m": bottom,
        "requested_top_z_m": top,
        "actual_top_z_m": actual_top,
        "block_height_m": block_height,
        "long_length_m": long_length,
        "short_length_m": short_length,
        "projection_m": projection,
        "embed_depth_m": embed_depth,
        "row_count": row_count,
        "corner_count": 4,
        "block_count": row_count * 4,
        "overall_dimensions_m": [
            width + projection * 2.0,
            depth + projection * 2.0,
            (row_count - 1) * block_height + block_height * 0.96,
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


def build_quoins(
    parameters: dict[str, Any],
    material_name: str,
    prefix: str = "SK_corner_stone_detail_v1",
    collection_name: str = "SK_COL_Ornament",
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
    half_width = checked["footprint_width_m"] / 2.0
    half_depth = checked["footprint_depth_m"] / 2.0
    thickness = checked["embed_depth_m"] + checked["projection_m"]
    outward_offset = (
        checked["projection_m"] - checked["embed_depth_m"]
    ) / 2.0
    row_height = checked["block_height_m"]
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            corner_x = sx * half_width
            corner_y = sy * half_depth
            for row in range(checked["row_count"]):
                center_z = (
                    checked["bottom_z_m"]
                    + row_height / 2.0
                    + row * row_height
                )
                x_long = row % 2 == 0
                x_length = (
                    checked["long_length_m"]
                    if x_long
                    else checked["short_length_m"]
                )
                y_length = (
                    checked["short_length_m"]
                    if x_long
                    else checked["long_length_m"]
                )
                builder.add_box(
                    (
                        corner_x - sx * x_length / 2.0,
                        corner_y + sy * outward_offset,
                        center_z,
                    ),
                    (
                        x_length,
                        thickness,
                        row_height * 0.96,
                    ),
                )
                builder.add_box(
                    (
                        corner_x + sx * outward_offset,
                        corner_y - sy * y_length / 2.0,
                        center_z,
                    ),
                    (
                        thickness,
                        y_length,
                        row_height * 0.96,
                    ),
                )
    obj = _mesh_object(
        f"{prefix}_stones",
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
    obj["part_id"] = "corner_stone_detail"
    obj["parameters_hash"] = parameters_hash
    return {
        "status": "generated",
        "root": root.name,
        "objects": [obj.name],
        "row_count": checked["row_count"],
        "block_count": checked["block_count"],
        "dimensions_m": checked["overall_dimensions_m"],
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
    parser.add_argument("--prefix", default="SK_corner_stone_detail_v1")
    parser.add_argument("--collection", default="SK_COL_Ornament")
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
        result = build_quoins(
            parameters,
            args.material_name,
            prefix=args.prefix,
            collection_name=args.collection,
        )
    except ImportError as exc:
        print(f"Quoin generation must run inside Blender: {exc}", file=sys.stderr)
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
