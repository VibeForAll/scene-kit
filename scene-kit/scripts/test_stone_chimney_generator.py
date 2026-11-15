#!/usr/bin/env python3

from __future__ import annotations

import unittest

import generate_stone_chimney


class StoneChimneyGeneratorTests(unittest.TestCase):
    def parameters(self) -> dict:
        return {
            "roof": {
                "eave_height_m": 6.0,
                "ridge_height_m": 8.8,
                "eave_depth_m": 7.9,
                "eave_width_m": 9.4,
            },
            "shaft": {
                "base_width_m": 0.82,
                "base_depth_m": 0.82,
                "top_width_m": 0.68,
                "top_depth_m": 0.68,
                "height_above_roof_m": 1.75,
                "embed_depth_m": 0.25,
            },
            "collar": {"overhang_m": 0.08, "height_m": 0.22},
            "cap": {"overhang_m": 0.12, "height_m": 0.14},
            "flues": {
                "count": 2,
                "radius_m": 0.09,
                "height_m": 0.26,
                "spacing_m": 0.22,
            },
            "moss": {"band_height_m": 0.08, "projection_m": 0.006},
            "placements": [
                {"id": "left", "x_m": -2.3, "y_m": -1.0},
                {"id": "right", "x_m": 2.3, "y_m": 1.0},
            ],
        }

    def test_two_chimneys_resolve_roof_surfaces(self) -> None:
        result = generate_stone_chimney.validate_parameters(
            self.parameters()
        )
        self.assertEqual(result["instance_count"], 2)
        self.assertEqual(len(result["placements"]), 2)
        self.assertGreater(
            result["placements"][0]["roof_surface_z_m"], 6.0
        )
        self.assertGreater(
            result["overall_chimney_dimensions_m"][2], 2.0
        )

    def test_duplicate_placement_ids_are_rejected(self) -> None:
        parameters = self.parameters()
        parameters["placements"][1]["id"] = "left"
        with self.assertRaisesRegex(ValueError, "duplicate"):
            generate_stone_chimney.validate_parameters(parameters)

    def test_placement_outside_roof_is_rejected(self) -> None:
        parameters = self.parameters()
        parameters["placements"][0]["x_m"] = 4.8
        with self.assertRaisesRegex(ValueError, "eave width"):
            generate_stone_chimney.validate_parameters(parameters)

    def test_shaft_cannot_widen_upward(self) -> None:
        parameters = self.parameters()
        parameters["shaft"]["top_width_m"] = 0.9
        with self.assertRaisesRegex(ValueError, "widen"):
            generate_stone_chimney.validate_parameters(parameters)

    def test_flues_can_be_disabled(self) -> None:
        parameters = self.parameters()
        parameters["flues"]["count"] = 0
        result = generate_stone_chimney.validate_parameters(parameters)
        self.assertEqual(result["flues"]["count"], 0)


if __name__ == "__main__":
    unittest.main()
