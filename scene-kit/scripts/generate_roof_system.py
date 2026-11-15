#!/usr/bin/env python3
"""Generate a parametric gable roof with gables, ridge cap, fascia and gutter."""

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


def resolve_parameters(parameters: dict[str, Any]) -> dict[str, Any]:
    eave_width = _number(
        parameters.get("eave_width_m"),
        "eave_width_m",
        0.5,
    )
    eave_depth = _number(
        parameters.get("eave_depth_m"),
        "eave_depth_m",
        0.5,
    )
    eave_height = _number(
        parameters.get("eave_height_m"),
        "eave_height_m",
        0.0,
    )
    ridge_height = _number(
        parameters.get("ridge_height_m"),
        "ridge_height_m",
        0.0,
    )
    if ridge_height <= eave_height:
        raise ValueError("ridge_height_m must be above eave_height_m")
    thickness = _number(
        parameters.get("roof_thickness_m", 0.18),
        "roof_thickness_m",
        0.02,
    )
    wall_width = _number(
        parameters.get("gable_wall_width_m", 9.0),
        "gable_wall_width_m",
        0.2,
    )
    wall_depth = _number(
        parameters.get("gable_wall_depth_m", 7.5),
        "gable_wall_depth_m",
        0.2,
    )
    wall_thickness = _number(
        parameters.get("gable_wall_thickness_m", 0.2),
        "gable_wall_thickness_m",
        0.02,
    )
    if wall_width > eave_width or wall_depth > eave_depth:
        raise ValueError("gable wall must fit beneath the roof overhang")
    ridge_radius = _number(
        parameters.get("ridge_cap_radius_m", 0.1),
        "ridge_cap_radius_m",
        0.01,
    )
    fascia_height = _number(
        parameters.get("fascia_height_m", 0.18),
        "fascia_height_m",
        0.02,
    )
    fascia_depth = _number(
        parameters.get("fascia_depth_m", 0.08),
        "fascia_depth_m",
        0.01,
    )
    gutter_width = _number(
        parameters.get("gutter_width_m", 0.12),
        "gutter_width_m",
        0.02,
    )
    gutter_height = _number(
        parameters.get("gutter_height_m", 0.12),
        "gutter_height_m",
        0.02,
    )
    gutter_projection = _number(
        parameters.get("gutter_projection_m", 0.06),
        "gutter_projection_m",
        0.0,
    )
    half_depth = eave_depth / 2.0
    rise = ridge_height - eave_height
    slope_length = math.hypot(half_depth, rise)
    pitch_deg = math.degrees(math.atan2(rise, half_depth))
    cross_gable = parameters.get("cross_gable") or {}
    if isinstance(cross_gable, dict) and cross_gable.get("enabled"):
        raise ValueError("cross_gable.enabled is not implemented in v1")
    return {
        "eave_width_m": eave_width,
        "eave_depth_m": eave_depth,
        "eave_height_m": eave_height,
        "ridge_height_m": ridge_height,
        "roof_thickness_m": thickness,
        "gable_wall_width_m": wall_width,
        "gable_wall_depth_m": wall_depth,
        "gable_wall_thickness_m": wall_thickness,
        "ridge_cap_radius_m": ridge_radius,
        "fascia_height_m": fascia_height,
        "fascia_depth_m": fascia_depth,
        "gutter_width_m": gutter_width,
        "gutter_height_m": gutter_height,
        "gutter_projection_m": gutter_projection,
        "half_depth_m": half_depth,
        "rise_m": rise,
        "slope_length_m": slope_length,
        "pitch_deg": pitch_deg,
        "overall_dimensions_m": [
            eave_width + 2.0 * ridge_radius,
            eave_depth + 2.0 * gutter_projection,
            ridge_height
            + ridge_radius
            - (eave_height - fascia_height),
        ],
        "material": parameters.get("material") or {},
    }


def validate_parameters(parameters: dict[str, Any]) -> dict[str, Any]:
    resolved = resolve_parameters(parameters)
    material = resolved.get("material")
    if not isinstance(material, dict):
        raise ValueError("material must be an object")
    slug = material.get("roof_slug")
    if not isinstance(slug, str) or not slug.strip():
        raise ValueError("material.roof_slug must be provided")
    scale = material.get("mapping_scale")
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
        raise ValueError("material.mapping_scale must contain 3 positive numbers")
    return {"status": "pass", **resolved}


def _move_to_collection(obj: Any, collection: Any) -> None:
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    collection.objects.link(obj)


def _active_mesh() -> Any:
    import bpy

    obj = bpy.context.view_layer.objects.active
    if obj is None or obj.type != "MESH":
        selected = [
            item
            for item in bpy.context.selected_objects
            if item.type == "MESH"
        ]
        if not selected:
            raise RuntimeError("Blender primitive was not created")
        obj = selected[-1]
    return obj


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


