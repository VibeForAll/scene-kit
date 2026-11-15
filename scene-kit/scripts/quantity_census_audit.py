"""Validate a project's critical-feature quantity census."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load(project, relative):
    return json.loads((project / relative).read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    args = parser.parse_args()
    project = args.project.expanduser().resolve()
    components_path = project / "internal" / "components.json"
    components = json.loads(components_path.read_text(encoding="utf-8"))
    audit = components.get("quantity_audit")
    errors = []
    checks = {}
    if not isinstance(audit, dict):
        errors.append("components.quantity_audit is missing")
        audit = {}
    counts = audit.get("counts")
    if not isinstance(counts, dict) or not counts:
        errors.append("quantity_audit.counts must be a non-empty object")
        counts = {}
    source_views = audit.get("source_views")
    if not isinstance(source_views, list) or not source_views:
        errors.append("quantity_audit.source_views must be non-empty")
    else:
        for relative in source_views:
            if not (project / relative).is_file():
                errors.append(f"quantity source view not found: {relative}")

    assembly_path = project / "internal" / "assembly.json"
    assembly = load(project, "internal/assembly.json") if assembly_path.is_file() else {}
    assembly_counts = {}
    for instance in assembly.get("instances", []):
        part_id = instance.get("part_id")
        assembly_counts[part_id] = assembly_counts.get(part_id, 0) + 1

    front_path = project / "internal" / "assembly_front_visibility_audit.json"
    front = load(project, "internal/assembly_front_visibility_audit.json") if front_path.is_file() else None
    live_part_counts = (
        (front or {}).get("inventory", {}).get("part_counts", {})
    )
    for key, item in counts.items():
        where = f"quantity_audit.counts.{key}"
        if not isinstance(item, dict):
            errors.append(f"{where} must be an object")
            continue
        expected = item.get("expected")
        actual = item.get("actual")
        if not isinstance(expected, int) or expected < 0:
            errors.append(f"{where}.expected must be a non-negative integer")
        if not isinstance(actual, int) or actual < 0:
            errors.append(f"{where}.actual must be a non-negative integer")
        elif expected != actual:
            errors.append(f"{where}.expected != actual")
        if not isinstance(item.get("unit"), str) or not item["unit"].strip():
            errors.append(f"{where}.unit is required")
        if item.get("count_scope") not in {
            "live_part_instances",
            "embedded_geometry",
            "removed_feature",
        }:
            errors.append(f"{where}.count_scope is invalid")
        evidence = item.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"{where}.evidence must be non-empty")
        else:
            for relative in evidence:
                if not (project / relative).is_file():
                    errors.append(f"{where} evidence not found: {relative}")
        part_id = item.get("part_id")
        if item.get("count_scope") == "live_part_instances" and part_id:
            live_count = live_part_counts.get(part_id)
            if live_count is None:
                live_count = assembly_counts.get(part_id)
            if live_count != actual:
                errors.append(
                    f"{where}.actual={actual} but live part count is {live_count}"
                )
        if item.get("count_scope") == "removed_feature" and actual != 0:
            errors.append(f"{where} is a removed feature but actual is not zero")

    windows = counts.get("main_windows")
    if isinstance(windows, dict):
        breakdown = windows.get("facade_breakdown")
        if not isinstance(breakdown, dict) or not breakdown:
            errors.append("main_windows.facade_breakdown is required")
            breakdown = {}
        total = 0
        for facade, floors in breakdown.items():
            if not isinstance(floors, dict):
                errors.append(
                    f"main_windows.facade_breakdown.{facade} must be an object"
                )
                continue
            lower = floors.get("lower", 0)
            upper = floors.get("upper", 0)
            facade_total = floors.get("total")
            if (
                not all(isinstance(value, int) and value >= 0 for value in (lower, upper))
                or not isinstance(facade_total, int)
                or facade_total != lower + upper
            ):
                errors.append(
                    f"main_windows facade {facade} total must equal lower + upper"
                )
            else:
                total += facade_total
        if total != windows.get("expected"):
            errors.append(
                f"main_windows total {total} != expected {windows.get('expected')}"
            )
        if front:
            live = front.get("facade_schedule", {}).get("actual_counts", {})
            for facade, floors in breakdown.items():
                for floor in ("lower", "upper"):
                    if live.get(facade, {}).get(floor) != floors.get(floor):
                        errors.append(
                            f"main_windows {facade}.{floor} differs from live audit"
                        )

    if front:
        checks["live_front_audit_available"] = True
        checks["live_front_audit_pass"] = front.get("status") == "pass"
    else:
        checks["live_front_audit_available"] = False
    checks["assembly_record_available"] = bool(assembly)
    checks["quantity_source_views_exist"] = all(
        (project / relative).is_file() for relative in source_views
    )
    checks["all_expected_equal_actual"] = all(
        isinstance(item, dict)
        and item.get("expected") == item.get("actual")
        for item in counts.values()
    )
    checks["all_declared_checks_pass"] = all(
        value is True for value in (audit.get("checks") or {}).values()
    )
    checks["unresolved_empty"] = audit.get("unresolved") == []
    decomposition = components.get("decomposition_review") or {}
    checks["decomposition_quantity_verified"] = (
        (decomposition.get("checks") or {}).get("quantity_verified") is True
    )
    if audit.get("status") != "pass":
        errors.append("quantity_audit.status must be pass")
    for key, value in checks.items():
        if value is not True:
            errors.append(f"quantity check {key} is not pass")

    report = {
        "schema_version": 1,
        "status": "pass" if not errors else "repair_required",
        "project": str(project),
        "count_types": len(counts),
        "live_part_counts": live_part_counts,
        "assembly_part_counts": assembly_counts,
        "checks": checks,
        "errors": errors,
    }
    output = project / "internal" / "quantity_census_audit.json"
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
