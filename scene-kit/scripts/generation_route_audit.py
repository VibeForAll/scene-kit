#!/usr/bin/env python3
"""Heuristic post-reference execution audit for Scene Kit components.

The whole-building reference model is the first gate. This report only decides
how an already mapped component should be rebuilt or generated; it does not
approve a paid generation and does not edit project state.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


PRECISE_TYPES = {
    "wall_envelope",
    "floor_slab",
    "slate_roof",
    "stone_base",
    "window",
    "divided_light_window",
    "paired_attic_window",
    "door",
    "entrance_portal",
    "stair",
    "entrance_steps",
    "railing",
    "iron_railing",
    "wooden_porch_railing",
    "chimney",
    "stone_chimney",
    "gutter",
    "downspout",
    "stone_facade_trim",
    "window_trim",
    "wall_lantern",
}
ORGANIC_TYPES = {
    "stone_relief",
    "wood_carving",
    "sculpture",
    "crest",
    "badge",
    "flower_cluster",
    "vegetation",
    "climbing_vine",
    "potted_plant",
    "organic_ornament",
}
STRUCTURE_CLASSES = {"structure"}


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} 必须是 JSON 对象")
    return value


def instance_count(part_id: str, inventory: list[dict[str, Any]]) -> int:
    counts = [
        int(item.get("instances", 1))
        for item in inventory
        if item.get("part_id") == part_id
        and isinstance(item.get("instances", 1), int)
        and not isinstance(item.get("instances", 1), bool)
    ]
    return max(counts, default=1)


def reference_model_gate(components: dict[str, Any]) -> dict[str, Any]:
    models = components.get("reference_models") or []
    ready = [
        model
        for model in models
        if isinstance(model, dict)
        and model.get("status") == "pass"
        and model.get("reference_only") is True
        and model.get("analysis_ready") is True
    ]
    return {
        "status": "pass" if ready else "blocked_reference_model_required",
        "reference_model_ids": [
            model.get("reference_model_id")
            for model in ready
            if isinstance(model.get("reference_model_id"), str)
        ],
        "message": (
            "整栋参考模型已完成归一化和组件映射，可评估组件执行方式"
            if ready
            else "必须先完成整栋三维参考模型、归一化和组件特征映射"
        ),
    }



def recommend_input_mode(part: dict[str, Any]) -> dict[str, Any]:
    """Recommend text-to-3D vs image-to-3D for a single component.

    Small organic assets (vines, flower clusters, potted plants) usually only
    have in-context reference crops that also contain the wall, window or
    ground around the asset. Feeding those crops to image-to-3D makes the
    provider import surrounding building geometry. When no isolated
    single-asset reference exists, or an image attempt already failed this
    way, text-to-3D with an explicit isolation prompt and negative list is the
    safer entry; Blender then locks the envelope, origin and triangle budget.
    """
    part_type = str(part.get("type", "")).lower()
    asset_class = str(part.get("asset_class", ""))
    organic = part_type in ORGANIC_TYPES or asset_class in {
        "vegetation",
        "decorative_ornament",
    }
    if not organic:
        return {
            "preferred": "image_to_3d",
            "eligible_modes": ["image_to_3d", "multiview_to_3d"],
            "reason": "非有机构件以参考图的几何和接口约束优先。",
            "signals": {
                "organic_asset": False,
                "isolated_asset_available": None,
                "image_to_3d_context_failure": False,
            },
        }

    pack = part.get("reference_pack") or {}
    isolated_asset = bool(pack.get("isolated_asset_available", False))
    attempt = part.get("ai_3d_attempt")
    context_failure = False
    if isinstance(attempt, dict) and attempt.get("result") in {
        "not_used",
        "failed",
    }:
        reason_text = str(attempt.get("reason", "")).lower()
        context_failure = any(
            token in reason_text
            for token in ("context", "building", "surrounding", "串景", "串入", "建筑")
        )

    if context_failure or not isolated_asset:
        return {
            "preferred": "text_to_3d",
            "eligible_modes": ["text_to_3d"],
            "reason": (
                "有机小构件只有在境裁剪参考，或图生 3D 已把环境/建筑串入单体；"
                "改用纯文生 3D 隔离提示与负面清单生成单体，再在 Blender 中"
                "旋转、减面、拟合锁定包络并外置 PBR 贴图。"
            ),
            "signals": {
                "organic_asset": True,
                "isolated_asset_available": isolated_asset,
                "image_to_3d_context_failure": context_failure,
            },
        }
    return {
        "preferred": "image_to_3d",
        "eligible_modes": ["image_to_3d", "multiview_to_3d"],
        "reason": "已有隔离单体参考，图生 3D 可同时保留轮廓、细节和材质。",
        "signals": {
            "organic_asset": True,
            "isolated_asset_available": isolated_asset,
            "image_to_3d_context_failure": context_failure,
        },
    }


def audit_part(part: dict[str, Any], inventory: list[dict[str, Any]]) -> dict[str, Any]:
    part_id = str(part.get("part_id", ""))
    part_type = str(part.get("type", "")).lower()
    asset_class = str(part.get("asset_class", ""))
    repeat_count = instance_count(part_id, inventory)
    free_count = len(part.get("free") or [])
    locked_count = len(part.get("locked") or {})
    reference_pack = part.get("reference_pack") or {}
    component_references = {
        value
        for key in ("geometry", "appearance")
        for value in (
            reference_pack.get(key, [])
            if isinstance(reference_pack.get(key, []), list)
            else []
        )
        if isinstance(value, str) and value.strip()
    }
    precise = part_type in PRECISE_TYPES
    organic = part_type in ORGANIC_TYPES or asset_class in {
        "vegetation",
        "decorative_ornament",
    }

    blender_score = 0
    ai_3d_score = 0
    reasons: list[str] = []

    if precise:
        blender_score += 4
        reasons.append("构件类型要求精确轮廓、接口或重复规律")
    if asset_class in STRUCTURE_CLASSES:
        blender_score += 2
        reasons.append("结构构件优先由 Blender 参数化控制")
    if repeat_count >= 5:
        blender_score += 4
        reasons.append(f"{repeat_count} 个实例，应只建一次并实例复用")
    elif repeat_count >= 2:
        blender_score += 2
        reasons.append(f"{repeat_count} 个实例，适合镜像或实例复用")
    if free_count <= 1:
        blender_score += 2
        reasons.append("自由造型区很少，AI 生成价值低")
    if locked_count >= 3:
        blender_score += 1
        reasons.append("锁定接口较多")

    if organic:
        ai_3d_score += 4
        reasons.append("构件具有有机、雕刻或手工造型价值")
    if free_count >= 3:
        ai_3d_score += 2
        reasons.append("存在多个可自由解释的造型细节")
    if repeat_count <= 2:
        ai_3d_score += 2
        reasons.append("实例少，不太适合把建模成本摊到大量复用中")
    if asset_class in {"decorative_ornament", "vegetation"}:
        ai_3d_score += 1
        reasons.append("非结构表现资产可能从 AI 造型中获益")

    if precise and repeat_count >= 5:
        recommended = "blender_procedural"
        confidence = "high"
    elif blender_score >= ai_3d_score + 2:
        recommended = "blender_procedural"
        confidence = "high" if blender_score >= ai_3d_score + 4 else "medium"
    elif ai_3d_score >= blender_score + 2:
        recommended = "ai_3d"
        confidence = "high" if ai_3d_score >= blender_score + 4 else "medium"
    else:
        recommended = "blender_procedural"
        confidence = "low"
        reasons.append("分数接近，默认先尝试低成本的 Blender 参数化")

    precision_demand = (
        "exact"
        if precise and repeat_count >= 2
        else "organic"
        if organic and free_count >= 3
        else "design_guided"
    )
    blender_effort = (
        "low"
        if recommended == "blender_procedural" and not organic and free_count <= 1
        else "high"
        if organic and free_count >= 3
        else "medium"
    )
    ai_3d_expected_benefit = (
        "high"
        if organic and free_count >= 3
        else "medium"
        if organic
        else "low"
    )
    token_risk = (
        "high"
        if repeat_count >= 5 or precision_demand == "exact"
        else "medium"
        if repeat_count >= 2
        else "low"
    )
    if recommended == "ai_3d" and ai_3d_expected_benefit == "low":
        recommended = "blender_procedural"
        confidence = "medium"
        reasons.append("AI 3D 造型收益为 low，改由 Blender 参数化")
    return {
        "part_id": part_id,
        "type": part_type,
        "asset_class": asset_class,
        "instance_count": repeat_count,
        "free_zone_count": free_count,
        "reference_view_count": len(component_references),
        "requires_multiview_reference": precise,
        "requires_whole_building_reference": True,
        "blender_score": blender_score,
        "ai_3d_score": ai_3d_score,
        "recommended_route": recommended,
        "confidence": confidence,
        "precision_demand": precision_demand,
        "blender_effort": blender_effort,
        "ai_3d_expected_benefit": ai_3d_expected_benefit,
        "ai_3d_token_risk": token_risk,
        "provider_agnostic": True,
        "input_mode_guidance": recommend_input_mode(part),
        "provider_selection": (
            {
                "status": "pending",
                "selected_provider": None,
                "note": "在提交前从当前可用插件、外部平台或模型库中选择，不预设厂商。",
            }
            if recommended == "ai_3d"
            else None
        ),
        "reasons": reasons,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Recommend Blender vs a provider-neutral AI 3D route before "
            "paid generation."
        )
    )
    parser.add_argument("project", type=Path)
    parser.add_argument("--part", help="Only audit one part_id")
    parser.add_argument(
        "--output",
        type=Path,
        help="Default: <project>/internal/generation_route_review.json",
    )
    args = parser.parse_args(argv)
    project = args.project.resolve()
    components = read_json(project / "internal" / "components.json")
    inventory = components.get("visual_inventory") or []
    gate = reference_model_gate(components)
    parts = [
        part
        for part in components.get("parts") or []
        if isinstance(part, dict)
        and (args.part is None or part.get("part_id") == args.part)
        and part.get("decision") == "ai_3d"
    ]
    if args.part and not parts:
        raise ValueError(f"找不到 AI 组件：{args.part}")
    report = {
        "schema_version": 1,
        "checked_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": (
            "diagnostic_only"
            if gate["status"] == "pass"
            else "blocked_reference_model_required"
        ),
        "reference_model_gate": gate,
        "parts": [audit_part(part, inventory) for part in parts],
    }
    output = (
        args.output
        or project / "internal" / "generation_route_review.json"
    ).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"Route review written to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
