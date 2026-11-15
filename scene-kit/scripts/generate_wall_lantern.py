#!/usr/bin/env python3
"""Generate repeated wall-mounted storybook lanterns in Blender."""

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


def resolve_parameters(parameters: dict[str, Any]) -> dict[str, Any]:
    width = _number(parameters.get("width_m"), "width_m", 0.12)
    body_height = _number(
        parameters.get("body_height_m"),
        "body_height_m",
        0.2,
    )
    depth = _number(parameters.get("depth_m"), "depth_m", 0.1)
    frame = _number(
        parameters.get("frame_bar_m"),
        "frame_bar_m",
        0.005,
    )
    glass_inset = _number(
        parameters.get("glass_inset_m"),
        "glass_inset_m",
        0.001,
    )
    backplate_width = _number(
        parameters.get("backplate_width_m"),
        "backplate_width_m",
        0.08,
    )
    backplate_height = _number(
        parameters.get("backplate_height_m"),
        "backplate_height_m",
        0.1,
    )
    backplate_depth = _number(
        parameters.get("backplate_depth_m"),
        "backplate_depth_m",
        0.01,
    )
    bracket_projection = _number(
        parameters.get("bracket_projection_m"),
        "bracket_projection_m",
        0.03,
    )
    bracket_width = _number(
        parameters.get("bracket_width_m"),
        "bracket_width_m",
        0.02,
    )
    bracket_height = _number(
        parameters.get("bracket_height_m"),
        "bracket_height_m",
        0.015,
    )
    cap_projection = _number(
        parameters.get("cap_projection_m"),
        "cap_projection_m",
        0.01,
    )
    cap_height = _number(
        parameters.get("cap_height_m"),
        "cap_height_m",
        0.03,
    )
    cap_base_gap = _number(
        parameters.get("cap_base_gap_m", 0.012),
        "cap_base_gap_m",
        0.0,
    )
    finial_radius = _number(
        parameters.get("finial_radius_m"),
        "finial_radius_m",
        0.006,
    )
    wall_y = _number(
        parameters.get("wall_face_y_m"),
        "wall_face_y_m",
    )
    if frame * 2.5 >= min(width, depth):
        raise ValueError("frame_bar_m is too large for the lantern body")
    if glass_inset <= frame * 0.25:
        raise ValueError("glass_inset_m must place glass behind the frame")
    if cap_projection * 2 + width > 0.7:
        raise ValueError("cap projection produces an excessive lantern width")
    placements = parameters.get("placements")
    if not isinstance(placements, list) or not placements:
        raise ValueError("placements must be a non-empty array")
    checked_placements = []
    seen_ids = set()
    for item in placements:
        if not isinstance(item, dict):
            raise ValueError("each placement must be an object")
        placement_id = item.get("id")
        if not isinstance(placement_id, str) or not placement_id.strip():
            raise ValueError("placement.id must be a non-empty string")
        if placement_id in seen_ids:
            raise ValueError(f"duplicate placement id: {placement_id}")
        seen_ids.add(placement_id)
        checked_placements.append(
            {
                "id": placement_id,
                "x_m": _number(item.get("x_m"), f"{placement_id}.x_m"),
                "center_z_m": _number(
                    item.get("center_z_m"),
                    f"{placement_id}.center_z_m",
                ),
            }
        )
    body_center_y = wall_y - backplate_depth - bracket_projection - depth / 2
    return {
        "width_m": width,
        "body_height_m": body_height,
        "depth_m": depth,
        "frame_bar_m": frame,
        "glass_inset_m": glass_inset,
        "backplate_width_m": backplate_width,
        "backplate_height_m": backplate_height,
        "backplate_depth_m": backplate_depth,
        "bracket_projection_m": bracket_projection,
        "bracket_width_m": bracket_width,
        "bracket_height_m": bracket_height,
        "cap_projection_m": cap_projection,
        "cap_height_m": cap_height,
        "cap_base_gap_m": cap_base_gap,
        "finial_radius_m": finial_radius,
        "wall_face_y_m": wall_y,
        "body_center_y_m": body_center_y,
        "body_front_y_m": body_center_y - depth / 2,
        "body_back_y_m": body_center_y + depth / 2,
        "overall_dimensions_m": [
            width + cap_projection * 2,
            backplate_depth + bracket_projection + depth + cap_projection,
            body_height + cap_base_gap + cap_height + finial_radius * 2,
        ],
        "placements": checked_placements,
    }


