#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("attachment_integrity_audit.py")


class AttachmentIntegrityAuditTests(unittest.TestCase):
    def _write(self, root, relative, value):
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
        for relative in (
            "raw/front.png",
            "raw/side.png",
            "evidence/contact.json",
        ):
            self._write(root, relative, relative)
        audit = {
            "status": "pass",
            "source_views": ["raw/front.png", "raw/side.png"],
            "items": [
                {
                    "attachment_id": "dormer_body",
                    "part_id": "dormer",
                    "attachment_type": "enclosed_dormer_body",
                    "host_part_ids": ["main_roof", "dormer"],
                    "has_volume": True,
                    "has_back_enclosure": True,
                    "has_side_enclosure": True,
                    "front_plane_only": False,
                    "host_contact_verified": True,
                    "body_projection_beyond_host_m": 0.41,
                    "front_eave_setback_m": 0.04,
                    "roof_covers_body_rear": True,
                    "host_contact_evidence": ["evidence/contact.json"],
                    "evidence_views": ["raw/front.png", "raw/side.png"],
                    "status": "pass",
                }
            ],
            "checks": {
                "attachments_inventoried": True,
                "front_plane_only_rejected": True,
                "host_contacts_verified": True,
            },
            "unresolved": [],
        }
        self._write(
            root,
            "internal/components.json",
            {
                "parts": [
                    {"part_id": "dormer"},
                    {"part_id": "main_roof"},
                ],
                "attachment_integrity_audit": audit,
                "decomposition_review": {
                    "checks": {"attachment_integrity_verified": True}
                },
            },
        )
        return temporary, root

    def test_host_connected_attachment_passes(self):
        temporary, root = self._project()
        self.addCleanup(temporary.cleanup)
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(root)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_front_plane_only_attachment_fails(self):
        temporary, root = self._project()
        self.addCleanup(temporary.cleanup)
        path = root / "internal" / "components.json"
        components = json.loads(path.read_text(encoding="utf-8"))
        item = components["attachment_integrity_audit"]["items"][0]
        item["front_plane_only"] = True
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

    def test_coplanar_attachment_fails_projection_gate(self):
        temporary, root = self._project()
        self.addCleanup(temporary.cleanup)
        path = root / "internal" / "components.json"
        components = json.loads(path.read_text(encoding="utf-8"))
        item = components["attachment_integrity_audit"]["items"][0]
        item["body_projection_beyond_host_m"] = 0.02
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

    def test_roof_beyond_host_eave_fails(self):
        temporary, root = self._project()
        self.addCleanup(temporary.cleanup)
        path = root / "internal" / "components.json"
        components = json.loads(path.read_text(encoding="utf-8"))
        item = components["attachment_integrity_audit"]["items"][0]
        item["front_eave_setback_m"] = -0.05
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


if __name__ == "__main__":
    unittest.main()
