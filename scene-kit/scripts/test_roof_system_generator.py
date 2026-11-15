#!/usr/bin/env python3

from __future__ import annotations

import unittest

import generate_roof_system


class RoofSystemGeneratorTests(unittest.TestCase):
    def parameters(self) -> dict:
        return {
            "eave_width_m": 9.4,
            "eave_depth_m": 7.9,
            "eave_height_m": 6.0,
            "ridge_height_m": 8.8,
            "roof_thickness_m": 0.18,
            "gable_wall_width_m": 9.0,
            "gable_wall_depth_m": 7.5,
            "gable_wall_thickness_m": 0.2,
            "ridge_cap_radius_m": 0.1,
            "fascia_height_m": 0.18,
            "fascia_depth_m": 0.08,
            "gutter_width_m": 0.12,
            "gutter_height_m": 0.12,
            "gutter_projection_m": 0.06,
            "material": {
                "roof_slug": "roof_slates_03",
                "mapping_scale": [0.333333, 0.333333, 0.333333],
            },
        }

    def test_valid_roof_resolves_pitch_and_slope(self) -> None:
        result = generate_roof_system.validate_parameters(
            self.parameters()
        )
        self.assertEqual(result["status"], "pass")
        self.assertGreater(result["pitch_deg"], 0)
        self.assertGreater(result["slope_length_m"], 3.95)
        self.assertEqual(len(result["overall_dimensions_m"]), 3)

    def test_ridge_must_be_above_eave(self) -> None:
        parameters = self.parameters()
        parameters["ridge_height_m"] = 5.5
        with self.assertRaisesRegex(ValueError, "above eave"):
            generate_roof_system.validate_parameters(parameters)

    def test_gable_must_fit_under_roof(self) -> None:
        parameters = self.parameters()
        parameters["gable_wall_width_m"] = 10.0
        with self.assertRaisesRegex(ValueError, "roof overhang"):
            generate_roof_system.validate_parameters(parameters)

    def test_mapping_scale_must_be_positive_vector(self) -> None:
        parameters = self.parameters()
        parameters["material"]["mapping_scale"] = [0.3, 0.0, 0.3]
        with self.assertRaisesRegex(ValueError, "mapping_scale"):
            generate_roof_system.validate_parameters(parameters)

    def test_cross_gable_is_explicitly_deferred(self) -> None:
        parameters = self.parameters()
        parameters["cross_gable"] = {"enabled": True}
        with self.assertRaisesRegex(ValueError, "not implemented"):
            generate_roof_system.validate_parameters(parameters)


if __name__ == "__main__":
    unittest.main()
