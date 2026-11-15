#!/usr/bin/env python3

from __future__ import annotations

import unittest

import generate_entrance_portal


class EntrancePortalGeneratorTests(unittest.TestCase):
    def parameters(self) -> dict:
        return {
            "rough_opening": {"width_m": 1.0, "height_m": 2.1},
            "stone_surround": {
                "border_m": 0.09,
                "depth_m": 0.26,
                "front_projection_m": 0.02,
                "threshold_height_m": 0.045,
                "threshold_depth_m": 0.32,
            },
            "door": {
                "width_m": 0.86,
                "height_m": 1.98,
                "arch_rise_m": 0.43,
                "bottom_m": 0.045,
                "thickness_m": 0.065,
                "leaf_count": 1,
                "panel_columns": 2,
                "panel_rows": 3,
                "panel_trim_width_m": 0.028,
                "panel_trim_depth_m": 0.018,
            },
            "hardware": {
                "hinge_count": 2,
                "hinge_width_m": 0.2,
                "hinge_height_m": 0.05,
                "handle_radius_m": 0.055,
                "handle_height_m": 1.02,
            },
        }

    def test_valid_portal_resolves_arch_and_panel_count(self) -> None:
        result = generate_entrance_portal.validate_parameters(
            self.parameters()
        )
        self.assertEqual(result["door"]["leaf_count"], 1)
        self.assertEqual(
            result["door"]["panel_columns"]
            * result["door"]["panel_rows"],
            6,
        )
        self.assertGreater(result["overall_height_m"], 2.1)

    def test_door_must_leave_side_reveal(self) -> None:
        parameters = self.parameters()
        parameters["door"]["width_m"] = 0.96
        with self.assertRaisesRegex(ValueError, "reveal"):
            generate_entrance_portal.validate_parameters(parameters)

    def test_door_must_leave_head_reveal(self) -> None:
        parameters = self.parameters()
        parameters["door"]["height_m"] = 2.08
        with self.assertRaisesRegex(ValueError, "head reveal"):
            generate_entrance_portal.validate_parameters(parameters)

    def test_arch_rise_must_be_smaller_than_half_width(self) -> None:
        parameters = self.parameters()
        parameters["door"]["arch_rise_m"] = 0.5
        with self.assertRaisesRegex(ValueError, "half width"):
            generate_entrance_portal.validate_parameters(parameters)

    def test_double_leaf_portal_is_supported(self) -> None:
        parameters = self.parameters()
        parameters["door"]["leaf_count"] = 2
        result = generate_entrance_portal.validate_parameters(parameters)
        self.assertEqual(result["door"]["leaf_count"], 2)


if __name__ == "__main__":
    unittest.main()
