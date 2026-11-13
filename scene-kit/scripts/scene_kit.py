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


SCHEMA_VERSION = 1
SKILL_VERSION = "7.2"
SUPPORTED_SKILL_VERSIONS = {"7.1", "7.2"}
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
            "decomposition_review": {
                "status": "pending",
                "source_views": [],
                "checks": {
                    "inventory_complete": False,
                    "multi_view_consistent": False,
                    "attachment_logic_verified": False,
                    "assembly_not_fragmented": False,
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

    elif stage == "REFERENCES":
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

    elif stage == "GENERATION":
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

    elif stage == "ASSEMBLY":
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
