#!/usr/bin/env python3
"""Normalize a reference mesh with uniform scale and render a fixed ten-view rig.

Run inside Blender:

blender --background source.blend --python reference_model_views.py -- \
  --object REF_building --output-dir output --uniform-scale 12 \
  --rotation-z-deg -90
"""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path

import bpy
import numpy as np
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector


VIEW_ANGLES = {
    "top": ((0.0, 0.0, 1.0), "Y"),
    "bottom": ((0.0, 0.0, -1.0), "Y"),
    "left": ((-1.0, 0.0, 0.0), "Z"),
    "right": ((1.0, 0.0, 0.0), "Z"),
    "front": ((0.0, -1.0, 0.0), "Z"),
    "back": ((0.0, 1.0, 0.0), "Z"),
    "front_left_45": ((-1.0, -1.0, 0.0), "Z"),
    "front_right_45": ((1.0, -1.0, 0.0), "Z"),
    "back_left_45": ((-1.0, 1.0, 0.0), "Z"),
    "back_right_45": ((1.0, 1.0, 0.0), "Z"),
}


def parse_args() -> argparse.Namespace:
    args = os.sys.argv
    parser = argparse.ArgumentParser()
    parser.add_argument("--object", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--uniform-scale", type=float, default=None)
    parser.add_argument("--rotation-z-deg", type=float, default=0.0)
    parser.add_argument("--ortho-scale", type=float, default=14.0)
    parser.add_argument("--resolution-x", type=int, default=1200)
    parser.add_argument("--resolution-y", type=int, default=800)
    parser.add_argument("--blend-out", type=Path, default=None)
    parser.add_argument("--glb-out", type=Path, default=None)
    parser.add_argument("--component-map", type=Path, default=None)
    parser.add_argument("--component-crops-dir", type=Path, default=None)
    parser.add_argument(
        "--component-views",
        default="front,front_right_45",
    )
    if "--" not in args:
        raise RuntimeError("Arguments must follow the Blender '--' separator")
    return parser.parse_args(args[args.index("--") + 1 :])


def connected_islands(mesh: bpy.types.Mesh, matrix) -> list[dict]:
    count = len(mesh.vertices)
    parent = list(range(count))
    sizes = [1] * count

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        left = find(left)
        right = find(right)
        if left == right:
            return
        if sizes[left] < sizes[right]:
            left, right = right, left
        parent[right] = left
        sizes[left] += sizes[right]

    for edge in mesh.edges:
        union(edge.vertices[0], edge.vertices[1])
    groups: dict[int, list[int]] = {}
    for index in range(count):
        groups.setdefault(find(index), []).append(index)
    records = []
    for island_id, indices in enumerate(
        sorted(groups.values(), key=len, reverse=True),
        start=1,
    ):
        points = [matrix @ mesh.vertices[index].co for index in indices]
        minimum = [min(point[axis] for point in points) for axis in range(3)]
        maximum = [max(point[axis] for point in points) for axis in range(3)]
        records.append(
            {
                "island_id": island_id,
                "vertices": len(indices),
                "min": [round(value, 4) for value in minimum],
                "max": [round(value, 4) for value in maximum],
                "dimensions": [
                    round(maximum[axis] - minimum[axis], 4)
                    for axis in range(3)
                ],
                "center": [
                    round((minimum[axis] + maximum[axis]) / 2, 4)
                    for axis in range(3)
                ],
            }
        )
    return records


def make_camera(collection, name: str, center: Vector, direction: tuple, up: str, scale: float):
    camera = bpy.data.objects.get(name)
    if camera is None:
        data = bpy.data.cameras.new(name)
        camera = bpy.data.objects.new(name, data)
        collection.objects.link(camera)
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = scale
    camera.data.clip_start = 0.01
    camera.data.clip_end = 200.0
    offset = Vector(direction).normalized() * 50.0
    camera.location = center + offset
    camera.rotation_euler = (
        (center - camera.location).to_track_quat("-Z", up).to_euler()
    )
    return camera


def main() -> int:
    args = parse_args()
    obj = bpy.data.objects.get(args.object)
    if obj is None or obj.type != "MESH":
        raise RuntimeError(f"Mesh reference object not found: {args.object}")
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    obj.rotation_mode = "XYZ"
    obj.rotation_euler.z += math.radians(args.rotation_z_deg)
    bpy.ops.object.transform_apply(
        location=False,
        rotation=True,
        scale=False,
    )
    if args.uniform_scale is not None:
        obj.scale = (args.uniform_scale,) * 3
        bpy.ops.object.transform_apply(
            location=False,
            rotation=False,
            scale=True,
        )
    minimum_z = min(
        (obj.matrix_world @ Vector(corner)).z for corner in obj.bound_box
    )
    obj.location.z -= minimum_z
    bpy.ops.object.transform_apply(
        location=True,
        rotation=False,
        scale=False,
    )

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    collection = bpy.data.collections.get("SK_COL_Reference")
    if collection is None:
        collection = bpy.data.collections.new("SK_COL_Reference")
        bpy.context.scene.collection.children.link(collection)
    for other in bpy.data.objects:
        if other.type == "MESH" and other.name != obj.name:
            other.hide_render = True
            other.hide_set(True)
    obj.hide_render = False
    obj.hide_set(False)

    scene = bpy.context.scene
    scene.render.resolution_x = args.resolution_x
    scene.render.resolution_y = args.resolution_y
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    if scene.world:
        scene.world.use_nodes = True
        background = next(
            (
                node
                for node in scene.world.node_tree.nodes
                if node.type == "BACKGROUND"
            ),
            None,
        )
        if background:
            background.inputs["Color"].default_value = (0.78, 0.78, 0.77, 1.0)
            background.inputs["Strength"].default_value = 0.8

    center = sum(
        (obj.matrix_world @ Vector(corner) for corner in obj.bound_box),
        Vector(),
    ) / 8.0
    views = {}
    camera_records = {}
    for view_id, (direction, up) in VIEW_ANGLES.items():
        name = f"CAM_REF_RIG_{view_id}"
        camera = make_camera(
            collection,
            name,
            center,
            direction,
            up,
            args.ortho_scale,
        )
        scene.camera = camera
        path = output_dir / f"{view_id}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        views[view_id] = str(path)
        camera_records[view_id] = {
            "camera": name,
            "location": [round(value, 4) for value in camera.location],
            "direction": list(direction),
            "up_axis": up,
            "ortho_scale": args.ortho_scale,
        }

    islands = connected_islands(obj.data, obj.matrix_world)
    component_crops = {}
    if args.component_map and args.component_crops_dir:
        mapping = json.loads(
            args.component_map.read_text(encoding="utf-8")
        )
        island_by_id = {
            record["island_id"]: record for record in islands
        }
        view_ids = [
            value.strip()
            for value in args.component_views.split(",")
            if value.strip()
        ]
        args.component_crops_dir.mkdir(parents=True, exist_ok=True)
        for part_id, value in mapping.items():
            ids = (
                value.get("island_ids", [])
                if isinstance(value, dict)
                else value
            )
            selected = [
                island_by_id[island_id]
                for island_id in ids
                if island_id in island_by_id
            ]
            if not selected:
                continue
            minimum = [
                min(item["min"][axis] for item in selected)
                for axis in range(3)
            ]
            maximum = [
                max(item["max"][axis] for item in selected)
                for axis in range(3)
            ]
            corners = [
                Vector((x, y, z))
                for x in (minimum[0], maximum[0])
                for y in (minimum[1], maximum[1])
                for z in (minimum[2], maximum[2])
            ]
            part_dir = args.component_crops_dir / part_id
            part_dir.mkdir(parents=True, exist_ok=True)
            component_crops[part_id] = {
                "island_ids": [item["island_id"] for item in selected],
                "bounds": {"min": minimum, "max": maximum},
                "views": [],
            }
            for view_id in view_ids:
                camera = bpy.data.objects.get(
                    f"CAM_REF_RIG_{view_id}"
                )
                if camera is None:
                    continue
                projected = [
                    world_to_camera_view(scene, camera, corner)
                    for corner in corners
                ]
                x1 = max(
                    0,
                    int(
                        min(point.x for point in projected)
                        * args.resolution_x
                    )
                    - 24,
                )
                x2 = min(
                    args.resolution_x,
                    int(
                        max(point.x for point in projected)
                        * args.resolution_x
                    )
                    + 24,
                )
                y1 = max(
                    0,
                    int(
                        min(point.y for point in projected)
                        * args.resolution_y
                    )
                    - 24,
                )
                y2 = min(
                    args.resolution_y,
                    int(
                        max(point.y for point in projected)
                        * args.resolution_y
                    )
                    + 24,
                )
                if x2 <= x1 or y2 <= y1:
                    continue
                source = bpy.data.images.load(
                    views[view_id],
                    check_existing=False,
                )
                pixels = np.empty(
                    source.size[0] * source.size[1] * 4,
                    dtype=np.float32,
                )
                source.pixels.foreach_get(pixels)
                pixels = pixels.reshape(
                    source.size[1],
                    source.size[0],
                    4,
                )
                crop = pixels[y1:y2, x1:x2, :].copy()
                image = bpy.data.images.new(
                    f"REF_CROP_{part_id}_{view_id}",
                    width=x2 - x1,
                    height=y2 - y1,
                    alpha=True,
                )
                image.pixels.foreach_set(crop.ravel())
                crop_path = part_dir / f"{view_id}.png"
                image.filepath_raw = str(crop_path)
                image.file_format = "PNG"
                image.save()
                component_crops[part_id]["views"].append(str(crop_path))
                bpy.data.images.remove(image)
                bpy.data.images.remove(source)
        (output_dir / "component_crops.json").write_text(
            json.dumps(component_crops, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    report = {
        "object": obj.name,
        "dimensions_m": [round(value, 4) for value in obj.dimensions],
        "triangles": len(obj.data.polygons),
        "vertices": len(obj.data.vertices),
        "uniform_scale": args.uniform_scale,
        "rotation_z_deg": args.rotation_z_deg,
        "camera_rig": {
            "center": [round(value, 4) for value in center],
            "resolution": [args.resolution_x, args.resolution_y],
            "ortho_scale": args.ortho_scale,
            "views": camera_records,
        },
        "views": views,
        "mesh_islands": islands,
        "component_crops": component_crops,
    }
    (output_dir / "reference_model_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if args.blend_out:
        args.blend_out.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(args.blend_out.resolve()))
    if args.glb_out:
        args.glb_out.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.export_scene.gltf(
            filepath=str(args.glb_out.resolve()),
            export_format="GLB",
            use_selection=True,
            export_apply=True,
        )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
