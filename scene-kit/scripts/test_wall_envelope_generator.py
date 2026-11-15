#!/usr/bin/env python3

from __future__ import annotations

import unittest

import generate_wall_envelope


class WallEnvelopeGeneratorTests(unittest.TestCase):
    def base_layout(self) -> dict:
        return {
            "basis": {
                "footprint_width_m": 9.0,
                "footprint_depth_m": 7.5,
                "wall_height_m": 6.0,
                "wall_thickness_m": 0.2,
            },
            "openings": [
                {
                    "id": "door",
                    "facade": "front",
                    "kind": "door",
                    "offset_m": 0.0,
                    "bottom_m": 0.0,
                    "width_m": 1.0,
                    "height_m": 2.1,
                },
                {
                    "id": "window_01",
                    "facade": "front",
                    "kind": "window",
                    "offset_m": -2.2,
                    "bottom_m": 0.9,
                    "width_m": 1.2,
                    "height_m": 1.5,
                },
            ],
            "constraints": {
                "minimum_edge_m": 0.1,
                "minimum_opening_gap_m": 0.2,
            },
        }

    def test_valid_layout_returns_facade_counts(self) -> None:
        result = generate_wall_envelope.validate_layout(
            self.base_layout()
        )
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["counts"]["front"], 2)
        self.assertEqual(result["counts"]["back"], 0)

    def test_disabled_opening_is_removed(self) -> None:
        layout = self.base_layout()
        layout["openings"][1]["enabled"] = False
        result = generate_wall_envelope.validate_layout(layout)
        self.assertEqual(result["counts"]["front"], 1)

    def test_overlapping_openings_are_rejected(self) -> None:
        layout = self.base_layout()
        layout["openings"].append(
            {
                "id": "window_overlap",
                "facade": "front",
                "kind": "window",
                "offset_m": -1.9,
                "bottom_m": 1.0,
                "width_m": 1.2,
                "height_m": 1.5,
            }
        )
        with self.assertRaisesRegex(ValueError, "too close or overlap"):
            generate_wall_envelope.validate_layout(layout)

    def test_facade_edge_margin_is_enforced(self) -> None:
        layout = self.base_layout()
        layout["openings"][1]["offset_m"] = -4.4
        with self.assertRaisesRegex(ValueError, "edge margin"):
            generate_wall_envelope.validate_layout(layout)

    def test_slot_pool_random_is_reproducible(self) -> None:
        layout = self.base_layout()
        layout["slot_pool"] = [
            {
                "id": f"slot_{index}",
                "facade": "back",
                "kind": "window",
                "offset_m": -3.0 + index * 1.2,
                "bottom_m": 0.9,
                "width_m": 0.8,
                "height_m": 1.2,
            }
            for index in range(6)
        ]
        layout["random"] = {"seed": 42, "keep_probability": 0.5}
        first = generate_wall_envelope.validate_layout(layout)
        second = generate_wall_envelope.validate_layout(layout)
        self.assertEqual(first["openings"], second["openings"])
        self.assertEqual(first["seed"], 42)


if __name__ == "__main__":
    unittest.main()
