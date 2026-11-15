#!/usr/bin/env python3

from __future__ import annotations

import unittest

import generate_corner_quoins


class CornerQuoinGeneratorTests(unittest.TestCase):
    def parameters(self) -> dict:
        return {
            "footprint_width_m": 9.0,
            "footprint_depth_m": 7.5,
            "bottom_z_m": 0.51,
            "top_z_m": 5.7,
            "block_height_m": 0.27,
            "long_length_m": 0.35,
            "short_length_m": 0.22,
            "projection_m": 0.06,
            "embed_depth_m": 0.04,
            "material": {
                "stone_mapping_scale": [0.5, 0.5, 0.5],
                "physical_texture_dimensions_m": [2.0, 2.0],
            },
        }

    def test_resolves_four_corners_and_rows(self) -> None:
        result = generate_corner_quoins.validate_parameters(
            self.parameters()
        )
        self.assertEqual(result["corner_count"], 4)
        self.assertEqual(result["row_count"], 19)
        self.assertEqual(result["block_count"], 76)
        self.assertAlmostEqual(result["overall_dimensions_m"][0], 9.12)
        self.assertAlmostEqual(result["overall_dimensions_m"][1], 7.62)
        self.assertAlmostEqual(result["overall_dimensions_m"][2], 5.1192)

    def test_long_block_must_exceed_short_block(self) -> None:
        parameters = self.parameters()
        parameters["long_length_m"] = 0.2
        with self.assertRaisesRegex(ValueError, "exceed"):
            generate_corner_quoins.validate_parameters(parameters)

    def test_blocks_must_fit_facade(self) -> None:
        parameters = self.parameters()
        parameters["long_length_m"] = 2.5
        with self.assertRaisesRegex(ValueError, "too long"):
            generate_corner_quoins.validate_parameters(parameters)

    def test_vertical_range_must_allow_rows(self) -> None:
        parameters = self.parameters()
        parameters["top_z_m"] = 0.78
        with self.assertRaisesRegex(ValueError, "vertical range"):
            generate_corner_quoins.validate_parameters(parameters)


if __name__ == "__main__":
    unittest.main()
