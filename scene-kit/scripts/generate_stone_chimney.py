#!/usr/bin/env python3
"""Generate repeated parametric stone chimneys on a gable roof."""

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
    roof = parameters.get("roof")
    shaft = parameters.get("shaft")
    collar = parameters.get("collar") or {}
    cap = parameters.get("cap") or {}
    flues = parameters.get("flues") or {}
    moss = parameters.get("moss") or {}
    for name, value in (
        ("roof", roof),
        ("shaft", shaft),
        ("collar", collar),
        ("cap", cap),
        ("flues", flues),
        ("moss", moss),
    ):
        if not isinstance(value, dict):
            raise ValueError(f"{name} must be an object")

    eave_width = _number(roof.get("eave_width_m"), "roof.eave_width_m", 0.2)
    eave_depth = _number(roof.get("eave_depth_m"), "roof.eave_depth_m", 0.2)
    eave_height = _number(
        roof.get("eave_height_m"),
        "roof.eave_height_m",
        0.0,
    )
    ridge_height = _number(
        roof.get("ridge_height_m"),
        "roof.ridge_height_m",
        0.0,
    )
    if ridge_height <= eave_height:
        raise ValueError("ridge height must be above eave height")

    base_width = _number(
        shaft.get("base_width_m"),
        "shaft.base_width_m",
        0.05,
    )
    base_depth = _number(
        shaft.get("base_depth_m"),
        "shaft.base_depth_m",
        0.05,
    )
    top_width = _number(
        shaft.get("top_width_m"),
        "shaft.top_width_m",
        0.05,
    )
    top_depth = _number(
        shaft.get("top_depth_m"),
        "shaft.top_depth_m",
        0.05,
    )
    if top_width > base_width or top_depth > base_depth:
        raise ValueError("chimney shaft must not widen toward the top")
    height_above = _number(
        shaft.get("height_above_roof_m"),
        "shaft.height_above_roof_m",
        0.1,
    )
    embed_depth = _number(
        shaft.get("embed_depth_m"),
        "shaft.embed_depth_m",
        0.01,
    )
    collar_overhang = _number(
        collar.get("overhang_m", 0.08),
        "collar.overhang_m",
        0.0,
    )
    collar_height = _number(
        collar.get("height_m", 0.22),
        "collar.height_m",
        0.01,
    )
    cap_overhang = _number(
        cap.get("overhang_m", 0.12),
        "cap.overhang_m",
        0.0,
    )
    cap_height = _number(
        cap.get("height_m", 0.14),
        "cap.height_m",
        0.01,
    )
    flue_count = _integer(flues.get("count", 2), "flues.count", 0)
    flue_radius = _number(
        flues.get("radius_m", 0.09),
        "flues.radius_m",
        0.01,
    )
    flue_height = _number(
        flues.get("height_m", 0.26),
        "flues.height_m",
        0.01,
    )
    flue_spacing = _number(
        flues.get("spacing_m", 0.22),
        "flues.spacing_m",
        0.0,
    )
    moss_height = _number(
        moss.get("band_height_m", 0.08),
        "moss.band_height_m",
        0.01,
    )
    moss_projection = _number(
        moss.get("projection_m", 0.006),
        "moss.projection_m",
        0.0,
    )

    placements = parameters.get("placements")
    if not isinstance(placements, list) or not placements:
        raise ValueError("placements must be a non-empty array")
    ids: set[str] = set()
    resolved_placements = []
    half_depth = eave_depth / 2.0
    rise = ridge_height - eave_height
    max_half_width = max(
        base_width + collar_overhang,
        top_width + cap_overhang,
        (flue_spacing + 2.0 * flue_radius) if flue_count else 0.0,
    )
    for index, item in enumerate(placements):
        if not isinstance(item, dict):
            raise ValueError(f"placements[{index}] must be an object")
        placement_id = item.get("id")
        if not isinstance(placement_id, str) or not placement_id:
            raise ValueError(f"placements[{index}].id must be provided")
        if placement_id in ids:
            raise ValueError(f"duplicate placement id: {placement_id}")
        ids.add(placement_id)
        x = _number(item.get("x_m"), f"{placement_id}.x_m")
        y = _number(item.get("y_m"), f"{placement_id}.y_m")
        if abs(x) + max_half_width / 2.0 > eave_width / 2.0:
            raise ValueError(f"{placement_id} exceeds roof eave width")
        if abs(y) >= half_depth:
            raise ValueError(f"{placement_id} must be inside the roof slope")
        roof_z = ridge_height - abs(y) / half_depth * rise
        rotation = _number(
            item.get("rotation_z_deg", 0.0),
            f"{placement_id}.rotation_z_deg",
        )
        resolved_placements.append(
            {
                "id": placement_id,
                "x_m": x,
                "y_m": y,
                "roof_surface_z_m": roof_z,
                "rotation_z_deg": rotation,
                "embedded": y,
            }
        )

    shaft_top = height_above
    cap_top = shaft_top + cap_height
    flue_top = cap_top + flue_height
    overall_width = max(
        base_width + 2.0 * collar_overhang,
        top_width + 2.0 * cap_overhang,
        (flue_spacing + 2.0 * flue_radius) if flue_count else 0.0,
    )
    overall_depth = max(
        base_depth + 2.0 * collar_overhang,
        top_depth + 2.0 * cap_overhang,
    )
    return {
        "eave_width_m": eave_width,
        "eave_depth_m": eave_depth,
        "eave_height_m": eave_height,
        "ridge_height_m": ridge_height,
        "shaft": {
            "base_width_m": base_width,
            "base_depth_m": base_depth,
            "top_width_m": top_width,
            "top_depth_m": top_depth,
            "height_above_roof_m": height_above,
            "embed_depth_m": embed_depth,
        },
        "collar": {
            "overhang_m": collar_overhang,
            "height_m": collar_height,
        },
        "cap": {
            "overhang_m": cap_overhang,
            "height_m": cap_height,
        },
        "flues": {
            "count": flue_count,
            "radius_m": flue_radius,
            "height_m": flue_height,
            "spacing_m": flue_spacing,
        },
        "moss": {
            "band_height_m": moss_height,
            "projection_m": moss_projection,
        },
        "placements": resolved_placements,
        "instance_count": len(resolved_placements),
        "overall_chimney_dimensions_m": [
            overall_width,
            overall_depth,
            embed_depth + flue_top,
        ],
    }


