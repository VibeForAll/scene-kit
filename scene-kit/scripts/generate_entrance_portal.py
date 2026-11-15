#!/usr/bin/env python3
"""Generate a parametric arched entrance portal."""

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
    opening = parameters.get("rough_opening")
    surround = parameters.get("stone_surround")
    door = parameters.get("door")
    hardware = parameters.get("hardware")
    placement = parameters.get("placement") or {}
    for name, value in (
        ("rough_opening", opening),
        ("stone_surround", surround),
        ("door", door),
        ("hardware", hardware),
        ("placement", placement),
    ):
        if not isinstance(value, dict):
            raise ValueError(f"{name} must be an object")
    rough_width = _number(
        opening.get("width_m"),
        "rough_opening.width_m",
        0.2,
    )
    rough_height = _number(
        opening.get("height_m"),
        "rough_opening.height_m",
        0.2,
    )
    border = _number(
        surround.get("border_m", 0.09),
        "stone_surround.border_m",
        0.01,
    )
    stone_depth = _number(
        surround.get("depth_m", 0.26),
        "stone_surround.depth_m",
        0.02,
    )
    front_projection = _number(
        surround.get("front_projection_m", 0.02),
        "stone_surround.front_projection_m",
        0.0,
    )
    threshold_height = _number(
        surround.get("threshold_height_m", 0.045),
        "stone_surround.threshold_height_m",
        0.005,
    )
    threshold_depth = _number(
        surround.get("threshold_depth_m", 0.32),
        "stone_surround.threshold_depth_m",
        stone_depth,
    )
    door_width = _number(door.get("width_m"), "door.width_m", 0.1)
    door_height = _number(door.get("height_m"), "door.height_m", 0.1)
    arch_rise = _number(
        door.get("arch_rise_m"),
        "door.arch_rise_m",
        0.05,
    )
    bottom = _number(door.get("bottom_m", threshold_height), "door.bottom_m", 0.0)
    door_thickness = _number(
        door.get("thickness_m", 0.065),
        "door.thickness_m",
        0.01,
    )
    leaf_count = _integer(
        door.get("leaf_count", 1),
        "door.leaf_count",
        1,
    )
    if leaf_count > 2:
        raise ValueError("door.leaf_count supports 1 or 2 leaves")
    panel_columns = _integer(
        door.get("panel_columns", 2),
        "door.panel_columns",
        1,
    )
    panel_rows = _integer(
        door.get("panel_rows", 3),
        "door.panel_rows",
        1,
    )
    panel_trim_width = _number(
        door.get("panel_trim_width_m", 0.028),
        "door.panel_trim_width_m",
        0.005,
    )
    panel_trim_depth = _number(
        door.get("panel_trim_depth_m", 0.018),
        "door.panel_trim_depth_m",
        0.002,
    )
    hinge_count = _integer(
        hardware.get("hinge_count", 2),
        "hardware.hinge_count",
        0,
    )
    hinge_width = _number(
        hardware.get("hinge_width_m", 0.2),
        "hardware.hinge_width_m",
        0.01,
    )
    hinge_height = _number(
        hardware.get("hinge_height_m", 0.05),
        "hardware.hinge_height_m",
        0.005,
    )
    handle_radius = _number(
        hardware.get("handle_radius_m", 0.055),
        "hardware.handle_radius_m",
        0.01,
    )
    handle_height = _number(
        hardware.get("handle_height_m", 1.02),
        "hardware.handle_height_m",
        bottom,
    )
    placement_x = _number(
        placement.get("x_m", 0.0),
        "placement.x_m",
    )
    placement_y = _number(
        placement.get("y_m", 0.0),
        "placement.y_m",
    )
    placement_z = _number(
        placement.get("z_m", 0.0),
        "placement.z_m",
    )
    if door_width > rough_width - 0.06:
        raise ValueError("door must leave at least 0.03 m reveal each side")
    if bottom + door_height > rough_height - 0.03:
        raise ValueError("door must leave at least 0.03 m head reveal")
    door_spring = bottom + door_height - arch_rise
    if door_spring <= bottom + 0.15:
        raise ValueError("door arch rise leaves no practical vertical panel zone")
    if arch_rise > door_width / 2.0 + 1.0e-9:
        raise ValueError("door arch rise must not exceed half width")
    stone_spring = rough_height - arch_rise
    outer_radius = rough_width / 2.0 + border
    outer_top = stone_spring + outer_radius
    if not bottom <= handle_height <= bottom + door_height:
        raise ValueError("handle height must be within the door leaf")
    return {
        "rough_opening": {
            "width_m": rough_width,
            "height_m": rough_height,
        },
        "stone_surround": {
            "border_m": border,
            "depth_m": stone_depth,
            "front_projection_m": front_projection,
            "threshold_height_m": threshold_height,
            "threshold_depth_m": threshold_depth,
            "spring_height_m": stone_spring,
            "inner_radius_m": rough_width / 2.0,
            "outer_radius_m": outer_radius,
        },
        "door": {
            "width_m": door_width,
            "height_m": door_height,
            "arch_rise_m": arch_rise,
            "spring_height_m": door_spring,
            "bottom_m": bottom,
            "top_m": bottom + door_height,
            "thickness_m": door_thickness,
            "leaf_count": leaf_count,
            "panel_columns": panel_columns,
            "panel_rows": panel_rows,
            "panel_trim_width_m": panel_trim_width,
            "panel_trim_depth_m": panel_trim_depth,
        },
        "hardware": {
            "hinge_count": hinge_count,
            "hinge_width_m": hinge_width,
            "hinge_height_m": hinge_height,
            "handle_radius_m": handle_radius,
            "handle_height_m": handle_height,
        },
        "placement": {
            "x_m": placement_x,
            "y_m": placement_y,
            "z_m": placement_z,
        },
        "overall_width_m": rough_width + 2.0 * border,
        "overall_height_m": outer_top,
        "overall_depth_m": max(stone_depth + front_projection, threshold_depth),
    }


