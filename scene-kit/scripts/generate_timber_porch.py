#!/usr/bin/env python3
"""Generate a parametric timber entrance canopy and landing."""

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
    width = _number(parameters.get("width_m"), "width_m", 1.5)
    landing_depth = _number(
        parameters.get("landing_depth_m"),
        "landing_depth_m",
        0.2,
    )
    landing_thickness = _number(
        parameters.get("landing_thickness_m"),
        "landing_thickness_m",
        0.06,
    )
    landing_top = _number(
        parameters.get("landing_top_z_m"),
        "landing_top_z_m",
        0.1,
    )
    landing_back_y = _number(
        parameters.get("landing_back_y_m"),
        "landing_back_y_m",
    )
    board_count = _integer(
        parameters.get("landing_board_count"),
        "landing_board_count",
        1,
    )
    post_width = _number(
        parameters.get("post_width_m"),
        "post_width_m",
        0.08,
    )
    post_x = _number(parameters.get("post_x_m"), "post_x_m", 0.5)
    post_front_y = _number(
        parameters.get("post_front_y_m"),
        "post_front_y_m",
    )
    post_top = _number(
        parameters.get("post_top_z_m"),
        "post_top_z_m",
        1.8,
    )
    base_height = _number(
        parameters.get("post_base_height_m"),
        "post_base_height_m",
        0.05,
    )
    base_width = _number(
        parameters.get("post_base_width_m"),
        "post_base_width_m",
        post_width,
    )
    beam_width = _number(
        parameters.get("beam_width_m"),
        "beam_width_m",
        0.08,
    )
    beam_height = _number(
        parameters.get("beam_height_m"),
        "beam_height_m",
        0.08,
    )
    roof_width = _number(
        parameters.get("roof_width_m"),
        "roof_width_m",
        width,
    )
    roof_back_y = _number(
        parameters.get("roof_back_y_m"),
        "roof_back_y_m",
    )
    roof_front_y = _number(
        parameters.get("roof_front_y_m"),
        "roof_front_y_m",
    )
    roof_back_z = _number(
        parameters.get("roof_back_z_m"),
        "roof_back_z_m",
    )
    roof_front_z = _number(
        parameters.get("roof_front_z_m"),
        "roof_front_z_m",
    )
    roof_thickness = _number(
        parameters.get("roof_thickness_m"),
        "roof_thickness_m",
        0.03,
    )
    rafter_count = _integer(
        parameters.get("rafter_count"),
        "rafter_count",
        2,
    )
    rafter_width = _number(
        parameters.get("rafter_width_m"),
        "rafter_width_m",
        0.03,
    )
    rafter_depth = _number(
        parameters.get("rafter_depth_m"),
        "rafter_depth_m",
        0.03,
    )
    if roof_front_y >= roof_back_y:
        raise ValueError("roof_front_y_m must be less than roof_back_y_m")
    if roof_front_z >= roof_back_z:
        raise ValueError("roof_front_z_m must be below roof_back_z_m")
    if post_top + beam_height / 2.0 >= roof_front_z:
        raise ValueError("post head would penetrate the roof")
    if post_x - post_width / 2.0 <= 0.9:
        raise ValueError("porch posts intrude into the stair clear width")
    if roof_width < width:
        raise ValueError("roof_width_m must cover the landing width")
    if base_height + 0.2 >= post_top:
        raise ValueError("post is too short above its stone base")
    material = parameters.get("material")
    if not isinstance(material, dict):
        raise ValueError("material must be an object")
    for key in (
        "wood_mapping_scale",
        "slate_mapping_scale",
        "stone_mapping_scale",
    ):
        scale = material.get(key)
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
            raise ValueError(f"material.{key} must contain 3 positive numbers")
    return {
        "status": "pass",
        "width_m": width,
        "landing_depth_m": landing_depth,
        "landing_thickness_m": landing_thickness,
        "landing_top_z_m": landing_top,
        "landing_bottom_z_m": landing_top - landing_thickness,
        "landing_back_y_m": landing_back_y,
        "landing_front_y_m": landing_back_y - landing_depth,
        "landing_board_count": board_count,
        "post_width_m": post_width,
        "post_x_m": post_x,
        "post_front_y_m": post_front_y,
        "post_top_z_m": post_top,
        "post_base_height_m": base_height,
        "post_base_width_m": base_width,
        "beam_width_m": beam_width,
        "beam_height_m": beam_height,
        "roof_width_m": roof_width,
        "roof_back_y_m": roof_back_y,
        "roof_front_y_m": roof_front_y,
        "roof_back_z_m": roof_back_z,
        "roof_front_z_m": roof_front_z,
        "roof_thickness_m": roof_thickness,
        "rafter_count": rafter_count,
        "rafter_width_m": rafter_width,
        "rafter_depth_m": rafter_depth,
        "overall_dimensions_m": [
            roof_width,
            max(roof_back_y, landing_back_y) - roof_front_y,
            roof_back_z + roof_thickness / 2.0,
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

    def add_sloped_y_box(
        self,
        x: float,
        y0: float,
        z0: float,
        y1: float,
        z1: float,
        width: float,
        thickness: float,
    ) -> None:
        hx = width / 2.0
        ht = thickness / 2.0
        offset = len(self.vertices)
        self.vertices.extend(
            [
                (x - hx, y0, z0 - ht),
                (x + hx, y0, z0 - ht),
                (x + hx, y1, z1 - ht),
                (x - hx, y1, z1 - ht),
                (x - hx, y0, z0 + ht),
                (x + hx, y0, z0 + ht),
                (x + hx, y1, z1 + ht),
                (x - hx, y1, z1 + ht),
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


def build_porch(
    parameters: dict[str, Any],
    wood_material_name: str,
    roof_material_name: str,
    stone_material_name: str,
    prefix: str = "SK_wooden_entrance_porch_v1",
    collection_name: str = "SK_COL_Structure",
    replace_existing: bool = True,
) -> dict[str, Any]:
    import bpy

    checked = validate_parameters(parameters)
    materials = {}
    for role, name in (
        ("wood", wood_material_name),
        ("roof", roof_material_name),
        ("stone", stone_material_name),
    ):
        material = bpy.data.materials.get(name)
        if material is None:
            raise ValueError(f"Material not found: {name}")
        materials[role] = material
    collection = bpy.data.collections.get(collection_name)
    if collection is None:
        collection = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(collection)
    if replace_existing:
        for obj in list(bpy.data.objects):
            if obj.name.startswith(prefix):
                bpy.data.objects.remove(obj, do_unlink=True)

    wood = MeshBuilder()
    roof = MeshBuilder()
    stone = MeshBuilder()
    width = checked["width_m"]
    landing_depth = checked["landing_depth_m"]
    landing_top = checked["landing_top_z_m"]
    landing_back = checked["landing_back_y_m"]
    landing_front = checked["landing_front_y_m"]
    board_count = checked["landing_board_count"]
    gap = min(0.008, width / board_count * 0.04)
    board_width = (width - gap * (board_count - 1)) / board_count
    for index in range(board_count):
        x = -width / 2.0 + board_width / 2.0 + index * (
            board_width + gap
        )
        wood.add_box(
            (
                x,
                (landing_back + landing_front) / 2.0,
                landing_top - checked["landing_thickness_m"] / 2.0,
            ),
            (
                board_width,
                landing_depth,
                checked["landing_thickness_m"],
            ),
        )
    wood.add_box(
        (
            0.0,
            landing_front + 0.045,
            landing_top - checked["landing_thickness_m"] - 0.06,
        ),
        (width, 0.09, 0.12),
    )

    post_width = checked["post_width_m"]
    for x in (-checked["post_x_m"], checked["post_x_m"]):
        stone.add_box(
            (
                x,
                checked["post_front_y_m"],
                checked["post_base_height_m"] / 2.0,
            ),
            (
                checked["post_base_width_m"],
                checked["post_base_width_m"],
                checked["post_base_height_m"],
            ),
        )
        wood.add_box(
            (
                x,
                checked["post_front_y_m"],
                (
                    checked["post_base_height_m"]
                    + checked["post_top_z_m"]
                )
                / 2.0,
            ),
            (
                post_width,
                post_width,
                checked["post_top_z_m"] - checked["post_base_height_m"],
            ),
        )
        wood.add_box(
            (
                x,
                checked["post_front_y_m"],
                checked["post_top_z_m"] - 0.06,
            ),
            (post_width * 1.35, post_width * 1.35, 0.12),
        )

    beam_width = checked["beam_width_m"]
    beam_height = checked["beam_height_m"]
    front_beam_z = checked["post_top_z_m"] + 0.02
    wood.add_box(
        (0.0, checked["post_front_y_m"], front_beam_z),
        (
            checked["roof_width_m"] - 0.12,
            beam_width,
            beam_height,
        ),
    )
    side_beam_length = (
        checked["post_front_y_m"] - checked["roof_back_y_m"]
    )
    for x in (-checked["post_x_m"], checked["post_x_m"]):
        wood.add_box(
            (
                x,
                (
                    checked["post_front_y_m"]
                    + checked["roof_back_y_m"]
                )
                / 2.0,
                checked["post_top_z_m"],
            ),
            (beam_width, abs(side_beam_length), beam_height),
        )

    for x in (
        -checked["post_x_m"] + 0.18,
        checked["post_x_m"] - 0.18,
    ):
        wood.add_box(
            (
                x,
                checked["post_front_y_m"] + 0.16,
                checked["post_top_z_m"] - 0.34,
            ),
            (0.12, 0.42, 0.14),
        )
        wood.add_box(
            (
                x,
                checked["post_front_y_m"] + 0.32,
                checked["post_top_z_m"] - 0.55,
            ),
            (0.1, 0.22, 0.24),
        )

    rafter_count = checked["rafter_count"]
    rafter_span = checked["roof_back_y_m"] - checked["roof_front_y_m"]
    for index in range(rafter_count):
        fraction = index / (rafter_count - 1)
        x = -checked["roof_width_m"] / 2.0 + 0.18 + fraction * (
            checked["roof_width_m"] - 0.36
        )
        wood.add_sloped_y_box(
            x,
            checked["roof_back_y_m"],
            checked["roof_back_z_m"] - 0.07,
            checked["roof_front_y_m"],
            checked["roof_front_z_m"] - 0.07,
            checked["rafter_width_m"],
            checked["rafter_depth_m"],
        )

    roof.add_sloped_y_box(
        0.0,
        checked["roof_back_y_m"],
        checked["roof_back_z_m"],
        checked["roof_front_y_m"],
        checked["roof_front_z_m"],
        checked["roof_width_m"],
        checked["roof_thickness_m"],
    )

    wood_obj = _mesh_object(
        f"{prefix}_wood",
        wood,
        materials["wood"],
        collection,
    )
    roof_obj = _mesh_object(
        f"{prefix}_roof",
        roof,
        materials["roof"],
        collection,
    )
    stone_obj = _mesh_object(
        f"{prefix}_stone",
        stone,
        materials["stone"],
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
    for obj in (wood_obj, roof_obj, stone_obj):
        obj.parent = root
        obj["part_id"] = "wooden_entrance_porch"
        obj["parameters_hash"] = parameters_hash
    return {
        "status": "generated",
        "root": root.name,
        "objects": [wood_obj.name, roof_obj.name, stone_obj.name],
        "dimensions_m": checked["overall_dimensions_m"],
        "landing_board_count": board_count,
        "rafter_count": rafter_count,
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
    parser.add_argument("--wood-material", required=True)
    parser.add_argument("--roof-material", required=True)
    parser.add_argument("--stone-material", required=True)
    parser.add_argument("--prefix", default="SK_wooden_entrance_porch_v1")
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
        result = build_porch(
            parameters,
            args.wood_material,
            args.roof_material,
            args.stone_material,
            prefix=args.prefix,
            collection_name=args.collection,
        )
    except ImportError as exc:
        print(f"Porch generation must run inside Blender: {exc}", file=sys.stderr)
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
