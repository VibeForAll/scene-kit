#!/usr/bin/env python3
"""Generate deterministic organic climbing vines or potted plants in Blender.

Revision 2 (skill 7.23) replaces the abstract low-poly v1 style (flat diamond
blades on straight stick cylinders, single muted green) with a vine-grade
organic builder:

* continuous curved tubes with base-to-tip taper and hierarchical branching;
* dense small curved leaves (cupped, bent, randomly oriented, petiole linked);
* multi-tone green materials plus yellow-green terminal buds;
* deterministic seeded output and explicit organic quality gates.

The CLI and the v1 parameter contract stay valid; new organic parameters are
optional. The module imports bpy lazily so validate_parameters stays testable
outside Blender.
"""

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
    maximum: float | None = None,
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
    if maximum is not None and result > maximum:
        raise ValueError(f"{name} must be <= {maximum}")
    return result


def _integer(value: Any, name: str, minimum: int, maximum: int | None = None) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{name} must be an integer")
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    if maximum is not None and value > maximum:
        raise ValueError(f"{name} must be <= {maximum}")
    return value


def validate_parameters(parameters: dict[str, Any]) -> dict[str, Any]:
    component_type = parameters.get("component_type")
    if component_type not in {"climbing_vine", "potted_plant"}:
        raise ValueError("component_type must be climbing_vine or potted_plant")
    width = _number(parameters.get("width_m"), "width_m", 0.1)
    depth = _number(parameters.get("depth_m"), "depth_m", 0.05)
    height = _number(parameters.get("height_m"), "height_m", 0.1)
    seed = _integer(parameters.get("seed", 1), "seed", 0)
    stem_count = _integer(parameters.get("stem_count"), "stem_count", 1, 24)
    leaf_count = _integer(parameters.get("leaf_count"), "leaf_count", 1, 20000)
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

    # Organic (7.23) options. Zero means "derive automatically from the envelope".
    lateral_branches = _integer(
        parameters.get("lateral_branches", 0),
        "lateral_branches",
        0,
        8,
    )
    leaf_density = _number(
        parameters.get("leaf_density", 1.0),
        "leaf_density",
        0.5,
        2.0,
    )
    leaf_curl = parameters.get("leaf_curl_m")
    leaf_curl = (
        _number(leaf_curl, "leaf_curl_m", 0.0, height)
        if leaf_curl is not None
        else leaf_height * 0.22
    )
    leaf_cup = parameters.get("leaf_cup_m")
    leaf_cup = (
        _number(leaf_cup, "leaf_cup_m", 0.0, width)
        if leaf_cup is not None
        else leaf_width * 0.22
    )

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
        "lateral_branches": lateral_branches,
        "leaf_density": leaf_density,
        "leaf_curl_m": leaf_curl,
        "leaf_cup_m": leaf_cup,
        "pot": pot_data,
    }


