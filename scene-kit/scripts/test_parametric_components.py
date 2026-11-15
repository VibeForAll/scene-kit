#!/usr/bin/env python3

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import parametric_components


class ParametricComponentTests(unittest.TestCase):
    def _write(self, root: Path, relative: str, value: object) -> str:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(value, (dict, list)):
            text = json.dumps(value, ensure_ascii=False, indent=2)
        else:
            text = str(value)
        path.write_text(text, encoding="utf-8")
        return relative

    def _setup_project(self) -> tuple[tempfile.TemporaryDirectory, Path]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        labels = self._write(
            root,
            "internal/opening_layout.json",
            {"openings": [{"id": "window_01", "enabled": True}]},
        )
        audit = self._write(root, "preview/audit.json", {"status": "pass"})
        material = self._write(
            root,
            "preview/material.jpg",
            "material-review",
        )
        components = {
            "parametric_registry": "internal/parametric_components.json",
            "parts": [
                {
                    "part_id": "window_01",
                    "parametric_contract_id": "window_01",
                }
            ],
        }
        self._write(
            root,
            "internal/components.json",
            components,
        )
        contract = {
            "part_id": "window_01",
            "generator_id": "window_01__window_assembly_grid",
            "generator_version": 1,
            "generator_type": "window_assembly_grid",
            "implementation": "blender_python",
            "variant_policy": "regenerate_geometry",
            "status": "pass",
            "revision": 1,
            "parameter_document": labels,
            "parameters": {
                "width_m": 1.2,
                "height_m": 1.5,
                "columns": 4,
                "rows": 4,
            },
            "parameter_schema": {
                "width_m": {
                    "type": "number",
                    "editable": True,
                    "unit": "m",
                },
                "height_m": {
                    "type": "number",
                    "editable": True,
                    "unit": "m",
                },
            },
            "constraints": [
                {
                    "id": "interface",
                    "rule": "Keep the wall opening and window interface equal.",
                    "enforced_by": "generator",
                }
            ],
            "outputs": {
                "root_object": "SK_window_01_ROOT",
                "collection": "SK_COL_AI",
            },
            "material_bindings": {
                "frame": "deep_brown_wood",
                "glass": "smoky_glass",
            },
            "quality_gate": {
                "approval_scope": "per_parameters_hash",
                "require_geometry_audit": True,
                "require_material_audit": True,
                "require_texture_mapping_audit": True,
                "require_multiview_render": True,
                "require_component_qa": True,
            },
            "last_build": {
                "status": "pass",
                "revision": 1,
                "audit_path": audit,
                "material_review_path": material,
                "built_at": "2026-11-14T00:00:00+08:00",
            },
        }
        contract["last_build"]["parameters_hash"] = (
            parametric_components.canonical_contract_hash(contract, root)
        )
        registry = {
            "schema_version": 1,
            "components": {"window_01": contract},
        }
        self._write(
            root,
            "internal/parametric_components.json",
            registry,
        )
        return temporary, root

    def test_current_parameters_hash_passes(self) -> None:
        temporary, root = self._setup_project()
        try:
            components = json.loads(
                (root / "internal/components.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                parametric_components.validate_registry(root, components),
                [],
            )
        finally:
            temporary.cleanup()

    def test_parameter_change_invalidates_previous_build(self) -> None:
        temporary, root = self._setup_project()
        try:
            path = root / "internal/parametric_components.json"
            registry = json.loads(path.read_text(encoding="utf-8"))
            registry["components"]["window_01"]["parameters"][
                "width_m"
            ] = 1.5
            path.write_text(
                json.dumps(registry, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            components = json.loads(
                (root / "internal/components.json").read_text(
                    encoding="utf-8"
                )
            )
            errors = parametric_components.validate_registry(
                root,
                components,
            )
            self.assertTrue(
                any("参数已变化但未重建" in error for error in errors)
            )
        finally:
            temporary.cleanup()

    def test_every_part_requires_a_contract(self) -> None:
        temporary, root = self._setup_project()
        try:
            components = json.loads(
                (root / "internal/components.json").read_text(
                    encoding="utf-8"
                )
            )
            components["parts"].append(
                {
                    "part_id": "door_01",
                    "parametric_contract_id": "door_01",
                }
            )
            errors = parametric_components.validate_registry(
                root,
                components,
            )
            self.assertTrue(
                any("缺少组件合同：door_01" in error for error in errors)
            )
        finally:
            temporary.cleanup()

if __name__ == "__main__":
    unittest.main()
