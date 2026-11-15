#!/usr/bin/env python3
"""Concept-first project state and validation helpers for scene-kit."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from parametric_components import validate_registry as validate_parametric_registry


SCHEMA_VERSION = 1
SKILL_VERSION = "7.21"
SUPPORTED_SKILL_VERSIONS = {
    "7.1",
    "7.2",
    "7.3",
    "7.4",
    "7.5",
    "7.6",
    "7.7",
    "7.8",
    "7.9",
    "7.10",
    "7.11",
    "7.12",
    "7.13",
    "7.14",
    "7.15",
    "7.16",
    "7.17",
    "7.18",
    "7.19",
    "7.20",
    "7.21",
}
STAGES = [
    "BRIEF",
    "CONCEPTS",
    "DESIGN",
    "COMPONENTS",
    "REFERENCES",
    "GENERATION",
    "ASSEMBLY",
    "FINISHING",
    "REVIEW",
    "COMPLETE",
]
CONCEPT_VIEW_SPECS = (
    {
        "id": "top",
        "label_en": "TOP ORTHOGRAPHIC VIEW",
        "label_zh": "正交俯视图",
        "instruction_en": "Strict orthographic top view, camera directly above the building looking straight down, entire roof and footprint visible, parallel lines remain parallel, no interior cutaway.",
        "instruction_zh": "严格正交俯视，相机位于建筑正上方垂直向下，完整展示屋顶和占地轮廓，线条不透视收缩，不做室内剖切。",
    },
    {
        "id": "bottom",
        "label_en": "BOTTOM ORTHOGRAPHIC VIEW",
        "label_zh": "正交仰视图",
        "instruction_en": "Strict orthographic bottom view, camera directly below the building looking straight up, entire underside and footprint visible without a ground plane blocking it, parallel lines remain parallel, no interior cutaway.",
        "instruction_zh": "严格正交仰视，相机位于建筑正下方垂直向上，完整展示底面和占地轮廓，地面不得遮挡模型，线条不透视收缩，不做室内剖切。",
    },
    {
        "id": "left",
        "label_en": "LEFT-SIDE ORTHOGRAPHIC ELEVATION",
        "label_zh": "左侧正交立面图",
        "instruction_en": "Strict orthographic left-side elevation, camera directly to the building's left, entire building visible, horizontal and vertical lines parallel, neutral background, no perspective distortion.",
        "instruction_zh": "严格正交左侧立面，相机位于建筑左侧正向平视，整栋建筑完整可见，水平线和垂直线保持平行，中性背景，无透视变形。",
    },
    {
        "id": "right",
        "label_en": "RIGHT-SIDE ORTHOGRAPHIC ELEVATION",
        "label_zh": "右侧正交立面图",
        "instruction_en": "Strict orthographic right-side elevation, camera directly to the building's right, entire building visible, horizontal and vertical lines parallel, neutral background, no perspective distortion.",
        "instruction_zh": "严格正交右侧立面，相机位于建筑右侧正向平视，整栋建筑完整可见，水平线和垂直线保持平行，中性背景，无透视变形。",
    },
    {
        "id": "front",
        "label_en": "FRONT ORTHOGRAPHIC ELEVATION",
        "label_zh": "正面正交立面图",
        "instruction_en": "Strict orthographic front elevation, camera directly in front of the building, entire facade and roof visible, horizontal and vertical lines parallel, neutral background, no perspective distortion.",
        "instruction_zh": "严格正交正面立面，相机位于建筑正前方平视，完整展示立面和屋顶，水平线和垂直线保持平行，中性背景，无透视变形。",
    },
    {
        "id": "back",
        "label_en": "BACK ORTHOGRAPHIC ELEVATION",
        "label_zh": "背面正交立面图",
        "instruction_en": "Strict orthographic back elevation, camera directly behind the building, entire rear facade and roof visible, horizontal and vertical lines parallel, neutral background, no perspective distortion.",
        "instruction_zh": "严格正交背面立面，相机位于建筑正后方平视，完整展示背立面和屋顶，水平线和垂直线保持平行，中性背景，无透视变形。",
    },
    {
        "id": "front_left_45",
        "label_en": "FRONT-LEFT 45-DEGREE VIEW",
        "label_zh": "左前侧 45 度视图",
        "instruction_en": "Orthographic 45-degree front-left three-quarter view, camera on the front-left diagonal at consistent mid-building height, entire building visible, parallel lines preserved, neutral background, no cropped roof or base.",
        "instruction_zh": "正交 45 度左前侧视图，相机位于建筑左前方对角线且保持中等建筑高度，整栋建筑完整可见，平行线不透视收缩，中性背景，屋顶和基座不得裁切。",
    },
    {
        "id": "front_right_45",
        "label_en": "FRONT-RIGHT 45-DEGREE VIEW",
        "label_zh": "右前侧 45 度视图",
        "instruction_en": "Orthographic 45-degree front-right three-quarter view, camera on the front-right diagonal at consistent mid-building height, entire building visible, parallel lines preserved, neutral background, no cropped roof or base.",
        "instruction_zh": "正交 45 度右前侧视图，相机位于建筑右前方对角线且保持中等建筑高度，整栋建筑完整可见，平行线不透视收缩，中性背景，屋顶和基座不得裁切。",
    },
    {
        "id": "back_left_45",
        "label_en": "BACK-LEFT 45-DEGREE VIEW",
        "label_zh": "左后侧 45 度视图",
        "instruction_en": "Orthographic 45-degree back-left three-quarter view, camera on the back-left diagonal at consistent mid-building height, entire building visible, parallel lines preserved, neutral background, no cropped roof or base.",
        "instruction_zh": "正交 45 度左后侧视图，相机位于建筑左后方对角线且保持中等建筑高度，整栋建筑完整可见，平行线不透视收缩，中性背景，屋顶和基座不得裁切。",
    },
    {
        "id": "back_right_45",
        "label_en": "BACK-RIGHT 45-DEGREE VIEW",
        "label_zh": "右后侧 45 度视图",
        "instruction_en": "Orthographic 45-degree back-right three-quarter view, camera on the back-right diagonal at consistent mid-building height, entire building visible, parallel lines preserved, neutral background, no cropped roof or base.",
        "instruction_zh": "正交 45 度右后侧视图，相机位于建筑右后方对角线且保持中等建筑高度，整栋建筑完整可见，平行线不透视收缩，中性背景，屋顶和基座不得裁切。",
    },
)
CONCEPT_VIEW_IDS = tuple(spec["id"] for spec in CONCEPT_VIEW_SPECS)
DELIVERY_PROFILES = {"unity_realtime", "offline_render", "concept_blockout"}
RENDER_DISPLAY_MODES = {
    "summary_only",
    "milestone_contact_sheet",
    "show_each_component",
}
DECISIONS = {"ai_3d", "library", "parametric", "reuse"}
PROMPT_KEYS = {"positive_en", "negative_en", "positive_zh", "negative_zh"}
IMAGE_INPUT_MODES = {"image_to_3d", "multiview_to_3d"}
INPUT_MODES = IMAGE_INPUT_MODES | {"text_to_3d"}
USER_CONFIRMED_STAGES = {"CONCEPTS", "COMPONENTS", "REFERENCES", "REVIEW"}
FINISHING_STATUSES = {"pending", "in_progress", "repair_required", "pass"}
DEFECT_SEVERITIES = {"blocker", "high", "medium", "low"}
DEFECT_STATUSES = {"fixed", "deferred"}
LIFECYCLE_RESULTS = {"pass", "repaired", "user_decision_required"}
LIBRARY_SCHEMA_VERSION = 1
ASSET_CLASSES = {
    "architectural_component",
    "decorative_ornament",
    "vegetation",
    "site_element",
    "structure",
}
REUSE_MODES = {"direct", "scale_variants", "placement_variants", "reference_only"}
MODEL_FORMATS = {".glb", ".gltf", ".obj", ".fbx"}
DETAIL_CATEGORIES = {
    "roof_and_skyline",
    "openings_and_frames",
    "trim_and_ornament",
    "attachments_and_services",
    "site_and_vegetation",
    "surface_and_material_patterns",
}
DETAIL_COVERAGE_KEYS = {
    "roof_and_skyline_scanned",
    "openings_and_frames_scanned",
    "trim_and_ornament_scanned",
    "attachments_and_services_scanned",
    "site_and_vegetation_scanned",
    "surface_and_material_patterns_scanned",
}
DETAIL_VISUAL_IMPACTS = {"silhouette", "near_view", "surface_only"}
DETAIL_DISPOSITIONS = {"part", "parametric", "reuse", "material"}
GENERATION_ROUTES = {
    "blender_procedural",
    "blender_manual",
    "library",
    "ai_3d",
    "tripo",
    "external_ai_3d",
}
ROUTE_STATUSES = {"pending", "approved", "rejected"}
ROUTE_PRECISIONS = {"exact", "design_guided", "organic"}
ROUTE_LEVELS = {"low", "medium", "high"}
MATERIAL_REVIEW_STATUSES = {"pending", "repair_required", "pass"}
FINE_STRUCTURE_STATUSES = {"pending", "repair_required", "pass"}
FINE_STRUCTURE_CONFIDENCE = {"low", "medium", "high"}
REFERENCE_CONSENSUS_STATUSES = {"pending", "repair_required", "pass"}
REFERENCE_CONSENSUS_CHECKS = {
    "identity_consistent",
    "silhouette_consistent",
    "structure_consistent",
    "material_consistent",
    "attachment_consistent",
    "lighting_variation_explained",
}
BOUNDARY_REVIEW_STATUSES = {"pending", "repair_required", "pass"}
BOUNDARY_SURFACES = {
    "front",
    "back",
    "left",
    "right",
    "top",
    "bottom",
}
BOUNDARY_REVIEW_CHECKS = {
    "volume_complete",
    "all_surfaces_accounted",
    "attachments_inventory_complete",
    "attached_geometry_included",
    "material_zones_complete",
    "interface_vs_overall_bounds_verified",
}
REFERENCE_MODEL_STATUSES = {"pending", "repair_required", "pass"}
REFERENCE_MODEL_INPUT_MODES = {
    "single_image_to_3d",
    "multiview_to_3d",
}
FEATURE_EXTRACTION_STATUSES = {"pending", "partial", "pass"}
WINDOW_PART_TYPES = {
    "window",
    "divided_light_window",
    "paired_attic_window",
}
PRECISE_REFERENCE_TYPES = WINDOW_PART_TYPES | {
    "door",
    "entrance_portal",
    "iron_railing",
    "wooden_porch_railing",
}
TEXTURE_SOURCES = {"project_pbr", "polyhaven", "generated", "existing"}


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
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


def write_text_atomic(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
        newline="\n",
    ) as handle:
        handle.write(value)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "scene-project"


def project_files(root: Path) -> dict[str, Path]:
    return {
        "scene": root / "scene.json",
        "progress": root / "progress.json",
        "brief": root / "internal" / "brief.json",
        "concepts": root / "internal" / "concept_directions.json",
        "design": root / "internal" / "design_contract.json",
        "components": root / "internal" / "components.json",
        "assembly": root / "internal" / "assembly.json",
    }


def default_model_library_root() -> Path:
    configured = os.environ.get("SCENE_KIT_LIBRARY")
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path.home() / ".scene-kit" / "model-library").resolve()


def model_library_files(root: Path) -> dict[str, Path]:
    root = root.resolve()
    return {
        "catalog": root / "catalog.json",
        "assets": root / "assets",
    }


def initialize_model_library(root: Path | None = None) -> dict[str, Any]:
    root = (root or default_model_library_root()).expanduser().resolve()
    paths = model_library_files(root)
    if paths["catalog"].exists():
        catalog = read_json(paths["catalog"])
        errors = validate_model_library(root, catalog)
        if errors:
            raise ValueError("模型库校验未通过：" + "；".join(errors[:5]))
        return {
            "library_root": str(root),
            "asset_count": len(catalog.get("assets", [])),
            "initialized": False,
        }
    if root.exists() and any(root.iterdir()):
        raise ValueError(f"模型库目录不是空目录且没有 catalog.json：{root}")
    paths["assets"].mkdir(parents=True, exist_ok=True)
    write_json_atomic(
        paths["catalog"],
        {
            "schema_version": LIBRARY_SCHEMA_VERSION,
            "library_id": "scene-kit-model-library",
            "updated_at": now_iso(),
            "assets": [],
        },
    )
    return {
        "library_root": str(root),
        "asset_count": 0,
        "initialized": True,
    }


def _require_library_catalog(root: Path) -> tuple[dict[str, Any], dict[str, Path]]:
    root = root.expanduser().resolve()
    paths = model_library_files(root)
    if not paths["catalog"].is_file():
        raise ValueError(
            f"模型库尚未初始化：{root}；先运行 library-init --library <目录>"
        )
    return read_json(paths["catalog"]), paths


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _positive_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and value > 0
    )


def _infer_asset_class(part: dict[str, Any]) -> str:
    explicit = part.get("asset_class")
    if isinstance(explicit, str) and explicit in ASSET_CLASSES:
        return explicit
    part_type = str(part.get("type") or "").lower()
    if any(token in part_type for token in ("relief", "ornament", "molding", "sculpture", "crest", "frieze")):
        return "decorative_ornament"
    if any(token in part_type for token in ("plant", "flower", "vine", "tree", "shrub", "grass", "foliage")):
        return "vegetation"
    if any(token in part_type for token in ("lamp", "bench", "pot", "planter", "sign", "fountain")):
        return "site_element"
    if any(token in part_type for token in ("wall", "floor", "roof", "stair", "foundation", "plinth")):
        return "structure"
    return "architectural_component"


def _part_model_dimensions(part: dict[str, Any]) -> dict[str, float]:
    metadata = part.get("library_metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    explicit = metadata.get("dimensions_m")
    if isinstance(explicit, dict):
        dimensions = {
            key: explicit.get(key)
            for key in ("width", "height", "depth")
        }
        if all(_positive_number(value) for value in dimensions.values()):
            return {key: float(value) for key, value in dimensions.items()}
    locked = part.get("locked")
    if not isinstance(locked, dict):
        locked = {}
    candidates = {
        "width": ("interface_width_m", "width_m", "width", "bounding_width_m"),
        "height": ("interface_height_m", "height_m", "height", "bounding_height_m"),
        "depth": ("thickness_m", "depth_m", "depth", "bounding_depth_m"),
    }
    dimensions: dict[str, float] = {}
    for key, names in candidates.items():
        value = next(
            (locked.get(name) for name in names if _positive_number(locked.get(name))),
            None,
        )
        if value is None:
            raise ValueError(
                f"{part.get('part_id')} 缺少可入库的 {key} 尺寸；"
                "请在 library_metadata.dimensions_m 或 locked 中记录"
            )
        dimensions[key] = float(value)
    return dimensions


def add_component_to_library(
    project_root: Path,
    part_id: str,
    library_root: Path | None = None,
    confirmed_by_user: bool = False,
) -> dict[str, Any]:
    _require(confirmed_by_user, "加入模型库需要用户明确确认")
    project_root = project_root.resolve()
    library_root = (library_root or default_model_library_root()).expanduser().resolve()
    catalog, library_paths = _require_library_catalog(library_root)
    paths = project_files(project_root)
    components = read_json(paths["components"])
    part = next(
        (
            item
            for item in components.get("parts", [])
            if isinstance(item, dict) and item.get("part_id") == part_id
        ),
        None,
    )
    if part is None:
        raise ValueError(f"项目中找不到组件：{part_id}")
    generation = part.get("generation")
    if not isinstance(generation, dict):
        raise ValueError(f"{part_id} 没有生成记录，不能加入模型库")
    if generation.get("status") not in {"generated", "approved", "normalized"}:
        raise ValueError(f"{part_id} 尚未生成完成")
    source_value = generation.get("source_path")
    source_path = _relative_path(
        source_value,
        project_root,
        f"{part_id}.generation.source_path",
        [],
    )
    if source_path is None or not source_path.is_file():
        raise ValueError(f"{part_id} 的模型文件不存在")
    suffix = source_path.suffix.lower()
    if suffix not in MODEL_FORMATS:
        raise ValueError(f"{part_id} 的模型格式不支持入库：{suffix}")
    qa = part.get("qa")
    if not isinstance(qa, dict) or qa.get("result") != "pass":
        raise ValueError(f"{part_id} 尚未通过 QA，不能加入模型库")
    review = part.get("review")
    for key in ("surface_quality", "construction_logic"):
        if not isinstance(review, dict) or review.get(key) is not True:
            raise ValueError(
                f"{part_id} 的 {key} 尚未通过，不能加入模型库"
            )
    comparison_value = qa.get("comparison_path")
    comparison_path = _relative_path(
        comparison_value,
        project_root,
        f"{part_id}.qa.comparison_path",
        [],
    )
    if comparison_path is None or not comparison_path.is_file():
        raise ValueError(f"{part_id} 缺少参考对照图，不能加入模型库")

    metadata = part.get("library_metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    asset_class = _infer_asset_class(part)
    part_type = metadata.get("type") or part.get("type")
    if not _nonempty_text(part_type):
        raise ValueError(f"{part_id} 缺少 type，无法判断门、窗、浮雕或植物")
    dimensions = _part_model_dimensions(part)
    source_hash = _sha256_file(source_path)
    existing = next(
        (
            asset
            for asset in catalog.get("assets", [])
            if asset.get("technical", {}).get("sha256") == source_hash
        ),
        None,
    )
    if existing is not None:
        return {
            "added": False,
            "duplicate_of": existing.get("asset_id"),
            "asset": existing,
        }

    scene = read_json(paths["scene"])
    name = (
        metadata.get("name")
        or part.get("purpose")
        or str(part_type).replace("_", " ").title()
    )
    asset_id = f"{slugify(str(name))}-{source_hash[:8]}"
    asset_dir = library_paths["assets"] / asset_id
    asset_dir.mkdir(parents=True, exist_ok=False)
    stored_model = asset_dir / f"model{suffix}"
    stored_preview = asset_dir / "comparison.png"
    shutil.copy2(source_path, stored_model)
    shutil.copy2(comparison_path, stored_preview)
    now = now_iso()
    tags = metadata.get("tags")
    if not isinstance(tags, list) or not all(_nonempty_text(tag) for tag in tags):
        tags = [str(part_type)]
    materials = metadata.get("materials")
    if not isinstance(materials, list):
        guided = part.get("guided")
        materials = guided.get("materials", []) if isinstance(guided, dict) else []
    style = metadata.get("style")
    if not isinstance(style, dict):
        guided = part.get("guided")
        style = {
            "keywords": [guided.get("silhouette")] if isinstance(guided, dict) and _nonempty_text(guided.get("silhouette")) else [],
            "palette": [],
        }
    reuse = metadata.get("reuse")
    if not isinstance(reuse, dict):
        reuse = {
            "allowed": True,
            "mode": "scale_variants",
            "constraints": [],
        }
    if reuse.get("mode") not in REUSE_MODES:
        raise ValueError(f"{part_id} 的 library_metadata.reuse.mode 无效")
    locked = part.get("locked") if isinstance(part.get("locked"), dict) else {}
    entry = {
        "asset_id": asset_id,
        "name": name,
        "version": 1,
        "status": "active",
        "asset_class": asset_class,
        "type": part_type,
        "tags": tags,
        "description": metadata.get("description") or part.get("purpose") or "",
        "source_project": {
            "project_id": scene.get("project_id"),
            "object_id": components.get("object_id"),
            "part_id": part_id,
        },
        "files": {
            "model": stored_model.relative_to(library_root).as_posix(),
            "preview": stored_preview.relative_to(library_root).as_posix(),
        },
        "geometry": {
            "dimensions_m": dimensions,
            "origin": locked.get("origin", "bottom_center"),
            "forward": locked.get("forward", "-Y"),
            "interfaces": {
                key: value
                for key, value in locked.items()
                if key not in {"origin", "forward"}
            },
        },
        "materials": materials,
        "style": style,
        "reuse": reuse,
        "license": metadata.get(
            "license",
            {"kind": "project_generated", "attribution": ""},
        ),
        "technical": {
            "format": suffix.lstrip("."),
            "sha256": source_hash,
            "polygon_count": metadata.get("polygon_count"),
        },
        "qa": {
            "result": "pass",
            "checked_at": now,
            "comparison": stored_preview.relative_to(library_root).as_posix(),
        },
        "created_at": now,
    }
    catalog.setdefault("assets", []).append(entry)
    catalog["updated_at"] = now
    write_json_atomic(library_paths["catalog"], catalog)
    part["library_ref"] = {
        "asset_id": asset_id,
        "version": 1,
        "status": "added",
        "library_root": str(library_root),
        "added_at": now,
    }
    write_json_atomic(paths["components"], components)
    return {"added": True, "asset": entry}


def search_model_library(
    library_root: Path | None = None,
    query: str = "",
    asset_class: str | None = None,
    type_filter: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    library_root = (library_root or default_model_library_root()).expanduser().resolve()
    catalog, _ = _require_library_catalog(library_root)
    terms = [term for term in query.lower().split() if term]
    scored: list[tuple[int, dict[str, Any]]] = []
    for asset in catalog.get("assets", []):
        if not isinstance(asset, dict):
            continue
        if asset.get("status") != "active":
            continue
        if asset_class and asset.get("asset_class") != asset_class:
            continue
        if type_filter and asset.get("type") != type_filter:
            continue
        searchable = json.dumps(asset, ensure_ascii=False).lower()
        score = sum(1 for term in terms if term in searchable)
        if terms and score == 0:
            continue
        scored.append((score, asset))
    scored.sort(
        key=lambda item: (
            item[0],
            str(item[1].get("created_at", "")),
        ),
        reverse=True,
    )
    assets = [asset for _, asset in scored[: max(0, limit)]]
    return {
        "library_root": str(library_root),
        "count": len(assets),
        "query": query,
        "assets": assets,
    }


def validate_model_library(
    root: Path | None = None,
    catalog: dict[str, Any] | None = None,
) -> list[str]:
    root = (root or default_model_library_root()).expanduser().resolve()
    if catalog is None:
        catalog, _ = _require_library_catalog(root)
    errors: list[str] = []
    if catalog.get("schema_version") != LIBRARY_SCHEMA_VERSION:
        errors.append(f"catalog.schema_version 必须为 {LIBRARY_SCHEMA_VERSION}")
    assets = catalog.get("assets")
    if not isinstance(assets, list):
        errors.append("catalog.assets 必须是数组")
        return errors
    asset_ids: set[str] = set()
    hashes: set[str] = set()
    for index, asset in enumerate(assets):
        where = f"assets[{index}]"
        if not isinstance(asset, dict):
            errors.append(f"{where} 必须是对象")
            continue
        asset_id = asset.get("asset_id")
        if not isinstance(asset_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", asset_id):
            errors.append(f"{where}.asset_id 无效")
        elif asset_id in asset_ids:
            errors.append(f"重复 asset_id：{asset_id}")
        else:
            asset_ids.add(asset_id)
        if not _nonempty_text(asset.get("name")):
            errors.append(f"{where}.name 不能为空")
        if not _nonempty_text(asset.get("type")):
            errors.append(f"{where}.type 不能为空")
        if asset.get("asset_class") not in ASSET_CLASSES:
            errors.append(f"{where}.asset_class 无效")
        if asset.get("status") not in {"active", "deprecated"}:
            errors.append(f"{where}.status 无效")
        if not isinstance(asset.get("tags"), list) or not asset.get("tags"):
            errors.append(f"{where}.tags 不能为空")
        files = asset.get("files")
        if not isinstance(files, dict):
            errors.append(f"{where}.files 必须是对象")
            files = {}
        for key in ("model", "preview"):
            value = files.get(key)
            stored = _relative_path(value, root, f"{where}.files.{key}", [])
            if stored is None or not stored.is_file():
                errors.append(f"{where}.files.{key} 不存在")
        model_path = _relative_path(
            files.get("model"), root, f"{where}.files.model", []
        )
        if model_path is not None and model_path.suffix.lower() not in MODEL_FORMATS:
            errors.append(f"{where}.files.model 格式不支持")
        technical = asset.get("technical")
        if not isinstance(technical, dict):
            errors.append(f"{where}.technical 必须是对象")
            technical = {}
        digest = technical.get("sha256")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            errors.append(f"{where}.technical.sha256 无效")
        elif model_path is not None and model_path.is_file() and _sha256_file(model_path) != digest:
            errors.append(f"{where}.technical.sha256 与模型文件不一致")
        elif digest in hashes:
            errors.append(f"{where}.technical.sha256 与其他资产重复")
        else:
            hashes.add(digest)
        geometry = asset.get("geometry")
        if not isinstance(geometry, dict):
            errors.append(f"{where}.geometry 必须是对象")
            geometry = {}
        dimensions = geometry.get("dimensions_m")
        if not isinstance(dimensions, dict):
            errors.append(f"{where}.geometry.dimensions_m 必须是对象")
        else:
            for dimension in ("width", "height", "depth"):
                if not _positive_number(dimensions.get(dimension)):
                    errors.append(
                        f"{where}.geometry.dimensions_m.{dimension} 必须大于 0"
                    )
        reuse = asset.get("reuse")
        if not isinstance(reuse, dict) or reuse.get("mode") not in REUSE_MODES:
            errors.append(f"{where}.reuse.mode 无效")
        if not isinstance(asset.get("materials"), list):
            errors.append(f"{where}.materials 必须是数组")
        license_value = asset.get("license")
        if not isinstance(license_value, dict) or not _nonempty_text(license_value.get("kind")):
            errors.append(f"{where}.license.kind 不能为空")
        qa = asset.get("qa")
        if not isinstance(qa, dict) or qa.get("result") != "pass":
            errors.append(f"{where}.qa.result 必须为 pass")
        if not isinstance(asset.get("source_project"), dict):
            errors.append(f"{where}.source_project 必须是对象")
    return errors


def link_library_asset(
    project_root: Path,
    part_id: str,
    asset_id: str,
    library_root: Path | None = None,
    confirmed_by_user: bool = False,
) -> dict[str, Any]:
    _require(confirmed_by_user, "从模型库选用资产需要用户明确确认")
    library_root = (library_root or default_model_library_root()).expanduser().resolve()
    catalog, _ = _require_library_catalog(library_root)
    errors = validate_model_library(library_root, catalog)
    if errors:
        raise ValueError("模型库校验未通过：" + "；".join(errors[:5]))
    asset = next(
        (
            item
            for item in catalog.get("assets", [])
            if item.get("asset_id") == asset_id and item.get("status") == "active"
        ),
        None,
    )
    if asset is None:
        raise ValueError(f"模型库中找不到可用资产：{asset_id}")
    project_root = project_root.resolve()
    paths = project_files(project_root)
    components = read_json(paths["components"])
    part = next(
        (
            item
            for item in components.get("parts", [])
            if isinstance(item, dict) and item.get("part_id") == part_id
        ),
        None,
    )
    if part is None:
        raise ValueError(f"项目中找不到组件：{part_id}")
    part["decision"] = "library"
    part["library_source"] = "scene_kit_model_library"
    part["library_ref"] = {
        "asset_id": asset_id,
        "version": asset.get("version"),
        "library_root": str(library_root),
        "model": asset.get("files", {}).get("model"),
        "selected_at": now_iso(),
    }
    write_json_atomic(paths["components"], components)
    return {"linked": True, "part_id": part_id, "asset_id": asset_id}


def initialize_project(root: Path, name: str) -> dict[str, Any]:
    root = root.resolve()
    if root.exists() and any(root.iterdir()):
        raise ValueError(f"项目目录不是空目录：{root}")
    for relative in [
        "internal",
        "concepts",
        "preview/references",
        "preview/qa",
        "preview/finishing",
        "raw",
        "out",
        "export",
    ]:
        (root / relative).mkdir(parents=True, exist_ok=True)

    write_json_atomic(
        root / "scene.json",
        {
            "schema_version": SCHEMA_VERSION,
            "project_id": slugify(name),
            "name": name,
            "skill_version": SKILL_VERSION,
            "concept_first": True,
            "delivery": {
                "profile": "unity_realtime",
                "camera_use": "street_three_quarter",
            },
            "render_policy": {
                "qa_render": "required",
                "display_mode": "summary_only",
                "display_requires_confirmation": True,
                "extra_presentation_renders_require_confirmation": True,
            },
            "created_at": now_iso(),
        },
    )
    write_json_atomic(
        root / "progress.json",
        {
            "schema_version": SCHEMA_VERSION,
            "mode": "concept_first",
            "stage": "BRIEF",
            "last_approved_stage": None,
            "pending_decision": None,
            "current_object": "B01",
            "history": [],
            "updated_at": now_iso(),
        },
    )
    write_json_atomic(
        root / "internal" / "brief.json",
        {
            "schema_version": SCHEMA_VERSION,
            "object_id": "B01",
            "summary": "",
            "floors": 0,
            "footprint_m": {"width": 0.0, "depth": 0.0},
            "critical_dimensions": {},
            "spatial_constraints": [],
            "design_goals": [],
            "degrees_of_freedom": [],
            "delivery": "unity_realtime",
            "camera_use": "street_three_quarter",
            "quality_target": {
                "primary_view": "street_three_quarter",
                "target_resolution": [1920, 1080],
                "quality_priority": [
                    "reference_match",
                    "surface_quality",
                    "construction_logic",
                ],
                "polygon_budget": None,
                "material_budget": None,
            },
        },
    )
    write_json_atomic(
        root / "internal" / "concept_directions.json",
        {
            "schema_version": SCHEMA_VERSION,
            "status": "draft",
            "selected_direction": None,
            "directions": [],
        },
    )
    write_json_atomic(
        root / "internal" / "design_contract.json",
        {
            "schema_version": SCHEMA_VERSION,
            "status": "draft",
            "selected_direction": None,
            "style_id": None,
            "style_version": 0,
            "fixed_style": {},
            "palette": [],
            "materials": [],
            "geometry_language": [],
            "component_rules": {},
        },
    )
    write_json_atomic(
        root / "internal" / "components.json",
        {
            "schema_version": SCHEMA_VERSION,
            "object_id": "B01",
            "parts": [],
            "visual_inventory": [],
            "quantity_audit": {
                "status": "pending",
                "source_views": [],
                "counts": {},
                "checks": {},
                "unresolved": [],
            },
            "attachment_integrity_audit": {
                "status": "pending",
                "source_views": [],
                "items": [],
                "checks": {},
                "unresolved": [],
            },
            "detail_audit": {
                "status": "pending",
                "scan_views": [],
                "coverage": {
                    "roof_and_skyline_scanned": False,
                    "openings_and_frames_scanned": False,
                    "trim_and_ornament_scanned": False,
                    "attachments_and_services_scanned": False,
                    "site_and_vegetation_scanned": False,
                    "surface_and_material_patterns_scanned": False,
                },
                "features": [],
                "unresolved": [],
            },
            "decomposition_review": {
                "status": "pending",
                "source_views": [],
                "checks": {
                    "inventory_complete": False,
                    "multi_view_consistent": False,
                    "attachment_logic_verified": False,
                    "assembly_not_fragmented": False,
                    "detail_features_complete": False,
                    "detail_geometry_decisions_verified": False,
                    "quantity_verified": False,
                    "attachment_integrity_verified": False,
                },
                "notes": [],
            },
        },
    )
    write_json_atomic(
        root / "internal" / "assembly.json",
        {
            "schema_version": SCHEMA_VERSION,
            "object_id": "B01",
            "blend_path": None,
            "screenshots": [],
            "instances": [],
            "artifact": {
                "revision": 0,
                "blend_sha256": None,
                "rendered_at": None,
            },
            "finishing": {
                "status": "pending",
            },
            "accepted": False,
        },
    )
    return {"root": str(root), "project_id": slugify(name), "skill_version": SKILL_VERSION}


def concept_prompt_pack_text(project_name: str, direction: dict[str, Any]) -> str:
    direction_id = direction.get("direction_id", "D??")
    name = direction.get("name", "未命名方向")
    premise = direction.get("premise", "")
    positive_en = direction.get("prompt_en") or ""
    positive_zh = direction.get("prompt_zh") or ""
    negative_en = direction.get("negative_en") or ""
    negative_zh = direction.get("negative_zh") or ""
    view_prompts_en = direction.get("view_prompts_en")
    view_prompts_zh = direction.get("view_prompts_zh")
    if not isinstance(view_prompts_en, dict):
        view_prompts_en = {}
    if not isinstance(view_prompts_zh, dict):
        view_prompts_zh = {}

    image_order = "\n".join(
        f"{index}. {spec['label_zh']}"
        for index, spec in enumerate(CONCEPT_VIEW_SPECS, start=1)
    )
    english_sections: list[str] = []
    chinese_sections: list[str] = []
    for index, spec in enumerate(CONCEPT_VIEW_SPECS, start=1):
        view_id = spec["id"]
        prompt_en = view_prompts_en.get(view_id)
        prompt_zh = view_prompts_zh.get(view_id)
        if view_id == "front":
            prompt_en = prompt_en or direction.get("front_prompt_en")
            prompt_zh = prompt_zh or direction.get("front_prompt_zh")
        if not _nonempty_text(prompt_en):
            prompt_en = positive_en
        if not _nonempty_text(prompt_zh):
            prompt_zh = positive_zh
        english_sections.append(
            f"""IMAGE {index} OF 10 · {spec['label_en']}
{prompt_en}