def validate_parameters(parameters: dict[str, Any]) -> dict[str, Any]:
    return {"status": "pass", **resolve_parameters(parameters)}


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

    def add_frustum(
        self,
        center: tuple[float, float, float],
        bottom_size: tuple[float, float],
        top_size: tuple[float, float],
        height: float,
    ) -> None:
        cx, cy, cz = center
        bx, by = (value / 2.0 for value in bottom_size)
        tx, ty = (value / 2.0 for value in top_size)
        z0 = cz - height / 2.0
        z1 = cz + height / 2.0
        offset = len(self.vertices)
        self.vertices.extend(
            [
                (cx - bx, cy - by, z0),
                (cx + bx, cy - by, z0),
                (cx + bx, cy + by, z0),
                (cx - bx, cy + by, z0),
                (cx - tx, cy - ty, z1),
                (cx + tx, cy - ty, z1),
                (cx + tx, cy + ty, z1),
                (cx - tx, cy + ty, z1),
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


def _warm_glass_material(name: str) -> Any:
    import bpy

    material = bpy.data.materials.get(name)
    if material is None:
        material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    shader.inputs["Base Color"].default_value = (0.34, 0.16, 0.045, 1.0)
    shader.inputs["Roughness"].default_value = 0.28
    shader.inputs["Metallic"].default_value = 0.0
    transmission = shader.inputs.get("Transmission Weight")
    if transmission is not None:
        transmission.default_value = 0.22
    emission_color = shader.inputs.get("Emission Color")
    if emission_color is not None:
        emission_color.default_value = (0.5, 0.19, 0.035, 1.0)
    emission_strength = shader.inputs.get("Emission Strength")
    if emission_strength is not None:
        emission_strength.default_value = 1.8
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    return material


def _add_lantern(
    metal: MeshBuilder,
    glass: MeshBuilder,
    checked: dict[str, Any],
    placement: dict[str, Any],
) -> None:
    x = placement["x_m"]
    center_z = placement["center_z_m"]
    width = checked["width_m"]
    depth = checked["depth_m"]
    body_height = checked["body_height_m"]
    frame = checked["frame_bar_m"]
    inset = checked["glass_inset_m"]
    wall_y = checked["wall_face_y_m"]
    backplate_depth = checked["backplate_depth_m"]
    bracket_projection = checked["bracket_projection_m"]
    body_y = checked["body_center_y_m"]
    body_front = checked["body_front_y_m"]
    body_bottom = center_z - body_height / 2.0
    body_top = center_z + body_height / 2.0

    metal.add_box(
        (x, wall_y - backplate_depth / 2.0, center_z),
        (
            checked["backplate_width_m"],
            backplate_depth,
            checked["backplate_height_m"],
        ),
    )
    bracket_center_y = wall_y - backplate_depth - bracket_projection / 2.0
    metal.add_box(
        (x, bracket_center_y, center_z + body_height * 0.28),
        (
            checked["bracket_width_m"],
            bracket_projection,
            checked["bracket_height_m"],
        ),
    )
    metal.add_box(
        (x, body_y, body_bottom + frame / 2.0),
        (width, depth, frame),
    )
    metal.add_box(
        (x, body_y, body_top - frame / 2.0),
        (width, depth, frame),
    )
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            metal.add_box(
                (
                    x + sx * (width / 2.0 - frame / 2.0),
                    body_y + sy * (depth / 2.0 - frame / 2.0),
                    center_z,
                ),
                (frame, frame, body_height - frame * 2.0),
            )

    glass_height = body_height - frame * 2.0 - inset * 2.0
    glass.add_box(
        (x, body_front + inset, center_z),
        (
            width - frame * 2.0 - inset * 2.0,
            0.004,
            glass_height,
        ),
    )
    for sx in (-1.0, 1.0):
        glass.add_box(
            (
                x + sx * (width / 2.0 - inset),
                body_y,
                center_z,
            ),
            (
                0.004,
                depth - frame * 2.0 - inset * 2.0,
                glass_height,
            ),
        )

    cap_width = width + checked["cap_projection_m"] * 2.0
    cap_depth = depth + checked["cap_projection_m"] * 2.0
    gap = checked["cap_base_gap_m"]
    cap_base_z = body_top + gap
    metal.add_box(
        (x, body_y, cap_base_z - gap),
        (cap_width, cap_depth, 0.024),
    )
    cap_height = checked["cap_height_m"]
    metal.add_frustum(
        (x, body_y, cap_base_z + cap_height / 2.0),
        (cap_width, cap_depth),
        (width * 0.35, depth * 0.35),
        cap_height,
    )
    finial = checked["finial_radius_m"]
    metal.add_box(
        (x, body_y, cap_base_z + cap_height + finial),
        (finial * 1.2, finial * 1.2, finial * 2.0),
    )


def build_lanterns(
    parameters: dict[str, Any],
    metal_material_name: str,
    glass_material_name: str,
    prefix: str = "SK_wall_lantern_primary_v1",
    collection_name: str = "SK_COL_Site",
    replace_existing: bool = True,
) -> dict[str, Any]:
    import bpy

    checked = validate_parameters(parameters)
    metal_material = bpy.data.materials.get(metal_material_name)
    if metal_material is None:
        raise ValueError(f"Material not found: {metal_material_name}")
    glass_material = _warm_glass_material(glass_material_name)
    collection = bpy.data.collections.get(collection_name)
    if collection is None:
        collection = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(collection)
    if replace_existing:
        for obj in list(bpy.data.objects):
            if obj.name.startswith(prefix):
                bpy.data.objects.remove(obj, do_unlink=True)

    metal = MeshBuilder()
    glass = MeshBuilder()
    for placement in checked["placements"]:
        _add_lantern(metal, glass, checked, placement)
    metal_obj = _mesh_object(
        f"{prefix}_metal",
        metal,
        metal_material,
        collection,
    )
    glass_obj = _mesh_object(
        f"{prefix}_glass",
        glass,
        glass_material,
        collection,
    )
    root = bpy.data.objects.new(f"{prefix}_ROOT", None)
    collection.objects.link(root)
    parameters_hash = hashlib.sha256(
        json.dumps(
            checked,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    for obj in (metal_obj, glass_obj):
        obj.parent = root
        obj["part_id"] = "wall_lantern_primary"
        obj["parameters_hash"] = parameters_hash
    return {
        "status": "generated",
        "root": root.name,
        "objects": [metal_obj.name, glass_obj.name],
        "lantern_count": len(checked["placements"]),
        "dimensions_m": checked["overall_dimensions_m"],
        "placements": checked["placements"],
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
    parser.add_argument("--metal-material", required=True)
    parser.add_argument("--glass-material", required=True)
    parser.add_argument("--prefix", default="SK_wall_lantern_primary_v1")
    parser.add_argument("--collection", default="SK_COL_Site")
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
        result = build_lanterns(
            parameters,
            args.metal_material,
            args.glass_material,
            prefix=args.prefix,
            collection_name=args.collection,
        )
    except ImportError as exc:
        print(f"Lantern generation must run inside Blender: {exc}", file=sys.stderr)
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
