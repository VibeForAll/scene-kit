#!/usr/bin/env python3
"""Generate the compact gabled timber entrance hood identified in the reference."""

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
    width = _number(parameters.get("width_m"), "width_m", 1.0)
    if width > 2.0:
        raise ValueError("entrance hood is too wide for the reference porch")
    depth = _number(parameters.get("depth_m"), "depth_m", 0.35)
    platform_top = _number(
        parameters.get("platform_top_z_m"),
        "platform_top_z_m",
        0.0,
    )
    landing_depth = _number(
        parameters.get("landing_depth_m"),
        "landing_depth_m",
        0.15,
    )
    landing_thickness = _number(
        parameters.get("landing_thickness_m"),
        "landing_thickness_m",
        0.06,
    )
    landing_back = _number(
        parameters.get("landing_back_y_m"),
        "landing_back_y_m",
    )
    board_count = _integer(
        parameters.get("landing_board_count"),
        "landing_board_count",
        2,
    )
    wall_y = _number(parameters.get("wall_y_m"), "wall_y_m")
    roof_width = _number(
        parameters.get("roof_width_m"),
        "roof_width_m",
        width,
    )
    roof_back = _number(
        parameters.get("roof_back_y_m"),
        "roof_back_y_m",
    )
    roof_front = _number(
        parameters.get("roof_front_y_m"),
        "roof_front_y_m",
    )
    eave = _number(parameters.get("eave_z_m"), "eave_z_m", 2.8)
    ridge = _number(parameters.get("ridge_z_m"), "ridge_z_m")
    thickness = _number(
        parameters.get("roof_thickness_m"),
        "roof_thickness_m",
        0.03,
    )
    ridge_width = _number(
        parameters.get("ridge_width_m"),
        "ridge_width_m",
        0.03,
    )
    ridge_height = _number(
        parameters.get("ridge_height_m"),
        "ridge_height_m",
        0.02,
    )
    fascia_width = _number(
        parameters.get("fascia_width_m"),
        "fascia_width_m",
        0.03,
    )
    fascia_height = _number(
        parameters.get("fascia_height_m"),
        "fascia_height_m",
        0.04,
    )
    bracket_width = _number(
        parameters.get("bracket_width_m"),
        "bracket_width_m",
        0.04,
    )
    bracket_thickness = _number(
        parameters.get("bracket_thickness_m"),
        "bracket_thickness_m",
        0.04,
    )
    bracket_wall_z = _number(
        parameters.get("bracket_wall_z_m"),
        "bracket_wall_z_m",
        platform_top + 0.4,
    )
    bracket_tip_y = _number(
        parameters.get("bracket_tip_y_m"),
        "bracket_tip_y_m",
        roof_front,
    )
    columns = parameters.get("columns")
    if not isinstance(columns, dict):
        raise ValueError("columns must be an object")
    column_count = _integer(columns.get("count"), "columns.count", 1)
    if column_count != 2:
        raise ValueError("entrance hood requires exactly two columns")
    column_width = _number(
        columns.get("width_m"),
        "columns.width_m",
        0.05,
    )
    column_x = _number(columns.get("x_m"), "columns.x_m", 0.45)
    column_y = _number(
        columns.get("front_y_m"),
        "columns.front_y_m",
    )
    column_base = _number(
        columns.get("base_z_m"),
        "columns.base_z_m",
        0.0,
    )
    column_top = _number(
        columns.get("top_z_m"),
        "columns.top_z_m",
        column_base + 0.5,
    )
    column_base_block = _number(
        columns.get("base_block_height_m"),
        "columns.base_block_height_m",
        0.01,
    )
    column_capital = _number(
        columns.get("capital_height_m"),
        "columns.capital_height_m",
        0.01,
    )
    triangular = parameters.get("triangular_window")
    if not isinstance(triangular, dict):
        raise ValueError("triangular_window must be an object")
    triangle_base_width = _number(
        triangular.get("base_width_m"),
        "triangular_window.base_width_m",
        0.15,
    )
    triangle_base_z = _number(
        triangular.get("base_z_m"),
        "triangular_window.base_z_m",
        platform_top,
    )
    triangle_apex_z = _number(
        triangular.get("apex_z_m"),
        "triangular_window.apex_z_m",
        triangle_base_z + 0.03,
    )
    pane_thickness = _number(
        triangular.get("pane_thickness_m"),
        "triangular_window.pane_thickness_m",
        0.002,
    )
    frame_width = _number(
        triangular.get("frame_width_m"),
        "triangular_window.frame_width_m",
        0.008,
    )
    glass_inset = _number(
        triangular.get("glass_inset_m"),
        "triangular_window.glass_inset_m",
        0.001,
    )
    if depth > 1.1:
        raise ValueError("entrance hood projection is too deep")
    if roof_width < 1.18:
        raise ValueError("roof_width_m must cover the entrance surround")
    if roof_front >= roof_back:
        raise ValueError("roof_front_y_m must be less than roof_back_y_m")
    if ridge <= eave:
        raise ValueError("ridge_z_m must be above eave_z_m")
    if bracket_tip_y > roof_back or bracket_tip_y < roof_front:
        raise ValueError("bracket tip must stay under the hood roof")
    if bracket_wall_z >= eave:
        raise ValueError("wall bracket starts too close to the eave")
    if column_x - column_width / 2.0 <= 0.43 + 0.05:
        raise ValueError("porch columns intrude into the door clear width")
    if column_x + column_width / 2.0 > width / 2.0:
        raise ValueError("porch columns exceed the landing width")
    if abs(column_base - platform_top) > 1e-6:
        raise ValueError("porch columns must stand on the landing")
    if column_top >= eave - thickness:
        raise ValueError("porch columns penetrate the hood roof")
    if triangle_base_z <= 2.77:
        raise ValueError("triangular window must start above the door surround")
    if triangle_apex_z >= ridge:
        raise ValueError("triangular window must stay below the ridge")
    eave_half = roof_width / 2.0
    gable_half_width_at_base = eave_half * (
        (ridge - triangle_base_z) / (ridge - eave)
    )
    if triangle_base_width / 2.0 > gable_half_width_at_base:
        raise ValueError("triangular window is too wide for the gable face")
    landing_front = landing_back - landing_depth
    if abs(landing_front - (-3.82)) > 0.02:
        raise ValueError("landing front must meet the top stair tread")
    material = parameters.get("material")
    if not isinstance(material, dict):
        raise ValueError("material must be an object")
    for key in ("wood_mapping_scale", "slate_mapping_scale"):
        values = material.get(key)
        if (
            not isinstance(values, list)
            or len(values) != 3
            or not all(
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and value > 0
                for value in values
            )
        ):
            raise ValueError(f"material.{key} must contain 3 positive numbers")
    return {
        "status": "pass",
        "width_m": width,
        "depth_m": depth,
        "platform_top_z_m": platform_top,
        "landing_depth_m": landing_depth,
        "landing_thickness_m": landing_thickness,
        "landing_back_y_m": landing_back,
        "landing_front_y_m": landing_front,
        "landing_board_count": board_count,
        "wall_y_m": wall_y,
        "roof_width_m": roof_width,
        "roof_back_y_m": roof_back,
        "roof_front_y_m": roof_front,
        "eave_z_m": eave,
        "ridge_z_m": ridge,
        "roof_thickness_m": thickness,
        "ridge_width_m": ridge_width,
        "ridge_height_m": ridge_height,
        "fascia_width_m": fascia_width,
        "fascia_height_m": fascia_height,
        "eave_x_m": eave_half,
        "bracket_width_m": bracket_width,
        "bracket_thickness_m": bracket_thickness,
        "bracket_wall_z_m": bracket_wall_z,
        "bracket_tip_y_m": bracket_tip_y,
        "columns": {
            "count": column_count,
            "width_m": column_width,
            "x_m": column_x,
            "front_y_m": column_y,
            "base_z_m": column_base,
            "top_z_m": column_top,
            "base_block_height_m": column_base_block,
            "capital_height_m": column_capital,
        },
        "triangular_window": {
            "base_width_m": triangle_base_width,
            "base_z_m": triangle_base_z,
            "apex_z_m": triangle_apex_z,
            "pane_thickness_m": pane_thickness,
            "frame_width_m": frame_width,
            "glass_inset_m": glass_inset,
        },
        "overall_dimensions_m": [
            roof_width,
            abs((roof_front - 0.03) - landing_back),
            (
                ridge
                + ridge_height
                - (
                    platform_top
                    - landing_thickness
                    - 0.1
                )
            ),
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
        ht = thickness / 2.0
        offset = len(self.vertices)
        self.vertices.extend(
            [
                (x0, y0, z0 - ht),
                (x1, y0, z1 - ht),
                (x1, y1, z1 - ht),
                (x0, y1, z0 - ht),
                (x0, y0, z0 + ht),
                (x1, y0, z1 + ht),
                (x1, y1, z1 + ht),
                (x0, y1, z0 + ht),
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

    def add_gable_prism(
        self,
        eave_x: float,
        eave_z: float,
        ridge_z: float,
        y0: float,
        y1: float,
    ) -> None:
        offset = len(self.vertices)
        self.vertices.extend(
            [
                (-eave_x, y0, eave_z),
                (eave_x, y0, eave_z),
                (0.0, y0, ridge_z),
                (-eave_x, y1, eave_z),
                (eave_x, y1, eave_z),
                (0.0, y1, ridge_z),
            ]
        )
        self.faces.extend(
            [
                (offset + 0, offset + 2, offset + 1),
                (offset + 3, offset + 4, offset + 5),
                (offset + 0, offset + 1, offset + 4, offset + 3),
                (offset + 1, offset + 2, offset + 5, offset + 4),
                (offset + 2, offset + 0, offset + 3, offset + 5),
            ]
        )

    def add_triangle_prism(
        self,
        base_width: float,
        base_z: float,
        apex_z: float,
        y0: float,
        y1: float,
    ) -> None:
        half = base_width / 2.0
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


def build_hood(
    parameters: dict[str, Any],
    wood_material_name: str,
    roof_material_name: str,
    glass_material_name: str,
    prefix: str = "SK_wooden_entrance_porch_v2",
    collection_name: str = "SK_COL_Structure",
    replace_existing: bool = True,
) -> dict[str, Any]:
    import bpy

    checked = validate_parameters(parameters)
    wood_material = bpy.data.materials.get(wood_material_name)
    roof_material = bpy.data.materials.get(roof_material_name)
    glass_material = bpy.data.materials.get(glass_material_name)
    if wood_material is None:
        raise ValueError(f"Material not found: {wood_material_name}")
    if roof_material is None:
        raise ValueError(f"Material not found: {roof_material_name}")
    if glass_material is None:
        raise ValueError(f"Material not found: {glass_material_name}")
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
    glass = MeshBuilder()
    width = checked["width_m"]
    landing_depth = checked["landing_depth_m"]
    landing_back = checked["landing_back_y_m"]
    landing_front = checked["landing_front_y_m"]
    platform_top = checked["platform_top_z_m"]
    count = checked["landing_board_count"]
    gap = 0.006
    board_width = (width - gap * (count - 1)) / count
    for index in range(count):
        x = -width / 2.0 + board_width / 2.0 + index * (
            board_width + gap
        )
        wood.add_box(
            (
                x,
                (landing_back + landing_front) / 2.0,
                platform_top - checked["landing_thickness_m"] / 2.0,
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
            landing_front + 0.04,
            platform_top - checked["landing_thickness_m"] - 0.05,
        ),
        (width, 0.08, 0.1),
    )

    roof_back = checked["roof_back_y_m"]
    roof_front = checked["roof_front_y_m"]
    eave_x = checked["eave_x_m"]
    eave_z = checked["eave_z_m"]
    ridge_z = checked["ridge_z_m"]
    roof_thickness = checked["roof_thickness_m"]
    roof.add_sloped_x_box(
        -eave_x,
        eave_z,
        0.0,
        ridge_z,
        roof_back,
        roof_front,
        roof_thickness,
    )
    roof.add_sloped_x_box(
        0.0,
        ridge_z,
        eave_x,
        eave_z,
        roof_back,
        roof_front,
        roof_thickness,
    )
    wood.add_gable_prism(
        eave_x,
        eave_z,
        ridge_z,
        roof_front - 0.03,
        roof_front + 0.03,
    )
    fascia_y = roof_front + 0.025
    wood.add_sloped_x_box(
        -eave_x,
        eave_z - 0.02,
        0.0,
        ridge_z - 0.02,
        fascia_y - checked["fascia_width_m"] / 2.0,
        fascia_y + checked["fascia_width_m"] / 2.0,
        checked["fascia_height_m"],
    )
    wood.add_sloped_x_box(
        0.0,
        ridge_z - 0.02,
        eave_x,
        eave_z - 0.02,
        fascia_y - checked["fascia_width_m"] / 2.0,
        fascia_y + checked["fascia_width_m"] / 2.0,
        checked["fascia_height_m"],
    )
    wood.add_box(
        (
            0.0,
            (roof_back + roof_front) / 2.0,
            ridge_z + checked["ridge_height_m"] / 2.0,
        ),
        (
            checked["ridge_width_m"],
            abs(roof_front - roof_back),
            checked["ridge_height_m"],
        ),
    )
    for x in (-width * 0.36, width * 0.36):
        wood.add_sloped_y_box(
            x,
            checked["wall_y_m"],
            checked["bracket_wall_z_m"],
            checked["bracket_tip_y_m"],
            eave_z - 0.04,
            checked["bracket_width_m"],
            checked["bracket_thickness_m"],
        )
    wood.add_box(
        (0.0, roof_front + 0.08, eave_z - 0.03),
        (width + 0.08, 0.12, 0.1),
    )
    columns = checked["columns"]
    roof_underside_height = lambda x: (
        eave_z
        + (eave_x - abs(x)) / eave_x * (ridge_z - eave_z)
        - roof_thickness / 2.0
    )
    for x in (-columns["x_m"], columns["x_m"]):
        wood.add_box(
            (
                x,
                columns["front_y_m"],
                (columns["base_z_m"] + columns["top_z_m"]) / 2.0,
            ),
            (
                columns["width_m"],
                columns["width_m"],
                columns["top_z_m"] - columns["base_z_m"],
            ),
        )
        shoe_half_span = 0.08
        shoe_thickness = 0.07
        roof_shoe_top_left = roof_underside_height(
            abs(x) - shoe_half_span
        )
        roof_shoe_top_right = roof_underside_height(
            abs(x) + shoe_half_span
        )
        wood.add_sloped_x_box(
            x - shoe_half_span,
            roof_shoe_top_left - shoe_thickness / 2.0,
            x + shoe_half_span,
            roof_shoe_top_right - shoe_thickness / 2.0,
            columns["front_y_m"] - 0.06,
            columns["front_y_m"] + 0.06,
            shoe_thickness,
        )
        wood.add_box(
            (
                x,
                columns["front_y_m"],
                columns["base_z_m"] + columns["base_block_height_m"] / 2.0,
            ),
            (
                columns["width_m"] * 1.45,
                columns["width_m"] * 1.45,
                columns["base_block_height_m"],
            ),
        )
        wood.add_box(
            (
                x,
                columns["front_y_m"],
                columns["top_z_m"] - columns["capital_height_m"] / 2.0,
            ),
            (
                columns["width_m"] * 1.4,
                columns["width_m"] * 1.4,
                columns["capital_height_m"],
            ),
        )
    wood.add_box(
        (
            0.0,
            columns["front_y_m"],
            columns["top_z_m"] + 0.035,
        ),
        (columns["x_m"] * 2.0 + columns["width_m"], 0.12, 0.1),
    )
    triangle = checked["triangular_window"]
    pane_y = roof_front - 0.03 - triangle["pane_thickness_m"] / 2.0
    glass.add_triangle_prism(
        triangle["base_width_m"] - triangle["glass_inset_m"] * 2.0,
        triangle["base_z_m"] + triangle["glass_inset_m"],
        triangle["apex_z_m"] - triangle["glass_inset_m"],
        pane_y - triangle["pane_thickness_m"] / 2.0,
        pane_y + triangle["pane_thickness_m"] / 2.0,
    )
    frame_y0 = pane_y - triangle["pane_thickness_m"]
    frame_y1 = pane_y + triangle["pane_thickness_m"]
    wood.add_box(
        (
            0.0,
            pane_y,
            triangle["base_z_m"] + triangle["frame_width_m"] / 2.0,
        ),
        (
            triangle["base_width_m"],
            triangle["frame_width_m"],
            triangle["frame_width_m"],
        ),
    )
    wood.add_sloped_x_box(
        -triangle["base_width_m"] / 2.0,
        triangle["base_z_m"],
        0.0,
        triangle["apex_z_m"],
        frame_y0,
        frame_y1,
        triangle["frame_width_m"],
    )
    wood.add_sloped_x_box(
        0.0,
        triangle["apex_z_m"],
        triangle["base_width_m"] / 2.0,
        triangle["base_z_m"],
        frame_y0,
        frame_y1,
        triangle["frame_width_m"],
    )
    wood.add_box(
        (
            0.0,
            pane_y,
            (triangle["base_z_m"] + triangle["apex_z_m"]) / 2.0,
        ),
        (
            triangle["frame_width_m"],
            triangle["frame_width_m"],
            triangle["apex_z_m"] - triangle["base_z_m"],
        ),
    )

    wood_obj = _mesh_object(
        f"{prefix}_wood",
        wood,
        wood_material,
        collection,
    )
    roof_obj = _mesh_object(
        f"{prefix}_roof",
        roof,
        roof_material,
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
    for obj in (wood_obj, roof_obj, glass_obj):
        obj.parent = root
        obj["part_id"] = "wooden_entrance_porch"
        obj["parameters_hash"] = parameters_hash
    return {
        "status": "generated",
        "root": root.name,
        "objects": [wood_obj.name, roof_obj.name, glass_obj.name],
        "dimensions_m": checked["overall_dimensions_m"],
        "eave_z_m": eave_z,
        "ridge_z_m": ridge_z,
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
    parser.add_argument("--glass-material", required=True)
    parser.add_argument("--prefix", default="SK_wooden_entrance_porch_v2")
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
        result = build_hood(
            parameters,
            args.wood_material,
            args.roof_material,
            args.glass_material,
            prefix=args.prefix,
            collection_name=args.collection,
        )
    except ImportError as exc:
        print(f"Entrance hood generation must run inside Blender: {exc}", file=sys.stderr)
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