class MeshBuilder:
    """Accumulate meshes with per-face material indices."""

    def __init__(self) -> None:
        self.vertices: list[tuple[float, float, float]] = []
        self.faces: list[tuple[int, ...]] = []
        self.face_materials: list[int] = []
        self.smooth_faces: set[int] = set()

    def _add_face(self, vertices: tuple[int, ...], material: int, smooth: bool) -> None:
        self.faces.append(vertices)
        self.face_materials.append(material)
        if smooth:
            self.smooth_faces.add(len(self.faces) - 1)

    def add_ring_surface(
        self,
        z0: float,
        z1: float,
        radius0: float,
        radius1: float,
        segments: int,
        material: int = 0,
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
            self._add_face(
                (
                    offset + index,
                    offset + nxt,
                    offset + segments + nxt,
                    offset + segments + index,
                ),
                material,
                True,
            )
        if close_bottom:
            self._add_face(
                tuple(offset + index for index in range(segments - 1, -1, -1)),
                material,
                False,
            )
        if close_top:
            self._add_face(
                tuple(
                    offset + segments + index
                    for index in range(segments)
                ),
                material,
                False,
            )

    def add_tube(
        self,
        points: list,
        radii: list[float],
        segments: int,
        material: int = 0,
        cap_ends: bool = True,
    ) -> None:
        """Smooth tapered tube along a curved path with parallel-transport frames."""
        from mathutils import Vector

        pts = [Vector(p) for p in points]
        if len(pts) < 2:
            return
        tangents = []
        for index, point in enumerate(pts):
            if index == 0:
                tangent = (pts[1] - point).normalized()
            elif index == len(pts) - 1:
                tangent = (point - pts[index - 1]).normalized()
            else:
                tangent = (pts[index + 1] - pts[index - 1]).normalized()
            tangents.append(tangent)
        helper = Vector((0.0, 0.0, 1.0))
        if abs(tangents[0].dot(helper)) > 0.9:
            helper = Vector((0.0, 1.0, 0.0))
        normal = tangents[0].cross(helper).normalized()
        frames = []
        for tangent in tangents:
            normal = (normal - tangent * normal.dot(tangent)).normalized()
            binormal = tangent.cross(normal).normalized()
            frames.append((normal, binormal))

        ring_offsets = []
        for point, radius, (normal, binormal) in zip(pts, radii, frames):
            offset = len(self.vertices)
            ring_offsets.append(offset)
            for index in range(segments):
                angle = 2.0 * math.pi * index / segments
                vertex = (
                    point
                    + normal * (math.cos(angle) * radius)
                    + binormal * (math.sin(angle) * radius)
                )
                self.vertices.append(tuple(vertex))
        for ring in range(len(pts) - 1):
            base_a = ring_offsets[ring]
            base_b = ring_offsets[ring + 1]
            for index in range(segments):
                nxt = (index + 1) % segments
                self._add_face(
                    (
                        base_a + index,
                        base_a + nxt,
                        base_b + nxt,
                        base_b + index,
                    ),
                    material,
                    True,
                )
        if cap_ends:
            start_center = len(self.vertices)
            self.vertices.append(tuple(pts[0]))
            end_center = len(self.vertices)
            self.vertices.append(tuple(pts[-1]))
            first = ring_offsets[0]
            last = ring_offsets[-1]
            for index in range(segments):
                nxt = (index + 1) % segments
                self._add_face(
                    (start_center, first + nxt, first + index),
                    material,
                    False,
                )
                self._add_face(
                    (end_center, last + index, last + nxt),
                    material,
                    False,
                )

    def add_leaf_blade(
        self,
        base: tuple[float, float, float],
        basis: tuple,
        length: float,
        width: float,
        curl: float,
        cup: float,
        material: int,
        length_segments: int = 8,
        width_segments: int = 6,
    ) -> None:
        """Curved lanceolate blade; local +Y runs from petiole base to tip."""
        from mathutils import Matrix, Vector

        x_axis, y_axis, z_axis = (Vector(v) for v in basis)
        grid = []
        for i in range(length_segments + 1):
            t = i / length_segments
            half_width = (
                width
                * 0.5
                * (math.sin(math.pi * t ** 0.72) ** 0.9)
                * (1.0 - 0.22 * t)
            )
            center_z = curl * math.sin(math.pi * t)
            row = []
            for j in range(width_segments + 1):
                s = -1.0 + 2.0 * j / width_segments
                local = Vector(
                    (
                        s * half_width,
                        length * t,
                        center_z + cup * s * s * math.copysign(1.0, cup or 1.0),
                    )
                )
                world = (
                    Vector(base)
                    + x_axis * local.x
                    + y_axis * local.y
                    + z_axis * local.z
                )
                row.append(len(self.vertices))
                self.vertices.append(tuple(world))
            grid.append(row)
        for i in range(length_segments):
            for j in range(width_segments):
                self._add_face(
                    (grid[i][j], grid[i][j + 1], grid[i + 1][j + 1]),
                    material,
                    True,
                )
                self._add_face(
                    (grid[i][j], grid[i + 1][j + 1], grid[i + 1][j]),
                    material,
                    True,
                )


def _mesh_object(
    name: str,
    builder: MeshBuilder,
    materials: list,
    collection,
    recalc_normals: bool = True,
) -> Any:
    import bmesh
    import bpy

    mesh = bpy.data.meshes.new(f"MESH_{name}")
    mesh.from_pydata(builder.vertices, [], builder.faces)
    mesh.update()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.00005)
    if recalc_normals:
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    for material in materials:
        mesh.materials.append(material)
    for index, polygon in enumerate(mesh.polygons):
        polygon.material_index = builder.face_materials[index]
        polygon.use_smooth = index in builder.smooth_faces
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


def _material(name: str, color: tuple[float, float, float, float], roughness: float) -> Any:
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
    for input_name, value in (
        ("Subsurface Weight", 0.05),
        ("Specular IOR Level", 0.22),
    ):
        if input_name in shader.inputs:
            try:
                shader.inputs[input_name].default_value = value
            except (TypeError, ValueError):
                pass
    return material