def _mesh_object(
    name: str,
    vertices: list[tuple[float, float, float]],
    faces: list[tuple[int, ...]],
    material: Any,
    collection: Any,
) -> Any:
    import bmesh
    import bpy

    mesh = bpy.data.meshes.new(f"MESH_{name}")
    mesh.from_pydata(vertices, [], faces)
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


def _box_mesh(
    name: str,
    center: tuple[float, float, float],
    size: tuple[float, float, float],
    material: Any,
    collection: Any,
) -> Any:
    cx, cy, cz = center
    hx, hy, hz = (value / 2.0 for value in size)
    vertices = [
        (cx - hx, cy - hy, cz - hz),
        (cx + hx, cy - hy, cz - hz),
        (cx + hx, cy + hy, cz - hz),
        (cx - hx, cy + hy, cz - hz),
        (cx - hx, cy - hy, cz + hz),
        (cx + hx, cy - hy, cz + hz),
        (cx + hx, cy + hy, cz + hz),
        (cx - hx, cy + hy, cz + hz),
    ]
    faces = [
        (0, 3, 2, 1),
        (4, 5, 6, 7),
        (0, 1, 5, 4),
        (1, 2, 6, 5),
        (2, 3, 7, 6),
        (3, 0, 4, 7),
    ]
    return _mesh_object(name, vertices, faces, material, collection)


def _cylinder_x(
    name: str,
    radius: float,
    length: float,
    center_z: float,
    material: Any,
    collection: Any,
    sides: int = 20,
) -> Any:
    vertices = []
    x0 = -length / 2.0
    x1 = length / 2.0
    for x in (x0, x1):
        for index in range(sides):
            angle = 2.0 * math.pi * index / sides
            vertices.append(
                (
                    x,
                    radius * math.cos(angle),
                    center_z + radius * math.sin(angle),
                )
            )
    faces = []
    for index in range(sides):
        next_index = (index + 1) % sides
        faces.append((index, next_index, sides + next_index, sides + index))
    faces.append(tuple(reversed(range(sides))))
    faces.append(tuple(range(sides, 2 * sides)))
    return _mesh_object(name, vertices, faces, material, collection)


