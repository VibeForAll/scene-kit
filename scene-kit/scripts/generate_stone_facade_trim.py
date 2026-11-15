#!/usr/bin/env python3
"""Generate continuous stone belt courses around a rectangular facade."""

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
    embed = _number(
        parameters.get("embed_depth_m"),
        "embed_depth_m",
        0.01,
    )
    projection = _number(
        parameters.get("projection_m"),
        "projection_m",
        0.01,
    )
    cap_projection = _number(
        parameters.get("cap_projection_m"),
        "cap_projection_m",
        0.0,
    )
    cap_height = _number(
        parameters.get("cap_height_m"),
        "cap_height_m",
        0.005,
    )
    clearance = parameters.get("opening_clearance")
    if not isinstance(clearance, dict):
        raise ValueError("opening_clearance must be an object")
    lower_top = _number(
        clearance.get("lower_window_top_m"),
        "opening_clearance.lower_window_top_m",
    )
    upper_bottom = _number(
        clearance.get("upper_window_bottom_m"),
        "opening_clearance.upper_window_bottom_m",
    )
    upper_top = _number(
        clearance.get("upper_window_top_m"),
        "opening_clearance.upper_window_top_m",
    )
    wall_top = _number(
        clearance.get("wall_top_m"),
        "opening_clearance.wall_top_m",
    )
    min_gap = _number(
        clearance.get("minimum_gap_m"),
        "opening_clearance.minimum_gap_m",
        0.0,
    )
    bands = parameters.get("bands")
    if not isinstance(bands, list) or not bands:
        raise ValueError("bands must be a non-empty array")
    checked_bands = []
    seen = set()
    for item in bands:
        if not isinstance(item, dict):
            raise ValueError("each band must be an object")
        band_id = item.get("id")
        if not isinstance(band_id, str) or not band_id.strip():
            raise ValueError("band.id must be a non-empty string")
        if band_id in seen:
            raise ValueError(f"duplicate band id: {band_id}")
        seen.add(band_id)
        z = _number(item.get("z_m"), f"{band_id}.z_m")
        height = _number(
            item.get("height_m"),
            f"{band_id}.height_m",
            0.04,
        )
        low = z - height / 2.0
        high = z + height / 2.0
        intersects_lower = low < lower_top + min_gap and high > 0.0
        intersects_upper = low < upper_top + min_gap and high > upper_bottom - min_gap
        if intersects_lower or intersects_upper:
            raise ValueError(f"{band_id} intersects a window opening")
        if high + cap_height / 2.0 > wall_top - min_gap:
            raise ValueError(f"{band_id} is too close to the wall top")
        checked_bands.append(
            {
                "id": band_id,
                "z_m": z,
                "height_m": height,
                "low_z_m": low,
                "high_z_m": high,
            }
        )
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
    thickness = embed + projection
    return {
        "status": "pass",
        "footprint_width_m": width,
        "footprint_depth_m": depth,
        "embed_depth_m": embed,
        "projection_m": projection,
        "cap_projection_m": cap_projection,
        "cap_height_m": cap_height,
        "thickness_m": thickness,
        "opening_clearance": clearance,
        "bands": checked_bands,
        "band_count": len(checked_bands),
        "facade_count": 4,
        "trim_segment_count": len(checked_bands) * 4,
        "overall_dimensions_m": [
            width + (projection + cap_projection) * 2.0,
            depth + (projection + cap_projection) * 2.0,
            max(item["high_z_m"] for item in checked_bands)
            - min(item["low_z_m"] for item in checked_bands),
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


def build_trim(
    parameters: dict[str, Any],
    material_name: str,
    prefix: str = "SK_stone_facade_trim_v1",
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
    width = checked["footprint_width_m"]
    depth = checked["footprint_depth_m"]
    thickness = checked["thickness_m"]
    cap_depth = thickness + checked["cap_projection_m"] * 2.0
    outward_offset = (
        checked["projection_m"] - checked["embed_depth_m"]
    ) / 2.0
    for band in checked["bands"]:
        z = band["z_m"]
        height = band["height_m"]
        cap_z = height / 2.0 - checked["cap_height_m"] / 2.0
        for facade in ("front", "back", "left", "right"):
            length = width if facade in {"front", "back"} else depth
            if facade == "front":
                center = (0.0, -depth / 2.0 - outward_offset, z)
                cap_center_y = -depth / 2.0 - outward_offset
                core_size = (length, thickness, height)
                cap_size = (length + 0.04, cap_depth, checked["cap_height_m"])
            elif facade == "back":
                center = (0.0, depth / 2.0 + outward_offset, z)
                cap_center_y = depth / 2.0 + outward_offset
                core_size = (length, thickness, height)
                cap_size = (length + 0.04, cap_depth, checked["cap_height_m"])
            elif facade == "left":
                center = (-width / 2.0 - outward_offset, 0.0, z)
                cap_center_y = 0.0
                core_size = (thickness, length, height)
                cap_size = (cap_depth, length + 0.04, checked["cap_height_m"])
            else:
                center = (width / 2.0 + outward_offset, 0.0, z)
                cap_center_y = 0.0
                core_size = (thickness, length, height)
                cap_size = (cap_depth, length + 0.04, checked["cap_height_m"])
            builder.add_box(center, core_size)
            if facade in {"front", "back"}:
                builder.add_box(
                    (0.0, cap_center_y, z + cap_z),
                    cap_size,
                )
                builder.add_box(
                    (0.0, cap_center_y, z - cap_z),
                    cap_size,
                )
            else:
                builder.add_box(
                    (center[0], 0.0, z + cap_z),
                    cap_size,
                )
                builder.add_box(
                    (center[0], 0.0, z - cap_z),
                    cap_size,
                )
    obj = _mesh_object(f"{prefix}_stone", builder, material, collection)
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
    obj["part_id"] = "stone_facade_trim"
    obj["parameters_hash"] = parameters_hash
    return {
        "status": "generated",
        "root": root.name,
        "objects": [obj.name],
        "bands": checked["band_count"],
        "segments": checked["trim_segment_count"],
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
    parser.add_argument("--prefix", default="SK_stone_facade_trim_v1")
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
        result = build_trim(
            parameters,
            args.material_name,
            prefix=args.prefix,
            collection_name=args.collection,
        )
    except ImportError as exc:
        print(f"Stone trim generation must run inside Blender: {exc}", file=sys.stderr)
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
