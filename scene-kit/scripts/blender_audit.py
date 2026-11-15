#!/usr/bin/env python3
"""Read-only Blender scene audit for scene-kit projects.

Run inside Blender:
    blender --background model.blend --python blender_audit.py -- \
      --output preview/finishing/blender_audit.json

The report is diagnostic evidence, not an automatic design or construction
verdict. It never saves the .blend or modifies scene data.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


EPSILON = 1.0e-9


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _round(value: float, digits: int = 6) -> float:
    return round(float(value), digits)


def _vec(values: Any, digits: int = 6) -> list[float]:
    return [_round(value, digits) for value in values]


def _default_output() -> Path:
    import bpy

    filepath = getattr(bpy.data, "filepath", "")
    if filepath:
        blend = Path(filepath).resolve()
        project_root = blend.parent.parent if blend.parent.name.lower() == "internal" else blend.parent
        return project_root / "preview" / "finishing" / "blender_audit.json"
    return Path.cwd() / "blender_audit.json"


def _write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
        newline="\n",
    ) as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)


def _all_collection_names(obj: Any) -> list[str]:
    return sorted(collection.name for collection in obj.users_collection)


def _world_bounds(obj: Any) -> dict[str, list[float]] | None:
    if not getattr(obj, "bound_box", None):
        return None
    from mathutils import Vector

    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    if not points:
        return None
    minimum = [min(point[index] for point in points) for index in range(3)]
    maximum = [max(point[index] for point in points) for index in range(3)]
    return {"min": _vec(minimum), "max": _vec(maximum)}


def _audit_mesh_materials(mesh: Any) -> dict[str, Any]:
    slots = []
    missing = 0
    for index, slot in enumerate(mesh.materials):
        name = slot.name if slot is not None else None
        if slot is None:
            missing += 1
        slots.append({"index": index, "name": name})
    return {
        "material_slots": slots,
        "material_count": len(slots),
        "missing_material_slots": missing,
    }


def _topology_from_bmesh(mesh: Any, bmesh: Any) -> dict[str, int]:
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        bm.normal_update()

        non_manifold_edges = 0
        boundary_edges = 0
        wire_edges = 0
        loose_vertices = 0
        zero_area_faces = 0
        ngons = 0
        duplicate_edges = 0
        duplicate_faces = 0

        edge_keys: set[tuple[int, int]] = set()
        face_keys: set[tuple[int, ...]] = set()
        for edge in bm.edges:
            links = len(edge.link_faces)
            if not edge.is_manifold:
                non_manifold_edges += 1
            if links == 1:
                boundary_edges += 1
            elif links == 0:
                wire_edges += 1
            key = (min(edge.verts[0].index, edge.verts[1].index), max(edge.verts[0].index, edge.verts[1].index))
            if key in edge_keys:
                duplicate_edges += 1
            else:
                edge_keys.add(key)

        for vertex in bm.verts:
            if not vertex.link_edges:
                loose_vertices += 1
        for face in bm.faces:
            if face.calc_area() <= EPSILON:
                zero_area_faces += 1
            if len(face.verts) > 4:
                ngons += 1
            key = tuple(sorted(vertex.index for vertex in face.verts))
            if key in face_keys:
                duplicate_faces += 1
            else:
                face_keys.add(key)

        return {
            "non_manifold_edges": non_manifold_edges,
            "boundary_edges": boundary_edges,
            "wire_edges": wire_edges,
            "loose_vertices": loose_vertices,
            "zero_area_faces": zero_area_faces,
            "ngons": ngons,
            "duplicate_edges": duplicate_edges,
            "duplicate_faces": duplicate_faces,
        }
    finally:
        bm.free()


def _audit_mesh_object(obj: Any, bmesh: Any) -> dict[str, Any]:
    mesh = obj.data
    mesh.calc_loop_triangles()
    data = {
        "name": obj.name,
        "type": obj.type,
        "collections": _all_collection_names(obj),
        "parent": obj.parent.name if obj.parent is not None else None,
        "hide_render": bool(obj.hide_render),
        "visible": not bool(getattr(obj, "hide_get", lambda: False)()),
        "location": _vec(obj.location),
        "rotation_euler": _vec(obj.rotation_euler),
        "scale": _vec(obj.scale),
        "dimensions": _vec(obj.dimensions),
        "world_bounds": _world_bounds(obj),
        "vertices": len(mesh.vertices),
        "edges": len(mesh.edges),
        "polygons": len(mesh.polygons),
        "triangles": len(mesh.loop_triangles),
        "modifiers": [{"name": item.name, "type": item.type} for item in obj.modifiers],
        "data_name": mesh.name,
    }
    data.update(_audit_mesh_materials(mesh))
    data.update(_topology_from_bmesh(mesh, bmesh))
    return data


def _audit_external_images(bpy: Any) -> list[dict[str, Any]]:
    result = []
    for image in bpy.data.images:
        source = getattr(image, "source", "")
        raw_path = getattr(image, "filepath", "")
        resolved = bpy.path.abspath(raw_path) if raw_path else ""
        exists = None
        if source == "FILE" and resolved:
            exists = Path(resolved).is_file()
        result.append(
            {
                "name": image.name,
                "source": source,
                "filepath": raw_path,
                "resolved_path": resolved,
                "exists": exists,
                "packed": bool(getattr(image, "packed_file", None)),
            }
        )
    return result


def _linked_node(
    node: Any,
    input_name: str,
) -> tuple[Any | None, str | None]:
    socket = node.inputs.get(input_name)
    if socket is None or not getattr(socket, "links", None):
        return None, None
    link = socket.links[0]
    return getattr(link, "from_node", None), getattr(
        getattr(link, "from_socket", None),
        "name",
        None,
    )


def _coordinate_chain(node: Any) -> dict[str, Any]:
    mapping_scale = None
    coordinate_source = None
    coordinate_output = None
    visited: set[int] = set()
    current = node
    for _ in range(8):
        if current is None or id(current) in visited:
            break
        visited.add(id(current))
        if current.type == "MAPPING":
            scale_socket = current.inputs.get("Scale")
            if scale_socket is not None:
                mapping_scale = _vec(scale_socket.default_value)
        upstream, output_name = _linked_node(current, "Vector")
        if upstream is None:
            break
        if upstream.type == "TEX_COORD":
            coordinate_source = "TEX_COORD"
            coordinate_output = output_name
            break
        if upstream.type == "UVMAP":
            coordinate_source = "UVMAP"
            coordinate_output = output_name or "UV"
            break
        current = upstream
    return {
        "mapping_scale": mapping_scale,
        "coordinate_source": coordinate_source,
        "coordinate_output": coordinate_output,
    }


def _audit_material_textures(material: Any) -> dict[str, Any]:
    if material is None:
        return {
            "material": None,
            "use_nodes": False,
            "image_textures": [],
            "risk_findings": [],
        }
    node_tree = getattr(material, "node_tree", None)
    if node_tree is None:
        return {
            "material": material.name,
            "use_nodes": False,
            "image_textures": [],
            "risk_findings": [],
        }

    textures = []
    risk_findings = []
    for node in node_tree.nodes:
        if getattr(node, "type", None) != "TEX_IMAGE":
            continue
        image = getattr(node, "image", None)
        chain = _coordinate_chain(node)
        projection = getattr(node, "projection", "FLAT")
        entry = {
            "node": getattr(node, "name", None),
            "image": getattr(image, "name", None),
            "image_size": (
                list(image.size) if image is not None else None
            ),
            "projection": projection,
            "extension": getattr(node, "extension", None),
            **chain,
        }
        scale = chain.get("mapping_scale")
        if scale and any(value <= 0.0 for value in scale):
            risk_findings.append(
                {
                    "code": "non_positive_texture_mapping_scale",
                    "severity": "high",
                    "node": entry["node"],
                    "message": "Texture mapping has a zero or negative scale axis.",
                }
            )
        coordinate_output = chain.get("coordinate_output")
        if projection == "FLAT" and coordinate_output in {
            "Object",
            "Generated",
        }:
            risk_findings.append(
                {
                    "code": "flat_3d_coordinate_projection",
                    "severity": "high",
                    "node": entry["node"],
                    "message": (
                        "Image texture uses flat projection with "
                        f"{coordinate_output} coordinates. Vertical or "
                        "turned faces can omit an axis and be stretched."
                    ),
                }
            )
        textures.append(entry)

    return {
        "material": material.name,
        "use_nodes": True,
        "image_textures": textures,
        "risk_findings": risk_findings,
    }


def audit_scene(output_path: str | os.PathLike[str] | None = None, strict: bool = False) -> tuple[dict[str, Any], Path]:
    """Audit the active Blender scene without changing it."""
    import bpy
    import bmesh

    scene = bpy.context.scene
    output = Path(output_path).expanduser() if output_path else _default_output()
    output = output.resolve()

    mesh_objects = [obj for obj in bpy.data.objects if obj.type == "MESH" and obj.data is not None]
    objects = [_audit_mesh_object(obj, bmesh) for obj in mesh_objects]
    cameras = sorted(obj.name for obj in bpy.data.objects if obj.type == "CAMERA")
    lights = sorted(obj.name for obj in bpy.data.objects if obj.type == "LIGHT")
    collections = sorted(collection.name for collection in bpy.data.collections)
    images = _audit_external_images(bpy)
    texture_materials = [
        _audit_material_textures(material)
        for material in bpy.data.materials
    ]
    texture_risk_findings = [
        (item["material"], risk)
        for item in texture_materials
        for risk in item["risk_findings"]
    ]

    total = {
        "vertices": sum(item["vertices"] for item in objects),
        "edges": sum(item["edges"] for item in objects),
        "polygons": sum(item["polygons"] for item in objects),
        "triangles": sum(item["triangles"] for item in objects),
        "non_manifold_edges": sum(item["non_manifold_edges"] for item in objects),
        "boundary_edges": sum(item["boundary_edges"] for item in objects),
        "wire_edges": sum(item["wire_edges"] for item in objects),
        "loose_vertices": sum(item["loose_vertices"] for item in objects),
        "zero_area_faces": sum(item["zero_area_faces"] for item in objects),
        "ngons": sum(item["ngons"] for item in objects),
        "duplicate_edges": sum(item["duplicate_edges"] for item in objects),
        "duplicate_faces": sum(item["duplicate_faces"] for item in objects),
    }

    zero_scale = [obj.name for obj in mesh_objects if min(abs(obj.scale[index]) for index in range(3)) <= EPSILON]
    negative_scale = [obj.name for obj in mesh_objects if obj.scale.x * obj.scale.y * obj.scale.z < 0.0]
    non_unit_scale = [
        obj.name
        for obj in mesh_objects
        if any(abs(float(obj.scale[index]) - 1.0) > 1.0e-6 for index in range(3))
    ]
    missing_materials = [item["name"] for item in objects if item["missing_material_slots"] > 0]
    missing_images = [item["name"] for item in images if item["exists"] is False and not item["packed"]]

    findings: list[dict[str, Any]] = []

    def add_finding(severity: str, code: str, message: str, affected: list[str]) -> None:
        findings.append(
            {
                "severity": severity,
                "code": code,
                "message": message,
                "affected_count": len(affected),
                "affected": affected[:100],
            }
        )

    if not mesh_objects:
        add_finding("blocker", "no_mesh_objects", "场景没有网格对象。", [])
    if zero_scale:
        add_finding("blocker", "zero_scale", "网格对象存在零缩放轴。", zero_scale)
    if negative_scale:
        add_finding("blocker", "negative_scale", "网格对象存在负缩放轴。", negative_scale)
    if total["zero_area_faces"]:
        add_finding("high", "zero_area_faces", "存在零面积面。", [item["name"] for item in objects if item["zero_area_faces"]])
    if total["duplicate_faces"]:
        add_finding("high", "duplicate_faces", "存在重复面。", [item["name"] for item in objects if item["duplicate_faces"]])
    if missing_materials:
        add_finding("high", "missing_material_slots", "存在空的材质槽。", missing_materials)
    if total["non_manifold_edges"]:
        add_finding("medium", "non_manifold_edges", "存在非流形边；区分真实边界、开放壳和布线错误。", [item["name"] for item in objects if item["non_manifold_edges"]])
    if total["loose_vertices"]:
        add_finding("medium", "loose_vertices", "存在孤立顶点。", [item["name"] for item in objects if item["loose_vertices"]])
    if total["wire_edges"]:
        add_finding("medium", "wire_edges", "存在不带面的线边。", [item["name"] for item in objects if item["wire_edges"]])
    if total["duplicate_edges"]:
        add_finding("medium", "duplicate_edges", "存在重复边。", [item["name"] for item in objects if item["duplicate_edges"]])
    if missing_images:
        add_finding("medium", "missing_external_images", "外部图片不存在且未打包。", missing_images)
    if texture_risk_findings:
        risk_codes = sorted(
            {risk["code"] for _, risk in texture_risk_findings}
        )
        affected_materials = sorted(
            {material for material, _ in texture_risk_findings}
        )
        add_finding(
            "high",
            "texture_projection_risk",
            "贴图使用可能造成跨立面拉伸的坐标/投影组合："
            + ", ".join(risk_codes),
            affected_materials,
        )
    if non_unit_scale:
        add_finding("low", "non_unit_scale", "存在非单位缩放；实例或有意变换可保留，但需确认导出和接口。", non_unit_scale)

    review_cameras = [name for name in cameras if name.startswith("CAM_Review_")]
    if not review_cameras:
        add_finding("medium", "no_review_camera", "没有 CAM_Review_* 标准审阅相机。", [])

    units = scene.unit_settings
    report = {
        "schema": 1,
        "generated_at": _now_iso(),
        "tool": "scene-kit blender_audit.py",
        "strict_requested": bool(strict),
        "blend_file": bpy.data.filepath,
        "scene": {
            "name": scene.name,
            "unit_system": units.system,
            "unit_scale": _round(units.scale_length),
            "frame_start": scene.frame_start,
            "frame_end": scene.frame_end,
            "render_engine": scene.render.engine,
            "resolution": [scene.render.resolution_x, scene.render.resolution_y],
            "resolution_percentage": scene.render.resolution_percentage,
        },
        "inventory": {
            "objects_total": len(bpy.data.objects),
            "mesh_objects": len(mesh_objects),
            "cameras": cameras,
            "review_cameras": review_cameras,
            "lights": lights,
            "collections": collections,
            "materials_total": len(bpy.data.materials),
        },
        "totals": total,
        "images": images,
        "texture_mapping_audit": {
            "status": (
                "repair_required"
                if texture_risk_findings
                else "pass"
            ),
            "image_texture_materials": len(
                [
                    item
                    for item in texture_materials
                    if item["image_textures"]
                ]
            ),
            "materials": texture_materials,
            "risk_findings": [
                {
                    "material": material,
                    **risk,
                }
                for material, risk in texture_risk_findings
            ],
        },
        "objects": objects,
        "findings": findings,
        "limitations": [
            "Report does not judge concept match, proportions, construction logic, material quality, or target-engine acceptance.",
            "Boundary and non-manifold edges may be intentional on open or temporary surfaces.",
            "Non-unit scaling may be intentional for instances and must be checked against export requirements.",
        ],
    }
    _write_json_atomic(output, report)
    return report, output


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only Blender scene audit for scene-kit")
    parser.add_argument("--output", type=Path, help="JSON report path")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return a non-zero status when blocker/high findings exist",
    )
    return parser


def _argument_argv(argv: list[str] | None) -> list[str]:
    if argv is not None:
        return argv
    if "--" in sys.argv:
        return sys.argv[sys.argv.index("--") + 1 :]
    return sys.argv[1:]


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(_argument_argv(argv))
    try:
        report, output = audit_scene(args.output, strict=args.strict)
    except ImportError as exc:
        print(f"blender_audit.py must run inside Blender: {exc}", file=sys.stderr)
        return 2

    totals = report["totals"]
    print(
        "scene-kit audit: "
        f"{report['inventory']['mesh_objects']} meshes, "
        f"{totals['triangles']} triangles, "
        f"{len(report['findings'])} findings"
    )
    print(f"report: {output}")
    for finding in report["findings"]:
        print(f"  [{finding['severity']}] {finding['code']}: {finding['message']}")

    if args.strict and any(item["severity"] in {"blocker", "high"} for item in report["findings"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