Required view for this image; override any camera or view wording above:
{spec['instruction_en']}"""
        )
        chinese_sections.append(
            f"""第 {index} 张，共 10 张：{spec['label_zh']}
{prompt_zh}

本图必须采用的视角，并覆盖上文任何镜头或视角描述：
{spec['instruction_zh']}"""
        )
    english_text = "\n\n".join(english_sections)
    chinese_text = "\n\n".join(chinese_sections)
    return f"""SCENE KIT · {direction_id} · {name}
项目：{project_name}

设计主张
{premise}

生成目标：10 张相互独立的 3:2 横版整栋概念图
{image_order}

执行规则
- 十张图必须是同一栋建筑、同一套体量、材质、配色、屋顶、入口和装饰语言。
- 十张图分别生成，不拼图，不生成多视图合页，不使用一张图中的多个小画面代替十张图。
- 单次工具只能生成一张图时，按下面十个编号逐张执行，并尽量固定模型、风格和种子。
- 每张图必须完整显示整栋建筑，不得裁切屋顶、基座或任何主要立面。
- 不出现人物、文字、标注、尺寸线和水印。
- 概念图不写绝对米数；精确尺寸只写入结构化尺寸合同。
- 关键构件细节图属于额外补充，不替代十张标准视图中的任何一张。

============================================================
ENGLISH · COPY EACH IMAGE SECTION SEPARATELY
============================================================

Consistency rule for all images:
Generate ten separate architectural concept images of the SAME building. Preserve the same massing, proportions, facade rhythm, openings, roof geometry, materials, colors, entrance and component language across all ten images. Each prompt creates one image containing exactly one complete building. Use a 3:2 landscape aspect ratio. Keep the entire roof, base and facade in frame. Do not create a collage, contact sheet or multi-view sheet. No people, labels, measurement lines or watermark.

{english_text}

Negative prompt for all images:
{negative_en}

============================================================
中文 · 分段复制
============================================================

全部图片的一致性要求：
生成同一栋建筑的十张独立建筑概念图。十张图保持相同体量、比例、立面节奏、门窗、屋顶、材质、配色、入口和构件语言。每段提示词只生成一张图，且图中有且只有一栋完整建筑。使用 3:2 横图。完整保留屋顶、基座和全部主要立面。不得输出拼图、九宫格或多视图合页。不出现人物、标注、尺寸线或水印。

{chinese_text}

