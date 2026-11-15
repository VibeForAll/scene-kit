#!/usr/bin/env python3
"""Generate a paired attic window with a compact timber hood."""

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


def _integer(value: Any, name: str, minimum: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{name} must be an integer")
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return value


def validate_parameters(parameters: dict[str, Any]) -> dict[str, Any]:
    width = _number(parameters.get("component_width_m"), "component_width_m")
    height = _number(parameters.get("component_height_m"), "component_height_m")
    window_count = _integer(parameters.get("window_count"), "window_count", 1)
    if window_count != 2:
        raise ValueError("paired attic window requires exactly two windows")
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
    gap = _number(parameters.get("gap_m"), "gap_m", 0.04)
    stone_border = _number(
        parameters.get("stone_border_m"),
        "stone_border_m",
        0.01,
    )
    stone_depth = _number(
        parameters.get("stone_depth_m"),
        "stone_depth_m",
        0.08,
    )
    sill_projection = _number(
        parameters.get("sill_projection_m"),
        "sill_projection_m",
        0.0,
    )
    sill_thickness = _number(
        parameters.get("sill_thickness_m"),
        "sill_thickness_m",
        0.01,
    )
    frame_thickness = _number(
        parameters.get("frame_thickness_m"),
        "frame_thickness_m",
        0.01,
    )
    frame_depth = _number(
        parameters.get("frame_depth_m"),
        "frame_depth_m",
        0.01,
    )
    bar_width = _number(parameters.get("bar_width_m"), "bar_width_m", 0.005)
    glass_depth = _number(
        parameters.get("glass_depth_m"),
        "glass_depth_m",
        0.002,
    )
    rows = _integer(parameters.get("rows"), "rows", 1)
    columns_per_window = _integer(
        parameters.get("columns_per_window"),
        "columns_per_window",
        1,
    )
    if rows != 2 or columns_per_window != 2:
        raise ValueError(
            "reference paired attic windows resolve to 2x2 panes per window"
        )

    hood = parameters.get("hood")
    if not isinstance(hood, dict):
        raise ValueError("hood must be an object")
    hood_width = _number(hood.get("width_m"), "hood.width_m", 0.4)
    hood_depth = _number(hood.get("depth_m"), "hood.depth_m", 0.06)
    hood_eave = _number(hood.get("eave_z_m"), "hood.eave_z_m", 0.2)
    hood_ridge = _number(hood.get("ridge_z_m"), "hood.ridge_z_m")
    hood_thickness = _number(
        hood.get("thickness_m"),
        "hood.thickness_m",
        0.01,
    )
    hood_ridge_width = _number(
        hood.get("ridge_width_m"),
        "hood.ridge_width_m",
        0.01,
    )
    hood_ridge_height = _number(
        hood.get("ridge_height_m"),
        "hood.ridge_height_m",
        0.005,
    )

    window_outer_width = opening_width + 2.0 * stone_border
    window_outer_height = opening_height + 2.0 * stone_border
    pair_width = window_count * window_outer_width + (window_count - 1) * gap
    if abs(pair_width - width) > 0.02:
        raise ValueError("window pair width does not match component width")
    if hood_width > width + 0.12:
        raise ValueError("attic hood projects too far beyond the window pair")
    if hood_eave <= window_outer_height:
        raise ValueError("attic hood must start above both window surrounds")
    lintel_top = window_outer_height - 0.005 + 0.065 / 2.0
    if hood_eave - hood_thickness / 2.0 > lintel_top:
        raise ValueError("attic hood must bear on the stone lintel")
    if hood_ridge <= hood_eave:
        raise ValueError("attic hood ridge must be above its eave")
    overall_height = hood_ridge + hood_thickness / 2.0 + hood_ridge_height
    if overall_height > height + 0.005:
        raise ValueError("attic hood exceeds the locked component height")
    overall_depth = max(stone_depth + sill_projection, hood_depth)
    if overall_depth > 0.28 + 0.005:
        raise ValueError("attic window assembly exceeds the locked depth")
    if frame_depth >= stone_depth:
        raise ValueError("window frame must sit inside the stone reveal")
    total_columns = window_count * columns_per_window
    return {
        "status": "pass",
        "component_width_m": width,
        "component_height_m": height,
        "window_count": window_count,
        "opening_width_m": opening_width,
        "opening_height_m": opening_height,
        "gap_m": gap,
        "stone_border_m": stone_border,
        "stone_depth_m": stone_depth,
        "sill_projection_m": sill_projection,
        "sill_thickness_m": sill_thickness,
        "frame_thickness_m": frame_thickness,
        "frame_depth_m": frame_depth,
        "bar_width_m": bar_width,
        "glass_depth_m": glass_depth,
        "rows": rows,
        "columns_per_window": columns_per_window,
        "columns": total_columns,
        "pane_count": total_columns * rows,
        "window_outer_width_m": window_outer_width,
        "window_outer_height_m": window_outer_height,
        "window_centers_x_m": [
            -(window_outer_width + gap) / 2.0,
            (window_outer_width + gap) / 2.0,
        ],
        "hood": {
            "width_m": hood_width,
            "depth_m": hood_depth,
            "eave_z_m": hood_eave,
            "ridge_z_m": hood_ridge,
            "thickness_m": hood_thickness,
            "ridge_width_m": hood_ridge_width,
            "ridge_height_m": hood_ridge_height,
        },
        "overall_dimensions_m": [
            width,
            overall_depth,
            overall_height,
        ],
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

    def add_sloped_x_box(
        self,
        x0: float,
        z0: float,
        x1: float,
        z1: float,
        y0: float,
        y1: float,
        thickness: float,
    ) -> None:
        half_thickness = thickness / 2.0
        offset = len(self.vertices)
        self.vertices.extend(
            [
                (x0, y0, z0 - half_thickness),
                (x1, y0, z1 - half_thickness),
                (x1, y1, z1 - half_thickness),
                (x0, y1, z0 - half_thickness),
                (x0, y0, z0 + half_thickness),
                (x1, y0, z1 + half_thickness),
                (x1, y1, z1 + half_thickness),
                (x0, y1, z0 + half_thickness),
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

    def add_triangle_prism(
        self,
        width: float,
        base_z: float,
        apex_z: float,
        y0: float,
        y1: float,
    ) -> None:
        half = width / 2.0
        offset = len(self.vertices)
        self.vertices.extend(
            [
                (-half, y0, base_z),
                (half, y0, base_z),
                (0.0, y0, apex_z),
                (-half, y1, base_z),
                (half, y1, base_z),
                (0.0, y1, apex_z),
            ]
        )
        self.faces.extend(
            [
                (offset, offset + 2, offset + 1),
                (offset + 3, offset + 4, offset + 5),
                (offset, offset + 1, offset + 4, offset + 3),
                (offset + 1, offset + 2, offset + 5, offset + 4),
                (offset + 2, offset, offset + 3, offset + 5),
            ]
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


def build_attic_window(
    parameters: dict[str, Any],
    materials: dict[str, str],
    prefix: str = "SK_attic_window_assembly",
    collection_name: str = "SK_COL_AI",
    replace_existing: bool = True,
) -> dict[str, Any]:
    import bpy

    scripts_dir = str(Path(__file__).resolve().parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    from generate_window_assembly import build_window

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

    window_parameters = {
        "opening_width_m": checked["opening_width_m"],
        "opening_height_m": checked["opening_height_m"],
        "installation_clearance_m": 0.012,
        "stone_border_m": checked["stone_border_m"],
        "stone_depth_m": checked["stone_depth_m"],
        "sill_projection_m": checked["sill_projection_m"],
        "sill_thickness_m": checked["sill_thickness_m"],
        "frame_thickness_m": checked["frame_thickness_m"],
        "frame_depth_m": checked["frame_depth_m"],
        "bar_width_m": checked["bar_width_m"],
        "glass_depth_m": checked["glass_depth_m"],
        "rows": checked["rows"],
        "major_vertical_sections": checked["columns_per_window"],
        "central_split": {"enabled": False, "sub_columns": 1},
    }
    roots = []
    window_objects: list[Any] = []
    for side, x in (
        ("left", checked["window_centers_x_m"][0]),
        ("right", checked["window_centers_x_m"][1]),
    ):
        result = build_window(
            window_parameters,
            materials,
            prefix=f"{prefix}_{side}",
            collection_name=collection_name,
            replace_existing=False,
        )
        root = bpy.data.objects[result["root"]]
        root.location.x = x
        roots.append(root)
        window_objects.extend(bpy.data.objects[name] for name in result["objects"])

    hood_parameters = checked["hood"]
    hood = MeshBuilder()
    hood_front = -hood_parameters["depth_m"] / 2.0
    hood_back = hood_parameters["depth_m"] / 2.0
    half_width = hood_parameters["width_m"] / 2.0
    hood.add_sloped_x_box(
        -half_width,
        hood_parameters["eave_z_m"],
        0.0,
        hood_parameters["ridge_z_m"],
        hood_front,
        hood_back,
        hood_parameters["thickness_m"],
    )
    hood.add_sloped_x_box(
        0.0,
        hood_parameters["ridge_z_m"],
        half_width,
        hood_parameters["eave_z_m"],
        hood_front,
        hood_back,
        hood_parameters["thickness_m"],
    )
    hood.add_triangle_prism(
        hood_parameters["width_m"],
        hood_parameters["eave_z_m"],
        hood_parameters["ridge_z_m"],
        hood_front - 0.012,
        hood_front + 0.012,
    )
    hood.add_box(
        (
            0.0,
            (hood_front + hood_back) / 2.0,
            hood_parameters["ridge_z_m"]
            + hood_parameters["ridge_height_m"] / 2.0,
        ),
        (
            hood_parameters["ridge_width_m"],
            hood_parameters["depth_m"],
            hood_parameters["ridge_height_m"],
        ),
    )
    hood_object = _mesh_object(
        f"{prefix}_hood",
        hood,
        material_values["wood"],
        collection,
    )

    lintel = MeshBuilder()
    lintel.add_box(
        (
            0.0,
            0.0,
            checked["window_outer_height_m"] - 0.005,
        ),
        (
            checked["component_width_m"] - 0.02,
            checked["stone_depth_m"],
            0.065,
        ),
    )
    lintel_object = _mesh_object(
        f"{prefix}_stone_lintel",
        lintel,
        material_values["stone"],
        collection,
    )

    assembly_root = bpy.data.objects.new(f"{prefix}_ROOT", None)
    collection.objects.link(assembly_root)
    for root in roots:
        root.parent = assembly_root
    hood_object.parent = assembly_root
    lintel_object.parent = assembly_root

    parameters_hash = hashlib.sha256(
        json.dumps(
            checked,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    all_meshes = [*window_objects, hood_object, lintel_object]
    for obj in all_meshes:
        obj["part_id"] = "attic_window_assembly"
        obj["parameters_hash"] = parameters_hash
    return {
        "status": "generated",
        "root": assembly_root.name,
        "objects": [obj.name for obj in all_meshes],
        "window_roots": [root.name for root in roots],
        "dimensions_m": checked["overall_dimensions_m"],
        "columns": checked["columns"],
        "rows": checked["rows"],
        "pane_count": checked["pane_count"],
        "hood_ridge_z_m": checked["hood"]["ridge_z_m"],
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
    parser.add_argument("--wood-material", required=True)
    parser.add_argument("--glass-material", required=True)
    parser.add_argument("--prefix", default="SK_attic_window_assembly")
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
        result = build_attic_window(
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
        print(f"Attic window generation must run inside Blender: {exc}", file=sys.stderr)
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