# ---------------------------------------------------------------------------
# Organic branch network
# ---------------------------------------------------------------------------


class BranchPath:
    def __init__(self, points, radii, kind):
        self.points = points
        self.radii = radii
        self.kind = kind

    @property
    def tip(self):
        return self.points[-1]


def _grow_path(
    rng: random.Random,
    start,
    init_direction,
    steps: int,
    step_length: float,
    up_bias: float,
    noise_weight: float,
    bounds: dict,
    radius0: float,
    radius1: float,
) -> BranchPath:
    from mathutils import Vector

    points = [Vector(start)]
    direction = Vector(init_direction).normalized()
    for _ in range(steps):
        wander = Vector(
            (
                rng.uniform(-1.0, 1.0),
                rng.uniform(-1.0, 1.0),
                rng.uniform(-0.4, 0.7),
            )
        )
        direction = (
            direction * 0.68
            + Vector((0.0, 0.0, 1.0)) * up_bias
            + wander * noise_weight
        ).normalized()
        nxt = points[-1] + direction * step_length
        for axis, limit in ((0, bounds["x"]), (1, bounds["y"])):
            if abs(nxt[axis]) > limit:
                nxt[axis] = math.copysign(limit, nxt[axis])
                direction[axis] = -direction[axis] * 0.6
        if nxt.z > bounds["z_max"]:
            nxt.z = bounds["z_max"]
            direction.z = -abs(direction.z) * 0.3
        if nxt.z < bounds["z_min"]:
            nxt.z = bounds["z_min"]
            direction.z = abs(direction.z)
        points.append(nxt)
    radii = [
        radius0 + (radius1 - radius0) * index / steps
        for index in range(steps + 1)
    ]
    return BranchPath(points, radii, "branch")


def _branch_network(checked: dict, rng: random.Random, base_z: float) -> list[BranchPath]:
    from mathutils import Vector

    is_pot = checked["component_type"] == "potted_plant"
    width = checked["width_m"]
    depth = checked["depth_m"]
    height = checked["height_m"]
    margin_x = width * 0.04
    margin_y = depth * 0.08
    bounds = {
        "x": max(width * 0.5 - margin_x, leaf_guard(checked, "x")),
        "y": max(depth * 0.5 - margin_y, leaf_guard(checked, "y")),
        "z_min": base_z,
        "z_max": height - checked["leaf_height_m"] * 0.4,
    }
    paths: list[BranchPath] = []
    base_radius = checked["stem_radius_m"]

    for stem_index in range(checked["stem_count"]):
        if is_pot:
            base_angle = rng.uniform(0.0, 2.0 * math.pi)
            base_r = rng.uniform(0.0, checked["pot"]["top_radius_m"] * 0.5)
            start = (
                math.cos(base_angle) * base_r,
                math.sin(base_angle) * base_r,
                base_z,
            )
            lean = rng.uniform(0.2, 0.45)
            height_fraction = rng.uniform(0.62, 0.95)
            up_bias = 0.42
            noise = 0.22
        else:
            start = (
                rng.uniform(-0.38, 0.38) * width,
                rng.uniform(-0.12, 0.12) * depth,
                base_z,
            )
            lean = rng.uniform(0.05, 0.2)
            height_fraction = rng.uniform(0.85, 1.0)
            up_bias = 0.55
            noise = 0.16
        azimuth = rng.uniform(0.0, 2.0 * math.pi)
        init_direction = Vector(
            (
                math.cos(azimuth) * math.sin(lean),
                math.sin(azimuth) * math.sin(lean),
                math.cos(lean),
            )
        )
        target_height = (height - base_z) * height_fraction
        steps = 9
        main = _grow_path(
            rng,
            start,
            init_direction,
            steps,
            target_height / steps,
            up_bias,
            noise,
            bounds,
            base_radius * rng.uniform(0.85, 1.15),
            base_radius * 0.28,
        )
        main.kind = "main"
        paths.append(main)

        lateral_target = checked["lateral_branches"]
        if lateral_target <= 0:
            lateral_target = rng.randint(2, 3) if is_pot else rng.randint(2, 4)
        node_count = len(main.points) - 1
        attach_slots = [
            int(round(fraction * node_count))
            for fraction in (0.38, 0.55, 0.72, 0.86)
        ]
        rng.shuffle(attach_slots)
        for lateral_index in range(min(lateral_target, len(attach_slots))):
            node_index = attach_slots[lateral_index]
            anchor = main.points[node_index]
            parent_tangent = (
                main.points[min(node_index + 1, node_count)]
                - main.points[max(node_index - 1, 0)]
            ).normalized()
            side = -1.0 if lateral_index % 2 == 0 else 1.0
            lateral_azimuth = azimuth + side * rng.uniform(0.85, 1.55) + rng.uniform(-0.25, 0.25)
            outward = Vector(
                (
                    math.cos(lateral_azimuth),
                    math.sin(lateral_azimuth),
                    0.0,
                )
            )
            lateral_direction = (
                parent_tangent * 0.35 + outward * 0.75 + Vector((0, 0, 0.35))
            ).normalized()
            parent_length = sum(
                (main.points[i + 1] - main.points[i]).length
                for i in range(node_count)
            )
            lateral_length = parent_length * rng.uniform(0.3, 0.45)
            lateral_steps = 5
            attach_radius = main.radii[node_index]
            lateral = _grow_path(
                rng,
                anchor,
                lateral_direction,
                lateral_steps,
                lateral_length / lateral_steps,
                0.48,
                0.26,
                bounds,
                attach_radius * 0.6,
                attach_radius * 0.18,
            )
            lateral.kind = "lateral"
            paths.append(lateral)

            if is_pot and rng.random() < 0.55:
                shoot_anchor = lateral.points[rng.randint(2, 3)]
                shoot_direction = (
                    lateral_direction * 0.5 + outward * 0.5 + Vector((0, 0, 0.45))
                ).normalized()
                shoot_steps = 3
                shoot = _grow_path(
                    rng,
                    shoot_anchor,
                    shoot_direction,
                    shoot_steps,
                    lateral_length * 0.35 / shoot_steps,
                    0.5,
                    0.3,
                    bounds,
                    attach_radius * 0.32,
                    attach_radius * 0.12,
                )
                shoot.kind = "shoot"
                paths.append(shoot)
    return paths


