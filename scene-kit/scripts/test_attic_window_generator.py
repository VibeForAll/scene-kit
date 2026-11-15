#!/usr/bin/env python3

from __future__ import annotations

import unittest

import generate_attic_window


class AtticWindowGeneratorTests(unittest.TestCase):
    def parameters(self) -> dict:
        return {
            "component_width_m": 1.6,
            "component_height_m": 1.2,
            "window_count": 2,
            "opening_width_m": 0.60,
            "opening_height_m": 0.86,
            "gap_m": 0.16,
            "stone_border_m": 0.06,
            "stone_depth_m": 0.18,
            "sill_projection_m": 0.08,
            "sill_thickness_m": 0.06,
            "frame_thickness_m": 0.045,
            "frame_depth_m": 0.13,
            "bar_width_m": 0.02,
            "glass_depth_m": 0.02,
            "rows": 2,
            "columns_per_window": 2,
            "hood": {
                "width_m": 1.5,
                "depth_m": 0.20,
                "eave_z_m": 1.01,
                "ridge_z_m": 1.12,
                "thickness_m": 0.04,
                "ridge_width_m": 0.05,
                "ridge_height_m": 0.03,
            },
        }

    def test_pair_resolves_to_eight_panes(self) -> None:
        result = generate_attic_window.validate_parameters(self.parameters())
        self.assertEqual(result["columns"], 4)
        self.assertEqual(result["rows"], 2)
        self.assertEqual(result["pane_count"], 8)

    def test_pair_width_must_match_contract(self) -> None:
        parameters = self.parameters()
        parameters["gap_m"] = 0.30
        with self.assertRaisesRegex(ValueError, "pair width"):
            generate_attic_window.validate_parameters(parameters)

    def test_hood_must_clear_window_surround(self) -> None:
        parameters = self.parameters()
        parameters["hood"]["eave_z_m"] = 0.95
        with self.assertRaisesRegex(ValueError, "above both window surrounds"):
            generate_attic_window.validate_parameters(parameters)

    def test_hood_must_fit_locked_height(self) -> None:
        parameters = self.parameters()
        parameters["hood"]["ridge_z_m"] = 1.30
        with self.assertRaisesRegex(ValueError, "locked component height"):
            generate_attic_window.validate_parameters(parameters)

    def test_hood_must_bear_on_stone_lintel(self) -> None:
        parameters = self.parameters()
        parameters["hood"]["eave_z_m"] = 1.08
        with self.assertRaisesRegex(ValueError, "bear on the stone lintel"):
            generate_attic_window.validate_parameters(parameters)

    def test_each_window_requires_two_by_two_panes(self) -> None:
        parameters = self.parameters()
        parameters["rows"] = 1
        with self.assertRaisesRegex(ValueError, "2x2 panes"):
            generate_attic_window.validate_parameters(parameters)


if __name__ == "__main__":
    unittest.main()
