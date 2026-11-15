#!/usr/bin/env python3
"""Generate parametric solid entrance steps."""

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
    width = _number(parameters.get("width_m"), "width_m", 0.2)
    step_count = _integer(
        parameters.get("step_count"),
        "step_count",
        1,
    )
    riser = _number(
        parameters.get("riser_height_m"),
        "riser_height_m",
        0.05,
    )
    tread = _number(
        parameters.get("tread_depth_m"),
        "tread_depth_m",
        0.15,
    )
    landing = _number(
        parameters.get("landing_depth_m", 0.32),
        "landing_depth_m",
        0.1,
    )
    back_y = _number(parameters.get("back_y_m"), "back_y_m")
    nosing_projection = _number(
        parameters.get("nosing_projection_m", 0.04),
        "nosing_projection_m",
        0.0,
    )
    nosing_height = _number(
        parameters.get("nosing_height_m", 0.018),
        "nosing_height_m",
        0.002,
    )
    if riser > 0.22:
        raise ValueError("riser_height_m exceeds comfortable stair rise")
    if tread < 0.25:
        raise ValueError("tread_depth_m is too shallow")
    platform_height = step_count * riser
    total_depth = landing + (step_count - 1) * tread
    front_y = back_y - total_depth
    riser_face_front_y = front_y + nosing_projection
    steps = []
    for index in range(step_count):
        number = index + 1
        steps.append(
            {
                "index": number,
                "top_z_m": number * riser,
                "nosing_tip_front_y_m": back_y
                - (landing + (step_count - number) * tread),
                "riser_face_front_y_m": back_y
                - (landing + (step_count - number) * tread)
                + nosing_projection,
                "back_y_m": back_y,
            }
        )
    return {
        "width_m": width,
        "step_count": step_count,
        "riser_height_m": riser,
        "tread_depth_m": tread,
        "landing_depth_m": landing,
        "back_y_m": back_y,
        "front_y_m": front_y,
        "riser_face_front_y_m": riser_face_front_y,
        "nosing_projection_m": nosing_projection,
        "nosing_height_m": nosing_height,
        "platform_height_m": platform_height,
        "total_depth_m": total_depth,
        "overall_dimensions_m": [width, total_depth, platform_height],
        "steps": steps,
        "material": parameters.get("material") or {},
    }


def validate_parameters(parameters: dict[str, Any]) -> dict[str, Any]:
    resolved = resolve_parameters(parameters)
    material = resolved["material"]
    if not isinstance(material, dict):
        raise ValueError("material must be an object")
    scale = material.get("stone_mapping_scale")
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
        raise ValueError("material.stone_mapping_scale must contain 3 positive numbers")
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


def build_steps(
    parameters: dict[str, Any],
    material_name: str,
    prefix: str = "SK_entrance_steps_v1",
    collection_name: str = "SK_COL_Structure",
    replace_existing: bool = True,
) -> dict[str, Any]:
    import bpy

    checked = validate_parameters(parameters)
    material = bpy.data.materials.get(material_name)
    if material is None:
        raise ValueError(f"Material not found: {material_name}")
    collection = bpy.data.collections.get(collection_name)
    if collection is None:
        collection = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(collection)
    if replace_existing:
        for obj in list(bpy.data.objects):
            if obj.name.startswith(prefix):
                bpy.data.objects.remove(obj, do_unlink=True)

    builder = MeshBuilder()
    width = checked["width_m"]
    back_y = checked["back_y_m"]
    nosing_projection = checked["nosing_projection_m"]
    nosing_height = checked["nosing_height_m"]
    for step in checked["steps"]:
        nosing_tip_front_y = step["nosing_tip_front_y_m"]
        riser_face_front_y = step["riser_face_front_y_m"]
        top_z = step["top_z_m"]
        depth = back_y - riser_face_front_y
        builder.add_box(
            (0.0, (riser_face_front_y + back_y) / 2.0, top_z / 2.0),
            (width, depth, top_z),
        )
        if nosing_projection > 0:
            builder.add_box(
                (
                    0.0,
                    nosing_tip_front_y + nosing_projection / 2.0,
                    top_z - nosing_height / 2.0,
                ),
                (
                    width,
                    nosing_projection,
                    nosing_height,
                ),
            )
    obj = _mesh_object(
        f"{prefix}_steps",
        builder,
        material,
        collection,
    )
    root = bpy.data.objects.new(f"{prefix}_ROOT", None)
    collection.objects.link(root)
    obj.parent = root
    parameters_hash = hashlib.sha256(
        json.dumps(
            checked,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    obj["part_id"] = "entrance_steps"
    obj["parameters_hash"] = parameters_hash
    return {
        "status": "generated",
        "root": root.name,
        "object": obj.name,
        "step_count": checked["step_count"],
        "platform_height_m": checked["platform_height_m"],
        "dimensions_m": checked["overall_dimensions_m"],
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
    parser.add_argument("--material-name", required=True)
    parser.add_argument("--prefix", default="SK_entrance_steps_v1")
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
        result = build_steps(
            parameters,
            args.material_name,
            prefix=args.prefix,
            collection_name=args.collection,
        )
    except ImportError as exc:
        print(f"Steps generation must run inside Blender: {exc}", file=sys.stderr)
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
