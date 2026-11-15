"""Render front-view masks by enumerating the live Blender component instances."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

import bpy
from mathutils import Vector


sys.stdout.reconfigure(encoding="utf-8")


def hierarchy(root):
    result = [root]
    pending = list(root.children)
    while pending:
        obj = pending.pop(0)
        result.append(obj)
        pending.extend(obj.children)
    return result


def canonical_name(name):
    return re.sub(r"\.\d{3}$", "", name)


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, required=True)
    return parser.parse_args(argv)


def build_root_map(parts):
    root_to_part = {}
    for part in parts:
        part_id = part["part_id"]
        assembly = part.get("assembly") or {}
        for root_name in assembly.get("instance_roots") or []:
            root_to_part[root_name] = part_id
            root_to_part[canonical_name(root_name)] = part_id
    return root_to_part


def mapped_part_id(obj, root_to_part):
    explicit = obj.get("part_id")
    if explicit:
        return explicit
    for name in (obj.name, canonical_name(obj.name)):
        if name in root_to_part:
            return root_to_part[name]
    if obj.name.startswith("SK_tall_window_instance_"):
        return "tall_window_assembly"
    if obj.name.startswith("SK_climbing_vine_"):
        return "climbing_vine_module"
    return None


def live_groups(parts):
    root_to_part = build_root_map(parts)
    groups = []
    for root in sorted(bpy.data.objects, key=lambda item: item.name):
        if not root.name.startswith("SK_"):
            continue
        if not re.search(r"_ROOT(?:\.\d{3})?$", root.name):
            continue
        part_id = mapped_part_id(root, root_to_part)
        if not part_id:
            continue
        meshes = [
            obj
            for obj in hierarchy(root)
            if obj.type == "MESH" and not obj.hide_render
        ]
        if not meshes:
            continue
        corners = [
            obj.matrix_world @ Vector(corner)
            for obj in meshes
            for corner in obj.bound_box
        ]
        world_min = [min(point[i] for point in corners) for i in range(3)]
        world_max = [max(point[i] for point in corners) for i in range(3)]
        groups.append(
            {
                "part_id": part_id,
                "instance_id": root.get("assembly_instance_id")
                or root.get("instance_id")
                or root.name,
                "root": root.name,
                "meshes": meshes,
                "world_min_m": [round(value, 5) for value in world_min],
                "world_max_m": [round(value, 5) for value in world_max],
                "facade": root.get("facade"),
                "root_z_m": round(root.location.z, 5),
                "root_x_m": round(root.location.x, 5),
                "root_location_m": [
                    round(value, 5) for value in root.location
                ],
                "rotation_deg": [
                    round(math.degrees(value), 4)
                    for value in root.rotation_euler
                ],
                "scale": [round(value, 5) for value in root.scale],
            }
        )
    return groups


def facade_audit(groups, layout):
    windows = [
        group for group in groups if group["part_id"] == "tall_window_assembly"
    ]
    expected = layout["counts"]
    counts = {}
    centers = {}
    for facade in ("front", "back", "left", "right"):
        facade_windows = [item for item in windows if item["facade"] == facade]
        counts[facade] = {
            "lower": sum(
                1 for item in facade_windows if item["root_z_m"] < 3.0
            ),
            "upper": sum(
                1 for item in facade_windows if item["root_z_m"] >= 3.0
            ),
        }
        centers[facade] = {
            "lower": sorted(
                item["root_x_m"]
                for item in facade_windows
                if item["root_z_m"] < 3.0
            ),
            "upper": sorted(
                item["root_x_m"]
                for item in facade_windows
                if item["root_z_m"] >= 3.0
            ),
        }
    checks = {
        "window_count_matches_contract": len(windows)
        == expected["main_windows"],
        "front_lower_matches_3": counts["front"]["lower"]
        == expected["front_lower_windows"],
        "front_upper_matches_4": counts["front"]["upper"]
        == expected["front_upper_windows"],
        "front_lower_skips_door_axis": all(
            abs(center) > 0.59 for center in centers["front"]["lower"]
        ),
        "front_upper_has_door_axis": any(
            abs(center) < 0.01 for center in centers["front"]["upper"]
        ),
        "back_counts_match_contract": (
            counts["back"]["lower"] + counts["back"]["upper"]
            == expected["back_tall_windows"]
        ),
        "left_counts_match_contract": (
            counts["left"]["lower"] + counts["left"]["upper"]
            == expected["left_tall_windows"]
        ),
        "right_counts_match_contract": (
            counts["right"]["lower"] + counts["right"]["upper"]
            == expected["right_tall_windows"]
        ),
    }
    return {
        "status": "pass" if all(checks.values()) else "repair_required",
        "source_contract": "internal/wall_openings_v2.json",
        "footprint_width_m": layout["basis"]["footprint_width_m"],
        "checks": checks,
        "actual_counts": counts,
        "window_center_x_m": centers,
        "door_axis_rule": (
            "ground floor skips x=0; upper floor has a centered window"
        ),
    }


def main():
    args = parse_args()
    project = args.project.resolve()
    components = json.loads(
        (project / "internal" / "components.json").read_text(encoding="utf-8")
    )
    layout = json.loads(
        (project / "internal" / "wall_openings_v2.json").read_text(
            encoding="utf-8"
        )
    )
    expected_instance_count = sum(
        int((part.get("assembly") or {}).get("instance_count") or 0)
        for part in components["parts"]
    )
    groups = live_groups(components["parts"])
    part_counts = Counter(group["part_id"] for group in groups)
    expected_part_counts = {
        part["part_id"]: int(
            (part.get("assembly") or {}).get("instance_count") or 0
        )
        for part in components["parts"]
    }
    inventory_checks = {
        "live_instance_count_matches_records": len(groups)
        == expected_instance_count,
        "every_expected_part_has_visible_instance": all(
            part_counts.get(part_id, 0) == count
            for part_id, count in expected_part_counts.items()
        ),
        "vegetation_visible": part_counts.get("climbing_vine_module", 0) == 3
        and part_counts.get("porch_planter_primary", 0) == 1,
        "round_tower_present": part_counts.get("round_corner_tower", 0) == 1,
    }
    facade = facade_audit(groups, layout)

    scene = bpy.context.scene
    camera = bpy.data.objects.get("CAM_ASM_front_ortho")
    if camera is None:
        raise RuntimeError("Missing CAM_ASM_front_ortho")
    scene.camera = camera
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 900
    scene.render.resolution_y = 675
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.display.shading.light = "FLAT"
    scene.display.shading.color_type = "SINGLE"
    scene.display.shading.single_color = (1.0, 1.0, 1.0)

    mask_dir = project / "internal" / "front_visibility_masks"
    mask_dir.mkdir(parents=True, exist_ok=True)
    for path in mask_dir.glob("*.png"):
        path.unlink()
    all_meshes = [
        obj
        for obj in scene.objects
        if obj.type == "MESH" and obj.name.startswith("SK_")
    ]
    for index, group in enumerate(groups):
        for obj in all_meshes:
            obj.hide_render = True
        for obj in group["meshes"]:
            obj.hide_render = False
        safe_root = re.sub(r"[^A-Za-z0-9_.-]+", "_", group["root"])
        path = mask_dir / f"{index:02d}_{group['part_id']}_{safe_root}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        group["mask"] = str(path.relative_to(project)).replace("\\", "/")
        group["meshes"] = [obj.name for obj in group["meshes"]]
        print("mask", group["part_id"], group["root"])

    manifest = {
        "schema_version": 2,
        "source": "live_blend_enumeration",
        "camera": camera.name,
        "resolution": [scene.render.resolution_x, scene.render.resolution_y],
        "source_image": "assets/preview/assembly/castle_assembly_front_ortho.png",
        "mask_dir": str(mask_dir.relative_to(project)).replace("\\", "/"),
        "expected_instance_count": expected_instance_count,
        "live_instance_count": len(groups),
        "part_counts": dict(sorted(part_counts.items())),
        "inventory_checks": inventory_checks,
        "facade_audit": facade,
        "groups": groups,
    }
    output = project / "internal" / "front_visibility_masks.json"
    output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    status = (
        "pass"
        if all(inventory_checks.values()) and facade["status"] == "pass"
        else "repair_required"
    )
    print(
        json.dumps(
            {
                "status": status,
                "groups": len(groups),
                "expected_instance_count": expected_instance_count,
                "facade_audit": facade,
                "inventory_checks": inventory_checks,
                "manifest": str(output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
