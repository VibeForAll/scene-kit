#!/usr/bin/env python3
"""Tests for the pre-generation route recommendation heuristics."""

from __future__ import annotations

import unittest

import generation_route_audit as route_audit


class GenerationRouteAuditTests(unittest.TestCase):
    def test_component_route_is_blocked_without_ready_reference_model(self) -> None:
        result = route_audit.reference_model_gate({"reference_models": []})
        self.assertEqual(
            result["status"],
            "blocked_reference_model_required",
        )

    def test_component_route_passes_after_reference_model_analysis(self) -> None:
        result = route_audit.reference_model_gate(
            {
                "reference_models": [
                    {
                        "reference_model_id": "whole_01",
                        "status": "pass",
                        "reference_only": True,
                        "analysis_ready": True,
                    }
                ]
            }
        )
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["reference_model_ids"], ["whole_01"])

    def test_repeated_window_prefers_blender(self) -> None:
        part = {
            "part_id": "window_01",
            "type": "divided_light_window",
            "asset_class": "architectural_component",
            "decision": "ai_3d",
            "locked": {"width_m": 1.2, "height_m": 1.5},
            "free": ["mullion rhythm"],
        }
        inventory = [{"part_id": "window_01", "instances": 21}]
        result = route_audit.audit_part(part, inventory)
        self.assertEqual(result["recommended_route"], "blender_procedural")
        self.assertEqual(result["precision_demand"], "exact")
        self.assertEqual(result["ai_3d_token_risk"], "high")

    def test_unique_organic_vine_can_prefer_ai_3d(self) -> None:
        part = {
            "part_id": "vine_01",
            "type": "climbing_vine",
            "asset_class": "vegetation",
            "decision": "ai_3d",
            "locked": {"module_width_m": 0.9, "module_height_m": 1.2},
            "free": ["leaf distribution", "stem branching", "cluster irregularity"],
        }
        inventory = [{"part_id": "vine_01", "instances": 1}]
        result = route_audit.audit_part(part, inventory)
        self.assertEqual(result["recommended_route"], "ai_3d")
        self.assertEqual(result["ai_3d_expected_benefit"], "high")
        self.assertEqual(
            result["provider_selection"]["status"],
            "pending",
        )

    def test_structure_without_free_zone_prefers_blender(self) -> None:
        part = {
            "part_id": "steps_01",
            "type": "entrance_steps",
            "asset_class": "structure",
            "decision": "ai_3d",
            "locked": {"width_m": 1.7, "depth_m": 1.2, "height_m": 0.45},
            "free": [],
        }
        result = route_audit.audit_part(part, [])
        self.assertEqual(result["recommended_route"], "blender_procedural")

    def test_ai_3d_is_never_recommended_with_low_benefit(self) -> None:
        part = {
            "part_id": "attic_window",
            "type": "paired_attic_window",
            "asset_class": "architectural_component",
            "decision": "ai_3d",
            "locked": {"width_m": 1.6, "height_m": 1.2},
            "free": ["mullion layout", "trim profile", "hood detail"],
        }
        result = route_audit.audit_part(part, [])
        self.assertEqual(result["ai_3d_expected_benefit"], "low")
        self.assertEqual(result["recommended_route"], "blender_procedural")

    def test_route_audit_counts_only_component_reference_views(self) -> None:
        part = {
            "part_id": "vine_01",
            "type": "climbing_vine",
            "asset_class": "vegetation",
            "decision": "ai_3d",
            "locked": {"module_width_m": 1.0},
            "free": ["leaf distribution", "stem branching", "cluster irregularity"],
            "reference_pack": {
                "geometry": ["geometry_front.png"],
                "appearance": [
                    "appearance_front.png",
                    "appearance_front.png",
                    "appearance_side.png",
                ],
                "review_only": ["whole_building.png"],
            },
        }
        result = route_audit.audit_part(part, [])
        self.assertEqual(result["reference_view_count"], 3)
        self.assertFalse(result["requires_multiview_reference"])


    def test_in_context_vine_with_failed_image_attempt_uses_text_to_3d(self) -> None:
        part = {
            "part_id": "climbing_vine_module",
            "type": "climbing_vine",
            "asset_class": "vegetation",
            "decision": "ai_3d",
            "locked": {"module_width_m": 0.9},
            "free": ["leaf distribution", "stem branching", "cluster irregularity"],
            "reference_pack": {
                "geometry": ["geometry_front.png"],
                "appearance": ["appearance_front.png"],
                "isolated_asset_available": False,
            },
            "ai_3d_attempt": {
                "result": "not_used",
                "reason": "image generation imported surrounding building geometry",
            },
        }
        result = route_audit.audit_part(part, [])
        guidance = result["input_mode_guidance"]
        self.assertEqual(guidance["preferred"], "text_to_3d")
        self.assertEqual(guidance["eligible_modes"], ["text_to_3d"])
        self.assertTrue(guidance["signals"]["image_to_3d_context_failure"])

    def test_isolated_organic_reference_keeps_image_to_3d(self) -> None:
        part = {
            "part_id": "porch_planter_primary",
            "type": "potted_plant",
            "asset_class": "vegetation",
            "decision": "ai_3d",
            "locked": {"width_m": 0.6},
            "free": ["leaf shape", "cluster density"],
            "reference_pack": {
                "geometry": ["isolated_front.png"],
                "appearance": ["isolated_side.png"],
                "isolated_asset_available": True,
            },
        }
        guidance = route_audit.recommend_input_mode(part)
        self.assertEqual(guidance["preferred"], "image_to_3d")
        self.assertIn("multiview_to_3d", guidance["eligible_modes"])

    def test_precise_component_defaults_to_image_guidance(self) -> None:
        part = {
            "part_id": "tall_window_assembly",
            "type": "window",
            "asset_class": "architectural_component",
            "decision": "parametric",
            "locked": {"width_m": 1.2},
            "free": [],
        }
        guidance = route_audit.recommend_input_mode(part)
        self.assertEqual(guidance["preferred"], "image_to_3d")
        self.assertFalse(guidance["signals"]["organic_asset"])




if __name__ == "__main__":
    unittest.main(verbosity=2)