def validate_parameters(parameters: dict[str, Any]) -> dict[str, Any]:
    resolved = resolve_parameters(parameters)
    return {"status": "pass", **resolved}


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

    def add_prism(
        self,
        outline: list[tuple[float, float]],
        y_front: float,
        y_back: float,
    ) -> None:
        offset = len(self.vertices)
        count = len(outline)
        self.vertices.extend((x, y_front, z) for x, z in outline)
        self.vertices.extend((x, y_back, z) for x, z in outline)
        self.faces.append(tuple(offset + index for index in range(count)))
        self.faces.append(
            tuple(offset + count + index for index in reversed(range(count)))
        )
        for index in range(count):
            next_index = (index + 1) % count
            self.faces.append(
                (
                    offset + index,
                    offset + next_index,
                    offset + count + next_index,
                    offset + count + index,
                )
            )

    def add_torus_y(
        self,
        center: tuple[float, float, float],
        major_radius: float,
        minor_radius: float,
        major_segments: int = 16,
        minor_segments: int = 8,
    ) -> None:
        cx, cy, cz = center
        offset = len(self.vertices)
        for major_index in range(major_segments):
            major_angle = 2.0 * math.pi * major_index / major_segments
            cos_major = math.cos(major_angle)
            sin_major = math.sin(major_angle)
            for minor_index in range(minor_segments):
                minor_angle = 2.0 * math.pi * minor_index / minor_segments
                radius = major_radius + minor_radius * math.cos(minor_angle)
                self.vertices.append(
                    (
                        cx + radius * cos_major,
                        cy + minor_radius * math.sin(minor_angle),
                        cz + radius * sin_major,
                    )
                )
        for major_index in range(major_segments):
            next_major = (major_index + 1) % major_segments
            for minor_index in range(minor_segments):
                next_minor = (minor_index + 1) % minor_segments
                self.faces.append(
                    (
                        offset + major_index * minor_segments + minor_index,
                        offset + next_major * minor_segments + minor_index,
                        offset + next_major * minor_segments + next_minor,
                        offset + major_index * minor_segments + next_minor,
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


def _arched_outline(
    width: float,
    spring_height: float,
    top_height: float,
    bottom: float,
    segments: int = 12,
) -> list[tuple[float, float]]:
    half = width / 2.0
    radius = half
    center_z = top_height - radius
    points = [(-half, bottom), (half, bottom), (half, center_z)]
    for index in range(1, segments):
        angle = math.pi * index / segments
        points.append(
            (
                radius * math.cos(angle),
                center_z + radius * math.sin(angle),
            )
        )
    points.append((-half, center_z))
    if abs(center_z + radius - top_height) > 1e-4:
        raise ValueError("arched outline height does not match radius")
    return points


def build_portal(
    parameters: dict[str, Any],
    materials: dict[str, str],
    prefix: str = "SK_entrance_portal_v1",
    collection_name: str = "SK_COL_Structure",
    replace_existing: bool = True,
) -> dict[str, Any]:
    import bpy

    checked = validate_parameters(parameters)
    material_values = {}
    for role in ("stone", "wood", "iron"):
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

    rough = checked["rough_opening"]
    surround = checked["stone_surround"]
    door = checked["door"]
    hardware = checked["hardware"]
    rough_w = rough["width_m"]
    rough_h = rough["height_m"]
    border = surround["border_m"]
    depth = surround["depth_m"]
    front_projection = surround["front_projection_m"]
    stone_y0 = -depth / 2.0 - front_projection
    stone_y1 = depth / 2.0
    stone_center_y = (stone_y0 + stone_y1) / 2.0
    stone = MeshBuilder()
    jamb_x = rough_w / 2.0 + border / 2.0
    outer_top = checked["overall_height_m"]
    stone.add_box(
        (-jamb_x, stone_center_y, outer_top / 2.0),
        (border, depth + front_projection, outer_top),
    )
    stone.add_box(
        (jamb_x, stone_center_y, outer_top / 2.0),
        (border, depth + front_projection, outer_top),
    )
    stone_spring = surround["spring_height_m"]
    inner_radius = surround["inner_radius_m"]
    outer_radius = surround["outer_radius_m"]
    arch_segments = 10
    for index in range(arch_segments):
        a0 = math.pi * index / arch_segments
        a1 = math.pi * (index + 1) / arch_segments
        for angle, radius in ((a0, inner_radius), (a1, inner_radius)):
            pass
        p0 = (
            inner_radius * math.cos(a0),
            stone_spring + inner_radius * math.sin(a0),
        )
        p1 = (
            outer_radius * math.cos(a0),
            stone_spring + outer_radius * math.sin(a0),
        )
        p2 = (
            outer_radius * math.cos(a1),
            stone_spring + outer_radius * math.sin(a1),
        )
        p3 = (
            inner_radius * math.cos(a1),
            stone_spring + inner_radius * math.sin(a1),
        )
        stone.add_prism([p0, p1, p2, p3], stone_y0, stone_y1)
    stone.add_box(
        (
            0.0,
            -0.02,
            surround["threshold_height_m"] / 2.0,
        ),
        (
            rough_w + 2.0 * border,
            surround["threshold_depth_m"],
            surround["threshold_height_m"],
        ),
    )
    stone_obj = _mesh_object(
        f"{prefix}_stone",
        stone,
        material_values["stone"],
        collection,
    )

    wood = MeshBuilder()
    door_y_front = stone_y0 + 0.02
    door_y_back = door_y_front + door["thickness_m"]
    leaf_count = door["leaf_count"]
    leaf_gap = 0.012 if leaf_count == 2 else 0.0
    leaf_width = (
        door["width_m"] - leaf_gap * (leaf_count - 1)
    ) / leaf_count
    for leaf_index in range(leaf_count):
        center_x = (
            (leaf_index - (leaf_count - 1) / 2.0)
            * (leaf_width + leaf_gap)
        )
        outline = _arched_outline(
            leaf_width,
            door["spring_height_m"],
            door["top_m"],
            door["bottom_m"],
        )
        outline = [(center_x + x, z) for x, z in outline]
        wood.add_prism(outline, door_y_front, door_y_back)
        panel_left = center_x - leaf_width / 2.0 + 0.075
        panel_right = center_x + leaf_width / 2.0 - 0.075
        panel_bottom = door["bottom_m"] + 0.09
        panel_top = door["spring_height_m"] - 0.08
        panel_width = (panel_right - panel_left) / door["panel_columns"]
        panel_height = (panel_top - panel_bottom) / door["panel_rows"]
        trim = door["panel_trim_width_m"]
        trim_depth = door["panel_trim_depth_m"]
        trim_y = door_y_front - trim_depth / 2.0 - 0.002
        for row in range(door["panel_rows"]):
            for column in range(door["panel_columns"]):
                x0 = panel_left + column * panel_width + trim / 2.0
                x1 = panel_left + (column + 1) * panel_width - trim / 2.0
                z0 = panel_bottom + row * panel_height + trim / 2.0
                z1 = panel_bottom + (row + 1) * panel_height - trim / 2.0
                cx = (x0 + x1) / 2.0
                cz = (z0 + z1) / 2.0
                width = x1 - x0
                height = z1 - z0
                wood.add_box((cx, trim_y, z0), (width, trim_depth, trim))
                wood.add_box((cx, trim_y, z1), (width, trim_depth, trim))
                wood.add_box((x0, trim_y, cz), (trim, trim_depth, height))
                wood.add_box((x1, trim_y, cz), (trim, trim_depth, height))
    wood_obj = _mesh_object(
        f"{prefix}_door",
        wood,
        material_values["wood"],
        collection,
    )

    iron = MeshBuilder()
    hinge_y = door_y_front - 0.008
    for leaf_index in range(leaf_count):
        center_x = (
            (leaf_index - (leaf_count - 1) / 2.0)
            * (leaf_width + leaf_gap)
        )
        left_x = center_x - leaf_width / 2.0 + hardware["hinge_width_m"] / 2.0
        for hinge_index in range(hardware["hinge_count"]):
            fraction = (hinge_index + 1) / (
                hardware["hinge_count"] + 1
            )
            z = door["bottom_m"] + fraction * (
                door["spring_height_m"] - door["bottom_m"]
            )
            iron.add_box(
                (left_x, hinge_y, z),
                (
                    hardware["hinge_width_m"],
                    0.016,
                    hardware["hinge_height_m"],
                ),
            )
    handle_x = leaf_width * 0.27 if leaf_count == 1 else 0.0
    iron.add_torus_y(
        (handle_x, door_y_front - 0.034, hardware["handle_height_m"]),
        hardware["handle_radius_m"],
        0.011,
    )
    iron.add_box(
        (handle_x, door_y_front - 0.014, hardware["handle_height_m"]),
        (0.04, 0.024, 0.12),
    )
    iron_obj = _mesh_object(
        f"{prefix}_iron",
        iron,
        material_values["iron"],
        collection,
    )

    root = bpy.data.objects.new(f"{prefix}_ROOT", None)
    collection.objects.link(root)
    root.location = (
        checked["placement"]["x_m"],
        checked["placement"]["y_m"],
        checked["placement"]["z_m"],
    )
    objects = [stone_obj, wood_obj, iron_obj]
    parameters_hash = hashlib.sha256(
        json.dumps(
            checked,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    for obj in objects:
        obj.parent = root
        obj["part_id"] = "entrance_portal"
        obj["parameters_hash"] = parameters_hash
    return {
        "status": "generated",
        "root": root.name,
        "objects": [obj.name for obj in objects],
        "dimensions_m": [
            checked["overall_width_m"],
            checked["overall_depth_m"],
            checked["overall_height_m"],
        ],
        "leaf_count": leaf_count,
        "panel_count": (
            leaf_count * door["panel_columns"] * door["panel_rows"]
        ),
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
    parser.add_argument("--iron-material", required=True)
    parser.add_argument("--prefix", default="SK_entrance_portal_v1")
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
        result = build_portal(
            parameters,
            {
                "stone": args.stone_material,
                "wood": args.wood_material,
                "iron": args.iron_material,
            },
            prefix=args.prefix,
            collection_name=args.collection,
        )
    except ImportError as exc:
        print(f"Portal generation must run inside Blender: {exc}", file=sys.stderr)
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