def leaf_guard(checked: dict, axis: str) -> float:
    value = checked["leaf_width_m"] if axis == "x" else checked["leaf_thickness_m"]
    return value * 1.2

# ---------------------------------------------------------------------------
# Build orchestration
# ---------------------------------------------------------------------------


def _review_scene(bpy, mesh_objects, foliage_objects, base_z: float, height: float) -> None:
    from mathutils import Vector

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 900
    scene.render.resolution_y = 700
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False

    world = bpy.data.worlds.new("SK_World_Review") if not bpy.data.worlds else bpy.data.worlds[0]
    scene.world = world
    world.use_nodes = True
    background = next(node for node in world.node_tree.nodes if node.type == "BACKGROUND")
    background.inputs[0].default_value = (0.055, 0.065, 0.075, 1.0)
    background.inputs[1].default_value = 0.35

    cameras = bpy.data.collections.get("SK_COL_Cameras")
    if cameras is None:
        cameras = bpy.data.collections.new("SK_COL_Cameras")
        scene.collection.children.link(cameras)
    for old in [obj for obj in bpy.data.objects if obj.name.startswith("CAM_Review_")]:
        bpy.data.objects.remove(old, do_unlink=True)
    for old in [obj for obj in bpy.data.objects if obj.name.startswith("SK_Review_")]:
        bpy.data.objects.remove(old, do_unlink=True)

    sun_data = bpy.data.lights.new("SK_Review_Sun", "SUN")
    sun_data.energy = 3.0
    sun = bpy.data.objects.new("SK_Review_Sun", sun_data)
    scene.collection.objects.link(sun)
    sun.rotation_euler = (0.85, 0.15, 0.45)

    fill_data = bpy.data.lights.new("SK_Review_Fill", "AREA")
    scale = max(0.6, height / 0.55)
    fill_data.energy = 600.0 * scale * scale
    fill_data.size = 0.6 * scale
    fill = bpy.data.objects.new("SK_Review_Fill", fill_data)
    scene.collection.objects.link(fill)
    fill.location = Vector((-1.018, -1.273, 0.902)) * scale

    def bounds_of(objects):
        points = [
            obj.matrix_world @ Vector(corner)
            for obj in objects
            for corner in obj.bound_box
        ]
        minimum = Vector([min(p[i] for p in points) for i in range(3)])
        maximum = Vector([max(p[i] for p in points) for i in range(3)])
        return minimum, maximum

    def add_camera(name, direction, target_objects, margin, aspect):
        minimum, maximum = bounds_of(target_objects)
        center = (minimum + maximum) / 2.0
        quat = (-direction).to_track_quat("-Z", "Y")
        right = quat @ Vector((1.0, 0.0, 0.0))
        up = quat @ Vector((0.0, 1.0, 0.0))
        points = [
            obj.matrix_world @ Vector(corner)
            for obj in target_objects
            for corner in obj.bound_box
        ]
        half_w = max(abs((p - center).dot(right)) for p in points)
        half_h = max(abs((p - center).dot(up)) for p in points)
        # With HORIZONTAL sensor fit, ortho_scale is the frame width; the
        # frame height equals ortho_scale / aspect.
        ortho_scale = max(half_w * 2.0, half_h * 2.0 * aspect) * margin
        data = bpy.data.cameras.new(name)
        data.type = "ORTHO"
        data.sensor_fit = "HORIZONTAL"
        data.ortho_scale = ortho_scale
        data.clip_start = 0.02
        data.clip_end = 200.0
        camera = bpy.data.objects.new(name, data)
        cameras.objects.link(camera)
        distance = max((maximum - minimum).length * 2.2, 2.0)
        camera.location = center + direction * distance
        camera.rotation_euler = quat.to_euler()
        return camera

    from mathutils import Vector as V  # noqa: F811

    add_camera("CAM_Review_front", V((0.0, -1.0, 0.0)), mesh_objects, 1.12, 900 / 700)
    add_camera("CAM_Review_side", V((1.0, 0.0, 0.0)), mesh_objects, 1.12, 900 / 700)
    add_camera(
        "CAM_Review_three_quarter",
        V((0.58, -0.8, 0.28)).normalized(),
        mesh_objects,
        1.12,
        900 / 700,
    )
    add_camera(
        "CAM_Review_closeup",
        V((0.55, -0.82, 0.32)).normalized(),
        foliage_objects,
        1.08,
        900 / 700,
    )
    scene.camera = bpy.data.objects["CAM_Review_three_quarter"]


