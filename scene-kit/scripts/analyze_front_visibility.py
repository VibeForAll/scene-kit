"""Compare live front-view silhouettes and enforce the facade schedule."""

from __future__ import annotations

import argparse
import json
import shutil
from itertools import combinations
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont


ALLOWED_PAIRS = {
    frozenset(pair)
    for pair in (
        ("wall_envelope", "floor_slab_system"),
        ("wall_envelope", "stone_base_plinth"),
        ("wall_envelope", "main_roof_assembly"),
        ("wall_envelope", "tall_window_assembly"),
        ("wall_envelope", "entrance_portal"),
        ("wall_envelope", "stone_facade_trim"),
        ("wall_envelope", "corner_stone_detail"),
        ("wall_envelope", "stone_chimney_primary"),
        ("wall_envelope", "porch_railing_primary"),
        ("wall_envelope", "attic_window_assembly"),
        ("wall_envelope", "wooden_entrance_porch"),
        ("wall_envelope", "entrance_steps"),
        ("wall_envelope", "wall_lantern_primary"),
        ("wall_envelope", "climbing_vine_module"),
        ("wall_envelope", "porch_planter_primary"),
        ("wall_envelope", "round_corner_tower"),
        ("floor_slab_system", "stone_base_plinth"),
        ("floor_slab_system", "stone_facade_trim"),
        ("floor_slab_system", "corner_stone_detail"),
        ("floor_slab_system", "wooden_entrance_porch"),
        ("floor_slab_system", "stone_chimney_primary"),
        ("floor_slab_system", "round_corner_tower"),
        ("stone_base_plinth", "entrance_portal"),
        ("stone_base_plinth", "entrance_steps"),
        ("stone_base_plinth", "wooden_entrance_porch"),
        ("stone_base_plinth", "round_corner_tower"),
        ("stone_base_plinth", "climbing_vine_module"),
        ("stone_base_plinth", "porch_planter_primary"),
        ("main_roof_assembly", "tall_window_assembly"),
        ("main_roof_assembly", "stone_facade_trim"),
        ("main_roof_assembly", "stone_chimney_primary"),
        ("main_roof_assembly", "attic_window_assembly"),
        ("main_roof_assembly", "wooden_entrance_porch"),
        ("main_roof_assembly", "climbing_vine_module"),
        ("main_roof_assembly", "round_corner_tower"),
        ("tall_window_assembly", "stone_facade_trim"),
        ("tall_window_assembly", "corner_stone_detail"),
        ("tall_window_assembly", "climbing_vine_module"),
        ("tall_window_assembly", "porch_railing_primary"),
        ("entrance_portal", "wooden_entrance_porch"),
        ("entrance_portal", "entrance_steps"),
        ("entrance_portal", "wall_lantern_primary"),
        ("stone_facade_trim", "corner_stone_detail"),
        ("stone_facade_trim", "wooden_entrance_porch"),
        ("stone_facade_trim", "stone_chimney_primary"),
        ("stone_facade_trim", "round_corner_tower"),
        ("corner_stone_detail", "round_corner_tower"),
        ("corner_stone_detail", "climbing_vine_module"),
        ("stone_chimney_primary", "attic_window_assembly"),
        ("stone_chimney_primary", "round_corner_tower"),
        ("porch_railing_primary", "entrance_steps"),
        ("porch_railing_primary", "wooden_entrance_porch"),
        ("porch_railing_primary", "wall_lantern_primary"),
        ("porch_railing_primary", "porch_planter_primary"),
        ("porch_railing_primary", "climbing_vine_module"),
        ("attic_window_assembly", "stone_facade_trim"),
        ("wooden_entrance_porch", "entrance_steps"),
        ("wooden_entrance_porch", "wall_lantern_primary"),
        ("wooden_entrance_porch", "climbing_vine_module"),
        ("wooden_entrance_porch", "porch_planter_primary"),
        ("entrance_steps", "porch_planter_primary"),
        ("entrance_steps", "climbing_vine_module"),
        ("wall_lantern_primary", "climbing_vine_module"),
        ("climbing_vine_module", "porch_planter_primary"),
        ("climbing_vine_module", "round_corner_tower"),
    )
}


