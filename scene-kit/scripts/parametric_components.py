#!/usr/bin/env python3
"""Parametric component contracts and build-fingerprint helpers.

The registry records how each component is generated, which parameters are
editable, what constraints protect the design, and which audits prove the
last output. A parameter change invalidates the previous audit fingerprint;
the generator must rebuild and rerun all quality checks.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


CONTRACT_STATUSES = {
    "pending",
    "ready",
    "generated",
    "repair_required",
    "pass",
}
GENERATOR_TYPES = {
    "facade_grid_wall",
    "floor_slab_grid",
    "base_ring",
    "roof_system",
    "window_assembly_grid",
    "door_assembly",
    "railing_array",
    "trim_array",
    "quoin_array",
    "step_array",
    "porch_frame",
    "chimney_generator",
    "lantern_generator",
    "vegetation_cluster",
    "ornament_wrapper",
    "library_wrapper",
    "generic_wrapper",
}
IMPLEMENTATIONS = {
    "geometry_nodes",
    "blender_python",
    "python_rebuild",
    "hybrid",
    "ai_wrapper",
    "reuse_wrapper",
}
VARIANT_POLICIES = {
    "regenerate_geometry",
    "topology_stable",
    "wrapper_only",
}
PARAMETER_TYPES = {
    "number",
    "integer",
    "boolean",
    "string",
    "enum",
    "vector",
    "object",
    "array",
}
QUALITY_GATE_KEYS = {
    "require_geometry_audit",
    "require_material_audit",
    "require_texture_mapping_audit",
    "require_multiview_render",
    "require_component_qa",
}


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


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


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _is_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def canonical_contract_hash(
    contract: dict[str, Any],
    root: Path,
) -> str:
    """Hash all inputs that can change generated geometry or materials."""
    document_hash = None
    document = contract.get("parameter_document")
    if _is_text(document):
        path = root / document
        if path.is_file():
            document_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    payload = {
        "generator_id": contract.get("generator_id"),
        "generator_version": contract.get("generator_version"),
        "generator_entrypoint": contract.get("generator_entrypoint"),
        "implementation": contract.get("implementation"),
        "variant_policy": contract.get("variant_policy"),
        "parameters": contract.get("parameters") or {},
        "material_bindings": contract.get("material_bindings") or {},
        "constraints": contract.get("constraints") or [],
        "parameter_document": document,
        "parameter_document_hash": document_hash,
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_registry(
    root: Path,
    components: dict[str, Any],
) -> tuple[dict[str, Any] | None, Path | None, list[str]]:
    errors: list[str] = []
    relative = components.get("parametric_registry")
    if not _is_text(relative):
        return None, None, [
            "components.parametric_registry 不能为空"
        ]
    path = root / relative
    if not path.is_file():
        return None, path, [
            f"components.parametric_registry 文件不存在：{relative}"
        ]
    try:
        registry = _read_json(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return None, path, [
            f"components.parametric_registry 无法读取：{exc}"
        ]
    return registry, path, errors


def validate_registry(
    root: Path,
    components: dict[str, Any],
) -> list[str]:
    """Validate that every component has a current parametric contract."""
    parts = [
        part
        for part in components.get("parts") or []
        if isinstance(part, dict)
    ]
    if not parts:
        return []

    registry, registry_path, errors = load_registry(root, components)
    if registry is None:
        return errors
    if registry.get("schema_version") != 1:
        errors.append(
            "parametric registry.schema_version 必须为 1"
        )
    contracts = registry.get("components")
    if not isinstance(contracts, dict):
        errors.append(
            f"parametric registry.components 必须是对象：{registry_path}"
        )
        return errors

    part_ids = {
        part.get("part_id")
        for part in parts
        if _is_text(part.get("part_id"))
    }
    unknown = sorted(set(contracts) - part_ids)
    if unknown:
        errors.append(
            "parametric registry 包含不存在的组件："
            + ", ".join(unknown)
        )

    for part in parts:
        part_id = part.get("part_id")
        if not _is_text(part_id):
            continue
        part["parametric_contract_id"] = part_id
        contract_id = part.get("parametric_contract_id")
        if not _is_text(contract_id):
            errors.append(
                f"components.parts[{part_id}].parametric_contract_id "
                "不能为空"
            )
            continue
        if contract_id != part_id:
            errors.append(
                f"components.parts[{part_id}].parametric_contract_id "
                f"必须为 {part_id}"
            )
        contract = contracts.get(contract_id)
        if not isinstance(contract, dict):
            errors.append(
                f"parametric registry 缺少组件合同：{contract_id}"
            )
            continue
        _validate_contract(
            root,
            part,
            contract_id,
            contract,
            errors,
        )
        built = (
            (part.get("qa") or {}).get("result") == "pass"
            or (part.get("parametric_build") or {}).get("status")
            == "pass"
        )
        if built and contract.get("status") not in {"generated", "pass"}:
            errors.append(
                f"components.parts[{part_id}] 已构建，但参数合同状态"
                f"为 {contract.get('status')}；必须记录生成版本和审计"
            )
    return errors


def _validate_path(
    root: Path,
    value: Any,
    where: str,
    errors: list[str],
    required: bool = True,
) -> Path | None:
    if not _is_text(value):
        if required:
            errors.append(f"{where} 不能为空")
        return None
    path = (root / value).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        errors.append(f"{where} 必须位于项目目录内")
        return None
    if required and not path.is_file():
        errors.append(f"{where} 文件不存在")
    return path


def _validate_contract(
    root: Path,
    part: dict[str, Any],
    contract_id: str,
    contract: dict[str, Any],
    errors: list[str],
) -> None:
    where = f"parametric registry.components[{contract_id}]"
    if contract.get("part_id") != contract_id:
        errors.append(f"{where}.part_id 必须为 {contract_id}")
    for key in ("generator_id", "generator_version"):
        if not _is_text(contract.get(key)) and not isinstance(
            contract.get(key),
            int,
        ):
            errors.append(f"{where}.{key} 不能为空")
    if contract.get("generator_type") not in GENERATOR_TYPES:
        errors.append(f"{where}.generator_type 无效")
    if contract.get("implementation") not in IMPLEMENTATIONS:
        errors.append(f"{where}.implementation 无效")
    if contract.get("variant_policy") not in VARIANT_POLICIES:
        errors.append(f"{where}.variant_policy 无效")
    if contract.get("status") not in CONTRACT_STATUSES:
        errors.append(f"{where}.status 无效")

    parameters = contract.get("parameters")
    if not isinstance(parameters, dict) or not parameters:
        errors.append(f"{where}.parameters 必须是非空对象")
    schema = contract.get("parameter_schema")
    if not isinstance(schema, dict) or not schema:
        errors.append(f"{where}.parameter_schema 必须是非空对象")
    else:
        for key, spec in schema.items():
            if not _is_text(key) or not isinstance(spec, dict):
                errors.append(
                    f"{where}.parameter_schema.{key} 必须是对象"
                )
                continue
            if spec.get("type") not in PARAMETER_TYPES:
                errors.append(
                    f"{where}.parameter_schema.{key}.type 无效"
                )
            if not isinstance(spec.get("editable"), bool):
                errors.append(
                    f"{where}.parameter_schema.{key}.editable "
                    "必须是布尔值"
                )

    constraints = contract.get("constraints")
    if not isinstance(constraints, list) or not constraints:
        errors.append(f"{where}.constraints 不能为空")
    else:
        for index, item in enumerate(constraints):
            if not isinstance(item, dict):
                errors.append(
                    f"{where}.constraints[{index}] 必须是对象"
                )
                continue
            for key in ("id", "rule", "enforced_by"):
                if not _is_text(item.get(key)):
                    errors.append(
                        f"{where}.constraints[{index}].{key} 不能为空"
                    )

    outputs = contract.get("outputs")
    if not isinstance(outputs, dict) or not outputs:
        errors.append(f"{where}.outputs 必须是非空对象")
    else:
        for key in ("root_object", "collection"):
            if not _is_text(outputs.get(key)):
                errors.append(f"{where}.outputs.{key} 不能为空")
        for key in ("blend_path", "source_path"):
            if outputs.get(key):
                _validate_path(
                    root,
                    outputs[key],
                    f"{where}.outputs.{key}",
                    errors,
                )

    material_bindings = contract.get("material_bindings")
    if not isinstance(material_bindings, dict) or not material_bindings:
        errors.append(f"{where}.material_bindings 必须是非空对象")

    document = contract.get("parameter_document")
    if document:
        _validate_path(
            root,
            document,
            f"{where}.parameter_document",
            errors,
        )

    gate = contract.get("quality_gate")
    if not isinstance(gate, dict):
        errors.append(f"{where}.quality_gate 必须是对象")
    else:
        if gate.get("approval_scope") != "per_parameters_hash":
            errors.append(
                f"{where}.quality_gate.approval_scope "
                "必须为 per_parameters_hash"
            )
        for key in QUALITY_GATE_KEYS:
            if gate.get(key) is not True:
                errors.append(
                    f"{where}.quality_gate.{key} 必须为 true"
                )

    status = contract.get("status")
    last_build = contract.get("last_build")
    if status in {"generated", "pass"}:
        if not isinstance(last_build, dict):
            errors.append(f"{where}.last_build 必须是对象")
            return
        if last_build.get("status") != "pass":
            errors.append(
                f"{where}.last_build.status 必须为 pass"
            )
        current_hash = canonical_contract_hash(contract, root)
        if last_build.get("parameters_hash") != current_hash:
            errors.append(
                f"{where} 参数已变化但未重建；请重新生成并完成"
                "几何、材质、贴图和多视图审计"
            )
        _validate_path(
            root,
            last_build.get("audit_path"),
            f"{where}.last_build.audit_path",
            errors,
        )
        _validate_path(
            root,
            last_build.get("material_review_path"),
            f"{where}.last_build.material_review_path",
            errors,
        )
        if not _is_text(last_build.get("built_at")):
            errors.append(f"{where}.last_build.built_at 不能为空")
        if last_build.get("revision") != contract.get("revision"):
            errors.append(
                f"{where}.last_build.revision 必须与合同 revision 一致"
            )
    elif last_build is not None and not isinstance(last_build, dict):
        errors.append(f"{where}.last_build 必须是对象或 null")


def _generator_for_part(part: dict[str, Any]) -> tuple[str, str]:
    part_type = str(part.get("type", "")).lower()
    part_id = str(part.get("part_id", "")).lower()
    if "lantern" in part_id or "lantern" in part_type:
        return "lantern_generator", "blender_python"
    if "window" in part_type:
        return "window_assembly_grid", "blender_python"
    if "door" in part_type or "portal" in part_id:
        return "door_assembly", "blender_python"
    if "railing" in part_type:
        return "railing_array", "geometry_nodes"
    if "trim" in part_type:
        return "trim_array", "geometry_nodes"
    if "quoin" in part_type:
        return "quoin_array", "geometry_nodes"
    if "steps" in part_type:
        return "step_array", "blender_python"
    if "porch" in part_type:
        return "porch_frame", "blender_python"
    if "chimney" in part_type:
        return "chimney_generator", "blender_python"
    if "wall" in part_id:
        return "facade_grid_wall", "hybrid"
    if "floor" in part_id:
        return "floor_slab_grid", "blender_python"
    if "base" in part_id:
        return "base_ring", "blender_python"
    if "roof" in part_id:
        return "roof_system", "geometry_nodes"
    if part.get("asset_class") == "vegetation":
        return "vegetation_cluster", "ai_wrapper"
    if part.get("asset_class") == "decorative_ornament":
        return "ornament_wrapper", "ai_wrapper"
    return "generic_wrapper", "hybrid"


def scaffold_registry(
    root: Path,
    force: bool = False,
) -> tuple[Path, dict[str, Any]]:
    components_path = root / "internal" / "components.json"
    components = _read_json(components_path)
    relative = components.get("parametric_registry")
    if not _is_text(relative):
        relative = "internal/parametric_components.json"
        components["parametric_registry"] = relative
        _write_json_atomic(components_path, components)
    registry_path = root / relative
    if registry_path.exists() and not force:
        raise ValueError(
            f"Registry already exists: {registry_path}; use --force"
        )

    contracts: dict[str, Any] = {}
    for part in components.get("parts") or []:
        if not isinstance(part, dict):
            continue
        part_id = part.get("part_id")
        if not _is_text(part_id):
            continue
        build = part.get("parametric_build") or {}
        generation = part.get("generation") or {}
        material_review = (part.get("qa") or {}).get(
            "material_review"
        ) or {}
        texture_audit = material_review.get("texture_audit") or {}
        generator_type, implementation = _generator_for_part(part)
        parameters = dict(part.get("locked") or {})
        parameters.update(
            {
                "asset_class": part.get("asset_class"),
                "component_type": part.get("type"),
                "instances": next(
                    (
                        item.get("instances")
                        for item in components.get("visual_inventory") or []
                        if item.get("part_id") == part_id
                    ),
                    1,
                ),
            }
        )
        for key in (
            "dimensions_m",
            "wall_height_m",
            "wall_thickness_m",
            "grid_columns",
            "grid_rows",
            "pane_count",
            "major_vertical_sections",
            "central_split_columns",
            "slab_thickness_m",
            "body_height_m",
            "cap_projection_m",
            "door_gap_width_m",
        ):
            if key in build:
                parameters[key] = build[key]
        pattern = (
            (part.get("fine_structure_review") or {}).get("pattern")
        )
        if isinstance(pattern, dict):
            parameters["pattern"] = pattern
        contract: dict[str, Any] = {
            "part_id": part_id,
            "generator_id": f"{part_id}__{generator_type}",
            "generator_version": 1,
            "generator_entrypoint": (
                "scripts/generate_wall_envelope.py"
                if generator_type == "facade_grid_wall"
                else "scripts/generate_window_assembly.py"
                if generator_type == "window_assembly_grid"
                else "scripts/generate_roof_system.py"
                if generator_type == "roof_system"
                else "scripts/generate_stone_chimney.py"
                if generator_type == "chimney_generator"
                else "scripts/generate_entrance_portal.py"
                if generator_type == "door_assembly"
                else "scripts/generate_entrance_steps.py"
                if generator_type == "step_array"
                else "scripts/generate_wall_lantern.py"
                if generator_type == "lantern_generator"
                else "scripts/generate_timber_porch.py"
                if generator_type == "porch_frame"
                else "scripts/generate_porch_railing.py"
                if generator_type == "railing_array"
                else "scripts/generate_corner_quoins.py"
                if generator_type == "quoin_array"
                else "scripts/generate_stone_facade_trim.py"
                if generator_type == "trim_array"
                else None
            ),
            "generator_type": generator_type,
            "implementation": implementation,
            "variant_policy": (
                "regenerate_geometry"
                if implementation
                in {"geometry_nodes", "blender_python", "python_rebuild", "hybrid"}
                else "wrapper_only"
            ),
            "status": "pending",
            "revision": 1,
            "parameters": parameters,
            "parameter_schema": {
                "component_type": {
                    "type": "string",
                    "editable": False,
                },
                "instances": {
                    "type": "integer",
                    "editable": True,
                    "minimum": 0,
                },
                "locked": {
                    "type": "object",
                    "editable": True,
                },
            },
            "constraints": [
                {
                    "id": "interface_contract",
                    "rule": "Preserve locked interfaces and mounting dimensions.",
                    "enforced_by": "scene_kit.py validate",
                },
                {
                    "id": "quality_on_every_variant",
                    "rule": "Every rebuilt variant must rerun geometry, material, texture projection, multiview and component QA.",
                    "enforced_by": "parametric_components.py validate",
                },
            ],
            "outputs": {
                "root_object": build.get(
                    "object_name",
                    f"SK_{part_id}_ROOT",
                ),
                "collection": (
                    "SK_COL_AI"
                    if part.get("decision") == "ai_3d"
                    else "SK_COL_Structure"
                ),
                "blend_path": build.get("blend_path"),
                "source_path": (
                    build.get("source_path")
                    or generation.get("source_path")
                ),
            },
            "material_bindings": {
                "texture_source": material_review.get("texture_source"),
                "polyhaven_assets": material_review.get(
                    "polyhaven_assets",
                    [],
                ),
                "material_review": material_review.get("status", "pending"),
            },
            "quality_gate": {
                "approval_scope": "per_parameters_hash",
                "require_geometry_audit": True,
                "require_material_audit": True,
                "require_texture_mapping_audit": True,
                "require_multiview_render": True,
                "require_component_qa": True,
            },
            "last_build": None,
        }
        openings = build.get("openings_path")
        if openings:
            contract["parameter_document"] = openings
        audit_path = (
            build.get("audit_path")
            or texture_audit.get("audit_path")
        )
        if (
            ((part.get("qa") or {}).get("result") == "pass")
            and audit_path
            and material_review.get("reference_comparison")
        ):
            contract["status"] = "pass"
            contract["last_build"] = {
                "status": "pass",
                "revision": contract["revision"],
                "parameters_hash": canonical_contract_hash(
                    contract,
                    root,
                ),
                "audit_path": audit_path,
                "material_review_path": material_review[
                    "reference_comparison"
                ],
                "built_at": _now_iso(),
            }
        contracts[part_id] = contract

    _write_json_atomic(components_path, components)
    registry = {
        "schema_version": 1,
        "updated_at": _now_iso(),
        "components": contracts,
    }
    _write_json_atomic(registry_path, registry)
    return registry_path, registry


def refresh_build_fingerprint(
    root: Path,
    part_id: str,
) -> dict[str, Any]:
    components = _read_json(root / "internal" / "components.json")
    registry, registry_path, errors = load_registry(root, components)
    if registry is None or registry_path is None:
        raise ValueError("; ".join(errors))
    contract = (registry.get("components") or {}).get(part_id)
    if not isinstance(contract, dict):
        raise ValueError(f"Unknown parametric component: {part_id}")
    last_build = contract.get("last_build")
    if not isinstance(last_build, dict):
        last_build = {}
    last_build["parameters_hash"] = canonical_contract_hash(contract, root)
    last_build["revision"] = contract.get("revision")
    last_build.setdefault("built_at", _now_iso())
    contract["last_build"] = last_build
    registry["updated_at"] = _now_iso()
    _write_json_atomic(registry_path, registry)
    return last_build


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate scene-kit parametric component contracts"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    validate_parser = sub.add_parser("validate")
    validate_parser.add_argument("project", type=Path)

    hash_parser = sub.add_parser("hash")
    hash_parser.add_argument("project", type=Path)
    hash_parser.add_argument("part_id")

    scaffold_parser = sub.add_parser("scaffold")
    scaffold_parser.add_argument("project", type=Path)
    scaffold_parser.add_argument("--force", action="store_true")

    refresh_parser = sub.add_parser("refresh-build")
    refresh_parser.add_argument("project", type=Path)
    refresh_parser.add_argument("part_id")

    args = parser.parse_args(argv)
    root = args.project.expanduser().resolve()
    if args.command == "validate":
        components = _read_json(root / "internal" / "components.json")
        errors = validate_registry(root, components)
        for error in errors:
            print(error, file=sys.stderr)
        if errors:
            return 1
        print("Parametric registry is valid")
        return 0
    if args.command == "hash":
        components = _read_json(root / "internal" / "components.json")
        registry, _, errors = load_registry(root, components)
        if registry is None:
            print("; ".join(errors), file=sys.stderr)
            return 1
        contract = (registry.get("components") or {}).get(
            args.part_id
        )
        if not isinstance(contract, dict):
            print(f"Unknown component: {args.part_id}", file=sys.stderr)
            return 1
        print(canonical_contract_hash(contract, root))
        return 0
    if args.command == "scaffold":
        path, registry = scaffold_registry(root, force=args.force)
        print(
            f"Created {path} with "
            f"{len(registry['components'])} component contracts"
        )
        return 0
    if args.command == "refresh-build":
        value = refresh_build_fingerprint(root, args.part_id)
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
