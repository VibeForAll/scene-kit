#!/usr/bin/env python3

from __future__ import annotations

import unittest

import generate_timber_porch


class TimberPorchGeneratorTests(unittest.TestCase):
    def parameters(self) -> dict:
        return {
            "width_m": 3.6,
            "landing_depth_m": 0.44,
            "landing_thickness_m": 0.14,
            "landing_top_z_m": 0.51,
            "landing_back_y_m": -3.38,
            "landing_board_count": 8,
            "post_width_m": 0.16,
            "post_x_m": 1.64,
            "post_front_y_m": -4.7,
            "post_top_z_m": 2.72,
            "post_base_height_m": 0.18,
            "post_base_width_m": 0.26,
            "beam_width_m": 0.18,
            "beam_height_m": 0.16,
            "roof_width_m": 4.0,
            "roof_back_y_m": -3.58,
            "roof_front_y_m": -4.98,
            "roof_back_z_m": 3.22,
            "roof_front_z_m": 2.96,
            "roof_thickness_m": 0.09,
            "rafter_count": 5,
            "rafter_width_m": 0.08,
            "rafter_depth_m": 0.1,
            "material": {
                "wood_mapping_scale": [0.5, 0.5, 0.5],
                "slate_mapping_scale": [0.333333, 0.333333, 0.333333],
                "stone_mapping_scale": [0.5, 0.5, 0.5],
            },
        }

    def test_resolves_landing_and_sloped_canopy(self) -> None:
        result = generate_timber_porch.validate_parameters(
            self.parameters()
        )
        self.assertAlmostEqual(result["landing_front_y_m"], -3.82)
        self.assertEqual(result["landing_board_count"], 8)
        self.assertEqual(result["rafter_count"], 5)
        self.assertGreater(
            result["roof_back_z_m"],
            result["roof_front_z_m"],
        )
        self.assertAlmostEqual(result["overall_dimensions_m"][0], 4.0)
        self.assertAlmostEqual(result["overall_dimensions_m"][1], 1.6)
        self.assertAlmostEqual(result["overall_dimensions_m"][2], 3.265)

    def test_posts_must_clear_stair_width(self) -> None:
        parameters = self.parameters()
        parameters["post_x_m"] = 0.95
        with self.assertRaisesRegex(ValueError, "stair clear width"):
            generate_timber_porch.validate_parameters(parameters)

    def test_roof_must_slope_downward(self) -> None:
        parameters = self.parameters()
        parameters["roof_front_z_m"] = 3.3
        with self.assertRaisesRegex(ValueError, "below"):
            generate_timber_porch.validate_parameters(parameters)

    def test_post_head_must_not_penetrate_roof(self) -> None:
        parameters = self.parameters()
        parameters["post_top_z_m"] = 3.0
        with self.assertRaisesRegex(ValueError, "penetrate"):
            generate_timber_porch.validate_parameters(parameters)


if __name__ == "__main__":
    unittest.main()