def alpha_mask(path):
    image = Image.open(path).convert("RGBA")
    alpha = image.getchannel("A").point(lambda value: 255 if value > 127 else 0)
    bbox = alpha.getbbox()
    visible_pixels = (
        sum(1 for value in alpha.getdata() if value > 127) if bbox else 0
    )
    return alpha, bbox, visible_pixels


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, required=True)
    args = parser.parse_args()
    project = args.project.expanduser().resolve()
    manifest_path = project / "internal" / "front_visibility_masks.json"
    output_path = project / "internal" / "assembly_front_visibility_audit.json"
    overlay_path = (
        project
        / "assets"
        / "preview"
        / "assembly"
        / "front_component_visibility_overlay.jpg"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = []
    for group in manifest["groups"]:
        mask, bbox, visible_pixels = alpha_mask(project / group["mask"])
        records.append(
            {
                **group,
                "_mask": mask,
                "bbox": bbox,
                "visible_pixels": visible_pixels,
            }
        )

    overlaps = []
    for first, second in combinations(records, 2):
        if first["part_id"] == second["part_id"]:
            continue
        a = first["bbox"]
        b = second["bbox"]
        if a is None or b is None:
            continue
        depth_overlap = (
            min(first["world_max_m"][1], second["world_max_m"][1])
            > max(first["world_min_m"][1], second["world_min_m"][1])
        )
        if not depth_overlap:
            continue
        x0, y0 = max(a[0], b[0]), max(a[1], b[1])
        x1, y1 = min(a[2], b[2]), min(a[3], b[3])
        if x0 >= x1 or y0 >= y1:
            continue
        intersection = ImageChops.multiply(
            first["_mask"].crop((x0, y0, x1, y1)),
            second["_mask"].crop((x0, y0, x1, y1)),
        )
        overlap = sum(1 for value in intersection.getdata() if value > 127)
        if overlap < 4:
            continue
        pair = frozenset((first["part_id"], second["part_id"]))
        overlaps.append(
            {
                "parts": [first["part_id"], second["part_id"]],
                "roots": [first["root"], second["root"]],
                "instance_ids": [
                    first["instance_id"],
                    second["instance_id"],
                ],
                "overlap_pixels": overlap,
                "depth_ranges_overlap": True,
                "policy": (
                    "allowed" if pair in ALLOWED_PAIRS else "review_required"
                ),
            }
        )

    tower_windows = [
        item
        for item in overlaps
        if "round_corner_tower" in item["parts"]
        and any(
            name in {"tall_window_assembly", "attic_window_assembly"}
            for name in item["parts"]
        )
    ]
    unexpected = [
        item for item in overlaps if item["policy"] == "review_required"
    ]
    empty_masks = [
        item
        for item in records
        if item["bbox"] is None or item["visible_pixels"] < 8
    ]
    plant_records = [
        item
        for item in records
        if item["part_id"]
        in {"climbing_vine_module", "porch_planter_primary"}
    ]
    plant_visibility = {
        "status": "pass"
        if len(plant_records) == 4
        and all(item["visible_pixels"] >= 8 for item in plant_records)
        else "repair_required",
        "instances": [
            {
                "part_id": item["part_id"],
                "instance_id": item["instance_id"],
                "bbox_pixels": item["bbox"],
                "visible_pixels": item["visible_pixels"],
            }
            for item in plant_records
        ],
        "expected_vines": 3,
        "expected_planters": 1,
    }
    inventory = {
        "status": "pass"
        if manifest["live_instance_count"]
        == manifest["expected_instance_count"]
        and all(manifest["inventory_checks"].values())
        else "repair_required",
        "expected_instance_count": manifest["expected_instance_count"],
        "live_instance_count": manifest["live_instance_count"],
        "checks": manifest["inventory_checks"],
        "part_counts": manifest["part_counts"],
        "rendered_groups": len(records),
    }
    facade = manifest["facade_audit"]
    checks = {
        "live_inventory_pass": inventory["status"] == "pass",
        "facade_schedule_pass": facade["status"] == "pass",
        "all_masks_nonempty": not empty_masks,
        "plants_visible": plant_visibility["status"] == "pass",
        "no_tower_window_overlap": not tower_windows,
        "no_unexpected_overlap": not unexpected,
    }
    status = "pass" if all(checks.values()) else "repair_required"

    source = Image.open(project / manifest["source_image"]).convert("RGB")
    draw = ImageDraw.Draw(source, "RGBA")
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 13)
    except OSError:
        font = ImageFont.load_default()
    flagged_parts = {
        part
        for item in unexpected + tower_windows
        for part in item["parts"]
    }
    for group in records:
        if group["bbox"] is None:
            continue
        x0, y0, x1, y1 = group["bbox"]
        color = (
            (230, 60, 55, 230)
            if group["part_id"] in flagged_parts
            else (50, 180, 220, 210)
        )
        draw.rectangle((x0, y0, x1, y1), outline=color, width=2)
        label = f"{group['part_id']} · {group['instance_id']}"
        box = draw.textbbox((x0 + 2, y0 + 2), label, font=font)
        draw.rectangle(box, fill=(15, 18, 22, 190))
        draw.text(
            (x0 + 2, y0 + 2),
            label,
            fill=(245, 245, 245, 255),
            font=font,
        )
    overlay_path.parent.mkdir(parents=True, exist_ok=True)
    source.save(overlay_path, quality=91)

    report = {
        "schema_version": 2,
        "status": status,
        "source": manifest["source"],
        "camera": manifest["camera"],
        "resolution": manifest["resolution"],
        "source_image": manifest["source_image"],
        "overlay_image": str(overlay_path.relative_to(project)).replace(
            "\\", "/"
        ),
        "checks": checks,
        "inventory": inventory,
        "facade_schedule": facade,
        "plant_visibility": plant_visibility,
        "groups": [
            {
                "part_id": group["part_id"],
                "instance_id": group["instance_id"],
                "root": group["root"],
                "root_location_m": group["root_location_m"],
                "rotation_deg": group["rotation_deg"],
                "scale": group["scale"],
                "bbox_pixels": group["bbox"],
                "visible_pixels": group["visible_pixels"],
            }
            for group in records
        ],
        "empty_masks": [
            {
                "part_id": item["part_id"],
                "instance_id": item["instance_id"],
                "root": item["root"],
            }
            for item in empty_masks
        ],
        "overlaps": overlaps,
        "unexpected_overlaps": unexpected,
        "tower_window_overlaps": tower_windows,
    }
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    shutil.rmtree(project / manifest["mask_dir"])
    manifest_path.unlink()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
