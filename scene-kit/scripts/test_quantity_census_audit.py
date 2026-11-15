#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("quantity_census_audit.py")


class QuantityCensusAuditTests(unittest.TestCase):
    def _write(self, root: Path, relative: str, value) -> None:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(value, (dict, list)):
            path.write_text(
                json.dumps(value, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        else:
            path.write_text(str(value), encoding="utf-8")

    def _project(self):
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        for view in ("front", "back", "left", "right", "top", "front_left_45"):
            self._write(root, f"raw/{view}.png", view)
        self._write(root, "evidence/windows.json", {"status": "pass"})
        quantity = {
            "status": "pass",
            "source_views": [
                f"raw/{view}.png"
                for view in ("front", "back", "left", "right", "top", "front_left_45")
            ],
            "counts": {
                "main_windows": {
                    "expected": 7,
                    "actual": 7,
                    "unit": "window",
                    "part_id": "window",
                    "count_scope": "live_part_instances",
                    "facade_breakdown": {
                        "front": {"lower": 3, "upper": 4, "total": 7}
                    },
                    "evidence": ["evidence/windows.json"],
                }
            },
            "checks": {"window_matrix_verified": True},
            "unresolved": [],
        }
        self._write(
            root,
            "internal/components.json",
            {
                "quantity_audit": quantity,
                "decomposition_review": {
                    "checks": {"quantity_verified": True}
                },
            },
        )
        self._write(
            root,
            "internal/assembly.json",
            {
                "instances": [
                    {"instance_id": f"w{index}", "part_id": "window"}
                    for index in range(7)
                ]
            },
        )
        self._write(
            root,
            "internal/assembly_front_visibility_audit.json",
            {
                "status": "pass",
                "inventory": {"part_counts": {"window": 7}},
                "facade_schedule": {
                    "actual_counts": {
                        "front": {"lower": 3, "upper": 4}
                    }
                },
            },
        )
        return temporary, root

    def test_quantity_census_passes_when_totals_and_live_counts_match(self):
        temporary, root = self._project()
        self.addCleanup(temporary.cleanup)
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(root)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(
            (root / "internal" / "quantity_census_audit.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(report["status"], "pass")

    def test_quantity_census_rejects_facade_total_mismatch(self):
        temporary, root = self._project()
        self.addCleanup(temporary.cleanup)
        path = root / "internal" / "components.json"
        components = json.loads(path.read_text(encoding="utf-8"))
        components["quantity_audit"]["counts"]["main_windows"][
            "facade_breakdown"
        ]["front"]["total"] = 8
        path.write_text(
            json.dumps(components, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(root)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        report = json.loads(
            (root / "internal" / "quantity_census_audit.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(report["status"], "repair_required")
        self.assertTrue(
            any("total must equal" in error for error in report["errors"])
        )


if __name__ == "__main__":
    unittest.main()