所有图片共用的负面提示词：
{negative_zh}
"""


def write_concept_prompt_packs(
    root: Path, direction_id: str | None = None
) -> dict[str, Any]:
    root = root.resolve()
    paths = project_files(root)
    scene = read_json(paths["scene"])
    concepts = read_json(paths["concepts"])
    directions = concepts.get("directions")
    if not isinstance(directions, list) or not directions:
        raise ValueError("概念方向为空，无法生成提示词包")

    written: list[str] = []
    for direction in directions:
        if not isinstance(direction, dict):
            continue
        current_id = direction.get("direction_id")
        if direction_id and current_id != direction_id:
            continue
        relative = direction.get("prompt_file") or f"concepts/{current_id}/prompts.txt"
        if not isinstance(relative, str):
            raise ValueError(f"{current_id}.prompt_file 必须是相对路径")
        resolved = _relative_path(relative, root, f"{current_id}.prompt_file", [])
        if resolved is None:
            raise ValueError(f"{current_id}.prompt_file 必须是项目内相对路径")
        write_text_atomic(
            resolved,
            concept_prompt_pack_text(scene.get("name", "未命名项目"), direction),
        )
        direction["prompt_file"] = relative
        written.append(relative)

    if direction_id and not written:
        raise ValueError(f"找不到概念方向：{direction_id}")
    write_json_atomic(paths["concepts"], concepts)
    return {"written": written, "count": len(written)}


def _relative_path(value: Any, root: Path, where: str, errors: list[str]) -> Path | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{where} 必须是非空相对路径")
        return None
    relative = Path(value)
    if relative.is_absolute():
        errors.append(f"{where} 必须是项目内相对路径")
        return None
    resolved = (root / relative).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        errors.append(f"{where} 不能指向项目目录之外")
        return None
    return resolved


def _nonempty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _nonempty(value: Any) -> bool:
    return isinstance(value, (dict, list, str)) and len(value) > 0


def _check_prompt(prompt: Any, where: str, errors: list[str]) -> None:
    if not isinstance(prompt, dict):
        errors.append(f"{where} 必须是对象")
        return
    for key in PROMPT_KEYS:
        if not _nonempty_text(prompt.get(key)):
            errors.append(f"{where} 缺少 {key}")


def _validate_route_assessment(part: dict[str, Any], errors: list[str]) -> None:
    part_id = part.get("part_id", "<unknown>")
    where = f"components.parts[{part_id}].route_assessment"
    assessment = part.get("route_assessment")
    if not isinstance(assessment, dict):
        errors.append(f"{where} 必须是对象")
        return
    if assessment.get("status") not in ROUTE_STATUSES:
        errors.append(f"{where}.status 无效")
    recommended = assessment.get("recommended_route")
    selected = assessment.get("selected_route")
    if recommended not in GENERATION_ROUTES:
        errors.append(f"{where}.recommended_route 无效")
    if selected not in GENERATION_ROUTES:
        errors.append(f"{where}.selected_route 无效")
    if recommended != selected:
        errors.append(f"{where} 推荐路线与选中路线不一致")
    if not _nonempty_text(assessment.get("decision_summary")):
        errors.append(f"{where}.decision_summary 不能为空")
    repetition = assessment.get("repeat_count")
    if (
        not isinstance(repetition, int)
        or isinstance(repetition, bool)
        or repetition < 0
    ):
        errors.append(f"{where}.repeat_count 必须是非负整数")
    if assessment.get("precision_demand") not in ROUTE_PRECISIONS:
        errors.append(f"{where}.precision_demand 无效")
    if assessment.get("blender_effort") not in ROUTE_LEVELS:
        errors.append(f"{where}.blender_effort 无效")
    ai_expected_benefit = assessment.get(
        "ai_3d_expected_benefit",
        assessment.get("tripo_expected_benefit"),
    )
    ai_token_risk = assessment.get(
        "ai_3d_token_risk",
        assessment.get("tripo_token_risk"),
    )
    if ai_expected_benefit not in ROUTE_LEVELS:
        errors.append(
            f"{where}.ai_3d_expected_benefit 无效"
        )
    if ai_token_risk not in ROUTE_LEVELS:
        errors.append(f"{where}.ai_3d_token_risk 无效")
    if assessment.get("reference_quality") not in ROUTE_LEVELS:
        errors.append(f"{where}.reference_quality 无效")
    evidence = assessment.get("evidence")
    if not isinstance(evidence, list) or not all(
        isinstance(value, str) and value.strip() for value in evidence
    ):
        errors.append(f"{where}.evidence 必须是字符串数组")

    decision = part.get("decision")
    if selected in {"ai_3d", "tripo", "external_ai_3d"}:
        if not _nonempty_text(assessment.get("reference_model_id")):
            errors.append(
                f"{where}.reference_model_id 不能为空"
            )
        if decision != "ai_3d":
            errors.append(f"{where} 选择 AI 3D 时组件 decision 必须为 ai_3d")
        if assessment.get("status") != "approved":
            errors.append(f"{where} AI 3D 路线尚未批准")
        if ai_expected_benefit == "low":
            errors.append(
                f"{where} AI 3D 造型收益为 low，不应提交生成"
            )
        if assessment.get("precision_demand") == "exact":
            errors.append(f"{where} 精确尺寸组件不应选择 AI 3D")
        if assessment.get("reference_quality") == "low":
            errors.append(f"{where} 参考质量不足，不应选择 AI 3D")
        reference_sufficiency = assessment.get("reference_sufficiency")
        if not isinstance(reference_sufficiency, dict):
            errors.append(f"{where}.reference_sufficiency 必须是对象")
        else:
            if reference_sufficiency.get("status") != "pass":
                errors.append(f"{where}.reference_sufficiency 尚未通过")
            usable_views = reference_sufficiency.get("usable_views")
            if not isinstance(usable_views, list) or not all(
                isinstance(value, str) and value.strip()
                for value in usable_views
            ):
                errors.append(
                    f"{where}.reference_sufficiency.usable_views "
                    "必须是字符串数组"
                )
                usable_views = []
            minimum_views = (
                2
                if str(part.get("type", "")).lower()
                in PRECISE_REFERENCE_TYPES
                else 1
            )
            if len(set(usable_views)) < minimum_views:
                errors.append(
                    f"{where}.reference_sufficiency 至少需要 "
                    f"{minimum_views} 个不同可用视角"
                )
            if minimum_views == 2 and (
                reference_sufficiency.get("has_front") is not True
                or reference_sufficiency.get(
                    "has_side_or_three_quarter"
                )
                is not True
            ):
                errors.append(
                    f"{where}.reference_sufficiency 精确构件必须同时"
                    "具备正面和侧面/45 度参考"
                )

        budget = assessment.get("triangle_budget")
        if not isinstance(budget, dict):
            errors.append(f"{where}.triangle_budget 必须是对象")
        else:
            values: dict[str, int] = {}
            for key in ("target_total", "hard_max"):
                value = budget.get(key)
                if (
                    not isinstance(value, int)
                    or isinstance(value, bool)
                    or value < 1
                ):
                    errors.append(
                        f"{where}.triangle_budget.{key} 必须是正整数"
                    )
                else:
                    values[key] = value
            if (
                "target_total" in values
                and "hard_max" in values
                and values["target_total"] > values["hard_max"]
            ):
                errors.append(
                    f"{where}.triangle_budget.target_total "
                    "不能大于 hard_max"
                )
            if not _nonempty_text(budget.get("basis")):
                errors.append(
                    f"{where}.triangle_budget.basis 不能为空"
                )

        low_poly = assessment.get("low_poly_strategy")
        if not isinstance(low_poly, dict):
            errors.append(f"{where}.low_poly_strategy 必须是对象")
        else:
            if not _nonempty_text(low_poly.get("provider_quality")):
                errors.append(
                    f"{where}.low_poly_strategy.provider_quality 无效"
                )
            if not isinstance(
                low_poly.get("provider_face_limit_exposed"),
                bool,
            ):
                errors.append(
                    f"{where}.low_poly_strategy."
                    "provider_face_limit_exposed 必须是布尔值"
                )
            for key in ("postprocess", "preserve"):
                values = low_poly.get(key)
                if not isinstance(values, list) or not values or not all(
                    isinstance(value, str) and value.strip()
                    for value in values
                ):
                    errors.append(
                        f"{where}.low_poly_strategy.{key} "
                        "必须是非空字符串数组"
                    )
    elif selected in {"blender_procedural", "blender_manual"}:
        if decision == "ai_3d":
            errors.append(f"{where} 推荐 Blender 时不能保持 ai_3d 决策")
    elif selected == "library" and decision != "library":
        errors.append(f"{where} 选择 library 时组件 decision 必须为 library")


def _validate_material_review(
    part: dict[str, Any],
    root: Path,
    errors: list[str],
) -> None:
    part_id = part.get("part_id", "<unknown>")
    where = f"components.parts[{part_id}].qa.material_review"
    review = (part.get("qa") or {}).get("material_review")
    if not isinstance(review, dict):
        errors.append(f"{where} 必须是对象")
        return
    status = review.get("status")
    if status not in MATERIAL_REVIEW_STATUSES:
        errors.append(f"{where}.status 无效")
    rendered_views = review.get("rendered_views")
    if not isinstance(rendered_views, list):
        errors.append(f"{where}.rendered_views 必须是数组")
        rendered_views = []
    for index, value in enumerate(rendered_views):
        path = _relative_path(
            value,
            root,
            f"{where}.rendered_views[{index}]",
            errors,
        )
        if path is not None and not path.is_file():
            errors.append(f"{where}.rendered_views[{index}] 图片不存在")
    comparison = review.get("reference_comparison")
    comparison_path = _relative_path(
        comparison,
        root,
        f"{where}.reference_comparison",
        errors,
    )
    if comparison_path is not None and not comparison_path.is_file():
        errors.append(f"{where}.reference_comparison 图片不存在")
    if not isinstance(review.get("polyhaven_checked"), bool):
        errors.append(f"{where}.polyhaven_checked 必须是布尔值")
    if review.get("texture_source") not in TEXTURE_SOURCES:
        errors.append(f"{where}.texture_source 无效")
    checks = review.get("checks")
    required_checks = {
        "reference_match",
        "base_color_match",
        "roughness_match",
        "texture_scale_match",
        "texture_projection_valid",
        "surface_quality",
    }
    if not isinstance(checks, dict):
        errors.append(f"{where}.checks 必须是对象")
        checks = {}
    notes = review.get("notes")
    if not isinstance(notes, list) or not all(
        isinstance(value, str) and value.strip() for value in notes
    ):
        errors.append(f"{where}.notes 必须是字符串数组")
    texture_audit = review.get("texture_audit")
    texture_checks: dict[str, Any] = {}
    risk_findings: list[Any] = []
    if not isinstance(texture_audit, dict):
        if status == "pass":
            errors.append(f"{where}.texture_audit 必须是对象")
        texture_audit = {}
    else:
        audit_path = _relative_path(
            texture_audit.get("audit_path"),
            root,
            f"{where}.texture_audit.audit_path",
            errors,
        )
        if audit_path is not None and not audit_path.is_file():
            errors.append(
                f"{where}.texture_audit.audit_path 文件不存在"
            )
        if not _nonempty_text(texture_audit.get("mapping_mode")):
            errors.append(
                f"{where}.texture_audit.mapping_mode 不能为空"
            )
        views_checked = texture_audit.get("views_checked")
        if (
            not isinstance(views_checked, list)
            or len(set(views_checked)) < 2
        ):
            errors.append(
                f"{where}.texture_audit.views_checked "
                "至少需要两个立面或角度"
            )
        texture_checks = texture_audit.get("checks")
        if not isinstance(texture_checks, dict):
            if status == "pass":
                errors.append(
                    f"{where}.texture_audit.checks 必须是对象"
                )
            texture_checks = {}
        risk_findings = texture_audit.get("risk_findings")
        if not isinstance(risk_findings, list):
            if status == "pass":
                errors.append(
                    f"{where}.texture_audit.risk_findings "
                    "必须是数组"
                )
            risk_findings = []

    if review.get("texture_source") == "polyhaven":
        assets = review.get("polyhaven_assets")
        if not isinstance(assets, list) or not assets or not all(
            isinstance(value, str) and value.strip() for value in assets
        ):
            errors.append(f"{where}.polyhaven_assets 不能为空")
    if review.get("texture_source") == "generated":
        textures = review.get("generated_textures")
        if not isinstance(textures, list) or not textures:
            errors.append(f"{where}.generated_textures 不能为空")

    if status == "pass":
        if len(set(rendered_views)) < 2:
            errors.append(f"{where}.rendered_views 至少需要两个材质渲染视图")
        if comparison_path is None:
            errors.append(f"{where} 缺少 reference_comparison")
        if review.get("polyhaven_checked") is not True:
            errors.append(f"{where} 未完成 Poly Haven 适用性检查")
        for key in sorted(required_checks):
            if checks.get(key) is not True:
                errors.append(f"{where}.checks.{key} 未通过")
        for key in (
            "source_image_loaded",
            "projection_axis_valid",
            "physical_scale_consistent",
            "no_visible_stretch_across_faces",
            "normal_and_roughness_aligned",
        ):
            if texture_checks.get(key) is not True:
                errors.append(
                    f"{where}.texture_audit.checks.{key} 未通过"
                )
        if texture_audit.get("status") != "pass":
            errors.append(
                f"{where}.texture_audit.status 必须为 pass"
            )
        if risk_findings:
            errors.append(
                f"{where}.texture_audit.risk_findings 必须为空"
            )


def _validate_reference_consensus(
    part: dict[str, Any],
    root: Path,
    errors: list[str],
) -> None:
    part_id = part.get("part_id", "<unknown>")
    where = f"components.parts[{part_id}].reference_consensus"
    review = part.get("reference_consensus")
    if not isinstance(review, dict):
        errors.append(f"{where} 必须是对象")
        return
    status = review.get("status")
    if status not in REFERENCE_CONSENSUS_STATUSES:
        errors.append(f"{where}.status 无效")
        return
    if status != "pass":
        errors.append(f"{where} 生成或建模前必须先通过多参考共识")
        return

    source_views = review.get("source_views")
    if not isinstance(source_views, list) or len(set(source_views)) < 2:
        errors.append(f"{where}.source_views 至少需要两个不同参考视角")
        source_views = []
    else:
        for index, value in enumerate(source_views):
            source = _relative_path(
                value,
                root,
                f"{where}.source_views[{index}]",
                errors,
            )
            if source is not None and not source.is_file():
                errors.append(f"{where}.source_views[{index}] 图片不存在")

    crops = review.get("crops")
    if not isinstance(crops, list) or len(set(crops)) < 2:
        errors.append(f"{where}.crops 至少需要两个构件裁剪图")
    else:
        for index, value in enumerate(crops):
            crop = _relative_path(
                value,
                root,
                f"{where}.crops[{index}]",
                errors,
            )
            if crop is not None and not crop.is_file():
                errors.append(f"{where}.crops[{index}] 图片不存在")

    model_crops = review.get("model_crops")
    if not isinstance(model_crops, list) or not model_crops:
        errors.append(
            f"{where}.model_crops 至少需要一个参考模型派生裁剪"
        )
    else:
        for index, value in enumerate(model_crops):
            crop = _relative_path(
                value,
                root,
                f"{where}.model_crops[{index}]",
                errors,
            )
            if crop is not None and not crop.is_file():
                errors.append(
                    f"{where}.model_crops[{index}] 图片不存在"
                )

    authority = review.get("authority_policy")
    if not isinstance(authority, dict):
        errors.append(f"{where}.authority_policy 必须是对象")
    else:
        expected = {
            "primary_geometry": "reference_model",
            "primary_component_reference": "model_derived_views",
            "original_views_role": "validation_and_surface_detail",
        }
        for key, value in expected.items():
            if authority.get(key) != value:
                errors.append(
                    f"{where}.authority_policy.{key} "
                    f"必须为 {value}"
                )

    observations = review.get("observations")
    if not isinstance(observations, list) or len(observations) < 2:
        errors.append(f"{where}.observations 至少需要两个视角的观察")

    samples = review.get("material_samples")
    if not isinstance(samples, list) or len(samples) < 2:
        errors.append(
            f"{where}.material_samples 至少需要两个视角的材质样本"
        )
        samples = []
    sample_views: set[str] = set()
    for index, sample in enumerate(samples):
        item_where = f"{where}.material_samples[{index}]"
        if not isinstance(sample, dict):
            errors.append(f"{item_where} 必须是对象")
            continue
        view = sample.get("view")
        if not _nonempty_text(view):
            errors.append(f"{item_where}.view 不能为空")
        else:
            sample_views.add(view)
        if not _nonempty_text(sample.get("role")):
            errors.append(f"{item_where}.role 不能为空")
        if not _nonempty_text(sample.get("method")):
            errors.append(f"{item_where}.method 不能为空")
        rgb = sample.get("mean_rgb")
        if (
            not isinstance(rgb, list)
            or len(rgb) != 3
            or not all(
                isinstance(value, int)
                and not isinstance(value, bool)
                and 0 <= value <= 255
                for value in rgb
            )
        ):
            errors.append(
                f"{item_where}.mean_rgb 必须是三个 0-255 整数"
            )
    if source_views and len(sample_views) < 2:
        errors.append(
            f"{where}.material_samples 必须覆盖至少两个不同视角"
        )

    consensus = review.get("consensus")
    if not isinstance(consensus, dict) or not _nonempty(consensus):
        errors.append(f"{where}.consensus 必须记录材质/结构共识")
    else:
        for key, value in consensus.items():
            if not _nonempty_text(value):
                errors.append(
                    f"{where}.consensus.{key} 必须是非空文本"
                )

    checks = review.get("checks")
    if not isinstance(checks, dict):
        errors.append(f"{where}.checks 必须是对象")
    else:
        for key in sorted(REFERENCE_CONSENSUS_CHECKS):
            if checks.get(key) is not True:
                errors.append(f"{where}.checks.{key} 未通过")
    unresolved = review.get("unresolved")
    if not isinstance(unresolved, list) or not all(
        isinstance(value, str) and value.strip()
        for value in unresolved
    ):
        errors.append(f"{where}.unresolved 必须是字符串数组")
        unresolved = []
    if unresolved:
        errors.append(f"{where} 通过时不能留下未解决分歧")
    if review.get("confirmed_before_generation") is not True:
        errors.append(
            f"{where}.confirmed_before_generation 必须为 true"
        )
    if review.get("confidence") not in {"medium", "high"}:
        errors.append(f"{where}.confidence 必须为 medium 或 high")


def _validate_boundary_review(
    part: dict[str, Any],
    root: Path,
    errors: list[str],
) -> None:
    part_id = part.get("part_id", "<unknown>")
    where = f"components.parts[{part_id}].boundary_review"
    review = part.get("boundary_review")
    if not isinstance(review, dict):
        errors.append(f"{where} 必须是对象")
        return
    status = review.get("status")
    if status not in BOUNDARY_REVIEW_STATUSES:
        errors.append(f"{where}.status 无效")
        return
    if status != "pass":
        errors.append(f"{where} 建模或装配前必须通过组件边界审查")
        return

    source_views = review.get("source_views")
    if not isinstance(source_views, list) or len(set(source_views)) < 2:
        errors.append(f"{where}.source_views 至少需要两个不同视角")
        source_views = []
    else:
        for index, value in enumerate(source_views):
            source = _relative_path(
                value,
                root,
                f"{where}.source_views[{index}]",
                errors,
            )
            if source is not None and not source.is_file():
                errors.append(f"{where}.source_views[{index}] 图片不存在")

    for key in (
        "overall_dimensions_m",
        "mounting_interface_dimensions_m",
    ):
        dimensions = review.get(key)
        if (
            not isinstance(dimensions, list)
            or len(dimensions) != 3
            or not all(
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and value > 0
                for value in dimensions
            )
        ):
            errors.append(f"{where}.{key} 必须是三个正数")

    surfaces = review.get("surfaces")
    if not isinstance(surfaces, dict):
        errors.append(f"{where}.surfaces 必须是对象")
    else:
        for surface in sorted(BOUNDARY_SURFACES):
            if surfaces.get(surface) is not True:
                errors.append(
                    f"{where}.surfaces.{surface} 未完成核查"
                )

    attachments = review.get("attachments")
    if not isinstance(attachments, list) or not attachments:
        errors.append(f"{where}.attachments 必须列出附加结构")
        attachments = []
    included_attachment_ids: list[str] = []
    for index, attachment in enumerate(attachments):
        item_where = f"{where}.attachments[{index}]"
        if not isinstance(attachment, dict):
            errors.append(f"{item_where} 必须是对象")
            continue
        attachment_id = attachment.get("id")
        if not _nonempty_text(attachment_id):
            errors.append(f"{item_where}.id 不能为空")
        if not _nonempty_text(attachment.get("type")):
            errors.append(f"{item_where}.type 不能为空")
        disposition = attachment.get("disposition")
        if disposition not in {
            "included_in_component",
            "separate_component",
            "not_present",
        }:
            errors.append(f"{item_where}.disposition 无效")
        evidence_views = attachment.get("evidence_views")
        if (
            not isinstance(evidence_views, list)
            or len(set(evidence_views)) < 2
        ):
            errors.append(
                f"{item_where}.evidence_views 至少需要两个视角"
            )
        projection = attachment.get("projection_m")
        if (
            not isinstance(projection, (int, float))
            or isinstance(projection, bool)
            or projection < 0
        ):
            errors.append(
                f"{item_where}.projection_m 必须是非负数"
            )
        if disposition == "included_in_component":
            if _nonempty_text(attachment_id):
                included_attachment_ids.append(attachment_id)
            if attachment.get("geometry_included") is not True:
                errors.append(
                    f"{item_where} 已纳入组件但缺少几何"
                )
            if not _nonempty_text(attachment.get("material")):
                errors.append(
                    f"{item_where}.material 不能为空"
                )
        elif disposition == "separate_component":
            if not _nonempty_text(attachment.get("part_id")):
                errors.append(
                    f"{item_where} 拆为独立组件时必须引用 part_id"
                )
    if not included_attachment_ids:
        errors.append(f"{where}.attachments 至少有一个纳入组件")

    material_zones = review.get("material_zones")
    if not isinstance(material_zones, list) or not material_zones:
        errors.append(f"{where}.material_zones 不能为空")
    else:
        for index, zone in enumerate(material_zones):
            if not isinstance(zone, dict) or not _nonempty_text(
                zone.get("role")
            ) or not _nonempty_text(zone.get("material")):
                errors.append(
                    f"{where}.material_zones[{index}] "
                    "必须记录 role 和 material"
                )

    checks = review.get("checks")
    if not isinstance(checks, dict):
        errors.append(f"{where}.checks 必须是对象")
    else:
        for key in sorted(BOUNDARY_REVIEW_CHECKS):
            if checks.get(key) is not True:
                errors.append(f"{where}.checks.{key} 未通过")
    unresolved = review.get("unresolved")
    if not isinstance(unresolved, list) or not all(
        isinstance(value, str) and value.strip()
        for value in unresolved
    ):
        errors.append(f"{where}.unresolved 必须是字符串数组")
        unresolved = []
    if unresolved:
        errors.append(f"{where} 通过时不能留下未解决边界")

    part_type = str(part.get("type", "")).lower()
    if part_type in WINDOW_PART_TYPES:
        sill = next(
            (
                item
                for item in attachments
                if isinstance(item, dict)
                and "sill" in str(item.get("type", "")).lower()
            ),
            None,
        )
        if not isinstance(sill, dict):
            errors.append(f"{where} 窗类组件必须记录窗台")
        else:
            if sill.get("disposition") != "included_in_component":
                errors.append(
                    f"{where} 窗台必须纳入当前窗户组件"
                )
            if "stone" not in str(sill.get("material", "")).lower():
                errors.append(f"{where} 窗台材质必须明确记录为石材")


def _validate_reference_models(
    reference_models: Any,
    root: Path,
    errors: list[str],
) -> None:
    if not isinstance(reference_models, list) or not reference_models:
        errors.append("components.reference_models 至少需要一个整栋参考模型")
        return
    ids: set[str] = set()
    for index, model in enumerate(reference_models):
        where = f"components.reference_models[{index}]"
        if not isinstance(model, dict):
            errors.append(f"{where} 必须是对象")
            continue
        model_id = model.get("reference_model_id")
        if not _nonempty_text(model_id):
            errors.append(f"{where}.reference_model_id 不能为空")
        elif model_id in ids:
            errors.append(f"重复整栋参考模型：{model_id}")
        else:
            ids.add(model_id)
        if model.get("status") not in REFERENCE_MODEL_STATUSES:
            errors.append(f"{where}.status 无效")
        if model.get("role") != "reference_only":
            errors.append(f"{where}.role 必须为 reference_only")
        if model.get("reference_only") is not True:
            errors.append(f"{where}.reference_only 必须为 true")
        if model.get("input_mode") not in REFERENCE_MODEL_INPUT_MODES:
            errors.append(f"{where}.input_mode 无效")
        for key in ("provider", "model", "selection_reason"):
            if not _nonempty_text(model.get(key)):
                errors.append(f"{where}.{key} 不能为空")

        authority = model.get("authority_policy")
        if not isinstance(authority, dict):
            errors.append(f"{where}.authority_policy 必须是对象")
        else:
            expected = {
                "primary_geometry": "reference_model",
                "primary_component_reference": "model_derived_views",
                "original_views_role": "validation_and_surface_detail",
            }
            for key, value in expected.items():
                if authority.get(key) != value:
                    errors.append(
                        f"{where}.authority_policy.{key} "
                        f"必须为 {value}"
                    )

        quality = model.get("reference_quality")
        if not isinstance(quality, dict):
            errors.append(f"{where}.reference_quality 必须是对象")
            quality = {}
        if quality.get("status") not in REFERENCE_MODEL_STATUSES:
            errors.append(f"{where}.reference_quality.status 无效")
        quality_checks = quality.get("checks")
        if not isinstance(quality_checks, dict):
            errors.append(
                f"{where}.reference_quality.checks 必须是对象"
            )
        elif quality.get("status") == "pass":
            for key in (
                "mesh_exists",
                "main_massing_complete",
                "roof_present",
                "openings_present",
                "attachment_relations_legible",
            ):
                if quality_checks.get(key) is not True:
                    errors.append(
                        f"{where}.reference_quality.checks.{key} "
                        "未通过"
                    )
        limitations = quality.get("limitations")
        if not isinstance(limitations, list) or not all(
            isinstance(value, str) and value.strip()
            for value in limitations
        ):
            errors.append(
                f"{where}.reference_quality.limitations "
                "必须是字符串数组"
            )

        camera_rig = model.get("camera_rig")
        if not isinstance(camera_rig, dict):
            errors.append(f"{where}.camera_rig 必须是对象")
            camera_rig = {}
        if camera_rig.get("status") not in REFERENCE_MODEL_STATUSES:
            errors.append(f"{where}.camera_rig.status 无效")
        if camera_rig.get("shared_center") is not True:
            errors.append(f"{where}.camera_rig.shared_center 必须为 true")
        views = camera_rig.get("views")
        if not isinstance(views, dict) or not set(CONCEPT_VIEW_IDS) <= set(
            views
        ):
            errors.append(
                f"{where}.camera_rig.views 必须覆盖固定十视图"
            )
        ortho_scale = camera_rig.get("ortho_scale")
        if (
            not isinstance(ortho_scale, (int, float))
            or isinstance(ortho_scale, bool)
            or ortho_scale <= 0
        ):
            errors.append(
                f"{where}.camera_rig.ortho_scale 必须为正数"
            )

        view_validation = model.get("derived_view_validation")
        if not isinstance(view_validation, dict):
            errors.append(
                f"{where}.derived_view_validation 必须是对象"
            )
            view_validation = {}
        if view_validation.get("status") not in REFERENCE_MODEL_STATUSES:
            errors.append(
                f"{where}.derived_view_validation.status 无效"
            )
        reliable_views = view_validation.get("reliable_views")
        if (
            not isinstance(reliable_views, list)
            or len(set(reliable_views)) < 6
            or not set(reliable_views) <= set(CONCEPT_VIEW_IDS)
        ):
            errors.append(
                f"{where}.derived_view_validation.reliable_views "
                "至少需要六个有效视图"
            )
        low_confidence_views = view_validation.get(
            "low_confidence_views"
        )
        if not isinstance(low_confidence_views, list) or not all(
            isinstance(value, str) and value in CONCEPT_VIEW_IDS
            for value in low_confidence_views
        ):
            errors.append(
                f"{where}.derived_view_validation."
                "low_confidence_views 必须是视图 ID 数组"
            )
        view_checks = view_validation.get("checks")
        if not isinstance(view_checks, dict):
            errors.append(
                f"{where}.derived_view_validation.checks 必须是对象"
            )
        elif view_validation.get("status") == "pass":
            for key in (
                "all_views_exist",
                "all_views_nonempty",
                "camera_rig_consistent",
                "same_building_identity",
                "scale_and_framing_consistent",
            ):
                if view_checks.get(key) is not True:
                    errors.append(
                        f"{where}.derived_view_validation.checks."
                        f"{key} 未通过"
                    )

        derived_views = model.get("model_derived_views")
        if not isinstance(derived_views, dict):
            errors.append(f"{where}.model_derived_views 必须是对象")
            derived_views = {}
        else:
            for view_id in CONCEPT_VIEW_IDS:
                path = _relative_path(
                    derived_views.get(view_id),
                    root,
                    f"{where}.model_derived_views.{view_id}",
                    errors,
                )
                if path is not None and not path.is_file():
                    errors.append(
                        f"{where}.model_derived_views.{view_id} "
                        "图片不存在"
                    )

        source_views = model.get("source_views")
        if not isinstance(source_views, list) or not source_views:
            errors.append(f"{where}.source_views 不能为空")
            source_views = []
        for view_index, value in enumerate(source_views):
            path = _relative_path(
                value,
                root,
                f"{where}.source_views[{view_index}]",
                errors,
            )
            if path is not None and not path.is_file():
                errors.append(
                    f"{where}.source_views[{view_index}] 图片不存在"
                )
        if (
            model.get("input_mode") == "multiview_to_3d"
            and len(set(source_views)) < 2
        ):
            errors.append(
                f"{where} 多图生成至少需要两个不同来源视图"
            )

        for key in ("raw_triangles", "decimated_triangles", "max_triangles"):
            value = model.get(key)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 1
            ):
                errors.append(f"{where}.{key} 必须是正整数")
        if (
            isinstance(model.get("decimated_triangles"), int)
            and isinstance(model.get("max_triangles"), int)
            and model["decimated_triangles"] > model["max_triangles"]
        ):
            errors.append(
                f"{where}.decimated_triangles 超过 max_triangles"
            )
        if not _nonempty_text(model.get("decimation_method")):
            errors.append(f"{where}.decimation_method 不能为空")

        for key in (
            "source_blend",
            "decimated_blend",
            "decimated_glb",
            "preview",
            "comparison",
            "audit",
        ):
            path = _relative_path(
                model.get(key),
                root,
                f"{where}.{key}",
                errors,
            )
            if path is not None and not path.is_file():
                errors.append(f"{where}.{key} 文件不存在")

        normalization = model.get("normalization")
        if not isinstance(normalization, dict):
            errors.append(f"{where}.normalization 必须是对象")
            normalization = {}
        if normalization.get("status") not in {
            "pending",
            "pass",
            "repair_required",
        }:
            errors.append(f"{where}.normalization.status 无效")

        extraction = model.get("feature_extraction")
        if not isinstance(extraction, dict):
            errors.append(f"{where}.feature_extraction 必须是对象")
            extraction = {}
        if extraction.get("status") not in FEATURE_EXTRACTION_STATUSES:
            errors.append(f"{where}.feature_extraction.status 无效")
        segmentation_report = _relative_path(
            extraction.get("segmentation_report"),
            root,
            f"{where}.feature_extraction.segmentation_report",
            errors,
        )
        if (
            segmentation_report is not None
            and not segmentation_report.is_file()
        ):
            errors.append(
                f"{where}.feature_extraction.segmentation_report "
                "文件不存在"
            )
        component_map = extraction.get("component_map")
        if not isinstance(component_map, list):
            errors.append(
                f"{where}.feature_extraction.component_map 必须是数组"
            )
        else:
            for map_index, item in enumerate(component_map):
                item_where = (
                    f"{where}.feature_extraction."
                    f"component_map[{map_index}]"
                )
                if not isinstance(item, dict):
                    errors.append(f"{item_where} 必须是对象")
                    continue
                if not _nonempty_text(item.get("part_id")):
                    errors.append(f"{item_where}.part_id 不能为空")
                if item.get("primary_source") != "model_derived_views":
                    errors.append(
                        f"{item_where}.primary_source "
                        "必须为 model_derived_views"
                    )
                island_ids = item.get("mesh_island_ids")
                if not isinstance(island_ids, list) or not all(
                    isinstance(value, int)
                    and not isinstance(value, bool)
                    and value > 0
                    for value in island_ids
                ):
                    errors.append(
                        f"{item_where}.mesh_island_ids "
                        "必须是正整数数组"
                    )
                observations = item.get("reference_observations")
                if (
                    not isinstance(observations, list)
                    or not _nonempty(observations)
                ):
                    errors.append(
                        f"{item_where}.reference_observations 不能为空"
                    )
                views = item.get("views_checked")
                if not isinstance(views, list) or len(set(views)) < 2:
                    errors.append(
                        f"{item_where}.views_checked "
                        "至少需要两个参考视角"
                    )

        analysis_ready = model.get("analysis_ready")
        if not isinstance(analysis_ready, bool):
            errors.append(f"{where}.analysis_ready 必须是布尔值")
        elif analysis_ready:
            if model.get("status") != "pass":
                errors.append(f"{where} 可分析前 status 必须为 pass")
            if normalization.get("status") != "pass":
                errors.append(f"{where} 可分析前必须完成多视图归一化")
            if extraction.get("status") != "pass":
                errors.append(f"{where} 可分析前必须完成组件特征映射")
            if quality.get("status") != "pass":
                errors.append(f"{where} 可分析前参考模型质量必须通过")
            if camera_rig.get("status") != "pass":
                errors.append(f"{where} 可分析前固定相机轨道必须通过")
            if view_validation.get("status") != "pass":
                errors.append(f"{where} 可分析前派生十视图必须通过验证")


def _reference_model_gate_errors(
    reference_models: Any,
    part_ids: set[str] | None = None,
) -> list[str]:
    errors: list[str] = []
    if not isinstance(reference_models, list) or not reference_models:
        return ["缺少整栋三维参考模型"]
    ready = [
        model
        for model in reference_models
        if isinstance(model, dict)
        and model.get("status") == "pass"
        and model.get("reference_only") is True
        and model.get("analysis_ready") is True
    ]
    if not ready:
        errors.append(
            "整栋三维参考模型尚未完成多视图归一化和组件特征映射"
        )
    elif part_ids:
        mapped = {
            item.get("part_id")
            for model in ready
            for item in (
                (model.get("feature_extraction") or {}).get(
                    "component_map",
                    [],
                )
            )
            if isinstance(item, dict)
        }
        missing = sorted(part_ids - mapped)
        if missing:
            errors.append(
                "整栋参考模型尚未映射组件："
                + "、".join(missing)
            )
    return errors


def _validate_fine_structure_review(
    part: dict[str, Any],
    root: Path,
    errors: list[str],
) -> None:
    part_id = part.get("part_id", "<unknown>")
    where = f"components.parts[{part_id}].fine_structure_review"
    review = part.get("fine_structure_review")
    if not isinstance(review, dict):
        errors.append(f"{where} 必须是对象")
        return

    status = review.get("status")
    if status not in FINE_STRUCTURE_STATUSES:
        errors.append(f"{where}.status 无效")
        return
    built = (
        (part.get("parametric_build") or {}).get("status") == "pass"
        or (part.get("qa") or {}).get("result") == "pass"
    )
    if built and status != "pass":
        errors.append(f"{where} 已建模组件必须通过细部结构复核")
        return
    if status != "pass":
        return

    evidence = review.get("evidence")
    if not isinstance(evidence, dict):
        errors.append(f"{where}.evidence 必须是对象")
        evidence = {}
    closeup = _relative_path(
        evidence.get("closeup"),
        root,
        f"{where}.evidence.closeup",
        errors,
    )
    if closeup is not None and not closeup.is_file():
        errors.append(f"{where}.evidence.closeup 图片不存在")
    if review.get("confidence") not in FINE_STRUCTURE_CONFIDENCE:
        errors.append(f"{where}.confidence 无效")
    if not _nonempty_text(evidence.get("observation")):
        errors.append(f"{where}.evidence.observation 不能为空")
    if not _nonempty_text(evidence.get("reidentification")):
        errors.append(f"{where}.evidence.reidentification 不能为空")

    source_views = review.get("source_views")
    if not isinstance(source_views, list) or len(set(source_views)) < 2:
        errors.append(f"{where}.source_views 至少需要两个不同视角")
    else:
        for index, value in enumerate(source_views):
            source = _relative_path(
                value,
                root,
                f"{where}.source_views[{index}]",
                errors,
            )
            if source is not None and not source.is_file():
                errors.append(
                    f"{where}.source_views[{index}] 图片不存在"
                )

    materials = review.get("material_cues")
    if not isinstance(materials, dict):
        errors.append(f"{where}.material_cues 必须是对象")
    else:
        for key in ("frame", "trim", "glass"):
            if not _nonempty_text(materials.get(key)):
                errors.append(
                    f"{where}.material_cues.{key} 不能为空"
                )

    unresolved = review.get("unresolved")
    if not isinstance(unresolved, list) or not all(
        isinstance(value, str) and value.strip()
        for value in unresolved
    ):
        errors.append(f"{where}.unresolved 必须是字符串数组")
        unresolved = []
    if unresolved:
        errors.append(f"{where} 通过时不能留下未解决分区")

    pattern = review.get("pattern")
    if not isinstance(pattern, dict):
        errors.append(f"{where}.pattern 必须是对象")
        return
    for key in (
        "major_vertical_sections",
        "columns",
        "rows",
        "pane_count",
        "horizontal_bars",
    ):
        value = pattern.get(key)
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or value < 1
        ):
            errors.append(f"{where}.pattern.{key} 必须是正整数")
    central = pattern.get("central_split")
    if not isinstance(central, dict):
        errors.append(f"{where}.pattern.central_split 必须是对象")
        central = {}
    enabled = central.get("enabled")
    if not isinstance(enabled, bool):
        errors.append(
            f"{where}.pattern.central_split.enabled 必须是布尔值"
        )
    sub_columns = central.get("sub_columns")
    if (
        not isinstance(sub_columns, int)
        or isinstance(sub_columns, bool)
        or sub_columns < 1
    ):
        errors.append(
            f"{where}.pattern.central_split.sub_columns 必须是正整数"
        )
    if isinstance(pattern.get("columns"), int) and isinstance(
        pattern.get("major_vertical_sections"), int
    ) and isinstance(sub_columns, int):
        expected_columns = (
            pattern["major_vertical_sections"] - 1 + sub_columns
            if enabled
            else pattern["major_vertical_sections"]
        )
        if pattern["columns"] != expected_columns:
            errors.append(
                f"{where}.pattern.columns 与主分区/中央再分列不一致"
            )
    if (
        isinstance(pattern.get("columns"), int)
        and isinstance(pattern.get("rows"), int)
        and isinstance(pattern.get("pane_count"), int)
        and pattern["pane_count"] != pattern["columns"] * pattern["rows"]
    ):
        errors.append(f"{where}.pattern.pane_count 与行列数不一致")

    build = part.get("parametric_build")
    if isinstance(build, dict) and build:
        comparisons = {
            "grid_columns": pattern.get("columns"),
            "grid_rows": pattern.get("rows"),
            "pane_count": pattern.get("pane_count"),
        }
        for key, expected in comparisons.items():
            if build.get(key) != expected:
                errors.append(
                    f"{where} 与 parametric_build.{key} 不一致"
                )


def _validate_detail_audit(
    detail_audit: Any,
    part_ids: set[str],
    root: Path,
    where: str,
    errors: list[str],
    selected_views: set[str] | None = None,
) -> None:
    if not isinstance(detail_audit, dict):
        errors.append(f"{where} 必须是对象")
        return

    status = detail_audit.get("status")
    if status not in {"pending", "repair_required", "pass"}:
        errors.append(f"{where}.status 无效")

    scan_views = detail_audit.get("scan_views")
    if not isinstance(scan_views, list) or not all(
        isinstance(value, str) and value.strip() for value in scan_views
    ):
        errors.append(f"{where}.scan_views 必须是字符串数组")
        scan_views = []
    else:
        for index, value in enumerate(scan_views):
            _relative_path(value, root, f"{where}.scan_views[{index}]", errors)
        if (
            status == "pass"
            and selected_views is not None
            and set(scan_views) != selected_views
        ):
            errors.append(
                f"{where}.scan_views 必须覆盖选中方向的全部十视图"
            )

    coverage = detail_audit.get("coverage")
    if not isinstance(coverage, dict):
        errors.append(f"{where}.coverage 必须是对象")
        coverage = {}
    if status == "pass":
        for key in sorted(DETAIL_COVERAGE_KEYS):
            if coverage.get(key) is not True:
                errors.append(f"{where}.coverage.{key} 未通过")

    unresolved = detail_audit.get("unresolved")
    if not isinstance(unresolved, list) or not all(
        isinstance(value, str) and value.strip() for value in unresolved
    ):
        errors.append(f"{where}.unresolved 必须是字符串数组")
        unresolved = []
    if status == "pass" and unresolved:
        errors.append(f"{where}.unresolved 通过时不能留有未解决细节")

    features = detail_audit.get("features")
    if not isinstance(features, list):
        errors.append(f"{where}.features 必须是数组")
        features = []
    if status == "pass" and not features:
        errors.append(f"{where}.features 通过时不能为空")

    feature_ids: set[str] = set()
    for index, feature in enumerate(features):
        item_where = f"{where}.features[{index}]"
        if not isinstance(feature, dict):
            errors.append(f"{item_where} 必须是对象")
            continue

        feature_id = feature.get("feature_id")
        if not isinstance(feature_id, str) or not re.fullmatch(
            r"[a-z][a-z0-9_]*", feature_id
        ):
            errors.append(f"{item_where}.feature_id 无效")
        elif feature_id in feature_ids:
            errors.append(f"重复细节特征：{feature_id}")
        else:
            feature_ids.add(feature_id)

        if feature.get("category") not in DETAIL_CATEGORIES:
            errors.append(f"{item_where}.category 无效")
        if not _nonempty_text(feature.get("type")):
            errors.append(f"{item_where}.type 不能为空")
        if feature.get("visual_impact") not in DETAIL_VISUAL_IMPACTS:
            errors.append(f"{item_where}.visual_impact 无效")
        if not isinstance(feature.get("geometry_required"), bool):
            errors.append(f"{item_where}.geometry_required 必须是布尔值")

        quantity = feature.get("quantity")
        if (
            not isinstance(quantity, int)
            or isinstance(quantity, bool)
            or quantity < 1
        ):
            errors.append(f"{item_where}.quantity 必须是正整数")

        views = feature.get("views")
        if not isinstance(views, list) or not all(
            isinstance(value, str) and value.strip() for value in views
        ):
            errors.append(f"{item_where}.views 必须是字符串数组")
            views = []
        else:
            for view_index, value in enumerate(views):
                _relative_path(
                    value,
                    root,
                    f"{item_where}.views[{view_index}]",
                    errors,
                )
            if status == "pass" and len(set(views)) < 2:
                errors.append(f"{item_where}.views 至少需要两个多视图来源")
            if (
                status == "pass"
                and selected_views is not None
                and not set(views) <= selected_views
            ):
                errors.append(
                    f"{item_where}.views 必须来自选中方向的多视图"
                )

        disposition = feature.get("disposition")
        if disposition not in DETAIL_DISPOSITIONS:
            errors.append(f"{item_where}.disposition 无效")
        if feature.get("geometry_required") is True and disposition == "material":
            errors.append(
                f"{item_where} 需要几何的细节不能只交给材质"
            )
        if disposition == "part" and feature.get("geometry_required") is not True:
            errors.append(
                f"{item_where} 独立组件必须声明 geometry_required=true"
            )
        part_id = feature.get("part_id")
        if disposition == "part":
            if not isinstance(part_id, str) or part_id not in part_ids:
                errors.append(
                    f"{item_where}.part_id 必须指向现有组件"
                )
        if not _nonempty_text(feature.get("observation")):
            errors.append(f"{item_where}.observation 不能为空")


def _validate_quantity_audit(
    components: dict[str, Any],
    root: Path,
    errors: list[str],
) -> None:
    where = "components.quantity_audit"
    audit = components.get("quantity_audit")
    if not isinstance(audit, dict):
        errors.append(f"{where} 必须是对象")
        return
    status = audit.get("status")
    if status not in {"pending", "repair_required", "pass"}:
        errors.append(f"{where}.status 无效")
    source_views = audit.get("source_views")
    if not isinstance(source_views, list):
        errors.append(f"{where}.source_views 必须是数组")
    elif status == "pass" and not source_views:
        errors.append(f"{where}.source_views 通过时必须非空")
    else:
        for index, value in enumerate(source_views):
            _relative_path(
                value, root, f"{where}.source_views[{index}]", errors
            )
    counts = audit.get("counts")
    if not isinstance(counts, dict):
        errors.append(f"{where}.counts 必须是对象")
        counts = {}
    elif status == "pass" and not counts:
        errors.append(f"{where}.counts 通过时必须非空")
    for key, item in counts.items():
        item_where = f"{where}.counts.{key}"
        if not isinstance(item, dict):
            errors.append(f"{item_where} 必须是对象")
            continue
        expected = item.get("expected")
        actual = item.get("actual")
        if (
            not isinstance(expected, int)
            or isinstance(expected, bool)
            or expected < 0
        ):
            errors.append(f"{item_where}.expected 必须是非负整数")
        if (
            not isinstance(actual, int)
            or isinstance(actual, bool)
            or actual < 0
        ):
            errors.append(f"{item_where}.actual 必须是非负整数")
        elif expected != actual:
            errors.append(f"{item_where} 的 expected 与 actual 不一致")
        if not _nonempty_text(item.get("unit")):
            errors.append(f"{item_where}.unit 不能为空")
        if item.get("count_scope") not in {
            "live_part_instances",
            "embedded_geometry",
            "removed_feature",
        }:
            errors.append(f"{item_where}.count_scope 无效")
        evidence = item.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"{item_where}.evidence 必须是非空数组")
        else:
            for index, value in enumerate(evidence):
                _relative_path(
                    value,
                    root,
                    f"{item_where}.evidence[{index}]",
                    errors,
                )
        if item.get("count_scope") == "removed_feature" and actual != 0:
            errors.append(f"{item_where} 为删除特征，actual 必须为 0")

    windows = counts.get("main_windows")
    if isinstance(windows, dict):
        breakdown = windows.get("facade_breakdown")
        if not isinstance(breakdown, dict) or not breakdown:
            errors.append(
                f"{where}.counts.main_windows.facade_breakdown 必须存在"
            )
            breakdown = {}
        total = 0
        for facade, floors in breakdown.items():
            facade_where = (
                f"{where}.counts.main_windows.facade_breakdown.{facade}"
            )
            if not isinstance(floors, dict):
                errors.append(f"{facade_where} 必须是对象")
                continue
            lower = floors.get("lower")
            upper = floors.get("upper")
            facade_total = floors.get("total")
            if not all(
                isinstance(value, int)
                and not isinstance(value, bool)
                and value >= 0
                for value in (lower, upper, facade_total)
            ):
                errors.append(
                    f"{facade_where} lower/upper/total 必须是非负整数"
                )
                continue
            if facade_total != lower + upper:
                errors.append(
                    f"{facade_where}.total 必须等于 lower + upper"
                )
            total += facade_total
        if total != windows.get("expected"):
            errors.append(
                f"{where}.counts.main_windows 分面合计 {total} "
                f"与 expected {windows.get('expected')} 不一致"
            )

    audit_checks = audit.get("checks")
    if not isinstance(audit_checks, dict):
        errors.append(f"{where}.checks 必须是对象")
    elif status == "pass" and (
        not audit_checks
        or not all(value is True for value in audit_checks.values())
    ):
        errors.append(f"{where}.checks 通过时必须非空且全部为 true")
    unresolved = audit.get("unresolved")
    if not isinstance(unresolved, list):
        errors.append(f"{where}.unresolved 必须是数组")
    elif status == "pass" and unresolved:
        errors.append(f"{where}.unresolved 通过时必须为空")
    decomposition = components.get("decomposition_review") or {}
    if (
        status == "pass"
        and (decomposition.get("checks") or {}).get("quantity_verified")
        is not True
    ):
        errors.append(
            "components.decomposition_review.checks.quantity_verified "
            "必须为 true"
        )


def _validate_attachment_integrity_audit(
    components: dict[str, Any],
    root: Path,
    errors: list[str],
) -> None:
    where = "components.attachment_integrity_audit"
    audit = components.get("attachment_integrity_audit")
    if not isinstance(audit, dict):
        errors.append(f"{where} 必须是对象")
        return
    status = audit.get("status")
    if status not in {"pending", "repair_required", "pass"}:
        errors.append(f"{where}.status 无效")
    source_views = audit.get("source_views")
    if not isinstance(source_views, list):
        errors.append(f"{where}.source_views 必须是数组")
    else:
        if status == "pass" and not source_views:
            errors.append(f"{where}.source_views 通过时必须非空")
        for index, value in enumerate(source_views):
            _relative_path(
                value, root, f"{where}.source_views[{index}]", errors
            )
    part_ids = {
        part.get("part_id")
        for part in components.get("parts", [])
        if isinstance(part, dict)
    }
    items = audit.get("items")
    if not isinstance(items, list):
        errors.append(f"{where}.items 必须是数组")
        items = []
    elif status == "pass" and not items:
        errors.append(f"{where}.items 通过时必须非空")
    for index, item in enumerate(items):
        item_where = f"{where}.items[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{item_where} 必须是对象")
            continue
        if item.get("part_id") not in part_ids:
            errors.append(f"{item_where}.part_id 必须指向现有组件")
        if not _nonempty_text(item.get("attachment_id")):
            errors.append(f"{item_where}.attachment_id 不能为空")
        hosts = item.get("host_part_ids")
        if not isinstance(hosts, list) or not hosts:
            errors.append(f"{item_where}.host_part_ids 必须是非空数组")
        else:
            for host in hosts:
                if host not in part_ids:
                    errors.append(
                        f"{item_where}.host_part_ids 包含未知组件 {host}"
                    )
        for key in (
            "has_volume",
            "has_back_enclosure",
            "has_side_enclosure",
        ):
            if item.get(key) is not True:
                errors.append(f"{item_where}.{key} 必须为 true")
        if item.get("front_plane_only") is not False:
            errors.append(f"{item_where}.front_plane_only 必须为 false")
        if item.get("host_contact_verified") is not True:
            errors.append(
                f"{item_where}.host_contact_verified 必须为 true"
            )
        contact_evidence = item.get("host_contact_evidence")
        if not isinstance(contact_evidence, list) or not contact_evidence:
            errors.append(
                f"{item_where}.host_contact_evidence 必须是非空数组"
            )
        else:
            for evidence_index, value in enumerate(contact_evidence):
                _relative_path(
                    value,
                    root,
                    f"{item_where}.host_contact_evidence[{evidence_index}]",
                    errors,
                )
        evidence_views = item.get("evidence_views")
        if (
            not isinstance(evidence_views, list)
            or len(set(evidence_views)) < 2
        ):
            errors.append(
                f"{item_where}.evidence_views 至少需要两个视角"
            )
        else:
            for evidence_index, value in enumerate(evidence_views):
                _relative_path(
                    value,
                    root,
                    f"{item_where}.evidence_views[{evidence_index}]",
                    errors,
                )
        if item.get("status") != "pass":
            errors.append(f"{item_where}.status 必须为 pass")
    audit_checks = audit.get("checks")
    if not isinstance(audit_checks, dict):
        errors.append(f"{where}.checks 必须是对象")
    elif status == "pass" and (
        not audit_checks
        or not all(value is True for value in audit_checks.values())
    ):
        errors.append(f"{where}.checks 通过时必须非空且全部为 true")
    unresolved = audit.get("unresolved")
    if not isinstance(unresolved, list):
        errors.append(f"{where}.unresolved 必须是数组")
    elif status == "pass" and unresolved:
        errors.append(f"{where}.unresolved 通过时必须为空")
    decomposition = components.get("decomposition_review") or {}
    if (
        status == "pass"
        and (decomposition.get("checks") or {}).get(
            "attachment_integrity_verified"
        )
        is not True
    ):
        errors.append(
            "components.decomposition_review.checks."
            "attachment_integrity_verified 必须为 true"
        )


def validate_project(root: Path) -> tuple[list[str], list[str]]:
    root = root.resolve()
    errors: list[str] = []
    warnings: list[str] = []
    paths = project_files(root)
    documents: dict[str, dict[str, Any]] = {}
    for name, path in paths.items():
        if not path.is_file():
            errors.append(f"缺少 {path.relative_to(root).as_posix()}")
            continue
        try:
            documents[name] = read_json(path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"{path.relative_to(root).as_posix()} 无法读取：{exc}")
    if errors:
        return errors, warnings

    scene = documents["scene"]
    progress = documents["progress"]
    brief = documents["brief"]
    concepts = documents["concepts"]
    design = documents["design"]
    components = documents["components"]
    assembly = documents["assembly"]

    for name, document in documents.items():
        if document.get("schema_version") != SCHEMA_VERSION:
            errors.append(f"{name}.schema_version 必须为 {SCHEMA_VERSION}")

    scene_skill_version = scene.get("skill_version")
    if scene_skill_version not in SUPPORTED_SKILL_VERSIONS:
        errors.append(
            "scene.skill_version 必须是以下值之一："
            + "、".join(sorted(SUPPORTED_SKILL_VERSIONS))
        )
    elif scene_skill_version != SKILL_VERSION:
        warnings.append(
            f"项目由 Scene Kit {scene_skill_version} 创建；"
            f"当前版本为 {SKILL_VERSION}，下次通过阶段门禁时应补齐精修数据"
        )
    if scene.get("concept_first") is not True:
        errors.append("scene.concept_first 必须为 true")
    delivery = scene.get("delivery")
    if not isinstance(delivery, dict) or delivery.get("profile") not in DELIVERY_PROFILES:
        errors.append("scene.delivery.profile 无效")
    render_policy = scene.get("render_policy")
    if render_policy is not None:
        if not isinstance(render_policy, dict):
            errors.append("scene.render_policy 必须是对象")
        else:
            if render_policy.get("qa_render") != "required":
                errors.append(
                    "scene.render_policy.qa_render 必须为 required"
                )
            if (
                render_policy.get("display_mode")
                not in RENDER_DISPLAY_MODES
            ):
                errors.append("scene.render_policy.display_mode 无效")
            for key in (
                "display_requires_confirmation",
                "extra_presentation_renders_require_confirmation",
            ):
                if not isinstance(render_policy.get(key), bool):
                    errors.append(
                        f"scene.render_policy.{key} 必须是布尔值"
                    )

    stage = progress.get("stage")
    if progress.get("mode") != "concept_first":
        errors.append("progress.mode 必须为 concept_first")
    if stage not in STAGES:
        errors.append(f"未知阶段：{stage}")
    current_object = progress.get("current_object")
    if not isinstance(current_object, str) or not re.fullmatch(r"B\d{2,}", current_object):
        errors.append("progress.current_object 必须类似 B01")
    if brief.get("object_id") != current_object:
        errors.append("brief.object_id 与 progress.current_object 不一致")
    if components.get("object_id") != current_object:
        errors.append("components.object_id 与 progress.current_object 不一致")
    if assembly.get("object_id") != current_object:
        errors.append("assembly.object_id 与 progress.current_object 不一致")

    reference_models = components.get("reference_models")
    if reference_models is None:
        if (
            scene_skill_version == SKILL_VERSION
            and stage in {
                "COMPONENTS",
                "REFERENCES",
                "GENERATION",
                "ASSEMBLY",
                "FINISHING",
                "REVIEW",
                "COMPLETE",
            }
        ):
            errors.append(
                "components.reference_models 至少需要一个"
                "整栋三维参考模型"
            )
        elif stage not in {"BRIEF", "CONCEPTS", "DESIGN"}:
            warnings.append(
                "项目缺少整栋三维参考模型；"
                "进入 COMPONENTS 门禁前必须补齐"
            )
    else:
        _validate_reference_models(reference_models, root, errors)

    quality_target = brief.get("quality_target")
    if quality_target is not None:
        if not isinstance(quality_target, dict):
            errors.append("brief.quality_target 必须是对象")
        else:
            if not _nonempty_text(quality_target.get("primary_view")):
                errors.append("brief.quality_target.primary_view 不能为空")
            priority = quality_target.get("quality_priority")
            if not isinstance(priority, list) or not all(
                isinstance(value, str) and value.strip() for value in priority
            ):
                errors.append(
                    "brief.quality_target.quality_priority 必须是字符串数组"
                )
            resolution = quality_target.get("target_resolution")
            if (
                not isinstance(resolution, list)
                or len(resolution) != 2
                or not all(
                    isinstance(value, int)
                    and not isinstance(value, bool)
                    and value > 0
                    for value in resolution
                )
            ):
                errors.append(
                    "brief.quality_target.target_resolution 必须是两个正整数"
                )

    directions = concepts.get("directions")
    direction_ids: set[str] = set()
    if not isinstance(directions, list):
        errors.append("concept_directions.directions 必须是数组")
        directions = []
    for index, direction in enumerate(directions):
        where = f"concept_directions.directions[{index}]"
        if not isinstance(direction, dict):
            errors.append(f"{where} 必须是对象")
            continue
        direction_id = direction.get("direction_id")
        if not isinstance(direction_id, str) or not re.fullmatch(r"D\d{2,}", direction_id):
            errors.append(f"{where}.direction_id 必须类似 D01")
        elif direction_id in direction_ids:
            errors.append(f"重复概念方向：{direction_id}")
        else:
            direction_ids.add(direction_id)
        for key in ("name", "premise", "prompt_en", "prompt_zh", "negative_en", "negative_zh"):
            if not _nonempty_text(direction.get(key)):
                errors.append(f"{where}.{key} 不能为空")
        for key in ("hero_path", "front_path", "details_path"):
            _relative_path(direction.get(key), root, f"{where}.{key}", errors)
        view_paths = direction.get("view_paths")
        if view_paths is not None:
            if not isinstance(view_paths, dict):
                errors.append(f"{where}.view_paths 必须是对象")
            else:
                for view_id, value in view_paths.items():
                    if view_id not in CONCEPT_VIEW_IDS:
                        errors.append(f"{where}.view_paths 包含未知视图：{view_id}")
                    _relative_path(
                        value,
                        root,
                        f"{where}.view_paths.{view_id}",
                        errors,
                    )
        consistency_review = direction.get("consistency_review")
        if consistency_review is not None:
            if not isinstance(consistency_review, dict):
                errors.append(f"{where}.consistency_review 必须是对象")
            else:
                if consistency_review.get("status") not in {
                    "pending",
                    "repair_required",
                    "pass",
                }:
                    errors.append(
                        f"{where}.consistency_review.status 无效"
                    )
                checked_views = consistency_review.get("checked_views")
                if not isinstance(checked_views, list) or not all(
                    value in CONCEPT_VIEW_IDS for value in checked_views
                ):
                    errors.append(
                        f"{where}.consistency_review.checked_views "
                        "必须使用固定视图键"
                    )
                checks = consistency_review.get("checks")
                if consistency_review.get("status") == "pass" and (
                    not isinstance(checks, dict)
                    or not all(value is True for value in checks.values())
                ):
                    errors.append(
                        f"{where}.consistency_review.checks "
                        "必须全部为 true"
                    )
                notes = consistency_review.get("notes")
                if not isinstance(notes, list) or not all(
                    isinstance(value, str) and value.strip()
                    for value in notes
                ):
                    errors.append(
                        f"{where}.consistency_review.notes "
                        "必须是字符串数组"
                    )
        prompt_path = _relative_path(
            direction.get("prompt_file"), root, f"{where}.prompt_file", errors
        )
        if prompt_path is not None and prompt_path.is_file():
            prompt_text = prompt_path.read_text(encoding="utf-8")
            if any(
                f"IMAGE {index} OF 10" not in prompt_text
                for index in range(1, len(CONCEPT_VIEW_SPECS) + 1)
            ):
                warnings.append(
                    f"{where}.prompt_file 尚未升级为十视图提示词包"
                )
    selected_direction = concepts.get("selected_direction")
    if selected_direction is not None and selected_direction not in direction_ids:
        errors.append("selected_direction 不存在")
    if concepts.get("status") not in {"draft", "reviewed", "selected"}:
        errors.append("concept_directions.status 无效")

    if design.get("status") not in {"draft", "approved", "superseded"}:
        errors.append("design_contract.status 无效")
    style_version = design.get("style_version")
    if not isinstance(style_version, int) or isinstance(style_version, bool) or style_version < 0:
        errors.append("design_contract.style_version 必须是非负整数")
    fixed_style = design.get("fixed_style")
    if not isinstance(fixed_style, dict):
        errors.append("design_contract.fixed_style 必须是对象")
    for key in ("positive_en", "positive_zh", "negative_en", "negative_zh"):
        value = fixed_style.get(key) if isinstance(fixed_style, dict) else None
        if design.get("status") == "approved" and not _nonempty_text(value):
            errors.append(f"design_contract.fixed_style.{key} 不能为空")
    if design.get("selected_direction") is not None and design.get("selected_direction") != selected_direction:
        errors.append("design_contract.selected_direction 与概念选型不一致")

    parts = components.get("parts")
    part_ids: set[str] = set()
    if not isinstance(parts, list):
        errors.append("components.parts 必须是数组")
        parts = []
    for index, part in enumerate(parts):
        where = f"components.parts[{index}]"
        if not isinstance(part, dict):
            errors.append(f"{where} 必须是对象")
            continue
        part_id = part.get("part_id")
        if not isinstance(part_id, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", part_id):
            errors.append(f"{where}.part_id 无效")
        elif part_id in part_ids:
            errors.append(f"重复组件：{part_id}")
        else:
            part_ids.add(part_id)
        if part.get("decision") not in DECISIONS:
            errors.append(f"{where}.decision 无效")
        if not _nonempty_text(part.get("type")):
            errors.append(f"{where}.type 不能为空")
        asset_class = part.get("asset_class")
        if asset_class is not None and asset_class not in ASSET_CLASSES:
            errors.append(f"{where}.asset_class 无效")
        if (
            part.get("decision") == "library"
            and part.get("library_source") == "scene_kit_model_library"
        ):
            library_ref = part.get("library_ref")
            if not isinstance(library_ref, dict):
                errors.append(f"{where}.library_ref 必须是对象")
            else:
                for key in ("asset_id", "library_root", "model"):
                    if not _nonempty_text(library_ref.get(key)):
                        errors.append(f"{where}.library_ref.{key} 不能为空")
        if part.get("decision") == "ai_3d":
            for key in ("locked", "guided", "free"):
                if not _nonempty(part.get(key)):
                    errors.append(f"{where}.{key} 不能为空")
        reference_pack = part.get("reference_pack")
        lists: dict[str, list[str]] = {}
        if not isinstance(reference_pack, dict):
            errors.append(f"{where}.reference_pack 必须是对象")
            reference_pack = {}
        for key in ("geometry", "appearance", "review_only"):
            values = reference_pack.get(key, [])
            if not isinstance(values, list):
                errors.append(f"{where}.reference_pack.{key} 必须是数组")
                values = []
            lists[key] = [value for value in values if isinstance(value, str)]
            for ref_index, value in enumerate(values):
                _relative_path(
                    value,
                    root,
                    f"{where}.reference_pack.{key}[{ref_index}]",
                    errors,
                )
        for review_path in lists.get("review_only", []):
            if review_path in lists.get("geometry", []) or review_path in lists.get("appearance", []):
                errors.append(f"{where} 将 review_only 图片误用作生成参考：{review_path}")
        reference_audit = reference_pack.get("audit")
        if reference_audit is not None:
            if not isinstance(reference_audit, dict):
                errors.append(f"{where}.reference_pack.audit 必须是对象")
            else:
                if reference_audit.get("status") not in {
                    "pending",
                    "repair_required",
                    "pass",
                }:
                    errors.append(
                        f"{where}.reference_pack.audit.status 无效"
                    )
                source_views = reference_audit.get("source_views")
                if not isinstance(source_views, list):
                    errors.append(
                        f"{where}.reference_pack.audit.source_views "
                        "必须是数组"
                    )
                else:
                    for source_index, value in enumerate(source_views):
                        _relative_path(
                            value,
                            root,
                            f"{where}.reference_pack.audit."
                            f"source_views[{source_index}]",
                            errors,
                        )
                checks = reference_audit.get("checks")
                if reference_audit.get("status") == "pass" and (
                    not isinstance(checks, dict)
                    or not all(value is True for value in checks.values())
                ):
                    errors.append(
                        f"{where}.reference_pack.audit.checks "
                        "必须全部为 true"
                    )
                notes = reference_audit.get("notes")
                if not isinstance(notes, list) or not all(
                    isinstance(value, str) and value.strip()
                    for value in notes
                ):
                    errors.append(
                        f"{where}.reference_pack.audit.notes "
                        "必须是字符串数组"
                    )
        decomposition_audit = part.get("decomposition_audit")
        if decomposition_audit is not None:
            if not isinstance(decomposition_audit, dict):
                errors.append(f"{where}.decomposition_audit 必须是对象")
            else:
                if decomposition_audit.get("status") not in {
                    "pending",
                    "repair_required",
                    "pass",
                }:
                    errors.append(
                        f"{where}.decomposition_audit.status 无效"
                    )
                source_views = decomposition_audit.get("source_views")
                if not isinstance(source_views, list):
                    errors.append(
                        f"{where}.decomposition_audit.source_views "
                        "必须是数组"
                    )
                else:
                    for source_index, value in enumerate(source_views):
                        _relative_path(
                            value,
                            root,
                            f"{where}.decomposition_audit."
                            f"source_views[{source_index}]",
                            errors,
                        )
                checks = decomposition_audit.get("checks")
                if decomposition_audit.get("status") == "pass" and (
                    not isinstance(checks, dict)
                    or not all(value is True for value in checks.values())
                ):
                    errors.append(
                        f"{where}.decomposition_audit.checks "
                        "必须全部为 true"
                    )
                notes = decomposition_audit.get("notes")
                if not isinstance(notes, list) or not all(
                    isinstance(value, str) and value.strip()
                    for value in notes
                ):
                    errors.append(
                        f"{where}.decomposition_audit.notes "
                        "必须是字符串数组"
                    )
        generation_path = (part.get("generation") or {}).get("source_path")
        _relative_path(generation_path, root, f"{where}.generation.source_path", errors)
        if part.get("decision") == "ai_3d":
            generation = part.get("generation")
            if not isinstance(generation, dict):
                generation = {}
            input_mode = generation.get("input_mode")
            if input_mode not in INPUT_MODES:
                errors.append(f"{where}.generation.input_mode 无效")
            if (
                input_mode == "text_to_3d"
                and not _nonempty_text(generation.get("text_only_reason"))
            ):
                errors.append(f"{where} 已提供参考图时使用纯文字生成，但没有 text_only_reason")
            references_used = generation.get("references_used")
            if not isinstance(references_used, list):
                errors.append(f"{where}.generation.references_used 必须是数组")
            elif input_mode in IMAGE_INPUT_MODES and not references_used:
                errors.append(f"{where}.generation.references_used 不能为空")
            else:
                for ref_index, value in enumerate(references_used):
                    _relative_path(
                        value,
                        root,
                        f"{where}.generation.references_used[{ref_index}]",
                        errors,
                    )
            for key, minimum in (("candidate_count", 1), ("paid_retries", 0)):
                value = generation.get(key)
                if (
                    not isinstance(value, int)
                    or isinstance(value, bool)
                    or value < minimum
                ):
                    errors.append(f"{where}.generation.{key} 必须是大于等于 {minimum} 的整数")

            qa = part.get("qa")
            if not isinstance(qa, dict):
                errors.append(f"{where}.qa 必须是对象")
                qa = {}
            _relative_path(
                qa.get("comparison_path"),
                root,
                f"{where}.qa.comparison_path",
                errors,
            )
            for key in ("differences", "repairs"):
                values = qa.get(key)
                if not isinstance(values, list) or not all(
                    isinstance(value, str) and value.strip() for value in values
                ):
                    errors.append(f"{where}.qa.{key} 必须是字符串数组")
            if qa.get("result") not in {"pass", "repair_required"}:
                errors.append(f"{where}.qa.result 无效")
        if "route_assessment" in part:
            _validate_route_assessment(part, errors)
        part_qa = part.get("qa") or {}
        generation_status = (part.get("generation") or {}).get("status")
        model_started = (
            part_qa.get("result") == "pass"
            or (part.get("parametric_build") or {}).get("status") == "pass"
            or generation_status
            in {
                "generated",
                "approved",
                "normalized",
                "superseded_by_blender",
            }
        )
        if "reference_consensus" in part or model_started:
            _validate_reference_consensus(part, root, errors)
        if "boundary_review" in part or model_started:
            _validate_boundary_review(part, root, errors)
        part_type = str(part.get("type", "")).lower()
        if part_type in WINDOW_PART_TYPES and (
            scene_skill_version == SKILL_VERSION
            or "fine_structure_review" in part
        ):
            _validate_fine_structure_review(part, root, errors)
        qa = part_qa
        needs_material_review = (
            qa.get("material_review") is not None
            or qa.get("result") == "pass"
            or (part.get("parametric_build") or {}).get("status") == "pass"
        )
        if needs_material_review and (
            scene_skill_version == SKILL_VERSION
            or qa.get("material_review") is not None
        ):
            _validate_material_review(part, root, errors)
        elif needs_material_review:
            warnings.append(
                f"{part.get('part_id')} 缺少 7.7 材质审查；"
                "再次标记通过或推进生成前必须补齐"
            )

    decomposition_review = components.get("decomposition_review")
    if decomposition_review is not None:
        if not isinstance(decomposition_review, dict):
            errors.append("components.decomposition_review 必须是对象")
        else:
            if decomposition_review.get("status") not in {
                "pending",
                "repair_required",
                "pass",
            }:
                errors.append(
                    "components.decomposition_review.status 无效"
                )
            source_views = decomposition_review.get("source_views")
            if not isinstance(source_views, list):
                errors.append(
                    "components.decomposition_review.source_views "
                    "必须是数组"
                )
            else:
                for index, value in enumerate(source_views):
                    _relative_path(
                        value,
                        root,
                        "components.decomposition_review."
                        f"source_views[{index}]",
                        errors,
                    )
            checks = decomposition_review.get("checks")
            if decomposition_review.get("status") == "pass" and (
                not isinstance(checks, dict)
                or not all(value is True for value in checks.values())
            ):
                errors.append(
                    "components.decomposition_review.checks "
                    "必须全部为 true"
                )
            notes = decomposition_review.get("notes")
            if not isinstance(notes, list) or not all(
                isinstance(value, str) and value.strip() for value in notes
            ):
                errors.append(
                    "components.decomposition_review.notes "
                    "必须是字符串数组"
                )

    visual_inventory = components.get("visual_inventory", [])
    if not isinstance(visual_inventory, list):
        errors.append("components.visual_inventory 必须是数组")
    else:
        for index, item in enumerate(visual_inventory):
            where = f"components.visual_inventory[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{where} 必须是对象")
                continue
            if item.get("asset_class") not in ASSET_CLASSES:
                errors.append(f"{where}.asset_class 无效")
            if not _nonempty_text(item.get("type")):
                errors.append(f"{where}.type 不能为空")
            if item.get("decision") not in DECISIONS:
                errors.append(f"{where}.decision 无效")
            source_view = _relative_path(
                item.get("source_view"),
                root,
                f"{where}.source_view",
                errors,
            )
            if source_view is not None and not source_view.is_file():
                errors.append(f"{where}.source_view 图片不存在")

    detail_audit = components.get("detail_audit")
    if detail_audit is None:
        if scene_skill_version == SKILL_VERSION:
            errors.append("components.detail_audit 必须是对象")
        else:
            warnings.append(
                "项目缺少 Scene Kit 7.3+ 的 detail_audit；"
                "进入 COMPONENTS 门禁前必须补齐细节特征盘点"
            )
    else:
        selected_id = concepts.get("selected_direction")
        selected_direction = next(
            (
                item
                for item in concepts.get("directions", [])
                if item.get("direction_id") == selected_id
            ),
            None,
        )
        selected_view_paths = (selected_direction or {}).get("view_paths", {})
        selected_views = {
            value
            for value in selected_view_paths.values()
            if isinstance(value, str) and value
        }
        _validate_detail_audit(
            detail_audit,
            part_ids,
            root,
            "components.detail_audit",
            errors,
            selected_views or None,
        )

    quantity_audit = components.get("quantity_audit")
    if quantity_audit is None:
        if scene_skill_version == SKILL_VERSION:
            errors.append("components.quantity_audit 必须是对象")
        else:
            warnings.append(
                "项目缺少 Scene Kit 7.20 的 quantity_audit；"
                "拆件和装配数量校验前必须补齐"
            )
    else:
        _validate_quantity_audit(components, root, errors)

    attachment_integrity = components.get("attachment_integrity_audit")
    if attachment_integrity is None:
        if scene_skill_version == SKILL_VERSION:
            errors.append("components.attachment_integrity_audit 必须是对象")
        else:
            warnings.append(
                "项目缺少 Scene Kit 7.21 的 attachment_integrity_audit；"
                "前置构件背面和宿主连接校验前必须补齐"
            )
    else:
        _validate_attachment_integrity_audit(components, root, errors)

    _relative_path(assembly.get("blend_path"), root, "assembly.blend_path", errors)
    screenshots = assembly.get("screenshots")
    if not isinstance(screenshots, list):
        errors.append("assembly.screenshots 必须是数组")
    else:
        for index, value in enumerate(screenshots):
            _relative_path(value, root, f"assembly.screenshots[{index}]", errors)
    if not isinstance(assembly.get("instances"), list):
        errors.append("assembly.instances 必须是数组")
    if not isinstance(assembly.get("accepted"), bool):
        errors.append("assembly.accepted 必须是布尔值")
    artifact = assembly.get("artifact")
    if artifact is not None:
        if not isinstance(artifact, dict):
            errors.append("assembly.artifact 必须是对象")
        else:
            revision = artifact.get("revision")
            if (
                not isinstance(revision, int)
                or isinstance(revision, bool)
                or revision < 0
            ):
                errors.append(
                    "assembly.artifact.revision 必须是非负整数"
                )
            blend_hash = artifact.get("blend_sha256")
            if blend_hash is not None and (
                not isinstance(blend_hash, str)
                or not re.fullmatch(r"[0-9a-fA-F]{64}", blend_hash)
            ):
                errors.append(
                    "assembly.artifact.blend_sha256 必须是 SHA-256"
                )
    finishing = assembly.get("finishing")
    if finishing is not None:
        if not isinstance(finishing, dict):
            errors.append("assembly.finishing 必须是对象")
        else:
            if finishing.get("status") not in FINISHING_STATUSES:
                errors.append("assembly.finishing.status 无效")
            views = finishing.get("views")
            if views is not None:
                if not isinstance(views, dict):
                    errors.append("assembly.finishing.views 必须是对象")
                else:
                    for key, value in views.items():
                        if key == "closeups":
                            if (
                                not isinstance(value, list)
                                or not all(
                                    isinstance(item, str) and item.strip()
                                    for item in value
                                )
                            ):
                                errors.append(
                                    "assembly.finishing.views.closeups "
                                    "必须是字符串数组"
                                )
                            else:
                                for index, item in enumerate(value):
                                    _relative_path(
                                        item,
                                        root,
                                        "assembly.finishing.views."
                                        f"closeups[{index}]",
                                        errors,
                                    )
                            continue
                        _relative_path(
                            value,
                            root,
                            f"assembly.finishing.views.{key}",
                            errors,
                        )
            comparison_paths = finishing.get("comparison_paths")
            if comparison_paths is not None:
                if not isinstance(comparison_paths, list):
                    errors.append(
                        "assembly.finishing.comparison_paths 必须是数组"
                    )
                else:
                    for index, value in enumerate(comparison_paths):
                        _relative_path(
                            value,
                            root,
                            "assembly.finishing."
                            f"comparison_paths[{index}]",
                            errors,
                        )
            inspected_views = finishing.get("inspected_views")
            if inspected_views is not None and (
                not isinstance(inspected_views, list)
                or not all(
                    isinstance(value, str) and value.strip()
                    for value in inspected_views
                )
            ):
                errors.append(
                    "assembly.finishing.inspected_views "
                    "必须是字符串数组"
                )
            checks = finishing.get("checks")
            if checks is not None and (
                not isinstance(checks, dict)
                or not all(value is True for value in checks.values())
            ):
                errors.append(
                    "assembly.finishing.checks 必须全部为 true"
                )
            issues = finishing.get("issues")
            if issues is not None:
                if not isinstance(issues, list):
                    errors.append("assembly.finishing.issues 必须是数组")
                else:
                    for index, issue in enumerate(issues):
                        where = f"assembly.finishing.issues[{index}]"
                        if not isinstance(issue, dict):
                            errors.append(f"{where} 必须是对象")
                            continue
                        if issue.get("severity") not in DEFECT_SEVERITIES:
                            errors.append(f"{where}.severity 无效")
                        if issue.get("status") not in DEFECT_STATUSES:
                            errors.append(f"{where}.status 无效")
                        for key in ("observation", "disposition"):
                            if not _nonempty_text(issue.get(key)):
                                errors.append(f"{where}.{key} 不能为空")
            relationships = finishing.get("logical_relationships")
            if relationships is not None:
                if not isinstance(relationships, list):
                    errors.append(
                        "assembly.finishing.logical_relationships "
                        "必须是数组"
                    )
                else:
                    for index, item in enumerate(relationships):
                        where = (
                            "assembly.finishing."
                            f"logical_relationships[{index}]"
                        )
                        if not isinstance(item, dict):
                            errors.append(f"{where} 必须是对象")
                            continue
                        for key in ("id", "relationship", "assessment"):
                            if not _nonempty_text(item.get(key)):
                                errors.append(f"{where}.{key} 不能为空")
                        if item.get("result") not in LIFECYCLE_RESULTS:
                            errors.append(f"{where}.result 无效")
                        if (
                            item.get("result") == "repaired"
                            and not _nonempty_text(item.get("repair"))
                        ):
                            errors.append(
                                f"{where}.repair 在 repaired 时不能为空"
                            )

    if stage == "COMPLETE" and not assembly.get("accepted"):
        warnings.append("项目已标记完成，但整栋尚未验收")
    if scene_skill_version == SKILL_VERSION:
        errors.extend(
            validate_parametric_registry(root, components)
        )
    return errors, warnings


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _stage_ready(
    root: Path,
    stage: str,
    scene: dict[str, Any],
    brief: dict[str, Any],
    concepts: dict[str, Any],
    design: dict[str, Any],
    components: dict[str, Any],
    assembly: dict[str, Any],
    confirmed: bool,
) -> None:
    if stage in USER_CONFIRMED_STAGES:
        _require(confirmed, f"{stage} 需要用户明确确认后才能推进")

    if stage == "BRIEF":
        _require(_nonempty_text(brief.get("summary")), "设计简报缺少 summary")
        _require(isinstance(brief.get("floors"), int) and brief["floors"] > 0, "设计简报缺少楼层数")
        footprint = brief.get("footprint_m") or {}
        _require(
            isinstance(footprint.get("width"), (int, float))
            and footprint["width"] > 0
            and isinstance(footprint.get("depth"), (int, float))
            and footprint["depth"] > 0,
            "设计简报缺少有效占地",
        )
        _require(_nonempty(brief.get("critical_dimensions")), "设计简报缺少关键尺寸")
        _require(_nonempty(brief.get("spatial_constraints")), "设计简报缺少空间约束")
        _require(_nonempty_text(brief.get("delivery")), "设计简报缺少交付目标")
        _require(_nonempty_text(brief.get("camera_use")), "设计简报缺少镜头用途")
        quality_target = brief.get("quality_target")
        _require(
            isinstance(quality_target, dict),
            "设计简报缺少 quality_target",
        )
        _require(
            _nonempty_text(quality_target.get("primary_view")),
            "quality_target 缺少 primary_view",
        )
        priority = quality_target.get("quality_priority")
        _require(
            isinstance(priority, list)
            and {"reference_match", "surface_quality", "construction_logic"}
            <= set(priority),
            "quality_priority 必须包含效果匹配、表面质量和构造逻辑",
        )

    elif stage == "CONCEPTS":
        directions = concepts.get("directions") or []
        _require(len(directions) >= 3, "至少需要 3 个概念方向")
        _require(concepts.get("status") == "selected", "概念方向尚未被用户选中")
        selected_id = concepts.get("selected_direction")
        selected = next(
            (item for item in directions if item.get("direction_id") == selected_id),
            None,
        )
        _require(selected is not None, "找不到选中的概念方向")
        for direction in directions:
            prompt_file = direction.get("prompt_file")
            _require(
                isinstance(prompt_file, str) and (root / prompt_file).is_file(),
                f"{direction.get('direction_id')} 缺少可复制的提示词包",
            )
            prompt_text = (root / prompt_file).read_text(encoding="utf-8")
            _require(
                all(
                    f"IMAGE {index} OF 10" in prompt_text
                    for index in range(1, len(CONCEPT_VIEW_SPECS) + 1)
                ),
                f"{direction.get('direction_id')} 的提示词包不是完整十视图版本",
            )
        view_paths = selected.get("view_paths")
        _require(isinstance(view_paths, dict), f"{selected_id} 缺少 view_paths")
        for view_id in CONCEPT_VIEW_IDS:
            value = view_paths.get(view_id)
            _require(
                isinstance(value, str) and (root / value).is_file(),
                f"{selected_id} 缺少 {view_id} 十视图图片",
            )
        consistency_review = selected.get("consistency_review")
        _require(
            isinstance(consistency_review, dict),
            f"{selected_id} 缺少十视图一致性审查",
        )
        _require(
            consistency_review.get("status") == "pass",
            f"{selected_id} 的十视图一致性审查尚未通过",
        )
        checked_views = consistency_review.get("checked_views")
        _require(
            isinstance(checked_views, list)
            and set(checked_views) == set(CONCEPT_VIEW_IDS),
            f"{selected_id} 的一致性审查必须覆盖全部十个视图",
        )
        checks = consistency_review.get("checks")
        for key in (
            "same_building",
            "same_proportions",
            "same_component_language",
            "complete_views",
            "no_impossible_structure",
        ):
            _require(
                isinstance(checks, dict) and checks.get(key) is True,
                f"{selected_id} 的十视图检查项 {key} 未通过",
            )
        _require(
            isinstance(consistency_review.get("notes"), list)
            and _nonempty(consistency_review.get("notes")),
            f"{selected_id} 的一致性审查缺少说明",
        )

    elif stage == "DESIGN":
        _require(design.get("status") == "approved", "设计合同尚未批准")
        _require(_nonempty_text(design.get("style_id")), "设计合同缺少 style_id")
        style_version = design.get("style_version")
        _require(
            isinstance(style_version, int)
            and not isinstance(style_version, bool)
            and style_version >= 1,
            "设计合同 style_version 必须是大于等于 1 的整数",
        )
        _require(_nonempty(design.get("palette")), "设计合同缺少配色")
        _require(_nonempty(design.get("materials")), "设计合同缺少材质策略")
        _require(_nonempty(design.get("geometry_language")), "设计合同缺少造型语言")
        _require(_nonempty(design.get("component_rules")), "设计合同缺少组件规则")

    elif stage == "COMPONENTS":
        parts = components.get("parts") or []
        _require(_nonempty(parts), "组件清单为空")
        selected_id = concepts.get("selected_direction")
        selected_direction = next(
            (
                item
                for item in concepts.get("directions", [])
                if item.get("direction_id") == selected_id
            ),
            None,
        )
        selected_views = set(
            (selected_direction or {}).get("view_paths", {}).values()
        )
        _require(bool(selected_views), "找不到选中方向的十视图路径")
        reference_errors = _reference_model_gate_errors(
            components.get("reference_models"),
            {
                part.get("part_id")
                for part in parts
                if isinstance(part.get("part_id"), str)
            },
        )
        _require(
            not reference_errors,
            "拆件前必须完成整栋三维参考模型："
            + "；".join(reference_errors),
        )
        decomposition_review = components.get("decomposition_review")
        _require(
            isinstance(decomposition_review, dict),
            "缺少 components.decomposition_review",
        )
        _require(
            decomposition_review.get("status") == "pass",
            "拆件多视图审查尚未通过",
        )
        review_views = decomposition_review.get("source_views")
        _require(
            isinstance(review_views, list)
            and len(set(review_views)) >= 3
            and set(review_views) <= selected_views,
            "拆件审查必须使用至少三个选中方向的多视图",
        )
        for key in (
            "inventory_complete",
            "multi_view_consistent",
            "attachment_logic_verified",
            "assembly_not_fragmented",
            "detail_features_complete",
            "detail_geometry_decisions_verified",
        ):
            _require(
                (decomposition_review.get("checks") or {}).get(key) is True,
                f"拆件审查项 {key} 未通过",
            )
        _require(
            _nonempty(decomposition_review.get("notes")),
            "拆件审查缺少说明",
        )
        for item in components.get("visual_inventory", []):
            source_view = item.get("source_view")
            _require(
                isinstance(source_view, str) and (root / source_view).is_file(),
                f"{item.get('item_id')} 的来源视图不存在",
            )
        for part in parts:
            _require(_nonempty_text(part.get("type")), f"{part.get('part_id')} 缺少 type")
            _require(
                part.get("asset_class") in ASSET_CLASSES,
                f"{part.get('part_id')} 缺少有效 asset_class",
            )
            decomposition_audit = part.get("decomposition_audit")
            _require(
                isinstance(decomposition_audit, dict)
                and decomposition_audit.get("status") == "pass",
                f"{part.get('part_id')} 缺少通过的拆件审查",
            )
            part_source_views = decomposition_audit.get("source_views")
            _require(
                isinstance(part_source_views, list)
                and len(set(part_source_views)) >= 2
                and set(part_source_views) <= selected_views,
                f"{part.get('part_id')} 必须回查至少两个选中方向的多视图",
            )
            for key in (
                "component_scope_complete",
                "multi_view_consistent",
                "attachment_logic_verified",
                "not_fragmented",
            ):
                _require(
                    (decomposition_audit.get("checks") or {}).get(key) is True,
                    f"{part.get('part_id')} 拆件检查项 {key} 未通过",
                )
            _require(
                _nonempty(decomposition_audit.get("notes")),
                f"{part.get('part_id')} 的拆件审查缺少说明",
            )
            if part.get("decision") == "ai_3d":
                for key in ("locked", "guided", "free"):
                    _require(_nonempty(part.get(key)), f"{part.get('part_id')} 缺少 {key} 合同")

        detail_audit = components.get("detail_audit")
        _require(
            isinstance(detail_audit, dict),
            "缺少 components.detail_audit",
        )
        detail_errors: list[str] = []
        _validate_detail_audit(
            detail_audit,
            {part.get("part_id") for part in parts if isinstance(part, dict)},
            root,
            "components.detail_audit",
            detail_errors,
            selected_views,
        )
        _require(
            not detail_errors,
            "细节特征盘点未通过：" + "；".join(detail_errors),
        )
        _require(
            detail_audit.get("status") == "pass",
            "细节特征盘点尚未通过",
        )
        linked_part_ids = {
            feature.get("part_id")
            for feature in detail_audit.get("features", [])
            if isinstance(feature, dict)
            and feature.get("disposition") == "part"
        }
        for part in parts:
            if part.get("decision") == "ai_3d":
                _require(
                    part.get("part_id") in linked_part_ids,
                    f"{part.get('part_id')} 未进入细节特征盘点",
                )

    elif stage == "REFERENCES":
        reference_errors = _reference_model_gate_errors(
            components.get("reference_models"),
            {
                part.get("part_id")
                for part in components.get("parts") or []
                if isinstance(part, dict)
                and isinstance(part.get("part_id"), str)
            },
        )
        _require(
            not reference_errors,
            "参考包阶段缺少可分析的整栋三维参考模型："
            + "；".join(reference_errors),
        )
        parts = components.get("parts") or []
        selected_id = concepts.get("selected_direction")
        selected_direction = next(
            (
                item
                for item in concepts.get("directions", [])
                if item.get("direction_id") == selected_id
            ),
            None,
        )
        selected_views = set(
            (selected_direction or {}).get("view_paths", {}).values()
        )
        for part in parts:
            consensus_errors: list[str] = []
            _validate_reference_consensus(part, root, consensus_errors)
            boundary_errors: list[str] = []
            _validate_boundary_review(part, root, boundary_errors)
            _require(
                not consensus_errors and not boundary_errors,
                f"{part.get('part_id')} 多参考共识未通过："
                + "；".join(consensus_errors + boundary_errors),
            )
            if part.get("decision") != "ai_3d":
                continue
            part_id = part.get("part_id")
            _check_prompt(part.get("prompt"), f"{part_id}.prompt", [])
            prompt = part.get("prompt") or {}
            for key in PROMPT_KEYS:
                _require(_nonempty_text(prompt.get(key)), f"{part_id} 缺少 {key}")
            pack = part.get("reference_pack") or {}
            for kind in ("geometry", "appearance"):
                values = pack.get(kind) or []
                _require(_nonempty(values), f"{part_id} 缺少 {kind} 参考图")
                for value in values:
                    _require(isinstance(value, str) and (root / value).is_file(), f"{part_id} 的参考图不存在：{value}")
            review_only = set(pack.get("review_only") or [])
            generation_refs = set(pack.get("geometry") or []) | set(pack.get("appearance") or [])
            _require(not review_only.intersection(generation_refs), f"{part_id} 把审阅图当成了生成参考")
            reference_audit = pack.get("audit")
            _require(
                isinstance(reference_audit, dict)
                and reference_audit.get("status") == "pass",
                f"{part_id} 缺少通过的拆件图片审查",
            )
            source_views = reference_audit.get("source_views")
            _require(
                isinstance(source_views, list)
                and len(set(source_views)) >= 2
                and set(source_views) <= selected_views,
                f"{part_id} 的拆件图片必须回查至少两个多视图来源",
            )
            for key in (
                "crop_complete",
                "boundary_isolated",
                "matches_multi_view",
                "attachment_visible",
                "no_hidden_context",
            ):
                _require(
                    (reference_audit.get("checks") or {}).get(key) is True,
                    f"{part_id} 的拆件图片检查项 {key} 未通过",
                )
            _require(
                _nonempty(reference_audit.get("notes")),
                f"{part_id} 的拆件图片审查缺少说明",
            )

        route_errors = []
        for part in parts:
            if part.get("decision") == "ai_3d":
                _validate_route_assessment(part, route_errors)
        _require(
            not route_errors,
            "进入生成前必须完成路线评估：" + "；".join(route_errors),
        )

    elif stage == "GENERATION":
        reference_errors = _reference_model_gate_errors(
            components.get("reference_models"),
            {
                part.get("part_id")
                for part in components.get("parts") or []
                if isinstance(part, dict)
                and isinstance(part.get("part_id"), str)
            },
        )
        _require(
            not reference_errors,
            "组件生成前必须完成整栋三维参考模型："
            + "；".join(reference_errors),
        )
        consensus_errors: list[str] = []
        boundary_errors: list[str] = []
        for part in components.get("parts") or []:
            _validate_reference_consensus(part, root, consensus_errors)
            _validate_boundary_review(part, root, boundary_errors)
        _require(
            not consensus_errors and not boundary_errors,
            "进入生成前必须完成多参考共识："
            + "；".join(consensus_errors + boundary_errors),
        )
        route_errors: list[str] = []
        for part in components.get("parts") or []:
            if part.get("decision") == "ai_3d":
                _validate_route_assessment(part, route_errors)
        _require(
            not route_errors,
            "生成路线评估未通过：" + "；".join(route_errors),
        )
        for part in components.get("parts") or []:
            if part.get("decision") != "ai_3d":
                continue
            part_id = part.get("part_id")
            generation = part.get("generation") or {}
            _require(generation.get("status") in {"generated", "approved", "normalized"}, f"{part_id} 尚未完成生成")
            source_path = generation.get("source_path")
            _require(isinstance(source_path, str) and (root / source_path).is_file(), f"{part_id} 缺少生成文件")
            references_used = generation.get("references_used") or []
            for value in references_used:
                _require(isinstance(value, str) and (root / value).is_file(), f"{part_id} 的生成参考图不存在：{value}")
            qa = part.get("qa") or {}
            comparison_path = qa.get("comparison_path")
            _require(
                isinstance(comparison_path, str) and (root / comparison_path).is_file(),
                f"{part_id} 缺少参考对照图",
            )
            _require(qa.get("result") == "pass", f"{part_id} 的参考对照尚未通过")
            review = part.get("review") or {}
            for key in (
                "single_object",
                "clean_background",
                "interface_clean",
                "style_aligned",
                "structure_legible",
                "surface_quality",
                "construction_logic",
            ):
                _require(review.get(key) is True, f"{part_id} 检查项 {key} 未通过")

        for part in components.get("parts") or []:
            qa = part.get("qa") or {}
            built = (
                part.get("decision") == "ai_3d" and qa.get("result") == "pass"
            ) or (part.get("parametric_build") or {}).get("status") == "pass"
            if not built:
                continue
            part_id = part.get("part_id")
            material_errors: list[str] = []
            _validate_material_review(part, root, material_errors)
            _require(
                not material_errors,
                f"{part_id} 材质贴图审查未通过：" + "；".join(material_errors),
            )
            _require(
                ((part.get("qa") or {}).get("material_review") or {}).get(
                    "status"
                )
                == "pass",
                f"{part_id} 材质与贴图渲染尚未通过",
            )

    elif stage == "ASSEMBLY":
        reference_errors = _reference_model_gate_errors(
            components.get("reference_models"),
            {
                part.get("part_id")
                for part in components.get("parts") or []
                if isinstance(part, dict)
                and isinstance(part.get("part_id"), str)
            },
        )
        _require(
            not reference_errors,
            "装配前缺少可分析的整栋三维参考模型："
            + "；".join(reference_errors),
        )
        consensus_errors: list[str] = []
        boundary_errors: list[str] = []
        for part in components.get("parts") or []:
            _validate_reference_consensus(part, root, consensus_errors)
            _validate_boundary_review(part, root, boundary_errors)
        _require(
            not consensus_errors and not boundary_errors,
            "进入装配前所有组件都必须通过多参考共识："
            + "；".join(consensus_errors + boundary_errors),
        )
        blend_path = assembly.get("blend_path")
        _require(isinstance(blend_path, str) and (root / blend_path).is_file(), "缺少整栋 Blender 文件")
        screenshots = assembly.get("screenshots") or []
        _require(len(screenshots) >= 3, "整栋至少需要三张审阅截图")
        for value in screenshots:
            _require(isinstance(value, str) and (root / value).is_file(), f"截图不存在：{value}")
        _require(_nonempty(assembly.get("instances")), "装配记录为空")

    elif stage == "FINISHING":
        quality_target = brief.get("quality_target")
        _require(
            isinstance(quality_target, dict)
            and _nonempty_text(quality_target.get("primary_view"))
            and isinstance(quality_target.get("quality_priority"), list)
            and {
                "reference_match",
                "surface_quality",
                "construction_logic",
            }
            <= set(quality_target.get("quality_priority")),
            "最终精修缺少有效的 quality_target",
        )
        blend_path = assembly.get("blend_path")
        _require(
            isinstance(blend_path, str) and (root / blend_path).is_file(),
            "最终精修缺少整栋 Blender 文件",
        )
        artifact = assembly.get("artifact")
        _require(isinstance(artifact, dict), "缺少 assembly.artifact")
        revision = artifact.get("revision")
        _require(
            isinstance(revision, int)
            and not isinstance(revision, bool)
            and revision >= 1,
            "最终精修 revision 必须大于等于 1",
        )
        blend_hash = artifact.get("blend_sha256")
        _require(
            isinstance(blend_hash, str)
            and _sha256_file(root / blend_path) == blend_hash.lower(),
            "最终精修记录与当前 Blender 文件哈希不一致",
        )
        finishing = assembly.get("finishing")
        _require(isinstance(finishing, dict), "缺少 assembly.finishing")
        _require(
            finishing.get("status") == "pass"
            and finishing.get("result") == "pass",
            "最终面片与效果精修尚未通过",
        )
        _require(
            finishing.get("revision") == revision,
            "最终精修 revision 与 Blender 产物 revision 不一致",
        )
        screenshots = assembly.get("screenshots")
        _require(
            isinstance(screenshots, list)
            and _nonempty(screenshots)
            and all(
                isinstance(value, str) and (root / value).is_file()
                for value in screenshots
            ),
            "最终精修缺少有效的整栋审阅截图",
        )
        _require(
            _nonempty_text(finishing.get("analysis_summary")),
            "最终精修缺少智能分析摘要",
        )
        views = finishing.get("views")
        _require(isinstance(views, dict), "最终精修缺少 views")
        for key in ("hero", "front", "three_quarter"):
            value = views.get(key)
            _require(
                isinstance(value, str) and (root / value).is_file(),
                f"最终精修缺少 {key} 视图",
            )
        _require(
            views.get("hero") in screenshots,
            "最终 hero 图没有登记到 assembly.screenshots",
        )
        closeups = views.get("closeups")
        _require(
            isinstance(closeups, list)
            and _nonempty(closeups)
            and all(
                isinstance(value, str) and (root / value).is_file()
                for value in closeups
            ),
            "最终精修缺少至少一张关键区域近景",
        )
        comparison_paths = finishing.get("comparison_paths")
        _require(
            isinstance(comparison_paths, list)
            and _nonempty(comparison_paths)
            and all(
                isinstance(value, str) and (root / value).is_file()
                for value in comparison_paths
            ),
            "最终精修缺少与概念或构件的参考对照图",
        )
        inspected_views = finishing.get("inspected_views")
        _require(
            isinstance(inspected_views, list)
            and _nonempty(inspected_views)
            and all(
                isinstance(value, str) and value.strip()
                for value in inspected_views
            ),
            "最终精修没有记录实际检查的视图",
        )
        checks = finishing.get("checks")
        for key in (
            "reference_match",
            "surface_quality",
            "mesh_integrity",
            "material_quality",
            "lighting_quality",
            "assembly_seams",
            "construction_logic",
            "all_asset_sources_covered",
        ):
            _require(
                isinstance(checks, dict) and checks.get(key) is True,
                f"最终精修检查项 {key} 未通过",
            )
        issues = finishing.get("issues")
        _require(isinstance(issues, list), "最终精修缺少缺陷记录")
        for issue in issues:
            _require(isinstance(issue, dict), "最终精修缺陷记录格式无效")
            severity = issue.get("severity")
            status = issue.get("status")
            _require(
                severity in DEFECT_SEVERITIES,
                "最终精修缺陷 severity 无效",
            )
            _require(
                status in DEFECT_STATUSES,
                "最终精修缺陷 status 无效",
            )
            _require(
                _nonempty_text(issue.get("observation"))
                and _nonempty_text(issue.get("disposition")),
                "最终精修缺陷缺少观察或处理说明",
            )
            _require(
                not (
                    severity in {"blocker", "high"}
                    and status == "deferred"
                ),
                f"{issue.get('id', '未编号缺陷')} 仍有 blocker/high 问题未修复",
            )
        relationships = finishing.get("logical_relationships")
        _require(
            isinstance(relationships, list) and _nonempty(relationships),
            "最终精修缺少构造逻辑关系分析",
        )
        for item in relationships:
            _require(
                isinstance(item, dict),
                "最终精修构造逻辑记录格式无效",
            )
            for key in ("id", "relationship", "assessment"):
                _require(
                    _nonempty_text(item.get(key)),
                    f"最终精修构造逻辑缺少 {key}",
                )
            _require(
                item.get("result") in {"pass", "repaired"},
                f"{item.get('id')} 仍需用户决策或尚未修复",
            )
            if item.get("result") == "repaired":
                _require(
                    _nonempty_text(item.get("repair")),
                    f"{item.get('id')} 标记为已修复但缺少修复记录",
                )

    elif stage == "REVIEW":
        _require(confirmed, "最终验收需要用户明确确认")
        _stage_ready(
            root,
            "FINISHING",
            scene,
            brief,
            concepts,
            design,
            components,
            assembly,
            confirmed,
        )
        _require(assembly.get("accepted") is True, "整栋验收状态尚未设为 accepted")


def advance_stage(root: Path, confirmed_by_user: bool = False) -> dict[str, Any]:
    root = root.resolve()
    errors, _ = validate_project(root)
    if errors:
        raise ValueError("项目校验未通过：" + "；".join(errors[:5]))
    paths = project_files(root)
    progress = read_json(paths["progress"])
    stage = progress.get("stage")
    if stage == "COMPLETE":
        raise ValueError("项目已经完成")
    if progress.get("pending_decision") and not confirmed_by_user:
        raise ValueError("存在待用户决策事项")
    documents = {name: read_json(path) for name, path in paths.items() if name != "progress"}
    if stage == "REVIEW" and confirmed_by_user:
        _stage_ready(
            root,
            "FINISHING",
            documents["scene"],
            documents["brief"],
            documents["concepts"],
            documents["design"],
            documents["components"],
            documents["assembly"],
            confirmed_by_user,
        )
        assembly = documents["assembly"]
        if assembly.get("accepted") is not True:
            finishing = assembly.get("finishing") or {}
            assembly["accepted"] = True
            assembly["accepted_at"] = now_iso()
            assembly["accepted_revision"] = finishing.get("revision")
            write_json_atomic(paths["assembly"], assembly)
    _stage_ready(
        root,
        stage,
        documents["scene"],
        documents["brief"],
        documents["concepts"],
        documents["design"],
        documents["components"],
        documents["assembly"],
        confirmed_by_user,
    )
    next_stage = STAGES[STAGES.index(stage) + 1]
    progress["last_approved_stage"] = stage
    progress["stage"] = next_stage
    progress["pending_decision"] = None
    progress["updated_at"] = now_iso()
    write_json_atomic(paths["progress"], progress)
    return {"from": stage, "to": next_stage}


def reopen_stage(
    root: Path,
    target_stage: str,
    reason: str,
    confirmed_by_user: bool = False,
) -> dict[str, Any]:
    if not confirmed_by_user:
        raise ValueError("返工或回退需要用户明确确认")
    if target_stage not in STAGES or target_stage == "COMPLETE":
        raise ValueError("无效的回退阶段")
    if not reason.strip():
        raise ValueError("回退必须记录原因")
    root = root.resolve()
    paths = project_files(root)
    progress = read_json(paths["progress"])
    current_stage = progress.get("stage")
    if current_stage not in STAGES:
        raise ValueError("当前阶段无效")
    if STAGES.index(target_stage) >= STAGES.index(current_stage):
        raise ValueError("回退目标必须早于当前阶段")
    history = progress.get("history")
    if not isinstance(history, list):
        history = []
    history.append(
        {
            "from": current_stage,
            "to": target_stage,
            "kind": "reopen",
            "reason": reason.strip(),
            "at": now_iso(),
        }
    )
    progress["history"] = history
    progress["stage"] = target_stage
    progress["pending_decision"] = None
    progress["updated_at"] = now_iso()
    write_json_atomic(paths["progress"], progress)

    assembly_path = paths["assembly"]
    if assembly_path.is_file():
        assembly = read_json(assembly_path)
        if assembly.get("accepted"):
            assembly["accepted"] = False
            assembly["accepted_at"] = None
            assembly["accepted_revision"] = None
            write_json_atomic(assembly_path, assembly)
    return {
        "from": current_stage,
        "to": target_stage,
        "reason": reason.strip(),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="scene-kit concept-first workflow")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="初始化概念优先项目")
    init_parser.add_argument("root", type=Path)
    init_parser.add_argument("--name", required=True)

    validate_parser = subparsers.add_parser("validate", help="只读校验项目")
    validate_parser.add_argument("root", type=Path)

    advance_parser = subparsers.add_parser("advance", help="校验当前阶段并推进")
    advance_parser.add_argument("root", type=Path)
    advance_parser.add_argument("--confirmed-by-user", action="store_true")

    reopen_parser = subparsers.add_parser(
        "reopen",
        help="用户确认后将项目回退到较早阶段进行返工",
    )
    reopen_parser.add_argument("root", type=Path)
    reopen_parser.add_argument("stage", choices=[stage for stage in STAGES if stage != "COMPLETE"])
    reopen_parser.add_argument("--reason", required=True)
    reopen_parser.add_argument("--confirmed-by-user", action="store_true")

    prompts_parser = subparsers.add_parser(
        "prompts", help="为概念方向生成可复制的纯文本提示词包"
    )
    prompts_parser.add_argument("root", type=Path)
    prompts_parser.add_argument("--direction", help="只生成指定方向，例如 D01")

    library_init_parser = subparsers.add_parser(
        "library-init", help="初始化跨项目模型库"
    )
    library_init_parser.add_argument("--library", type=Path)

    library_add_parser = subparsers.add_parser(
        "library-add", help="将已通过 QA 的组件加入模型库"
    )
    library_add_parser.add_argument("project_root", type=Path)
    library_add_parser.add_argument("part_id")
    library_add_parser.add_argument("--library", type=Path)
    library_add_parser.add_argument("--confirmed-by-user", action="store_true")

    library_search_parser = subparsers.add_parser(
        "library-search", help="按类型、标签和风格检索模型库"
    )
    library_search_parser.add_argument("query", nargs="?", default="")
    library_search_parser.add_argument("--library", type=Path)
    library_search_parser.add_argument("--asset-class", choices=sorted(ASSET_CLASSES))
    library_search_parser.add_argument("--type")
    library_search_parser.add_argument("--limit", type=int, default=20)

    library_list_parser = subparsers.add_parser(
        "library-list", help="列出模型库中的全部可用资产"
    )
    library_list_parser.add_argument("--library", type=Path)
    library_list_parser.add_argument("--limit", type=int, default=100)

    library_validate_parser = subparsers.add_parser(
        "library-validate", help="校验模型库目录、元数据和文件哈希"
    )
    library_validate_parser.add_argument("--library", type=Path)

    library_link_parser = subparsers.add_parser(
        "library-link", help="用户确认后，将模型库资产链接到项目组件"
    )
    library_link_parser.add_argument("project_root", type=Path)
    library_link_parser.add_argument("part_id")
    library_link_parser.add_argument("asset_id")
    library_link_parser.add_argument("--library", type=Path)
    library_link_parser.add_argument("--confirmed-by-user", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "init":
            print(json.dumps(initialize_project(args.root, args.name), ensure_ascii=False, indent=2))
            return 0
        if args.command == "validate":
            errors, warnings = validate_project(args.root)
            for warning in warnings:
                print(f"警告：{warning}")
            if errors:
                for error in errors:
                    print(f"错误：{error}", file=sys.stderr)
                return 1
            print(f"校验通过：0 个错误，{len(warnings)} 个警告")
            return 0
        if args.command == "advance":
            result = advance_stage(args.root, args.confirmed_by_user)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.command == "reopen":
            result = reopen_stage(
                args.root,
                args.stage,
                args.reason,
                args.confirmed_by_user,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.command == "prompts":
            result = write_concept_prompt_packs(args.root, args.direction)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.command == "library-init":
            result = initialize_model_library(args.library)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.command == "library-add":
            result = add_component_to_library(
                args.project_root,
                args.part_id,
                args.library,
                args.confirmed_by_user,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.command == "library-search":
            result = search_model_library(
                args.library,
                args.query,
                args.asset_class,
                args.type,
                args.limit,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.command == "library-list":
            result = search_model_library(
                args.library,
                limit=args.limit,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.command == "library-validate":
            library_root = (
                args.library or default_model_library_root()
            ).expanduser().resolve()
            catalog, _ = _require_library_catalog(library_root)
            errors = validate_model_library(library_root, catalog)
            if errors:
                for error in errors:
                    print(f"错误：{error}", file=sys.stderr)
                return 1
            print(
                f"模型库校验通过：{len(catalog.get('assets', []))} 个资产"
            )
            return 0
        if args.command == "library-link":
            result = link_library_asset(
                args.project_root,
                args.part_id,
                args.asset_id,
                args.library,
                args.confirmed_by_user,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"失败：{exc}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