def build_vegetation(
    parameters: dict[str, Any],
    prefix: str,
    collection_name: str = "SK_COL_Vegetation",
    replace_existing: bool = True,
) -> dict[str, Any]:
    import bpy
    from mathutils import Vector

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

    bark = _material(
        "MAT_vegetation_DarkWoodyStem_v2",
        (0.085, 0.05, 0.028, 1.0),
        0.9,
    )
    leaf_deep = _material(
        "MAT_vegetation_LeafDeep_v2",
        (0.04, 0.105, 0.026, 1.0),
        0.64,
    )
    leaf_mid = _material(
        "MAT_vegetation_LeafMid_v2",
        (0.085, 0.17, 0.048, 1.0),
        0.6,
    )
    leaf_light = _material(
        "MAT_vegetation_LeafLight_v2",
        (0.13, 0.225, 0.075, 1.0),
        0.6,
    )
    bud_material = _material(
        "MAT_vegetation_Bud_v2",
        (0.32, 0.34, 0.11, 1.0),
        0.6,
    )
    leaf_materials = [leaf_deep, leaf_mid, leaf_light, bud_material]
    pot_material = _material(
        "MAT_porch_planter_Terracotta_v1",
        (0.3, 0.105, 0.045, 1.0),
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
            24,
        )
        pot_builder.add_ring_surface(
            pot["height_m"] - pot["rim_height_m"],
            pot["height_m"] + pot["rim_height_m"] * 0.35,
            pot["top_radius_m"] * 0.98,
            pot["top_radius_m"] * 1.06,
            24,
        )
        objects.append(
            _mesh_object(f"{prefix}_pot", pot_builder, [pot_material], collection)
        )
        soil = MeshBuilder()
        soil.add_ring_surface(
            pot["height_m"] - 0.015,
            pot["height_m"] + 0.005,
            pot["top_radius_m"] * 0.88,
            pot["top_radius_m"] * 0.88,
            24,
        )
        objects.append(
            _mesh_object(f"{prefix}_soil", soil, [soil_material], collection)
        )
        base_z = pot["height_m"]
    else:
        base_z = 0.0

    paths = _branch_network(checked, rng, base_z)
    stems = MeshBuilder()
    for path in paths:
        stems.add_tube(
            [tuple(p) for p in path.points],
            path.radii,
            segments=8 if path.kind == "main" else 6,
            material=0,
        )

    leaves = MeshBuilder()
    target_leaves = max(8, int(round(checked["leaf_count"] * checked["leaf_density"])))
    slots = []
    for path_index, path in enumerate(paths):
        first_node = 2 if path.kind == "main" else 1
        for node_index in range(first_node, len(path.points)):
            slots.append((path_index, node_index))
    rng.shuffle(slots)
    assignments = {}
    for slot in slots:
        if len(assignments) >= target_leaves:
            break
        assignments[slot] = 1
    while len(assignments) < target_leaves and slots:
        slot = slots[rng.randrange(len(slots))]
        assignments[slot] = min(3, assignments.get(slot, 0) + 1)

    leaf_lengths = []
    material_usage = [0, 0, 0, 0]
    golden_angle = math.pi * (3.0 - math.sqrt(5.0))
    leaf_index = 0
    for (path_index, node_index), copies in sorted(assignments.items()):
        path = paths[path_index]
        anchor = path.points[node_index]
        tangent = (
            path.points[min(node_index + 1, len(path.points) - 1)]
            - path.points[max(node_index - 1, 0)]
        ).normalized()
        radial = Vector((anchor.x, anchor.y, 0.0))
        if radial.length < 1e-5:
            radial = Vector((math.cos(leaf_index), math.sin(leaf_index), 0.0))
        radial.normalize()
        for copy_index in range(copies):
            angle = leaf_index * golden_angle
            outward = (
                radial * math.cos(angle)
                + Vector((-radial.y, radial.x, 0.0)) * math.sin(angle)
            )
            y_axis = (
                outward * rng.uniform(0.55, 0.9)
                + tangent * rng.uniform(0.25, 0.6)
                + Vector((0.0, 0.0, rng.uniform(0.15, 0.55)))
            ).normalized()
            reference = tangent if abs(tangent.dot(y_axis)) < 0.92 else Vector((0, 0, 1))
            x_axis = y_axis.cross(reference).normalized()
            roll = rng.uniform(-0.9, 0.9)
            x_axis = (x_axis * math.cos(roll) + y_axis.cross(x_axis) * math.sin(roll)).normalized()
            z_axis = x_axis.cross(y_axis).normalized()
            tip_node = node_index >= len(path.points) - 2
            scale = rng.uniform(0.62, 0.85) if tip_node else rng.uniform(0.72, 1.24)
            length = checked["leaf_height_m"] * scale
            width = checked["leaf_width_m"] * scale * rng.uniform(0.85, 1.1)
            petiole_length = length * rng.uniform(0.22, 0.38)
            blade_base = anchor + y_axis * petiole_length
            stems.add_tube(
                [tuple(anchor), tuple(blade_base)],
                [checked["stem_radius_m"] * 0.22, checked["stem_radius_m"] * 0.12],
                segments=5,
                material=0,
            )
            if tip_node and rng.random() < 0.55:
                material_index = 2
            else:
                roll_dice = rng.random()
                material_index = 0 if roll_dice < 0.55 else (1 if roll_dice < 0.87 else 2)
            leaves.add_leaf_blade(
                tuple(blade_base),
                (tuple(x_axis), tuple(y_axis), tuple(z_axis)),
                length,
                width,
                checked["leaf_curl_m"] * rng.uniform(0.7, 1.3),
                checked["leaf_cup_m"] * rng.uniform(-1.0, 1.0),
                material_index,
            )
            leaf_lengths.append(length)
            material_usage[material_index] += 1
            leaf_index += 1

    for path in paths:
        tip = path.tip
        tangent = (tip - path.points[-2]).normalized()
        helper = Vector((0.0, 0.0, 1.0))
        if abs(tangent.dot(helper)) > 0.92:
            helper = Vector((1.0, 0.0, 0.0))
        x_axis = tangent.cross(helper).normalized()
        z_axis = x_axis.cross(tangent).normalized()
        bud_length = checked["leaf_height_m"] * 0.42
        leaves.add_leaf_blade(
            tuple(tip),
            (tuple(x_axis), tuple(tangent), tuple(z_axis)),
            bud_length,
            checked["leaf_width_m"] * 0.55,
            checked["leaf_curl_m"] * 0.25,
            checked["leaf_cup_m"] * 0.4,
            3,
        )
        material_usage[3] += 1

    stem_object = _mesh_object(f"{prefix}_stems", stems, [bark], collection)
    leaf_object = _mesh_object(
        f"{prefix}_leaves", leaves, leaf_materials, collection, recalc_normals=False
    )
    objects.extend([stem_object, leaf_object])

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

    bpy.context.view_layer.update()
    quality = _organic_quality(
        checked, paths, leaf_lengths, material_usage, leaf_object, root, base_z
    )
    _review_scene(bpy, objects, [stem_object, leaf_object], base_z, checked["height_m"])

    all_corners = [
        obj.matrix_world @ Vector(corner)
        for obj in objects
        for corner in obj.bound_box
    ]
    dimensions = [
        round(
            max(corner[i] for corner in all_corners)
            - min(corner[i] for corner in all_corners),
            5,
        )
        for i in range(3)
    ]
    triangles = sum(
        max(0, len(poly.vertices) - 2)
        for obj in objects
        for poly in obj.data.polygons
    )
    return {
        "status": "generated",
        "generator_revision": 2,
        "root": root.name,
        "objects": [obj.name for obj in objects],
        "dimensions_m": dimensions,
        "triangles": triangles,
        "seed": checked["seed"],
        "parameters_hash": parameters_hash,
        "organic_quality": quality,
    }