def validate_parameters(parameters: dict[str, Any]) -> dict[str, Any]:
    resolved = resolve_parameters(parameters)
    if resolved["instance_count"] < 1:
        raise ValueError("at least one chimney is required")
    return {"status": "pass", **resolved}


def _move_to_collection(obj: Any, collection: Any) -> None:
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    collection.objects.link(obj)


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


def _box(
    name: str,
    cx: float,
    cy: float,
    z0: float,
    z1: float,
    width: float,
    depth: float,
    material: Any,
    collection: Any,
) -> Any:
    hx = width / 2.0
    hy = depth / 2.0
    vertices = [
        (cx - hx, cy - hy, z0),
        (cx + hx, cy - hy, z0),
        (cx + hx, cy + hy, z0),
        (cx - hx, cy + hy, z0),
        (cx - hx, cy - hy, z1),
        (cx + hx, cy - hy, z1),
        (cx + hx, cy + hy, z1),
        (cx - hx, cy + hy, z1),
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


def _frustum(
    name: str,
    base_size: tuple[float, float],
    top_size: tuple[float, float],
    z0: float,
    z1: float,
    material: Any,
    collection: Any,
) -> Any:
    bx = base_size[0] / 2.0
    by = base_size[1] / 2.0
    tx = top_size[0] / 2.0
    ty = top_size[1] / 2.0
    vertices = [
        (-bx, -by, z0),
        (bx, -by, z0),
        (bx, by, z0),
        (-bx, by, z0),
        (-tx, -ty, z1),
        (tx, -ty, z1),
        (tx, ty, z1),
        (-tx, ty, z1),
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


def _cylinder_z(
    name: str,
    cx: float,
    cy: float,
    radius: float,
    z0: float,
    z1: float,
    material: Any,
    collection: Any,
    sides: int = 16,
) -> Any:
    vertices = []
    for z in (z0, z1):
        for index in range(sides):
            angle = 2.0 * math.pi * index / sides
            vertices.append(
                (
                    cx + radius * math.cos(angle),
                    cy + radius * math.sin(angle),
                    z,
                )
            )
    faces = []
    for index in range(sides):
        next_index = (index + 1) % sides
        faces.append((index, next_index, sides + next_index, sides + index))
    faces.append(tuple(reversed(range(sides))))
    faces.append(tuple(range(sides, 2 * sides)))
    return _mesh_object(name, vertices, faces, material, collection)


def _linked_instance(
    source: Any,
    name: str,
    location: tuple[float, float, float],
    rotation_z: float,
    collection: Any,
) -> Any:
    import bpy

    obj = source.copy()
    obj.data = source.data
    obj.name = name
    collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler.z = math.radians(rotation_z)
    obj["instance_id"] = name
    return obj


def build_chimneys(
    parameters: dict[str, Any],
    materials: dict[str, str],
    prefix: str = "SK_stone_chimney_primary_v1",
    collection_name: str = "SK_COL_Structure",
    replace_existing: bool = True,
) -> dict[str, Any]:
    import bpy

    checked = validate_parameters(parameters)
    material_values = {}
    for role in ("stone", "cap", "flue", "moss"):
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

    shaft = checked["shaft"]
    collar = checked["collar"]
    cap = checked["cap"]
    flues = checked["flues"]
    moss = checked["moss"]
    embed = shaft["embed_depth_m"]
    shaft_top = shaft["height_above_roof_m"]
    collar_w = shaft["base_width_m"] + 2.0 * collar["overhang_m"]
    collar_d = shaft["base_depth_m"] + 2.0 * collar["overhang_m"]
    collar_obj = _box(
        f"{prefix}__collar_source",
        0.0,
        0.0,
        -embed,
        collar["height_m"],
        collar_w,
        collar_d,
        material_values["stone"],
        collection,
    )
    shaft_obj = _frustum(
        f"{prefix}__shaft_source",
        (shaft["base_width_m"], shaft["base_depth_m"]),
        (shaft["top_width_m"], shaft["top_depth_m"]),
        -embed,
        shaft_top,
        material_values["stone"],
        collection,
    )
    moss_obj = _box(
        f"{prefix}__moss_source",
        0.0,
        0.0,
        0.0,
        moss["band_height_m"],
        shaft["base_width_m"] + 2.0 * moss["projection_m"],
        shaft["base_depth_m"] + 2.0 * moss["projection_m"],
        material_values["moss"],
        collection,
    )
    cap_obj = _box(
        f"{prefix}__cap_source",
        0.0,
        0.0,
        shaft_top,
        shaft_top + cap["height_m"],
        shaft["top_width_m"] + 2.0 * cap["overhang_m"],
        shaft["top_depth_m"] + 2.0 * cap["overhang_m"],
        material_values["cap"],
        collection,
    )
    flue_sources = []
    if flues["count"]:
        if flues["count"] == 1:
            centers = [0.0]
        else:
            total = (flues["count"] - 1) * flues["spacing_m"]
            centers = [
                -total / 2.0 + index * flues["spacing_m"]
                for index in range(flues["count"])
            ]
        for index, flue_x in enumerate(centers):
            flue_sources.append(
                _cylinder_z(
                    f"{prefix}__flue_{index}_source",
                    flue_x,
                    0.0,
                    flues["radius_m"],
                    shaft_top + cap["height_m"],
                    shaft_top + cap["height_m"] + flues["height_m"],
                    material_values["flue"],
                    collection,
                )
            )

    root = bpy.data.objects.new(f"{prefix}_ROOT", None)
    collection.objects.link(root)
    sources = [collar_obj, shaft_obj, moss_obj, cap_obj, *flue_sources]
    instance_objects = []
    for placement_index, placement in enumerate(checked["placements"]):
        instance_root = bpy.data.objects.new(
            f"{prefix}_{placement['id']}_ROOT",
            None,
        )
        collection.objects.link(instance_root)
        instance_root.parent = root
        instance_root.location = (
            placement["x_m"],
            placement["y_m"],
            placement["roof_surface_z_m"],
        )
        instance_root.rotation_euler.z = math.radians(
            placement["rotation_z_deg"]
        )
        instance_root["placement_id"] = placement["id"]
        for source in sources:
            obj = _linked_instance(
                source,
                f"{prefix}_{placement['id']}_{source.name.split('__')[-1].replace('_source', '')}",
                (0.0, 0.0, 0.0),
                0.0,
                collection,
            )
            obj.parent = instance_root
            instance_objects.append(obj)
    for source in sources:
        bpy.data.objects.remove(source, do_unlink=True)
    parameters_hash = hashlib.sha256(
        json.dumps(
            checked,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    for obj in instance_objects:
        obj["part_id"] = "stone_chimney_primary"
        obj["parameters_hash"] = parameters_hash
    return {
        "status": "generated",
        "root": root.name,
        "instance_roots": [
            f"{prefix}_{placement['id']}_ROOT"
            for placement in checked["placements"]
        ],
        "object_count": len(instance_objects),
        "instance_count": checked["instance_count"],
        "overall_chimney_dimensions_m": checked[
            "overall_chimney_dimensions_m"
        ],
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
    parser.add_argument("--stone-material", required=True)
    parser.add_argument("--cap-material", required=True)
    parser.add_argument("--flue-material", required=True)
    parser.add_argument("--moss-material", required=True)
    parser.add_argument("--prefix", default="SK_stone_chimney_primary_v1")
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
        result = build_chimneys(
            parameters,
            {
                "stone": args.stone_material,
                "cap": args.cap_material,
                "flue": args.flue_material,
                "moss": args.moss_material,
            },
            prefix=args.prefix,
            collection_name=args.collection,
        )
    except ImportError as exc:
        print(f"Chimney generation must run inside Blender: {exc}", file=sys.stderr)
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
