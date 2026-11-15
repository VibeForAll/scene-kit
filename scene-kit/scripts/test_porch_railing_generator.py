#!/usr/bin/env python3

from __future__ import annotations

import unittest

import generate_porch_railing


class PorchRailingGeneratorTests(unittest.TestCase):
    def parameters(self) -> dict:
        return {
            "total_width_m": 3.6,
            "center_opening_m": 1.8,
            "height_m": 0.95,
            "platform_top_z_m": 0.51,
            "front_y_m": -3.76,
            "outer_inset_m": 0.04,
            "post_width_m": 0.09,
            "post_cap_height_m": 0.04,
            "top_rail_height_m": 0.09,
            "top_rail_depth_m": 0.08,
            "bottom_rail_height_m": 0.06,
            "bottom_rail_depth_m": 0.06,
            "bottom_rail_z_m": 0.2,
            "baluster_width_m": 0.035,
            "baluster_spacing_m": 0.14,
            "material": {
                "wood_mapping_scale": [0.5, 0.5, 0.5],
                "physical_texture_dimensions_m": [2.0, 2.0],
            },
        }

    def test_resolves_two_side_bays(self) -> None:
        result = generate_porch_railing.validate_parameters(
            self.parameters()
        )
        self.assertAlmostEqual(result["center_opening_m"], 1.8)
        self.assertAlmostEqual(result["bay_length_m"], 0.86)
        self.assertAlmostEqual(result["overall_dimensions_m"][0], 3.6415)
        self.assertAlmostEqual(result["overall_dimensions_m"][1], 0.144)
        self.assertAlmostEqual(result["overall_dimensions_m"][2], 0.99)

    def test_opening_cannot_consume_all_width(self) -> None:
        parameters = self.parameters()
        parameters["center_opening_m"] = 3.55
        with self.assertRaisesRegex(ValueError, "side railing bay"):
            generate_porch_railing.validate_parameters(parameters)

    def test_bottom_rail_must_fit(self) -> None:
        parameters = self.parameters()
        parameters["bottom_rail_z_m"] = 0.94
        with self.assertRaisesRegex(ValueError, "bottom rail"):
            generate_porch_railing.validate_parameters(parameters)

    def test_baluster_spacing_must_leave_openings(self) -> None:
        parameters = self.parameters()
        parameters["baluster_spacing_m"] = 0.052
        with self.assertRaisesRegex(ValueError, "too tight"):
            generate_porch_railing.validate_parameters(parameters)


if __name__ == "__main__":
    unittest.main()
