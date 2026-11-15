#!/usr/bin/env python3
"""Behavior tests for the scene-kit concept-first workflow."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import scene_kit
import parametric_components


PNG_BYTES = b"\x89PNG\r\n\x1a\nscene-kit-test"


class SceneKitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "project"
        scene_kit.initialize_project(self.root, "测试建筑")
        self.paths = scene_kit.project_files(self.root)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def load(self, name: str) -> dict:
        return scene_kit.read_json(self.paths[name])

    def save(self, name: str, value: dict) -> None:
        scene_kit.write_json_atomic(self.paths[name], value)

    def make_file(self, relative: str) -> str:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(PNG_BYTES)
        return relative

    def complete_brief(self) -> None:
        brief = self.load("brief")
        brief.update(
            {
                "summary": "两层欧式小楼，右侧方形露台下方为花园",
                "floors": 2,
                "footprint_m": {"width": 9.0, "depth": 7.5},
                "critical_dimensions": {
                    "floor_height_m": 3.0,
                    "wall_thickness_m": 0.2,
                    "door_m": {"width": 1.0, "height": 2.1},
                },
                "spatial_constraints": ["右侧露台覆盖一层花园"],
                "design_goals": ["克制的欧式古典"],
                "degrees_of_freedom": ["栏杆花纹", "窗格构图"],
            }
        )
        self.save("brief", brief)

    def complete_concepts(self, selected: bool = True) -> None:
        directions = []
        for index, name in enumerate(("轻法式", "暖地中海", "精简装饰艺术"), start=1):
            direction_id = f"D{index:02d}"
            view_paths = {
                view_id: self.make_file(
                    f"concepts/{direction_id}/views/{view_id}.png"
                )
                for view_id in scene_kit.CONCEPT_VIEW_IDS
            }
            directions.append(
                {
                    "direction_id": direction_id,
                    "name": name,
                    "premise": f"{name}方向需使用不同立面秩序",
                    "prompt_en": f"Complete English prompt for {name}.",
                    "prompt_zh": f"{name}的完整中文概念提示词。",
                    "negative_en": "complete building errors, labels, watermark",
                    "negative_zh": "错误建筑结构、文字、水印",
                    "view_paths": view_paths,
                    "preserved_constraints": ["右侧露台", "下方花园"],
                    "design_moves": ["立面节奏", "构件语言"],
                    "selected": selected and index == 1,
                    "consistency_review": {
                        "status": "pass",
                        "checked_views": list(scene_kit.CONCEPT_VIEW_IDS),
                        "checks": {
                            "same_building": True,
                            "same_proportions": True,
                            "same_component_language": True,
                            "complete_views": True,
                            "no_impossible_structure": True,
                        },
                        "notes": ["十视图已对照，体量和构件语言一致"],
                    },
                }
            )
        concepts = self.load("concepts")
        concepts["directions"] = directions
        concepts["status"] = "selected" if selected else "reviewed"
        concepts["selected_direction"] = "D01" if selected else None
        self.save("concepts", concepts)
        scene_kit.write_concept_prompt_packs(self.root)

    def complete_design(self) -> None:
        design = self.load("design")
        design.update(
            {
                "status": "approved",
                "selected_direction": "D01",
                "style_id": "restrained_french_01",
                "style_version": 1,
                "fixed_style": {
                    "positive_en": "Restrained French classical architecture.",
                    "positive_zh": "克制轻法式古典建筑。",
                    "negative_en": "No style drift and no excessive ornament.",
                    "negative_zh": "避免风格漂移和过度装饰。",
                },
                "palette": ["warm off-white", "dark bronze"],
                "materials": ["fine stucco", "painted metal"],
                "geometry_language": ["clear rectangular openings"],
                "component_rules": {"window": "slender divided lights"},
            }
        )
        self.save("design", design)

    def complete_component(self, include_free: bool = True, misuse_review: bool = False) -> None:
        reference_view = self.make_file(
            "preview/reference-models/front_right_45.png"
        )
        reference_source = self.make_file(
            "out/reference_source.blend"
        )
        reference_blend = self.make_file(
            "out/reference_decimated.blend"
        )
        reference_glb = self.make_file("raw/reference_decimated.glb")
        reference_preview = self.make_file(
            "preview/reference-models/reference.png"
        )
        reference_comparison = self.make_file(
            "preview/reference-models/comparison.png"
        )
        reference_audit = self.make_file(
            "preview/reference-models/audit.json"
        )
        segmentation_report = self.make_file(
            "internal/reference-mesh-segmentation.json"
        )
        derived_views = {
            view_id: self.make_file(
                f"preview/reference-models/derived-views/{view_id}.png"
            )
            for view_id in scene_kit.CONCEPT_VIEW_IDS
        }
        geometry = self.make_file("preview/references/window_01/geometry.png")
        appearance = self.make_file("preview/references/window_01/appearance.png")
        review = self.make_file("preview/references/window_01/review.png")
        comparison = self.make_file("preview/qa/window_01/comparison.png")
        material_front = self.make_file(
            "preview/qa/window_01/material_front.png"
        )
        material_three_quarter = self.make_file(
            "preview/qa/window_01/material_three_quarter.png"
        )
        material_comparison = self.make_file(
            "preview/qa/window_01/material_comparison.png"
        )
        texture_audit_path = self.make_file(
            "preview/qa/window_01/blender_audit.json"
        )
        view_paths = {
            view_id: self.make_file(f"concepts/D01/views/{view_id}.png")
            for view_id in scene_kit.CONCEPT_VIEW_IDS
        }
        source_front = view_paths["front"]
        source_left = view_paths["left"]
        source_three_quarter = view_paths["front_left_45"]
        all_views = list(view_paths.values())
        part = {
            "part_id": "window_01",
            "type": "window",
            "asset_class": "architectural_component",
            "decision": "ai_3d",
            "purpose": "重复二层窗",
            "library_metadata": {
                "name": "Slender divided-light window",
                "tags": ["window", "sage shutters", "repeating"],
                "reuse": {
                    "allowed": True,
                    "mode": "scale_variants",
                    "constraints": ["recreate wall opening per project"],
                },
            },
            "locked": {
                "interface_width_m": 1.2,
                "interface_height_m": 1.5,
                "thickness_m": 0.08,
                "origin": "bottom_center",
                "forward": "-Y",
            },
            "guided": {
                "silhouette": "slender light casement",
                "materials": ["painted metal", "glass"],
            },
            "free": ["mullion rhythm", "ornament"] if include_free else [],
            "route_assessment": {
                "reference_model_id": "whole_building_reference_01",
                "status": "approved",
                "recommended_route": "tripo",
                "selected_route": "tripo",
                "decision_summary": "测试构件具有独立造型参考，且尺寸可按锁定接口后处理。",
                "repeat_count": 1,
                "precision_demand": "design_guided",
                "blender_effort": "high",
                "tripo_expected_benefit": "high",
                "tripo_token_risk": "low",
                "reference_quality": "high",
                "evidence": ["单件参考轮廓和风格裁剪已通过审查"],
                "reference_sufficiency": {
                    "status": "pass",
                    "usable_views": [source_front, source_left],
                    "has_front": True,
                    "has_side_or_three_quarter": True,
                },
                "triangle_budget": {
                    "target_total": 15000,
                    "hard_max": 25000,
                    "basis": "单体近景与实时场景预算",
                },
                "low_poly_strategy": {
                    "provider_quality": "standard",
                    "provider_face_limit_exposed": False,
                    "postprocess": ["decimation", "retopology"],
                    "preserve": ["silhouette", "UV seams", "material boundaries"],
                },
            },
            "reference_pack": {
                "geometry": [geometry],
                "appearance": [review if misuse_review else appearance],
                "review_only": [review],
                "audit": {
                    "status": "pass",
                    "source_views": [
                        source_front,
                        source_left,
                        source_three_quarter,
                    ],
                    "checks": {
                        "crop_complete": True,
                        "boundary_isolated": True,
                        "matches_multi_view": True,
                        "attachment_visible": True,
                        "no_hidden_context": True,
                    },
                    "notes": [
                        "拆件图完整保留窗框、侧厚和安装背面",
                        "已对照正面、侧面和 45 度视图",
                    ],
                },
            },
            "reference_consensus": {
                "status": "pass",
                "confidence": "high",
                "authority_policy": {
                    "primary_geometry": "reference_model",
                    "primary_component_reference": "model_derived_views",
                    "original_views_role": "validation_and_surface_detail",
                },
                "source_views": [
                    source_front,
                    source_left,
                    source_three_quarter,
                ],
                "crops": [appearance, review],
                "model_crops": [derived_views["front"]],
                "observations": [
                    {
                        "view": source_front,
                        "silhouette": "slender rectangular window",
                        "structure": "three major sections with a divided center",
                        "material": "deep brown wood frame",
                    },
                    {
                        "view": source_left,
                        "silhouette": "same depth and sill",
                        "structure": "rear mounting face visible",
                        "material": "warm brown frame and pale stone trim",
                    },
                ],
                "material_samples": [
                    {
                        "view": source_front,
                        "role": "frame",
                        "method": "dominant dark warm-pixel sample",
                        "mean_rgb": [64, 50, 38],
                    },
                    {
                        "view": source_left,
                        "role": "frame",
                        "method": "dominant dark warm-pixel sample",
                        "mean_rgb": [71, 55, 42],
                    },
                ],
                "consensus": {
                    "frame": "deep brown low-sheen wood",
                    "trim": "warm pale stone",
                    "glass": "muted dark glazing",
                },
                "checks": {
                    "identity_consistent": True,
                    "silhouette_consistent": True,
                    "structure_consistent": True,
                    "material_consistent": True,
                    "attachment_consistent": True,
                    "lighting_variation_explained": True,
                },
                "unresolved": [],
                "confirmed_before_generation": True,
            },
            "boundary_review": {
                "status": "pass",
                "source_views": [
                    source_front,
                    source_left,
                    source_three_quarter,
                ],
                "overall_dimensions_m": [1.2, 0.32, 1.5],
                "mounting_interface_dimensions_m": [1.2, 0.24, 1.5],
                "surfaces": {
                    "front": True,
                    "back": True,
                    "left": True,
                    "right": True,
                    "top": True,
                    "bottom": True,
                },
                "attachments": [
                    {
                        "id": "stone_window_sill",
                        "type": "protruding_stone_window_sill",
                        "disposition": "included_in_component",
                        "geometry_included": True,
                        "material": "warm stone",
                        "projection_m": 0.08,
                        "evidence_views": [source_front, source_three_quarter],
                    },
                    {
                        "id": "stone_surround",
                        "type": "stone_window_surround",
                        "disposition": "included_in_component",
                        "geometry_included": True,
                        "material": "warm stone",
                        "projection_m": 0.02,
                        "evidence_views": [source_front, source_left],
                    },
                ],
                "material_zones": [
                    {"role": "frame", "material": "deep brown wood"},
                    {"role": "sill", "material": "warm stone"},
                    {"role": "glass", "material": "muted dark glazing"},
                ],
                "checks": {
                    "volume_complete": True,
                    "all_surfaces_accounted": True,
                    "attachments_inventory_complete": True,
                    "attached_geometry_included": True,
                    "material_zones_complete": True,
                    "interface_vs_overall_bounds_verified": True,
                },
                "unresolved": [],
            },
            "decomposition_audit": {
                "status": "pass",
                "source_views": [
                    source_front,
                    source_left,
                    source_three_quarter,
                ],
                "checks": {
                    "component_scope_complete": True,
                    "multi_view_consistent": True,
                    "attachment_logic_verified": True,
                    "not_fragmented": True,
                },
                "notes": ["窗框、百叶和洞口被视为一个完整可安装构件"],
            },
            "fine_structure_review": {
                "status": "pass",
                "confidence": "high",
                "evidence": {
                    "closeup": appearance,
                    "observation": "三分区中，中区再分成两列，共四列四行。",
                    "reidentification": "局部放大与独立问题复核一致。",
                },
                "source_views": [
                    source_front,
                    source_left,
                    source_three_quarter,
                ],
                "material_cues": {
                    "frame": "aged black-brown painted timber",
                    "trim": "warm pale stone",
                    "glass": "muted blue-grey",
                },
                "pattern": {
                    "major_vertical_sections": 3,
                    "columns": 4,
                    "rows": 4,
                    "pane_count": 16,
                    "horizontal_bars": 3,
                    "central_split": {
                        "enabled": True,
                        "sub_columns": 2,
                    },
                },
                "unresolved": [],
            },
            "prompt": {
                "positive_en": "One isolated window with repeatable interface.",
                "negative_en": "complete building, environment, watermark",
                "positive_zh": "单一独立窗，接口可重复。",
                "negative_zh": "完整建筑、环境、水印。",
            },
            "generation": {
                "status": "generated",
                "provider": "test",
                "input_mode": "image_to_3d",
                "references_used": [appearance],
                "candidate_count": 1,
                "paid_retries": 0,
                "source_path": self.make_file("raw/window_01_v1.glb"),
                "source_version": 1,
            },
            "qa": {
                "comparison_path": comparison,
                "differences": [],
                "repairs": [],
                "result": "pass",
                "material_review": {
                    "status": "pass",
                    "rendered_views": [
                        material_front,
                        material_three_quarter,
                    ],
                    "reference_comparison": material_comparison,
                    "polyhaven_checked": True,
                    "polyhaven_assets": [],
                    "texture_source": "project_pbr",
                    "checks": {
                        "reference_match": True,
                        "base_color_match": True,
                        "roughness_match": True,
                        "texture_scale_match": True,
                        "texture_projection_valid": True,
                        "surface_quality": True,
                    },
                    "texture_audit": {
                        "status": "pass",
                        "audit_path": texture_audit_path,
                        "mapping_mode": "uv",
                        "views_checked": [
                            "front",
                            "side",
                            "three_quarter",
                        ],
                        "checks": {
                            "source_image_loaded": True,
                            "projection_axis_valid": True,
                            "physical_scale_consistent": True,
                            "no_visible_stretch_across_faces": True,
                            "normal_and_roughness_aligned": True,
                        },
                        "risk_findings": [],
                    },
                    "notes": [
                        "项目 PBR 材质与参考色调和粗糙度匹配",
                    ],
                },
            },
            "review": {
                "single_object": True,
                "clean_background": True,
                "interface_clean": True,
                "style_aligned": True,
                "structure_legible": True,
                "surface_quality": True,
                "construction_logic": True,
            },
        }
        components = self.load("components")
        components["parts"] = [part]
        components["reference_models"] = [
            {
                "reference_model_id": "whole_building_reference_01",
                "status": "pass",
                "role": "reference_only",
                "reference_only": True,
                "input_mode": "single_image_to_3d",
                "source_views": [reference_view],
                "authority_policy": {
                    "primary_geometry": "reference_model",
                    "primary_component_reference": "model_derived_views",
                    "original_views_role": "validation_and_surface_detail",
                },
                "model_derived_views": derived_views,
                "reference_quality": {
                    "status": "pass",
                    "checks": {
                        "mesh_exists": True,
                        "main_massing_complete": True,
                        "roof_present": True,
                        "openings_present": True,
                        "attachment_relations_legible": True,
                    },
                    "limitations": ["单图生成模型仅用于空间参考"],
                },
                "camera_rig": {
                    "status": "pass",
                    "shared_center": True,
                    "ortho_scale": 12.0,
                    "views": {
                        view_id: {"camera": f"CAM_{view_id}"}
                        for view_id in scene_kit.CONCEPT_VIEW_IDS
                    },
                },
                "derived_view_validation": {
                    "status": "pass",
                    "reliable_views": list(scene_kit.CONCEPT_VIEW_IDS)[2:],
                    "low_confidence_views": list(
                        scene_kit.CONCEPT_VIEW_IDS
                    )[:2],
                    "checks": {
                        "all_views_exist": True,
                        "all_views_nonempty": True,
                        "camera_rig_consistent": True,
                        "same_building_identity": True,
                        "scale_and_framing_consistent": True,
                    },
                },
                "selection_reason": "三视角度同时展示正面和侧向深度。",
                "provider": "tripo",
                "model": "test-model",
                "provider_quality": "standard",
                "provider_face_limit_exposed": False,
                "raw_triangles": 1000000,
                "decimated_triangles": 150000,
                "max_triangles": 200000,
                "decimation_method": "collapse",
                "source_blend": reference_source,
                "decimated_blend": reference_blend,
                "decimated_glb": reference_glb,
                "preview": reference_preview,
                "comparison": reference_comparison,
                "audit": reference_audit,
                "normalization": {
                    "status": "pass",
                    "verified_views": [
                        source_front,
                        source_left,
                        source_three_quarter,
                    ],
                },
                "feature_extraction": {
                    "status": "pass",
                    "segmentation_report": segmentation_report,
                    "component_map": [
                        {
                            "part_id": "window_01",
                            "primary_source": "model_derived_views",
                            "mesh_island_ids": [1],
                            "reference_observations": [
                                "窗台外突",
                                "窗套侧返口",
                                "16 格窗棂",
                            ],
                            "views_checked": [
                                source_front,
                                source_left,
                                source_three_quarter,
                            ],
                        }
                    ],
                },
                "analysis_ready": True,
            }
        ]
        components["detail_audit"] = {
            "status": "pass",
            "scan_views": all_views,
            "coverage": {
                "roof_and_skyline_scanned": True,
                "openings_and_frames_scanned": True,
                "trim_and_ornament_scanned": True,
                "attachments_and_services_scanned": True,
                "site_and_vegetation_scanned": True,
                "surface_and_material_patterns_scanned": True,
            },
            "features": [
                {
                    "feature_id": "window_01_feature",
                    "category": "openings_and_frames",
                    "type": "divided_light_window",
                    "views": [
                        source_front,
                        source_left,
                        source_three_quarter,
                    ],
                    "quantity": 1,
                    "visual_impact": "silhouette",
                    "geometry_required": True,
                    "disposition": "part",
                    "part_id": "window_01",
                    "observation": "高窄分格窗及其石质窗套在多视图中一致。",
                },
                {
                    "feature_id": "chimney_01_feature",
                    "category": "attachments_and_services",
                    "type": "chimney",
                    "views": [
                        source_front,
                        source_left,
                        source_three_quarter,
                    ],
                    "quantity": 1,
                    "visual_impact": "silhouette",
                    "geometry_required": True,
                    "disposition": "parametric",
                    "observation": "屋面烟囱形成天际线特征，必须由参数化几何补回。",
                },
                {
                    "feature_id": "roof_tile_pattern",
                    "category": "surface_and_material_patterns",
                    "type": "roof_tile_pattern",
                    "views": [source_front, source_three_quarter],
                    "quantity": 1,
                    "visual_impact": "surface_only",
                    "geometry_required": False,
                    "disposition": "material",
                    "observation": "石板瓦纹理没有独立厚度，由 PBR 与法线表达。",
                },
            ],
            "unresolved": [],
        }
        components["decomposition_review"] = {
            "status": "pass",
            "source_views": [
                source_front,
                source_left,
                source_three_quarter,
            ],
            "checks": {
                "inventory_complete": True,
                "multi_view_consistent": True,
                "attachment_logic_verified": True,
                "assembly_not_fragmented": True,
                "detail_features_complete": True,
                "detail_geometry_decisions_verified": True,
            },
            "notes": ["所有可见构件均已在多视图之间核对"],
        }
        self.save("components", components)
        parametric_components.scaffold_registry(self.root)

    def complete_assembly(self) -> None:
        blend = self.make_file("out/B01.blend")
        hero = self.make_file("preview/finishing/B01_hero.png")
        front = self.make_file("preview/finishing/B01_front.png")
        three_quarter = self.make_file(
            "preview/finishing/B01_three_quarter.png"
        )
        eave_closeup = self.make_file(
            "preview/finishing/B01_eave_door_closeup.png"
        )
        comparison = self.make_file(
            "preview/finishing/B01_comparison.png"
        )
        blend_hash = hashlib.sha256((self.root / blend).read_bytes()).hexdigest()
        assembly = self.load("assembly")
        assembly.update(
            {
                "blend_path": blend,
                "screenshots": [hero, front, three_quarter],
                "instances": [
                    {
                        "instance_id": "B01-window-01",
                        "part_id": "window_01",
                        "position_m": [1.5, -0.1, 0.9],
                        "rotation_deg": [0.0, 0.0, 0.0],
                    }
                ],
                "artifact": {
                    "revision": 1,
                    "blend_sha256": blend_hash,
                    "rendered_at": "2026-11-13T10:00:00+08:00",
                },
                "finishing": {
                    "status": "pass",
                    "result": "pass",
                    "revision": 1,
                    "analysis_summary": (
                        "逐视图对照后完成面片、法线、材质和构造关系检查；"
                        "入口屋檐悬空问题已自主修复。"
                    ),
                    "views": {
                        "hero": hero,
                        "front": front,
                        "three_quarter": three_quarter,
                        "closeups": [eave_closeup],
                    },
                    "comparison_paths": [comparison],
                    "inspected_views": [
                        "hero",
                        "front",
                        "three_quarter",
                        "eave_door_closeup",
                    ],
                    "checks": {
                        "reference_match": True,
                        "surface_quality": True,
                        "mesh_integrity": True,
                        "material_quality": True,
                        "lighting_quality": True,
                        "assembly_seams": True,
                        "construction_logic": True,
                        "all_asset_sources_covered": True,
                    },
                    "issues": [
                        {
                            "id": "F01",
                            "severity": "high",
                            "status": "fixed",
                            "observation": "入口屋檐没有可靠连接，门廊呈悬空状态",
                            "disposition": (
                                "延长屋面并补回墙体接触面与支座，重新渲染近景"
                            ),
                        }
                    ],
                    "logical_relationships": [
                        {
                            "id": "R01",
                            "relationship": "entrance_eave_to_wall_and_door",
                            "assessment": (
                                "屋檐与墙体、门廊之间存在可见缝隙，"
                                "不符合受力与遮挡逻辑"
                            ),
                            "result": "repaired",
                            "repair": (
                                "补齐墙体嵌入、梁端连接和防水收口，"
                                "确认门与屋檐之间不再悬空"
                            ),
                        }
                    ],
                },
                "accepted": False,
            }
        )
        self.save("assembly", assembly)

    def reach_finishing(self) -> None:
        self.complete_brief()
        self.advance()
        self.complete_concepts()
        self.advance(confirmed=True)
        self.complete_design()
        self.advance()
        self.complete_component()
        self.advance(confirmed=True)
        self.advance(confirmed=True)
        self.advance()
        self.complete_assembly()
        self.advance()

    def advance(self, confirmed: bool = False) -> dict:
        return scene_kit.advance_stage(self.root, confirmed_by_user=confirmed)

    def test_init_creates_valid_concept_first_project(self) -> None:
        errors, warnings = scene_kit.validate_project(self.root)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])
        self.assertEqual(self.load("progress")["stage"], "BRIEF")
        self.assertTrue(self.load("scene")["concept_first"])
        self.assertEqual(
            self.load("scene")["render_policy"]["qa_render"],
            "required",
        )

    def test_legacy_7_1_project_is_readable_with_migration_warning(self) -> None:
        scene = self.load("scene")
        scene["skill_version"] = "7.1"
        self.save("scene", scene)
        errors, warnings = scene_kit.validate_project(self.root)
        self.assertEqual(errors, [])
        self.assertTrue(any(f"当前版本为 {scene_kit.SKILL_VERSION}" in warning for warning in warnings))

    def test_empty_brief_cannot_advance(self) -> None:
        with self.assertRaises(ValueError):
            self.advance()

    def test_concepts_require_three_directions_selection_and_confirmation(self) -> None:
        self.complete_brief()
        self.advance()
        self.complete_concepts(selected=False)
        with self.assertRaises(ValueError):
            self.advance(confirmed=True)
        self.complete_concepts(selected=True)
        with self.assertRaises(ValueError):
            self.advance()
        self.assertEqual(self.advance(confirmed=True)["to"], "DESIGN")

    def test_only_selected_direction_needs_complete_ten_view_group(self) -> None:
        self.complete_brief()
        self.advance()
        self.complete_concepts()
        concepts = self.load("concepts")
        for direction in concepts["directions"][1:]:
            direction["view_paths"] = {}
        for direction in concepts["directions"]:
            direction["prompt_file"] = (
                f"concepts/{direction['direction_id']}/prompts.txt"
            )
        self.save("concepts", concepts)
        scene_kit.write_concept_prompt_packs(self.root)
        self.assertEqual(self.advance(confirmed=True)["to"], "DESIGN")

    def test_selected_direction_requires_all_ten_view_images(self) -> None:
        self.complete_brief()
        self.advance()
        self.complete_concepts()
        concepts = self.load("concepts")
        del concepts["directions"][0]["view_paths"]["back_right_45"]
        self.save("concepts", concepts)
        with self.assertRaisesRegex(ValueError, "back_right_45"):
            self.advance(confirmed=True)

    def test_selected_direction_requires_multiview_consistency_review(self) -> None:
        self.complete_brief()
        self.advance()
        self.complete_concepts()
        concepts = self.load("concepts")
        del concepts["directions"][0]["consistency_review"]
        self.save("concepts", concepts)
        with self.assertRaisesRegex(ValueError, "十视图一致性审查"):
            self.advance(confirmed=True)

    def test_prompt_pack_is_copyable_and_complete(self) -> None:
        directions = [
            {
                "direction_id": "D01",
                "name": "测试方向",
                "premise": "一个清楚的设计主张",
                "prompt_en": "English hero prompt.",
                "front_prompt_en": "English front prompt.",
                "details_prompt_en": "English details prompt.",
                "prompt_zh": "中文主图提示词。",
                "front_prompt_zh": "中文正面提示词。",
                "details_prompt_zh": "中文细节提示词。",
                "negative_en": "No text, no watermark.",
                "negative_zh": "无文字，无水印。",
            }
        ]
        concepts = self.load("concepts")
        concepts["directions"] = directions
        self.save("concepts", concepts)
        result = scene_kit.write_concept_prompt_packs(self.root, "D01")
        self.assertEqual(result["count"], 1)
        text = (self.root / "concepts/D01/prompts.txt").read_text(encoding="utf-8")
        for index in range(1, 11):
            self.assertIn(f"IMAGE {index} OF 10", text)
            self.assertIn(f"第 {index} 张，共 10 张", text)
        english_positions = [
            text.index(f"IMAGE {index} OF 10") for index in range(1, 11)
        ]
        self.assertEqual(english_positions, sorted(english_positions))
        for expected in (
            "正交俯视图",
            "正交仰视图",
            "左侧正交立面图",
            "右侧正交立面图",
            "正面正交立面图",
            "背面正交立面图",
            "左前侧 45 度视图",
            "右前侧 45 度视图",
            "左后侧 45 度视图",
            "右后侧 45 度视图",
            "负面提示词",
            "3:2",
        ):
            self.assertIn(expected, text)
        self.assertNotIn("IMAGE 1 OF 3", text)

    def test_design_contract_is_required_before_components(self) -> None:
        self.complete_brief()
        self.advance()
        self.complete_concepts()
        self.advance(confirmed=True)
        with self.assertRaises(ValueError):
            self.advance()
        self.complete_design()
        self.assertEqual(self.advance()["to"], "COMPONENTS")

    def test_ai_component_requires_freedom_contract(self) -> None:
        self.complete_component(include_free=False)
        errors, _ = scene_kit.validate_project(self.root)
        self.assertTrue(any("free" in error for error in errors))

    def test_components_require_whole_building_reference_model(self) -> None:
        self.complete_brief()
        self.advance()
        self.complete_concepts()
        self.advance(confirmed=True)
        self.complete_design()
        self.assertEqual(self.advance()["to"], "COMPONENTS")
        errors, _ = scene_kit.validate_project(self.root)
        self.assertTrue(
            any("reference_models" in error for error in errors)
        )

    def test_component_stage_blocks_unanalysed_reference_model(self) -> None:
        self.complete_brief()
        self.advance()
        self.complete_concepts()
        self.advance(confirmed=True)
        self.complete_design()
        self.advance()
        self.complete_component()
        components = self.load("components")
        components["reference_models"][0]["analysis_ready"] = False
        self.save("components", components)
        with self.assertRaisesRegex(ValueError, "尚未完成多视图归一化"):
            self.advance(confirmed=True)

    def test_reference_quality_rejects_incomplete_massing(self) -> None:
        self.complete_component()
        components = self.load("components")
        quality = components["reference_models"][0]["reference_quality"]
        quality["checks"]["main_massing_complete"] = False
        self.save("components", components)
        errors, _ = scene_kit.validate_project(self.root)
        self.assertTrue(
            any(
                "reference_quality.checks.main_massing_complete" in error
                for error in errors
            )
        )

    def test_camera_rig_requires_shared_center(self) -> None:
        self.complete_component()
        components = self.load("components")
        components["reference_models"][0]["camera_rig"][
            "shared_center"
        ] = False
        self.save("components", components)
        errors, _ = scene_kit.validate_project(self.root)
        self.assertTrue(
            any("camera_rig.shared_center" in error for error in errors)
        )

    def test_component_map_requires_traceable_mesh_islands(self) -> None:
        self.complete_component()
        components = self.load("components")
        component_map = components["reference_models"][0][
            "feature_extraction"
        ]["component_map"]
        component_map[0]["mesh_island_ids"] = ["island-a"]
        self.save("components", components)
        errors, _ = scene_kit.validate_project(self.root)
        self.assertTrue(
            any("mesh_island_ids" in error for error in errors)
        )

    def test_component_stage_requires_typed_asset_class(self) -> None:
        self.complete_brief()
        self.advance()
        self.complete_concepts()
        self.advance(confirmed=True)
        self.complete_design()
        self.advance()
        self.complete_component()
        components = self.load("components")
        del components["parts"][0]["asset_class"]
        self.save("components", components)
        with self.assertRaisesRegex(ValueError, "asset_class"):
            self.advance(confirmed=True)

    def test_component_stage_requires_decomposition_audit(self) -> None:
        self.complete_brief()
        self.advance()
        self.complete_concepts()
        self.advance(confirmed=True)
        self.complete_design()
        self.advance()
        self.complete_component()
        components = self.load("components")
        del components["parts"][0]["decomposition_audit"]
        self.save("components", components)
        with self.assertRaisesRegex(ValueError, "拆件审查"):
            self.advance(confirmed=True)

    def test_component_stage_requires_detail_audit(self) -> None:
        self.complete_brief()
        self.advance()
        self.complete_concepts()
        self.advance(confirmed=True)
        self.complete_design()
        self.advance()
        self.complete_component()
        components = self.load("components")
        del components["detail_audit"]
        self.save("components", components)
        with self.assertRaisesRegex(ValueError, "detail_audit"):
            self.advance(confirmed=True)

    def test_detail_audit_rejects_unresolved_features(self) -> None:
        self.complete_brief()
        self.advance()
        self.complete_concepts()
        self.advance(confirmed=True)
        self.complete_design()
        self.advance()
        self.complete_component()
        components = self.load("components")
        components["detail_audit"]["unresolved"] = [
            "烟囱数量尚未在背视图确认"
        ]
        self.save("components", components)
        with self.assertRaisesRegex(ValueError, "未解决细节"):
            self.advance(confirmed=True)

    def test_detail_audit_rejects_geometry_lost_to_material(self) -> None:
        self.complete_brief()
        self.advance()
        self.complete_concepts()
        self.advance(confirmed=True)
        self.complete_design()
        self.advance()
        self.complete_component()
        components = self.load("components")
        components["detail_audit"]["features"][1]["disposition"] = "material"
        self.save("components", components)
        with self.assertRaisesRegex(ValueError, "不能只交给材质"):
            self.advance(confirmed=True)

    def test_detail_audit_requires_all_ten_selected_views(self) -> None:
        self.complete_brief()
        self.advance()
        self.complete_concepts()
        self.advance(confirmed=True)
        self.complete_design()
        self.advance()
        self.complete_component()
        components = self.load("components")
        components["detail_audit"]["scan_views"].pop()
        self.save("components", components)
        with self.assertRaisesRegex(ValueError, "全部十视图"):
            self.advance(confirmed=True)

    def test_references_require_generation_route_assessment(self) -> None:
        self.complete_brief()
        self.advance()
        self.complete_concepts()
        self.advance(confirmed=True)
        self.complete_design()
        self.advance()
        self.complete_component()
        self.advance(confirmed=True)
        components = self.load("components")
        del components["parts"][0]["route_assessment"]
        self.save("components", components)
        with self.assertRaisesRegex(ValueError, "路线评估"):
            self.advance(confirmed=True)

    def test_tripo_route_rejects_exact_precision(self) -> None:
        self.complete_component()
        components = self.load("components")
        components["parts"][0]["route_assessment"]["precision_demand"] = "exact"
        self.save("components", components)
        errors, _ = scene_kit.validate_project(self.root)
        self.assertTrue(any("精确尺寸" in error for error in errors))

    def test_tripo_precise_window_requires_two_reference_views(self) -> None:
        self.complete_component()
        components = self.load("components")
        sufficiency = components["parts"][0]["route_assessment"][
            "reference_sufficiency"
        ]
        sufficiency["usable_views"] = sufficiency["usable_views"][:1]
        self.save("components", components)
        errors, _ = scene_kit.validate_project(self.root)
        self.assertTrue(any("至少需要 2 个" in error for error in errors))

    def test_tripo_route_requires_triangle_budget(self) -> None:
        self.complete_component()
        components = self.load("components")
        del components["parts"][0]["route_assessment"]["triangle_budget"]
        self.save("components", components)
        errors, _ = scene_kit.validate_project(self.root)
        self.assertTrue(any("triangle_budget" in error for error in errors))

    def test_model_start_requires_multi_reference_consensus(self) -> None:
        self.complete_component()
        components = self.load("components")
        del components["parts"][0]["reference_consensus"]
        self.save("components", components)
        errors, _ = scene_kit.validate_project(self.root)
        self.assertTrue(
            any("reference_consensus" in error for error in errors)
        )

    def test_reference_consensus_rejects_single_view(self) -> None:
        self.complete_component()
        components = self.load("components")
        review = components["parts"][0]["reference_consensus"]
        review["source_views"] = review["source_views"][:1]
        review["crops"] = review["crops"][:1]
        review["material_samples"] = review["material_samples"][:1]
        self.save("components", components)
        errors, _ = scene_kit.validate_project(self.root)
        self.assertTrue(any("至少需要两个" in error for error in errors))

    def test_model_start_requires_component_boundary_review(self) -> None:
        self.complete_component()
        components = self.load("components")
        del components["parts"][0]["boundary_review"]
        self.save("components", components)
        errors, _ = scene_kit.validate_project(self.root)
        self.assertTrue(any("boundary_review" in error for error in errors))

    def test_window_boundary_requires_included_stone_sill(self) -> None:
        self.complete_component()
        components = self.load("components")
        sill = components["parts"][0]["boundary_review"]["attachments"][0]
        sill["disposition"] = "separate_component"
        sill["part_id"] = "separate_sill"
        self.save("components", components)
        errors, _ = scene_kit.validate_project(self.root)
        self.assertTrue(any("窗台必须纳入" in error for error in errors))

    def test_built_window_requires_fine_structure_pass(self) -> None:
        self.complete_component()
        components = self.load("components")
        components["parts"][0]["fine_structure_review"]["status"] = (
            "repair_required"
        )
        self.save("components", components)
        errors, _ = scene_kit.validate_project(self.root)
        self.assertTrue(any("细部结构" in error for error in errors))

    def test_fine_structure_rejects_pane_count_mismatch(self) -> None:
        self.complete_component()
        components = self.load("components")
        pattern = components["parts"][0]["fine_structure_review"]["pattern"]
        pattern["columns"] = 3
        pattern["pane_count"] = 12
        self.save("components", components)
        errors, _ = scene_kit.validate_project(self.root)
        self.assertTrue(any("中央再分列不一致" in error for error in errors))

    def test_route_cannot_recommend_blender_but_keep_ai_decision(self) -> None:
        self.complete_component()
        components = self.load("components")
        route = components["parts"][0]["route_assessment"]
        route["recommended_route"] = "blender_procedural"
        route["selected_route"] = "blender_procedural"
        self.save("components", components)
        errors, _ = scene_kit.validate_project(self.root)
        self.assertTrue(any("不能保持 ai_3d" in error for error in errors))

    def test_model_library_add_search_validate_and_link(self) -> None:
        library_root = Path(self.temp.name) / "library"
        initialized = scene_kit.initialize_model_library(library_root)
        self.assertTrue(initialized["initialized"])
        self.complete_component()
        with self.assertRaisesRegex(ValueError, "用户明确确认"):
            scene_kit.add_component_to_library(
                self.root,
                "window_01",
                library_root,
            )
        added = scene_kit.add_component_to_library(
            self.root,
            "window_01",
            library_root,
            confirmed_by_user=True,
        )
        self.assertTrue(added["added"])
        self.assertEqual(added["asset"]["type"], "window")
        self.assertEqual(
            added["asset"]["asset_class"],
            "architectural_component",
        )
        self.assertEqual(
            added["asset"]["geometry"]["dimensions_m"],
            {"width": 1.2, "height": 1.5, "depth": 0.08},
        )
        model_path = library_root / added["asset"]["files"]["model"]
        self.assertTrue(model_path.is_file())
        self.assertEqual(scene_kit.validate_model_library(library_root), [])
        result = scene_kit.search_model_library(
            library_root,
            "window",
            asset_class="architectural_component",
        )
        self.assertEqual(result["count"], 1)
        with self.assertRaisesRegex(ValueError, "用户明确确认"):
            scene_kit.link_library_asset(
                self.root,
                "window_01",
                added["asset"]["asset_id"],
                library_root,
            )
        linked = scene_kit.link_library_asset(
            self.root,
            "window_01",
            added["asset"]["asset_id"],
            library_root,
            confirmed_by_user=True,
        )
        self.assertTrue(linked["linked"])
        part = self.load("components")["parts"][0]
        self.assertEqual(part["decision"], "library")
        self.assertEqual(
            part["library_ref"]["asset_id"],
            added["asset"]["asset_id"],
        )

    def test_decorative_assets_are_searchable_in_library(self) -> None:
        library_root = Path(self.temp.name) / "library"
        scene_kit.initialize_model_library(library_root)
        self.complete_component()
        components = self.load("components")
        part = components["parts"][0]
        part["part_id"] = "stone_relief_01"
        part["type"] = "stone_relief"
        part["asset_class"] = "decorative_ornament"
        part["purpose"] = "入口上方石质浮雕"
        part["library_metadata"] = {
            "name": "Storybook stone relief",
            "tags": ["relief", "stone", "floral", "ornament"],
            "reuse": {
                "allowed": True,
                "mode": "placement_variants",
                "constraints": ["keep front face intact"],
            },
        }
        source = self.root / "raw/relief_v1.glb"
        source.write_bytes(PNG_BYTES + b"relief")
        part["generation"]["source_path"] = "raw/relief_v1.glb"
        self.save("components", components)
        added = scene_kit.add_component_to_library(
            self.root,
            "stone_relief_01",
            library_root,
            confirmed_by_user=True,
        )
        self.assertEqual(
            added["asset"]["asset_class"],
            "decorative_ornament",
        )
        result = scene_kit.search_model_library(
            library_root,
            "floral relief",
            asset_class="decorative_ornament",
        )
        self.assertEqual(result["count"], 1)
        self.assertEqual(
            result["assets"][0]["source_project"]["part_id"],
            "stone_relief_01",
        )

    def test_visual_inventory_rejects_unknown_asset_class(self) -> None:
        self.complete_component()
        components = self.load("components")
        components["visual_inventory"] = [
            {
                "item_id": "relief_01",
                "part_id": "stone_relief_01",
                "source_view": "concepts/D01/views/front.png",
                "asset_class": "loose_decoration",
                "type": "stone_relief",
                "decision": "ai_3d",
            }
        ]
        self.save("components", components)
        errors, _ = scene_kit.validate_project(self.root)
        self.assertTrue(any("asset_class" in error for error in errors))

    def test_review_only_cannot_be_generation_reference(self) -> None:
        self.complete_component(misuse_review=True)
        errors, _ = scene_kit.validate_project(self.root)
        self.assertTrue(any("review_only" in error for error in errors))

    def test_reference_image_must_drive_first_generation(self) -> None:
        self.complete_component()
        components = self.load("components")
        components["parts"][0]["generation"]["input_mode"] = "text_to_3d"
        self.save("components", components)
        errors, _ = scene_kit.validate_project(self.root)
        self.assertTrue(any("text_only_reason" in error for error in errors))

    def test_generation_requires_reference_comparison_artifact(self) -> None:
        self.complete_component()
        components = self.load("components")
        components["parts"][0]["qa"]["comparison_path"] = "preview/qa/window_01/missing.png"
        self.save("components", components)
        self.complete_brief()
        self.advance()
        self.complete_concepts()
        self.advance(confirmed=True)
        self.complete_design()
        self.advance()
        self.advance(confirmed=True)
        self.advance(confirmed=True)
        with self.assertRaisesRegex(ValueError, "缺少参考对照图"):
            self.advance()

    def test_generation_requires_material_review(self) -> None:
        self.complete_component()
        components = self.load("components")
        del components["parts"][0]["qa"]["material_review"]
        self.save("components", components)
        errors, _ = scene_kit.validate_project(self.root)
        self.assertTrue(any("material_review" in error for error in errors))

    def test_material_review_requires_polyhaven_check(self) -> None:
        self.complete_component()
        components = self.load("components")
        review = components["parts"][0]["qa"]["material_review"]
        review["polyhaven_checked"] = False
        self.save("components", components)
        errors, _ = scene_kit.validate_project(self.root)
        self.assertTrue(any("Poly Haven" in error for error in errors))

    def test_material_review_requires_color_and_roughness_match(self) -> None:
        self.complete_component()
        components = self.load("components")
        review = components["parts"][0]["qa"]["material_review"]
        review["checks"]["base_color_match"] = False
        self.save("components", components)
        errors, _ = scene_kit.validate_project(self.root)
        self.assertTrue(any("base_color_match" in error for error in errors))

    def test_material_review_requires_texture_projection_check(self) -> None:
        self.complete_component()
        components = self.load("components")
        review = components["parts"][0]["qa"]["material_review"]
        review["checks"]["texture_projection_valid"] = False
        self.save("components", components)
        errors, _ = scene_kit.validate_project(self.root)
        self.assertTrue(
            any("texture_projection_valid" in error for error in errors)
        )

    def test_material_review_requires_texture_mapping_audit(self) -> None:
        self.complete_component()
        components = self.load("components")
        review = components["parts"][0]["qa"]["material_review"]
        del review["texture_audit"]
        self.save("components", components)
        errors, _ = scene_kit.validate_project(self.root)
        self.assertTrue(any("texture_audit" in error for error in errors))

    def test_full_concept_to_review_workflow(self) -> None:
        self.reach_finishing()
        self.assertEqual(self.advance()["to"], "REVIEW")
        with self.assertRaisesRegex(ValueError, "用户明确确认"):
            self.advance()
        self.assertEqual(self.advance(confirmed=True)["to"], "COMPLETE")
        self.assertTrue(self.load("assembly")["accepted"])
        self.assertEqual(self.load("assembly")["accepted_revision"], 1)

    def test_reference_crop_audit_requires_multiview_sources(self) -> None:
        self.complete_brief()
        self.advance()
        self.complete_concepts()
        self.advance(confirmed=True)
        self.complete_design()
        self.advance()
        self.complete_component()
        components = self.load("components")
        del components["parts"][0]["reference_pack"]["audit"]
        self.save("components", components)
        self.advance(confirmed=True)
        with self.assertRaisesRegex(ValueError, "拆件图片审查"):
            self.advance(confirmed=True)

    def test_reference_audit_rejects_unrelated_source_images(self) -> None:
        self.complete_brief()
        self.advance()
        self.complete_concepts()
        self.advance(confirmed=True)
        self.complete_design()
        self.advance()
        self.complete_component()
        components = self.load("components")
        components["parts"][0]["reference_pack"]["audit"]["source_views"] = [
            self.make_file("preview/references/window_01/unrelated.png")
        ]
        self.save("components", components)
        self.advance(confirmed=True)
        with self.assertRaisesRegex(ValueError, "多视图来源"):
            self.advance(confirmed=True)

    def test_finishing_rejects_unrepaired_high_construction_defect(self) -> None:
        self.reach_finishing()
        assembly = self.load("assembly")
        assembly["finishing"]["issues"][0]["status"] = "deferred"
        self.save("assembly", assembly)
        with self.assertRaisesRegex(ValueError, "blocker/high"):
            self.advance()

    def test_finishing_requires_current_blend_hash(self) -> None:
        self.reach_finishing()
        assembly = self.load("assembly")
        assembly["artifact"]["blend_sha256"] = "0" * 64
        self.save("assembly", assembly)
        with self.assertRaisesRegex(ValueError, "哈希不一致"):
            self.advance()

    def test_review_reopen_clears_acceptance_and_records_reason(self) -> None:
        self.reach_finishing()
        self.advance()
        self.advance(confirmed=True)
        self.assertEqual(self.load("progress")["stage"], "COMPLETE")
        reopened = scene_kit.reopen_stage(
            self.root,
            "FINISHING",
            "入口屋檐仍需自主修补",
            confirmed_by_user=True,
        )
        self.assertEqual(reopened["to"], "FINISHING")
        self.assertFalse(self.load("assembly")["accepted"])
        progress = self.load("progress")
        self.assertEqual(progress["stage"], "FINISHING")
        self.assertEqual(progress["history"][-1]["kind"], "reopen")

    def test_design_style_version_can_increment(self) -> None:
        self.complete_brief()
        self.advance()
        self.complete_concepts()
        self.advance(confirmed=True)
        self.complete_design()
        design = self.load("design")
        design["style_version"] = 2
        self.save("design", design)
        self.assertEqual(self.advance()["to"], "COMPONENTS")


if __name__ == "__main__":
    unittest.main(verbosity=2)
