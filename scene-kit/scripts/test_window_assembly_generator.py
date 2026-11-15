#!/usr/bin/env python3

from __future__ import annotations

import unittest

import generate_window_assembly


class WindowAssemblyGeneratorTests(unittest.TestCase):
    def parameters(self) -> dict:
        return {
            "opening_width_m": 1.2,
            "opening_height_m": 1.5,
            "installation_clearance_m": 0.015,
            "stone_border_m": 0.06,
            "stone_depth_m": 0.24,
            "sill_projection_m": 0.08,
            "sill_thickness_m": 0.06,
            "frame_thickness_m": 0.055,
            "frame_depth_m": 0.165,
            "bar_width_m": 0.024,
            "glass_depth_m": 0.025,
            "rows": 4,
            "major_vertical_sections": 3,
            "central_split": {"enabled": True, "sub_columns": 2},
            "column_ratios": [1.3, 0.8, 0.8, 1.3],
        }

    def test_default_pattern_is_four_by_four(self) -> None:
        result = generate_window_assembly.validate_parameters(
            self.parameters()
        )
        self.assertEqual(result["columns"], 4)
        self.assertEqual(result["rows"], 4)
        self.assertEqual(result["pane_count"], 16)
        self.assertGreater(result["overall_width_m"], 1.2)

    def test_central_split_off_resolves_three_columns(self) -> None:
        parameters = self.parameters()
        parameters["central_split"] = {
            "enabled": False,
            "sub_columns": 2,
        }
        parameters["column_ratios"] = [1.0, 1.0, 1.0]
        result = generate_window_assembly.validate_parameters(parameters)
        self.assertEqual(result["columns"], 3)
        self.assertEqual(result["pane_count"], 12)

    def test_resized_width_updates_column_widths(self) -> None:
        narrow = self.parameters()
        wide = self.parameters()
        wide["opening_width_m"] = 1.6
        narrow_result = generate_window_assembly.validate_parameters(narrow)
        wide_result = generate_window_assembly.validate_parameters(wide)
        self.assertGreater(
            wide_result["frame_inner_width_m"],
            narrow_result["frame_inner_width_m"],
        )
        self.assertGreater(
            sum(wide_result["column_widths_m"]),
            sum(narrow_result["column_widths_m"]),
        )

    def test_column_ratio_count_must_match_columns(self) -> None:
        parameters = self.parameters()
        parameters["column_ratios"] = [1.0, 1.0, 1.0]
        with self.assertRaisesRegex(ValueError, "column_ratios"):
            generate_window_assembly.validate_parameters(parameters)

    def test_excessive_frame_thickness_is_rejected(self) -> None:
        parameters = self.parameters()
        parameters["frame_thickness_m"] = 0.6
        with self.assertRaisesRegex(ValueError, "frame thickness"):
            generate_window_assembly.validate_parameters(parameters)


if __name__ == "__main__":
    unittest.main()
