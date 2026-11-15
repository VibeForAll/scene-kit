#!/usr/bin/env python3

from __future__ import annotations

import unittest

import generate_entrance_steps


class EntranceStepsGeneratorTests(unittest.TestCase):
    def parameters(self) -> dict:
        return {
            "width_m": 1.8,
            "step_count": 3,
            "riser_height_m": 0.17,
            "tread_depth_m": 0.36,
            "landing_depth_m": 0.32,
            "back_y_m": -3.82,
            "nosing_projection_m": 0.04,
            "nosing_height_m": 0.018,
            "material": {
                "stone_mapping_scale": [0.5, 0.5, 0.5]
            },
        }

    def test_three_steps_resolve_platform_and_depth(self) -> None:
        result = generate_entrance_steps.validate_parameters(
            self.parameters()
        )
        self.assertEqual(result["step_count"], 3)
        self.assertAlmostEqual(result["platform_height_m"], 0.51)
        self.assertAlmostEqual(result["total_depth_m"], 1.04)
        self.assertAlmostEqual(result["front_y_m"], -4.86)
        self.assertAlmostEqual(
            result["riser_face_front_y_m"],
            -4.82,
        )

    def test_nosing_is_included_in_contract_depth(self) -> None:
        result = generate_entrance_steps.validate_parameters(
            self.parameters()
        )
        first_step = result["steps"][0]
        self.assertAlmostEqual(
            first_step["nosing_tip_front_y_m"],
            result["front_y_m"],
        )
        self.assertAlmostEqual(
            first_step["riser_face_front_y_m"]
            - first_step["nosing_tip_front_y_m"],
            result["nosing_projection_m"],
        )
        geometry_depth = (
            result["back_y_m"]
            - result["riser_face_front_y_m"]
        )
        self.assertGreater(geometry_depth, 0.0)
        self.assertLessEqual(
            geometry_depth,
            result["total_depth_m"],
        )

    def test_riser_height_is_limited(self) -> None:
        parameters = self.parameters()
        parameters["riser_height_m"] = 0.25
        with self.assertRaisesRegex(ValueError, "comfortable"):
            generate_entrance_steps.validate_parameters(parameters)

    def test_tread_depth_is_limited(self) -> None:
        parameters = self.parameters()
        parameters["tread_depth_m"] = 0.2
        with self.assertRaisesRegex(ValueError, "too shallow"):
            generate_entrance_steps.validate_parameters(parameters)

    def test_mapping_scale_must_be_positive(self) -> None:
        parameters = self.parameters()
        parameters["material"]["stone_mapping_scale"] = [0.5, 0.0, 0.5]
        with self.assertRaisesRegex(ValueError, "mapping_scale"):
            generate_entrance_steps.validate_parameters(parameters)


if __name__ == "__main__":
    unittest.main()