def _organic_quality(checked, paths, leaf_lengths, material_usage, leaf_object, root, base_z) -> dict:
    from mathutils import Vector

    turn_angles = []
    for path in paths:
        for i in range(1, len(path.points) - 1):
            a = (path.points[i] - path.points[i - 1]).normalized()
            b = (path.points[i + 1] - path.points[i]).normalized()
            turn_angles.append(math.degrees(a.angle(b)))
    taper = min(p.radii[-1] / p.radii[0] for p in paths)
    world_points = [
        leaf_object.matrix_world @ Vector(corner)
        for corner in leaf_object.bound_box
    ]
    min_x = min(p.x for p in world_points)
    max_x = max(p.x for p in world_points)
    min_z = min(p.z for p in world_points)
    max_z = max(p.z for p in world_points)
    cells = set()
    grid = 28
    for polygon in leaf_object.data.polygons:
        for vertex_index in polygon.vertices:
            vertex = leaf_object.matrix_world @ leaf_object.data.vertices[vertex_index].co
            gx = int((vertex.x - min_x) / max(max_x - min_x, 1e-6) * (grid - 1))
            gz = int((vertex.z - min_z) / max(max_z - min_z, 1e-6) * (grid - 1))
            cells.add((gx, gz))
    silhouette_fill = len(cells) / (grid * grid)
    mean_leaf = sum(leaf_lengths) / max(1, len(leaf_lengths))
    gates = {
        "hierarchical_branches": len(paths) >= checked["stem_count"] * 2,
        "curved_stems": max(turn_angles, default=0.0) >= 4.0,
        "tapered_stems": taper <= 0.4,
        "dense_small_leaves": len(leaf_lengths) >= max(40, checked["stem_count"] * 12)
        and mean_leaf / checked["height_m"] <= 0.12,
        "multi_tone_greens": sum(1 for count in material_usage[:3] if count > 0) >= 3,
        "terminal_buds": material_usage[3] == len(paths),
        "organic_silhouette": silhouette_fill >= 0.3,
        "foliage_above_base": min_z >= base_z - 0.01,
    }
    return {
        "status": "pass" if all(gates.values()) else "repair_required",
        "branch_paths": len(paths),
        "main_stems": checked["stem_count"],
        "leaves": len(leaf_lengths),
        "buds": material_usage[3],
        "leaf_material_variants": sum(1 for count in material_usage[:3] if count > 0),
        "leaf_length_min_m": round(min(leaf_lengths), 5),
        "leaf_length_mean_m": round(mean_leaf, 5),
        "leaf_length_max_m": round(max(leaf_lengths), 5),
        "max_stem_turn_deg": round(max(turn_angles, default=0.0), 2),
        "tip_to_base_radius_ratio": round(taper, 4),
        "silhouette_fill": round(silhouette_fill, 4),
        "gates": gates,
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
        import bpy

        # Standalone generation starts from an empty scene so startup
        # primitives (cube/camera/light) cannot frame or shadow the asset.
        bpy.ops.wm.read_factory_settings(use_empty=True)
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
    return 0 if result["organic_quality"]["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
