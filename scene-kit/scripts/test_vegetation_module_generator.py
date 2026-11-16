#!/usr/bin/env python3

from __future__ import annotations

import unittest

import generate_vegetation_module


class VegetationModuleGeneratorTests(unittest.TestCase):
    def vine_parameters(self) -> dict:
        return {
            "component_type": "climbing_vine",
            "width_m": 0.9,
            "depth_m": 0.18,
            "height_m": 1.2,
            "seed": 19,
            "stem_count": 5,
            "leaf_count": 72,
            "leaf_width_m": 0.055,
            "leaf_height_m": 0.09,
            "leaf_thickness_m": 0.006,
            "stem_radius_m": 0.008,
        }

    def planter_parameters(self) -> dict:
        return {
            "component_type": "potted_plant",
            "width_m": 0.3,
            "depth_m": 0.3,
            "height_m": 0.55,
            "seed": 7,
            "stem_count": 7,
            "leaf_count": 34,
            "leaf_width_m": 0.035,
            "leaf_height_m": 0.065,
            "leaf_thickness_m": 0.005,
            "stem_radius_m": 0.005,
            "pot": {
                "height_m": 0.2,
                "rim_height_m": 0.025,
                "top_radius_m": 0.14,
                "bottom_radius_m": 0.1,
            },
        }

    def test_vine_contract_resolves(self) -> None:
        result = generate_vegetation_module.validate_parameters(
            self.vine_parameters()
        )
        self.assertEqual(result["component_type"], "climbing_vine")
        self.assertEqual(result["seed"], 19)

    def test_planter_pot_is_tapered_and_fits(self) -> None:
        result = generate_vegetation_module.validate_parameters(
            self.planter_parameters()
        )
        self.assertGreater(result["pot"]["top_radius_m"], result["pot"]["bottom_radius_m"])

    def test_leaf_must_fit_inside_component(self) -> None:
        parameters = self.vine_parameters()
        parameters["leaf_width_m"] = 1.0
        with self.assertRaisesRegex(ValueError, "leaf dimensions"):
            generate_vegetation_module.validate_parameters(parameters)

    def test_planter_requires_valid_pot(self) -> None:
        parameters = self.planter_parameters()
        parameters["pot"]["top_radius_m"] = 0.08
        with self.assertRaisesRegex(ValueError, "taper outward"):
            generate_vegetation_module.validate_parameters(parameters)

    def test_legacy_v1_contract_still_validates(self) -> None:
        result = generate_vegetation_module.validate_parameters(
            self.planter_parameters()
        )
        # 7.23 organic options get deterministic defaults for old contracts.
        self.assertEqual(result["lateral_branches"], 0)
        self.assertEqual(result["leaf_density"], 1.0)
        self.assertGreater(result["leaf_curl_m"], 0.0)
        self.assertGreater(result["leaf_cup_m"], 0.0)

    def test_organic_overrides_validate(self) -> None:
        parameters = self.planter_parameters()
        parameters.update(
            {
                "lateral_branches": 3,
                "leaf_density": 1.6,
                "leaf_curl_m": 0.012,
                "leaf_cup_m": 0.008,
            }
        )
        result = generate_vegetation_module.validate_parameters(parameters)
        self.assertEqual(result["lateral_branches"], 3)
        self.assertAlmostEqual(result["leaf_density"], 1.6)
        self.assertAlmostEqual(result["leaf_curl_m"], 0.012)

    def test_leaf_density_bounds(self) -> None:
        parameters = self.planter_parameters()
        parameters["leaf_density"] = 3.0
        with self.assertRaisesRegex(ValueError, "leaf_density"):
            generate_vegetation_module.validate_parameters(parameters)

    def test_lateral_branch_bounds(self) -> None:
        parameters = self.planter_parameters()
        parameters["lateral_branches"] = 12
        with self.assertRaisesRegex(ValueError, "lateral_branches"):
            generate_vegetation_module.validate_parameters(parameters)


if __name__ == "__main__":
    unittest.main()
