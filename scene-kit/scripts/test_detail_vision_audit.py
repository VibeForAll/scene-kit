#!/usr/bin/env python3
"""Deterministic tests for the optional detail vision audit helpers."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import detail_vision_audit
from PIL import Image, ImageDraw


class DetailVisionAuditTests(unittest.TestCase):
    def test_clamp_box_adds_margin_and_clamps(self) -> None:
        self.assertEqual(
            detail_vision_audit.clamp_box([-20, 10, 30, 50], 100, 100, 0.2),
            (0, 0, 40, 60),
        )
        self.assertEqual(
            detail_vision_audit.clamp_box([90, 80, 130, 120], 100, 100, 0.2),
            (82, 72, 100, 100),
        )

    def test_summarize_grounding_reports_per_view_and_aggregate(self) -> None:
        empty = {"parsed": {"<CAPTION_TO_PHRASE_GROUNDING>": {"labels": []}}}
        results = {view_id: empty for view_id in detail_vision_audit.CONCEPT_VIEW_IDS}
        results["front"] = {
            "parsed": {
                "<CAPTION_TO_PHRASE_GROUNDING>": {
                    "labels": ["chimney", "chimney", "door", "window"]
                }
            }
        }
        results["top"] = {
            "parsed": {
                "<CAPTION_TO_PHRASE_GROUNDING>": {
                    "labels": ["chimney", "chimney", "window", "window"]
                }
            }
        }
        summary = detail_vision_audit.summarize_grounding(results)
        self.assertEqual(summary["per_view"]["front"]["chimney"], 2)
        self.assertEqual(summary["aggregate"]["chimney"]["max"], 2)
        self.assertEqual(summary["aggregate"]["chimney"]["views_seen"], 2)
        self.assertEqual(summary["aggregate"]["window"]["max"], 2)

    def test_representative_detection_prefers_front(self) -> None:
        results = {
            view_id: {
                "parsed": {"<CAPTION_TO_PHRASE_GROUNDING>": {"labels": [], "bboxes": []}}
            }
            for view_id in detail_vision_audit.CONCEPT_VIEW_IDS
        }
        results["left"]["parsed"]["<CAPTION_TO_PHRASE_GROUNDING>"] = {
            "labels": ["chimney"],
            "bboxes": [[1, 1, 2, 2]],
        }
        results["front"]["parsed"]["<CAPTION_TO_PHRASE_GROUNDING>"] = {
            "labels": ["chimney"],
            "bboxes": [[3, 3, 4, 4]],
        }
        chosen = detail_vision_audit.representative_detections(results)
        self.assertEqual(chosen["chimney"]["view_id"], "front")
        self.assertEqual(chosen["chimney"]["box"], [3, 3, 4, 4])

    def test_resolve_selected_views_requires_all_ten_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            internal = project / "internal"
            internal.mkdir()
            view_paths = {}
            for view_id in detail_vision_audit.CONCEPT_VIEW_IDS:
                relative = f"concepts/D01/views/{view_id}.png"
                path = project / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"placeholder")
                view_paths[view_id] = relative
            concepts = {
                "selected_direction": "D01",
                "directions": [
                    {
                        "direction_id": "D01",
                        "view_paths": view_paths,
                    }
                ],
            }
            (internal / "concept_directions.json").write_text(
                json.dumps(concepts),
                encoding="utf-8",
            )
            selected, views = detail_vision_audit.resolve_selected_views(project)
            self.assertEqual(selected, "D01")
            self.assertEqual(len(views), 10)
            del concepts["directions"][0]["view_paths"]["back"]
            (internal / "concept_directions.json").write_text(
                json.dumps(concepts),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "图片不完整"):
                detail_vision_audit.resolve_selected_views(project)

    def test_resolve_view_dir_uses_model_derived_ten_views(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            view_dir = project / "preview/reference-models/derived-views"
            view_dir.mkdir(parents=True)
            for view_id in detail_vision_audit.CONCEPT_VIEW_IDS:
                (view_dir / f"{view_id}.png").write_bytes(b"placeholder")
            selected, views = detail_vision_audit.resolve_view_source(
                project,
                view_dir,
                None,
            )
            self.assertEqual(selected, "model_derived_views")
            self.assertEqual(set(views), set(detail_vision_audit.CONCEPT_VIEW_IDS))

    def test_fine_structure_probe_reports_internal_grid_lines(self) -> None:
        image = Image.new("RGB", (120, 160), (150, 150, 150))
        draw = ImageDraw.Draw(image)
        for x in (30, 60, 90):
            draw.line((x, 15, x, 145), fill=(20, 20, 20), width=2)
        for y in (40, 80, 120):
            draw.line((15, y, 105, y), fill=(20, 20, 20), width=2)
        result = detail_vision_audit.analyze_fine_structure(image)
        self.assertEqual(result["status"], "diagnostic_only")
        self.assertGreaterEqual(len(result["vertical_line_ratios"]), 3)
        self.assertGreaterEqual(len(result["horizontal_line_ratios"]), 3)
        self.assertTrue(
            any(0.45 <= value <= 0.55 for value in result["vertical_line_ratios"])
        )

    def test_grouped_detections_keep_multiple_views_for_same_label(self) -> None:
        empty = {"parsed": {"<CAPTION_TO_PHRASE_GROUNDING>": {"labels": [], "bboxes": []}}}
        results = {view_id: empty for view_id in detail_vision_audit.CONCEPT_VIEW_IDS}
        results["front"] = {
            "parsed": {
                "<CAPTION_TO_PHRASE_GROUNDING>": {
                    "labels": ["window"],
                    "bboxes": [[1, 2, 3, 4]],
                }
            }
        }
        results["right"] = {
            "parsed": {
                "<CAPTION_TO_PHRASE_GROUNDING>": {
                    "labels": ["window"],
                    "bboxes": [[5, 6, 7, 8]],
                }
            }
        }
        grouped = detail_vision_audit.grouped_detections(results)
        self.assertEqual(
            [item["view_id"] for item in grouped["window"]],
            ["right", "front"],
        )

    def test_dominant_palette_returns_rgb_and_ratios(self) -> None:
        image = Image.new("RGB", (20, 20), (72, 48, 30))
        palette = detail_vision_audit.dominant_palette(image, colors=4)
        self.assertTrue(palette)
        self.assertEqual(len(palette[0]["rgb"]), 3)
        self.assertAlmostEqual(palette[0]["sample_ratio"], 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
