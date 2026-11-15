#!/usr/bin/env python3

from __future__ import annotations

import unittest

import generate_wall_lantern


class WallLanternGeneratorTests(unittest.TestCase):
    def parameters(self) -> dict:
        return {
            "width_m": 0.24,
            "body_height_m": 0.38,
            "depth_m": 0.18,
            "frame_bar_m": 0.016,
            "glass_inset_m": 0.006,
            "backplate_width_m": 0.16,
            "backplate_height_m": 0.22,
            "backplate_depth_m": 0.025,
            "bracket_projection_m": 0.08,
            "bracket_width_m": 0.048,
            "bracket_height_m": 0.034,
            "cap_projection_m": 0.035,
            "cap_height_m": 0.075,
            "cap_base_gap_m": 0.012,
            "finial_radius_m": 0.018,
            "wall_face_y_m": -3.75,
            "placements": [
                {"id": "left", "x_m": -0.76, "center_z_m": 2.12},
                {"id": "right", "x_m": 0.76, "center_z_m": 2.12},
            ],
        }

    def test_resolves_two_wall_lanterns(self) -> None:
        result = generate_wall_lantern.validate_parameters(self.parameters())
        self.assertEqual(len(result["placements"]), 2)
        self.assertAlmostEqual(result["overall_dimensions_m"][0], 0.31)
        self.assertAlmostEqual(result["overall_dimensions_m"][1], 0.32)
        self.assertAlmostEqual(result["overall_dimensions_m"][2], 0.503)
        self.assertGreater(result["body_center_y_m"], result["body_front_y_m"])

    def test_duplicate_placement_ids_are_rejected(self) -> None:
        parameters = self.parameters()
        parameters["placements"][1]["id"] = "left"
        with self.assertRaisesRegex(ValueError, "duplicate placement"):
            generate_wall_lantern.validate_parameters(parameters)

    def test_excessive_frame_is_rejected(self) -> None:
        parameters = self.parameters()
        parameters["frame_bar_m"] = 0.08
        with self.assertRaisesRegex(ValueError, "frame_bar_m"):
            generate_wall_lantern.validate_parameters(parameters)

    def test_cap_projection_is_limited(self) -> None:
        parameters = self.parameters()
        parameters["cap_projection_m"] = 0.25
        with self.assertRaisesRegex(ValueError, "cap projection"):
            generate_wall_lantern.validate_parameters(parameters)


if __name__ == "__main__":
    unittest.main()
