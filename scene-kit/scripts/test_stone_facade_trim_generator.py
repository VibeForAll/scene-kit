#!/usr/bin/env python3

from __future__ import annotations

import unittest

import generate_stone_facade_trim


class StoneFacadeTrimGeneratorTests(unittest.TestCase):
    def parameters(self) -> dict:
        return {
            "footprint_width_m": 9.0,
            "footprint_depth_m": 7.5,
            "embed_depth_m": 0.04,
            "projection_m": 0.06,
            "cap_projection_m": 0.02,
            "cap_height_m": 0.024,
            "bands": [
                {"id": "upper_floor_belt", "z_m": 3.0, "height_m": 0.14},
                {"id": "eave_belt", "z_m": 5.72, "height_m": 0.12},
            ],
            "opening_clearance": {
                "lower_window_top_m": 2.4,
                "upper_window_bottom_m": 3.9,
                "upper_window_top_m": 5.4,
                "wall_top_m": 6.0,
                "minimum_gap_m": 0.05,
            },
            "material": {
                "stone_mapping_scale": [0.5, 0.5, 0.5],
                "physical_texture_dimensions_m": [2.0, 2.0],
            },
        }

    def test_resolves_two_belt_courses(self) -> None:
        result = generate_stone_facade_trim.validate_parameters(
            self.parameters()
        )
        self.assertEqual(result["band_count"], 2)
        self.assertEqual(result["trim_segment_count"], 8)
        self.assertAlmostEqual(result["overall_dimensions_m"][0], 9.16)
        self.assertAlmostEqual(result["overall_dimensions_m"][1], 7.66)
        self.assertAlmostEqual(result["overall_dimensions_m"][2], 2.85)

    def test_band_cannot_cross_lower_window(self) -> None:
        parameters = self.parameters()
        parameters["bands"][0]["z_m"] = 2.35
        with self.assertRaisesRegex(ValueError, "window opening"):
            generate_stone_facade_trim.validate_parameters(parameters)

    def test_band_cannot_cross_upper_window(self) -> None:
        parameters = self.parameters()
        parameters["bands"][1]["z_m"] = 5.35
        with self.assertRaisesRegex(ValueError, "window opening"):
            generate_stone_facade_trim.validate_parameters(parameters)

    def test_band_cannot_touch_wall_top(self) -> None:
        parameters = self.parameters()
        parameters["bands"][1]["z_m"] = 5.99
        with self.assertRaisesRegex(ValueError, "wall top"):
            generate_stone_facade_trim.validate_parameters(parameters)


if __name__ == "__main__":
    unittest.main()
