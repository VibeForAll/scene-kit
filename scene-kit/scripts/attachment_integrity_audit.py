"""Validate backside volume and host connections for attached components."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    args = parser.parse_args()
    project = args.project.expanduser().resolve()
    components = json.loads(
        (project / "internal" / "components.json").read_text(encoding="utf-8")
    )
    audit = components.get("attachment_integrity_audit")
    part_ids = {
        part.get("part_id")
        for part in components.get("parts", [])
        if isinstance(part, dict)
    }
    errors = []
    checks = {}
    if not isinstance(audit, dict):
        errors.append("components.attachment_integrity_audit is missing")
        audit = {}
    status = audit.get("status")
    if status not in {"pending", "repair_required", "pass"}:
        errors.append("attachment_integrity_audit.status is invalid")
    source_views = audit.get("source_views")
    if not isinstance(source_views, list):
        errors.append("attachment_integrity_audit.source_views must be a list")
        source_views = []
    if status == "pass" and not source_views:
        errors.append("attachment_integrity_audit.source_views is empty")
    for relative in source_views:
        if not (project / relative).is_file():
            errors.append(f"source view not found: {relative}")

    items = audit.get("items")
    if not isinstance(items, list):
        errors.append("attachment_integrity_audit.items must be a list")
        items = []
    if status == "pass" and not items:
        errors.append("attachment_integrity_audit.items is empty")
    for index, item in enumerate(items):
        where = f"attachment_integrity_audit.items[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{where} must be an object")
            continue
        if item.get("part_id") not in part_ids:
            errors.append(f"{where}.part_id is not a project component")
        if not isinstance(item.get("attachment_id"), str) or not item[
            "attachment_id"
        ].strip():
            errors.append(f"{where}.attachment_id is required")
        hosts = item.get("host_part_ids")
        if not isinstance(hosts, list) or not hosts:
            errors.append(f"{where}.host_part_ids is required")
        else:
            for host in hosts:
                if host not in part_ids:
                    errors.append(f"{where}.host_part_ids contains unknown {host}")
        for key in ("has_volume", "has_back_enclosure", "has_side_enclosure"):
            if item.get(key) is not True:
                errors.append(f"{where}.{key} must be true")
        if item.get("front_plane_only") is not False:
            errors.append(f"{where}.front_plane_only must be false")
        if item.get("host_contact_verified") is not True:
            errors.append(f"{where}.host_contact_verified must be true")
        projection = item.get("body_projection_beyond_host_m")
        if (
            not isinstance(projection, (int, float))
            or isinstance(projection, bool)
            or projection <= 0.05
        ):
            errors.append(
                f"{where}.body_projection_beyond_host_m must exceed 0.05"
            )
        eave_setback = item.get("front_eave_setback_m")
        if (
            not isinstance(eave_setback, (int, float))
            or isinstance(eave_setback, bool)
            or eave_setback < 0
        ):
            errors.append(
                f"{where}.front_eave_setback_m must be non-negative"
            )
        if item.get("roof_covers_body_rear") is not True:
            errors.append(f"{where}.roof_covers_body_rear must be true")
        contact_evidence = item.get("host_contact_evidence")
        if not isinstance(contact_evidence, list) or not contact_evidence:
            errors.append(f"{where}.host_contact_evidence is required")
        else:
            for relative in contact_evidence:
                if not (project / relative).is_file():
                    errors.append(f"host contact evidence not found: {relative}")
        evidence_views = item.get("evidence_views")
        if not isinstance(evidence_views, list) or len(set(evidence_views)) < 2:
            errors.append(f"{where}.evidence_views requires at least two views")
        else:
            for relative in evidence_views:
                if not (project / relative).is_file():
                    errors.append(f"attachment evidence not found: {relative}")
        if item.get("status") != "pass":
            errors.append(f"{where}.status must be pass")

    declared_checks = audit.get("checks")
    if not isinstance(declared_checks, dict):
        errors.append("attachment_integrity_audit.checks must be an object")
    elif status == "pass" and (
        not declared_checks
        or not all(value is True for value in declared_checks.values())
    ):
        errors.append("attachment_integrity_audit.checks must all be true")
    unresolved = audit.get("unresolved")
    if not isinstance(unresolved, list):
        errors.append("attachment_integrity_audit.unresolved must be a list")
    elif status == "pass" and unresolved:
        errors.append("attachment_integrity_audit.unresolved must be empty")
    decomposition = components.get("decomposition_review") or {}
    checks["decomposition_attachment_integrity_verified"] = (
        (decomposition.get("checks") or {}).get(
            "attachment_integrity_verified"
        )
        is True
    )
    checks["audit_status_pass"] = status == "pass"
    checks["source_views_exist"] = all(
        (project / relative).is_file() for relative in source_views
    )
    checks["attachments_have_host_connections"] = all(
        isinstance(item, dict)
        and item.get("host_contact_verified") is True
        and item.get("front_plane_only") is False
        and isinstance(item.get("body_projection_beyond_host_m"), (int, float))
        and item.get("body_projection_beyond_host_m") > 0.05
        and isinstance(item.get("front_eave_setback_m"), (int, float))
        and item.get("front_eave_setback_m") >= 0
        and item.get("roof_covers_body_rear") is True
        for item in items
    )
    for key, value in checks.items():
        if value is not True:
            errors.append(f"attachment integrity check {key} failed")

    report = {
        "schema_version": 1,
        "status": "pass" if not errors else "repair_required",
        "attachment_count": len(items),
        "checks": checks,
        "errors": errors,
    }
    output = project / "internal" / "attachment_integrity_audit.json"
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