def build_roof(
    parameters: dict[str, Any],
    materials: dict[str, str],
    prefix: str = "SK_main_roof_assembly_v1",
    collection_name: str = "SK_COL_Structure",
    replace_existing: bool = True,
) -> dict[str, Any]:
    import bpy

    checked = validate_parameters(parameters)
    material_values = {}
    for role in ("roof", "gable", "ridge", "fascia", "gutter"):
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

    width = checked["eave_width_m"]
    depth = checked["eave_depth_m"]
    eave = checked["eave_height_m"]
    ridge = checked["ridge_height_m"]
    thickness = checked["roof_thickness_m"]
    half_depth = checked["half_depth_m"]
    rise = checked["rise_m"]
    slope_length = checked["slope_length_m"]
    normal_z = half_depth / slope_length
    normal_y = rise / slope_length
    roof_vertices: list[tuple[float, float, float]] = []
    roof_faces: list[tuple[int, ...]] = []
    for sign in (-1.0, 1.0):
        ridge_top = (0.0, ridge)
        eave_top = (sign * half_depth, eave)
        ridge_bottom = (
            ridge_top[0],
            ridge_top[1] - thickness,
        )
        eave_bottom = (
            eave_top[0],
            eave_top[1] - thickness,
        )
        x0 = -width / 2.0
        x1 = width / 2.0
        offset = len(roof_vertices)
        roof_vertices.extend([
            (x0, ridge_top[0], ridge_top[1]),
            (x1, ridge_top[0], ridge_top[1]),
            (x1, eave_top[0], eave_top[1]),
            (x0, eave_top[0], eave_top[1]),
            (x0, ridge_bottom[0], ridge_bottom[1]),
            (x1, ridge_bottom[0], ridge_bottom[1]),
            (x1, eave_bottom[0], eave_bottom[1]),
            (x0, eave_bottom[0], eave_bottom[1]),
        ])
        roof_faces.extend([
            (0, 1, 2, 3),
            (7, 6, 5, 4),
            (0, 4, 5, 1),
            (1, 5, 6, 2),
            (2, 6, 7, 3),
            (3, 7, 4, 0),
        ])
        roof_faces[-6:] = [
            tuple(offset + index for index in face)
            for face in roof_faces[-6:]
        ]
    roof = _mesh_object(
        f"{prefix}_roof",
        roof_vertices,
        roof_faces,
        material_values["roof"],
        collection,
    )

    wall_width = checked["gable_wall_width_m"]
    wall_depth = checked["gable_wall_depth_m"]
    wall_thickness = checked["gable_wall_thickness_m"]
    gable_vertices: list[tuple[float, float, float]] = []
    gable_faces: list[tuple[int, ...]] = []
    for sign in (-1.0, 1.0):
        x_outer = sign * wall_width / 2.0
        x_inner = x_outer - sign * wall_thickness
        y0 = -wall_depth / 2.0
        y1 = wall_depth / 2.0
        offset = len(gable_vertices)
        gable_vertices.extend([
            (x_outer, y0, eave),
            (x_outer, y1, eave),
            (x_outer, 0.0, ridge),
            (x_inner, y0, eave),
            (x_inner, y1, eave),
            (x_inner, 0.0, ridge),
        ])
        gable_faces.extend([
            (0, 1, 2),
            (5, 4, 3),
            (0, 3, 4, 1),
            (1, 4, 5, 2),
            (2, 5, 3, 0),
        ])
        gable_faces[-5:] = [
            tuple(offset + index for index in face)
            for face in gable_faces[-5:]
        ]
    gable = _mesh_object(
        f"{prefix}_gable",
        gable_vertices,
        gable_faces,
        material_values["gable"],
        collection,
    )

    ridge_cap = _cylinder_x(
        f"{prefix}_ridge_cap",
        checked["ridge_cap_radius_m"],
        width + 2.0 * checked["ridge_cap_radius_m"],
        ridge,
        material_values["ridge"],
        collection,
    )

    fascia_vertices: list[tuple[float, float, float]] = []
    fascia_faces: list[tuple[int, ...]] = []
    fascia_height = checked["fascia_height_m"]
    fascia_depth = checked["fascia_depth_m"]
    for sign in (-1.0, 1.0):
        part = _box_mesh(
            "fascia_part",
            (
                0.0,
                sign * (half_depth - fascia_depth / 2.0),
                eave - fascia_height / 2.0,
            ),
            (width, fascia_depth, fascia_height),
            material_values["fascia"],
            collection,
        )
        offset = len(fascia_vertices)
        fascia_vertices.extend(tuple(vertex.co) for vertex in part.data.vertices)
        fascia_faces.extend(
            tuple(offset + index for index in polygon.vertices)
            for polygon in part.data.polygons
        )
        bpy.data.objects.remove(part, do_unlink=True)
    fascia = _mesh_object(
        f"{prefix}_fascia",
        fascia_vertices,
        fascia_faces,
        material_values["fascia"],
        collection,
    )

    gutter_vertices: list[tuple[float, float, float]] = []
    gutter_faces: list[tuple[int, ...]] = []
    gutter_width = checked["gutter_width_m"]
    gutter_height = checked["gutter_height_m"]
    gutter_projection = checked["gutter_projection_m"]
    for sign in (-1.0, 1.0):
        part = _box_mesh(
            "gutter_part",
            (
                0.0,
                sign * (half_depth + gutter_projection / 2.0),
                eave - gutter_height / 2.0 - fascia_height * 0.35,
            ),
            (width, gutter_width, gutter_height),
            material_values["gutter"],
            collection,
        )
        offset = len(gutter_vertices)
        gutter_vertices.extend(tuple(vertex.co) for vertex in part.data.vertices)
        gutter_faces.extend(
            tuple(offset + index for index in polygon.vertices)
            for polygon in part.data.polygons
        )
        bpy.data.objects.remove(part, do_unlink=True)
    gutter = _mesh_object(
        f"{prefix}_gutter",
        gutter_vertices,
        gutter_faces,
        material_values["gutter"],
        collection,
    )

    for obj in (roof, gable, ridge_cap, fascia, gutter):
        obj["part_id"] = "main_roof_assembly"
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
    for obj in (roof, gable, ridge_cap, fascia, gutter):
        obj.parent = root
    return {
        "status": "generated",
        "root": root.name,
        "objects": [
            roof.name,
            gable.name,
            ridge_cap.name,
            fascia.name,
            gutter.name,
        ],
        "dimensions_m": checked["overall_dimensions_m"],
        "pitch_deg": checked["pitch_deg"],
        "slope_length_m": checked["slope_length_m"],
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
    parser.add_argument("--roof-material", required=True)
    parser.add_argument("--gable-material", required=True)
    parser.add_argument("--ridge-material", required=True)
    parser.add_argument("--fascia-material", required=True)
    parser.add_argument("--gutter-material", required=True)
    parser.add_argument("--prefix", default="SK_main_roof_assembly_v1")
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
        result = build_roof(
            parameters,
            {
                "roof": args.roof_material,
                "gable": args.gable_material,
                "ridge": args.ridge_material,
                "fascia": args.fascia_material,
                "gutter": args.gutter_material,
            },
            prefix=args.prefix,
            collection_name=args.collection,
        )
    except ImportError as exc:
        print(f"Roof generation must run inside Blender: {exc}", file=sys.stderr)
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
