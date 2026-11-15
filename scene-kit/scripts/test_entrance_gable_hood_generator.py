#!/usr/bin/env python3

from __future__ import annotations

import unittest

import generate_entrance_gable_hood


class EntranceGableHoodGeneratorTests(unittest.TestCase):
    def parameters(self) -> dict:
        return {
            "width_m": 1.65,
            "depth_m": 0.82,
            "platform_top_z_m": 0.51,
            "landing_depth_m": 0.32,
            "landing_thickness_m": 0.14,
            "landing_back_y_m": -3.5,
            "landing_board_count": 4,
            "wall_y_m": -3.55,
            "roof_width_m": 1.75,
            "roof_back_y_m": -3.58,
            "roof_front_y_m": -4.3,
            "eave_z_m": 2.86,
            "ridge_z_m": 3.0,
            "roof_thickness_m": 0.07,
            "ridge_width_m": 0.08,
            "ridge_height_m": 0.055,
            "fascia_width_m": 0.09,
            "fascia_height_m": 0.12,
            "bracket_width_m": 0.09,
            "bracket_thickness_m": 0.1,
            "bracket_wall_z_m": 2.53,
            "bracket_tip_y_m": -4.2,
            "columns": {
                "count": 2,
                "width_m": 0.1,
                "x_m": 0.68,
                "front_y_m": -3.76,
                "base_z_m": 0.51,
                "top_z_m": 2.72,
                "base_block_height_m": 0.08,
                "capital_height_m": 0.06,
            },
            "triangular_window": {
                "base_width_m": 0.52,
                "base_z_m": 2.88,
                "apex_z_m": 2.985,
                "pane_thickness_m": 0.006,
                "frame_width_m": 0.018,
                "glass_inset_m": 0.008,
            },
            "material": {
                "wood_mapping_scale": [0.5, 0.5, 0.5],
                "slate_mapping_scale": [0.333333, 0.333333, 0.333333],
                "physical_texture_dimensions_m": [2.0, 2.0],
            },
        }

    def test_resolves_compact_gable_hood(self) -> None:
        result = generate_entrance_gable_hood.validate_parameters(
            self.parameters()
        )
        self.assertAlmostEqual(result["landing_front_y_m"], -3.82)
        self.assertAlmostEqual(result["overall_dimensions_m"][0], 1.75)
        self.assertAlmostEqual(result["overall_dimensions_m"][1], 0.83)
        self.assertAlmostEqual(result["overall_dimensions_m"][2], 2.785)
        self.assertGreater(result["ridge_z_m"], result["eave_z_m"])

    def test_hood_cannot_cover_whole_stairs(self) -> None:
        parameters = self.parameters()
        parameters["width_m"] = 2.5
        with self.assertRaisesRegex(ValueError, "too wide"):
            generate_entrance_gable_hood.validate_parameters(parameters)

    def test_ridge_must_be_above_eave(self) -> None:
        parameters = self.parameters()
        parameters["ridge_z_m"] = 2.8
        with self.assertRaisesRegex(ValueError, "above eave"):
            generate_entrance_gable_hood.validate_parameters(parameters)

    def test_landing_must_meet_top_step(self) -> None:
        parameters = self.parameters()
        parameters["landing_depth_m"] = 0.5
        with self.assertRaisesRegex(ValueError, "top stair tread"):
            generate_entrance_gable_hood.validate_parameters(parameters)

    def test_columns_must_not_penetrate_roof(self) -> None:
        parameters = self.parameters()
        parameters["columns"]["top_z_m"] = 2.82
        with self.assertRaisesRegex(ValueError, "penetrate the hood roof"):
            generate_entrance_gable_hood.validate_parameters(parameters)

    def test_triangular_window_must_fit_gable_face(self) -> None:
        parameters = self.parameters()
        parameters["triangular_window"]["base_width_m"] = 1.7
        with self.assertRaisesRegex(ValueError, "too wide for the gable"):
            generate_entrance_gable_hood.validate_parameters(parameters)


if __name__ == "__main__":
    unittest.main()
