#!/usr/bin/env python3
"""Generate deterministic low-poly climbing vines or a potted plant in Blender."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
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
    component_type = parameters.get("component_type")
    if component_type not in {"climbing_vine", "potted_plant"}:
        raise ValueError("component_type must be climbing_vine or potted_plant")
    width = _number(parameters.get("width_m"), "width_m", 0.1)
    depth = _number(parameters.get("depth_m"), "depth_m", 0.05)
    height = _number(parameters.get("height_m"), "height_m", 0.1)
    seed = _integer(parameters.get("seed", 1), "seed", 0)
    stem_count = _integer(parameters.get("stem_count"), "stem_count", 1)
    leaf_count = _integer(parameters.get("leaf_count"), "leaf_count", 1)
    leaf_width = _number(
        parameters.get("leaf_width_m", 0.055),
        "leaf_width_m",
        0.005,
    )
    leaf_height = _number(
        parameters.get("leaf_height_m", 0.09),
        "leaf_height_m",
        0.005,
    )
    leaf_thickness = _number(
        parameters.get("leaf_thickness_m", 0.006),
        "leaf_thickness_m",
        0.001,
    )
    stem_radius = _number(
        parameters.get("stem_radius_m", 0.008),
        "stem_radius_m",
        0.001,
    )
    if leaf_width >= width or leaf_height >= height:
        raise ValueError("leaf dimensions must fit inside the component")
    if leaf_thickness >= depth:
        raise ValueError("leaf thickness must be smaller than component depth")
    if stem_radius * 2.0 >= min(width, depth):
        raise ValueError("stem diameter is too large for the component")

    pot = parameters.get("pot") or {}
    if component_type == "potted_plant":
        if not isinstance(pot, dict):
            raise ValueError("pot must be an object")
        pot_height = _number(pot.get("height_m"), "pot.height_m", 0.04)
        rim_height = _number(pot.get("rim_height_m"), "pot.rim_height_m", 0.01)
        top_radius = _number(pot.get("top_radius_m"), "pot.top_radius_m", 0.03)
        bottom_radius = _number(
            pot.get("bottom_radius_m"),
            "pot.bottom_radius_m",
            0.02,
        )
        if rim_height >= pot_height:
            raise ValueError("pot rim must be shorter than the pot")
        if top_radius <= bottom_radius:
            raise ValueError("pot must taper outward toward its rim")
        if top_radius * 2.0 > width or top_radius * 2.0 > depth:
            raise ValueError("pot does not fit inside the component footprint")
        if pot_height >= height:
            raise ValueError("pot height must be below total plant height")
        pot_data = {
            "height_m": pot_height,
            "rim_height_m": rim_height,
            "top_radius_m": top_radius,
            "bottom_radius_m": bottom_radius,
        }
    else:
        pot_data = {}

    return {
        "status": "pass",
        "component_type": component_type,
        "width_m": width,
        "depth_m": depth,
        "height_m": height,
        "seed": seed,
        "stem_count": stem_count,
        "leaf_count": leaf_count,
        "leaf_width_m": leaf_width,
        "leaf_height_m": leaf_height,
        "leaf_thickness_m": leaf_thickness,
        "stem_radius_m": stem_radius,
        "pot": pot_data,
    }


class MeshBuilder:
    def __init__(self) -> None:
        self.vertices: list[tuple[float, float, float]] = []
        self.faces: list[tuple[int, ...]] = []

    def add_cylinder_between(
        self,
        start: tuple[float, float, float],
        end: tuple[float, float, float],
        radius: float,
        segments: int = 6,
    ) -> None:
        from mathutils import Vector

        a = Vector(start)
        b = Vector(end)
        direction = b - a
        if direction.length < 1e-6:
            return
        basis_z = direction.normalized()
        helper = Vector((0.0, 0.0, 1.0))
        if abs(basis_z.dot(helper)) > 0.95:
            helper = Vector((0.0, 1.0, 0.0))
        basis_x = basis_z.cross(helper).normalized()
        basis_y = basis_z.cross(basis_x).normalized()
        offset = len(self.vertices)
        for center in (a, b):
            for index in range(segments):
                angle = 2.0 * math.pi * index / segments
                point = (
                    center
                    + basis_x * (math.cos(angle) * radius)
                    + basis_y * (math.sin(angle) * radius)
                )
                self.vertices.append(tuple(point))
        for index in range(segments):
            nxt = (index + 1) % segments
            self.faces.append(
                (
                    offset + index,
                    offset + nxt,
                    offset + segments + nxt,
                    offset + segments + index,
                )
            )
        self.faces.append(tuple(offset + index for index in range(segments - 1, -1, -1)))
        self.faces.append(
            tuple(
                offset + segments + index
                for index in range(segments)
            )
        )

    def add_leaf(
        self,
        center: tuple[float, float, float],
        width: float,
        height: float,
        thickness: float,
        rotation_y: float,
        tilt_x: float = 0.0,
    ) -> None:
        from mathutils import Matrix, Vector

        profile = (
            (0.0, 0.50),
            (0.26, 0.19),
            (0.48, -0.08),
            (0.0, -0.50),
            (-0.48, -0.08),
            (-0.26, 0.19),
        )
        rotation = Matrix.Rotation(rotation_y, 4, "Y") @ Matrix.Rotation(
            tilt_x,
            4,
            "X",
        )
        offset = len(self.vertices)
        for y in (-thickness / 2.0, thickness / 2.0):
            for px, pz in profile:
                point = rotation @ Vector(
                    (px * width, y, pz * height)
                )
                point += Vector(center)
                self.vertices.append(tuple(point))
        count = len(profile)
        self.faces.append(tuple(offset + index for index in range(count)))
        self.faces.append(
            tuple(offset + count + index for index in range(count - 1, -1, -1))
        )
        for index in range(count):
            nxt = (index + 1) % count
            self.faces.append(
                (
                    offset + index,
                    offset + nxt,
                    offset + count + nxt,
                    offset + count + index,
                )
            )

    def add_ring_surface(
        self,
        z0: float,
        z1: float,
        radius0: float,
        radius1: float,
        segments: int,
        close_bottom: bool = True,
        close_top: bool = True,
    ) -> None:
        offset = len(self.vertices)
        for z, radius in ((z0, radius0), (z1, radius1)):
            for index in range(segments):
                angle = 2.0 * math.pi * index / segments
                self.vertices.append(
                    (
                        math.cos(angle) * radius,
                        math.sin(angle) * radius,
                        z,
                    )
                )
        for index in range(segments):
            nxt = (index + 1) % segments
            self.faces.append(
                (
                    offset + index,
                    offset + nxt,
                    offset + segments + nxt,
                    offset + segments + index,
                )
            )
        if close_bottom:
            self.faces.append(
                tuple(offset + index for index in range(segments - 1, -1, -1))
            )
        if close_top:
            self.faces.append(
                tuple(
                    offset + segments + index
                    for index in range(segments)
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
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj


def _material(
    name: str,
    color: tuple[float, float, float, float],
    roughness: float,
) -> Any:
    import bpy

    material = bpy.data.materials.get(name)
    if material is not None:
        return material
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    shader = next(
        node
        for node in material.node_tree.nodes
        if node.type == "BSDF_PRINCIPLED"
    )
    shader.inputs["Base Color"].default_value = color
    shader.inputs["Roughness"].default_value = roughness
    return material


def _stem_paths(
    checked: dict[str, Any],
    rng: random.Random,
    base_z: float,
) -> list[list[tuple[float, float, float]]]:
    width = checked["width_m"]
    depth = checked["depth_m"]
    height = checked["height_m"]
    paths = []
    for stem_index in range(checked["stem_count"]):
        base_x = rng.uniform(-width * 0.36, width * 0.36)
        top_x = base_x + rng.uniform(-width * 0.2, width * 0.2)
        top_z = rng.uniform(
            max(base_z + 0.15, height * 0.55),
            height * 0.97,
        )
        points = []
        for step in range(7):
            ratio = step / 6.0
            x = base_x + (top_x - base_x) * ratio
            x += math.sin(ratio * math.pi * 2.2 + stem_index) * width * 0.035
            z = base_z + (top_z - base_z) * ratio
            y = 0.0 if step == 0 else rng.uniform(-depth * 0.28, -depth * 0.08)
            points.append((x, y, z))
        paths.append(points)
    return paths


def build_vegetation(
    parameters: dict[str, Any],
    prefix: str,
    collection_name: str = "SK_COL_Vegetation",
    replace_existing: bool = True,
) -> dict[str, Any]:
    import bpy

    checked = validate_parameters(parameters)
    rng = random.Random(checked["seed"])
    collection = bpy.data.collections.get(collection_name)
    if collection is None:
        collection = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(collection)
    if replace_existing:
        for obj in list(bpy.data.objects):
            if obj.name.startswith(prefix):
                bpy.data.objects.remove(obj, do_unlink=True)

    leaf_material = _material(
        "MAT_vegetation_MutedGreenLeaves_v1",
        (0.10, 0.23, 0.075, 1.0),
        0.72,
    )
    stem_material = _material(
        "MAT_vegetation_DarkWoodyStem_v1",
        (0.13, 0.075, 0.035, 1.0),
        0.85,
    )
    pot_material = _material(
        "MAT_porch_planter_Terracotta_v1",
        (0.30, 0.105, 0.045, 1.0),
        0.78,
    )
    soil_material = _material(
        "MAT_porch_planter_Soil_v1",
        (0.07, 0.035, 0.018, 1.0),
        0.92,
    )

    objects = []
    if checked["component_type"] == "potted_plant":
        pot = checked["pot"]
        pot_builder = MeshBuilder()
        pot_builder.add_ring_surface(
            0.0,
            pot["height_m"],
            pot["bottom_radius_m"],
            pot["top_radius_m"],
            20,
            close_bottom=True,
            close_top=True,
        )
        pot_builder.add_ring_surface(
            pot["height_m"] - pot["rim_height_m"],
            pot["height_m"] + pot["rim_height_m"] * 0.35,
            pot["top_radius_m"] * 0.98,
            pot["top_radius_m"] * 1.06,
            20,
            close_bottom=True,
            close_top=True,
        )
        objects.append(
            _mesh_object(
                f"{prefix}_pot",
                pot_builder,
                pot_material,
                collection,
            )
        )
        soil = MeshBuilder()
        soil.add_ring_surface(
            pot["height_m"] - 0.015,
            pot["height_m"] + 0.005,
            pot["top_radius_m"] * 0.88,
            pot["top_radius_m"] * 0.88,
            20,
            close_bottom=True,
            close_top=True,
        )
        objects.append(
            _mesh_object(
                f"{prefix}_soil",
                soil,
                soil_material,
                collection,
            )
        )
        stem_base_z = pot["height_m"]
        width_scale = checked["width_m"] * 0.55
        depth_scale = checked["depth_m"] * 0.55
    else:
        stem_base_z = 0.0
        width_scale = checked["width_m"]
        depth_scale = checked["depth_m"]

    paths = _stem_paths(checked, rng, stem_base_z)
    stems = MeshBuilder()
    for path in paths:
        for start, end in zip(path, path[1:]):
            stems.add_cylinder_between(
                start,
                end,
                checked["stem_radius_m"],
                segments=6,
            )
    leaves = MeshBuilder()
    leaf_total = checked["leaf_count"]
    for index in range(leaf_total):
        path = paths[index % len(paths)]
        anchor = path[1 + (index * 3) % (len(path) - 1)]
        center_x = max(
            -width_scale / 2.0 + checked["leaf_width_m"] / 2.0,
            min(
                width_scale / 2.0 - checked["leaf_width_m"] / 2.0,
                anchor[0] + rng.uniform(-width_scale * 0.18, width_scale * 0.18),
            ),
        )
        center_z = max(
            stem_base_z + checked["leaf_height_m"] / 2.0,
            min(
                checked["height_m"] - checked["leaf_height_m"] / 2.0,
                anchor[2] + rng.uniform(-0.08, 0.08),
            ),
        )
        center_y = max(
            -depth_scale + checked["leaf_thickness_m"],
            min(-0.005, anchor[1] - rng.uniform(0.0, 0.035)),
        )
        stems.add_cylinder_between(
            anchor,
            (center_x, center_y, center_z),
            checked["stem_radius_m"] * 0.45,
            segments=4,
        )
        leaves.add_leaf(
            (center_x, center_y, center_z),
            checked["leaf_width_m"] * rng.uniform(0.8, 1.18),
            checked["leaf_height_m"] * rng.uniform(0.8, 1.18),
            checked["leaf_thickness_m"],
            rng.uniform(-math.pi, math.pi),
            rng.uniform(-0.22, 0.22),
        )
    stem_object = _mesh_object(
        f"{prefix}_stems",
        stems,
        stem_material,
        collection,
    )
    objects.append(stem_object)
    leaf_object = _mesh_object(
        f"{prefix}_leaves",
        leaves,
        leaf_material,
        collection,
    )
    objects.append(leaf_object)

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
    for obj in objects:
        obj.parent = root
        obj["parameters_hash"] = parameters_hash
        obj["part_id"] = (
            "porch_planter_primary"
            if checked["component_type"] == "potted_plant"
            else "climbing_vine_module"
        )
    for obj in objects:
        obj.data.calc_loop_triangles()
    return {
        "status": "generated",
        "root": root.name,
        "objects": [obj.name for obj in objects],
        "dimensions_m": [
            checked["width_m"],
            checked["depth_m"],
            checked["height_m"],
        ],
        "triangles": sum(len(obj.data.loop_triangles) for obj in objects),
        "seed": checked["seed"],
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
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--collection", default="SK_COL_Vegetation")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--output-blend", type=Path)
    args = parser.parse_args(_argument_argv(argv))
    project = args.project.expanduser().resolve() if args.project else Path.cwd()
    parameter_path = args.parameters
    if not parameter_path.is_absolute():
        parameter_path = project / parameter_path
    parameters = _read_json(parameter_path)
    checked = validate_parameters(parameters)
    if args.validate_only:
        print(json.dumps(checked, ensure_ascii=False, indent=2))
        return 0
    try:
        result = build_vegetation(
            parameters,
            args.prefix,
            collection_name=args.collection,
        )
    except ImportError as exc:
        print(f"Vegetation generation must run inside Blender: {exc}", file=sys.stderr)
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
