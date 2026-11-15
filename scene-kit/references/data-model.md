# 数据结构

所有长度单位为米。文件使用 UTF-8 JSON。

## 项目结构

```text
project/
  scene.json
  progress.json
  internal/
    brief.json
    concept_directions.json
    design_contract.json
    components.json
    assembly.json
    toolchain.json
  concepts/
    D01/
    D02/
    D03/
    selected/
  preview/
    references/<part_id>/
    qa/<part_id>/
    finishing/
    style_anchor.<ext>
  raw/
  out/
  export/
```

## scene.json

```json
{
  "schema_version": 1,
  "project_id": "european-villa-01",
  "name": "二层欧式小楼",
  "skill_version": "7.15",
  "concept_first": true,
  "delivery": {
    "profile": "unity_realtime",
    "camera_use": "street_three_quarter"
  },
  "render_policy": {
    "qa_render": "required",
    "display_mode": "summary_only",
    "display_requires_confirmation": true,
    "extra_presentation_renders_require_confirmation": true
  },
  "created_at": "2026-11-12T00:00:00+08:00"
}
```

`delivery.profile` 允许 `unity_realtime`、`offline_render` 或 `concept_blockout`。

`render_policy.qa_render` 固定为 `required`：每个组件必须实际渲染材质 QA 视图，不能用项目设置关闭。`display_mode` 允许：

- `summary_only`：默认。聊天只回报摘要和文件链接。
- `milestone_contact_sheet`：只在里程碑或用户请求时展示压缩对照图。
- `show_each_component`：用户明确要求每个组件都在聊天中展示时使用。

`display_requires_confirmation` 和 `extra_presentation_renders_require_confirmation` 控制额外展示性渲染，不控制强制 QA 渲染。

当前脚本兼容读取 `7.1`–`7.21`。旧项目首次进入后续门禁时会收到迁移警告；进入 `COMPONENTS` 门禁前必须补齐 `reference_models`、`detail_audit` 和两项细节检查。7.8 的窗、门、栏杆和格栅还必须补齐 `fine_structure_review`；7.9 的所有组件在生成或建模前还必须通过 `reference_consensus`；7.10 还必须通过 `boundary_review`；7.11 要求整栋参考模型完成多视图归一化和组件映射；7.12 要求参考模型派生十视图成为组件识别和拆件的主输入；7.13 要求参考模型质量门禁、固定共享中心的正交相机轨道、派生视图可信度验证、网格分段报告和组件候选岛追溯；7.14 要求每个已构建组件的材质审查记录贴图投影、坐标、物理尺度和跨立面拉伸审计；7.15 要求每个组件都有参数化合同，且已构建组件的参数指纹与审计一致；7.19 要求正视图审计从实时 `.blend` 枚举实例，并校验合同实例数、逐件数量、立面层数窗数和植物可见性；7.20 要求拆件前完成关键特征数量清点，逐立面逐层记录窗门数量，并分开记录主屋顶、小屋顶、烟囱和端子数量；7.21 要求前置构件记录背面体量、宿主构件和真实接触关系。不能把旧版本的状态直接迁移为当前版本通过。

## progress.json

```json
{
  "schema_version": 1,
  "mode": "concept_first",
  "stage": "BRIEF",
  "last_approved_stage": null,
  "pending_decision": null,
  "current_object": "B01",
  "history": [],
  "updated_at": "2026-11-12T00:00:00+08:00"
}
```

只通过 `scene_kit.py advance` 修改阶段。

返工时只通过 `scene_kit.py reopen` 回退，并在 `history` 追加 `from`、`to`、`kind`、`reason`、`at`。不能用聊天记忆或手工编辑绕过记录。

## internal/toolchain.json

在参数化建模、AI 3D 后处理、装配或精修前，由 `ensure_modeling_extensions.py` 生成：

```json
{
  "schema_version": 1,
  "checked_at": "2026-11-14T19:50:00+08:00",
  "blender_version": "5.3.0 Release Candidate",
  "platform": "windows-x64",
  "extensions": [
    {
      "id": "archimesh",
      "name": "Archimesh",
      "module": "bl_ext.user_default.archimesh",
      "installed": true,
      "enabled": true,
      "version": "1.2.5",
      "action": "already_enabled"
    }
  ],
  "ready": true
}
```

只有 `ready=true` 才能继续依赖该工具链的建模步骤。安装报告不是项目阶段状态，不替代 `progress.json`，也不证明生成模型已达到质量要求。

## internal/brief.json

```json
{
  "schema_version": 1,
  "object_id": "B01",
  "summary": "两层欧式小楼，右侧方形露台下方为一层花园",
  "floors": 2,
  "footprint_m": {"width": 9.0, "depth": 7.5},
  "critical_dimensions": {
    "floor_height_m": 3.0,
    "wall_thickness_m": 0.2,
    "door_m": {"width": 1.0, "height": 2.1},
    "window_m": {"width": 1.2, "height": 1.5, "sill": 0.9}
  },
  "spatial_constraints": [
    "二层露台位于右侧并覆盖一层花园",
    "上下两层各有一扇侧门"
  ],
  "design_goals": [
    "克制的欧式古典",
    "适合 Unity 实时场景"
  ],
  "degrees_of_freedom": [
    "栏杆花纹",
    "窗格构图",
    "门板细节"
  ],
  "delivery": "unity_realtime",
  "camera_use": "street_three_quarter",
  "quality_target": {
    "primary_view": "street_three_quarter",
    "target_resolution": [1920, 1080],
    "quality_priority": [
      "reference_match",
      "surface_quality",
      "construction_logic"
    ],
    "polygon_budget": null,
    "material_budget": null
  }
}
```

`quality_target` 定义最终可见效果的生产目标。`target_resolution` 和 `primary_view` 用于判断面片、材质和近景在交付视角下是否足够。实时/离线预算可按项目填写，不能用“节省渲染时间”替代这些硬目标。

## internal/concept_directions.json

```json
{
  "schema_version": 1,
  "status": "selected",
  "selected_direction": "D02",
  "directions": [
    {
      "direction_id": "D01",
      "name": "克制法式古典",
      "premise": "以秩序和轻线脚为主",
      "prompt_en": "Complete English concept prompt.",
      "prompt_zh": "完整中文概念提示词。",
      "negative_en": "Complete English negative prompt.",
      "negative_zh": "完整中文负面提示词。",
      "view_paths": {
        "top": "concepts/D01/views/top.png",
        "bottom": "concepts/D01/views/bottom.png",
        "left": "concepts/D01/views/left.png",
        "right": "concepts/D01/views/right.png",
        "front": "concepts/D01/views/front.png",
        "back": "concepts/D01/views/back.png",
        "front_left_45": "concepts/D01/views/front_left_45.png",
        "front_right_45": "concepts/D01/views/front_right_45.png",
        "back_left_45": "concepts/D01/views/back_left_45.png",
        "back_right_45": "concepts/D01/views/back_right_45.png"
      },
      "prompt_file": "concepts/D01/prompts.txt",
      "preserved_constraints": ["右侧方形露台", "露台下方花园"],
      "design_moves": ["细长窗", "轻石质线脚", "克制铁艺栏杆"],
      "selected": false,
      "consistency_review": {
        "status": "pass",
        "checked_views": [
          "top",
          "bottom",
          "left",
          "right",
          "front",
          "back",
          "front_left_45",
          "front_right_45",
          "back_left_45",
          "back_right_45"
        ],
        "checks": {
          "same_building": true,
          "same_proportions": true,
          "same_component_language": true,
          "complete_views": true,
          "no_impossible_structure": true
        },
        "notes": ["十视图已逐张对照，屋顶和构件语言一致"]
      }
    }
  ]
}
```

`status` 为 `draft`、`reviewed` 或 `selected`。`selected_direction` 必须对应一个方向。所有方向都应有包含十个固定视图的 `prompt_file`。`view_paths` 必须使用固定键 `top`、`bottom`、`left`、`right`、`front`、`back`、`front_left_45`、`front_right_45`、`back_left_45`、`back_right_45`。离开 CONCEPTS 时只要求选中方向的十张视图全部存在；未选方向可以只有提示词包，`view_paths` 可以为空对象。旧版 `hero_path`、`front_path`、`details_path` 不再满足概念阶段门禁，关键构件细节图不能替代十视图。

选中方向离开 `CONCEPTS` 前，`consistency_review.status` 必须为 `pass`，`checked_views` 必须覆盖全部十视图，五个一致性/可建造检查均为 `true`。文件存在不能代替视觉一致性审查。

## internal/design_contract.json

```json
{
  "schema_version": 1,
  "status": "approved",
  "selected_direction": "D02",
  "style_id": "warm_restrained_european_01",
  "style_version": 1,
  "fixed_style": {
    "positive_en": "Warm restrained European classical architecture...",
    "positive_zh": "温暖克制的欧式古典建筑...",
    "negative_en": "No style drift, no excessive ornament...",
    "negative_zh": "避免风格漂移、过度装饰..."
  },
  "palette": ["warm off-white plaster", "dark bronze", "grey-blue glass"],
  "materials": ["fine stucco", "painted metal", "stone trim"],
  "geometry_language": ["clear rectangular openings", "restrained facade rhythm"],
  "component_rules": {
    "window": "slender divided lights with a shallow stone surround",
    "railing": "light painted metal with controlled ornamental rhythm"
  }
}
```

## internal/components.json

```json
{
  "schema_version": 1,
  "object_id": "B01",
  "visual_inventory": [
    {
      "item_id": "relief_01",
      "part_id": "stone_relief_01",
      "source_view": "concepts/D01/views/front.png",
      "asset_class": "decorative_ornament",
      "type": "stone_relief",
      "decision": "ai_3d",
      "observation": "raised floral relief above the entrance",
      "instances": 1
    }
  ],
  "decomposition_review": {
    "status": "pass",
    "source_views": [
      "concepts/D01/views/front.png",
      "concepts/D01/views/left.png",
      "concepts/D01/views/front_left_45.png"
    ],
    "checks": {
      "inventory_complete": true,
      "multi_view_consistent": true,
      "attachment_logic_verified": true,
      "assembly_not_fragmented": true,
      "detail_features_complete": true,
      "detail_geometry_decisions_verified": true
    },
    "notes": ["构件范围已跨视图核对，未发现漏项或无法安装的孤立部件"]
  },
  "parts": [
    {
      "part_id": "window_01",
      "type": "window",
      "asset_class": "architectural_component",
      "decision": "ai_3d",
      "purpose": "重复使用的二层窗",
      "library_metadata": {
        "name": "Slender divided-light window",
        "tags": ["window", "sage shutters", "repeating"],
        "reuse": {
          "allowed": true,
          "mode": "scale_variants",
          "constraints": ["recreate wall opening per project"]
        }
      },
      "locked": {
        "interface_width_m": 1.2,
        "interface_height_m": 1.5,
        "thickness_m": 0.08,
        "origin": "bottom_center",
        "forward": "-Y"
      },
      "guided": {
        "silhouette": "slender light European casement",
        "materials": ["painted metal", "glass", "shallow stone trim"]
      },
      "free": ["mullion rhythm", "panel outline", "subtle ornamental detail"],
      "decomposition_audit": {
        "status": "pass",
        "source_views": [
          "concepts/D01/views/front.png",
          "concepts/D01/views/left.png",
          "concepts/D01/views/front_left_45.png"
        ],
        "checks": {
          "component_scope_complete": true,
          "multi_view_consistent": true,
          "attachment_logic_verified": true,
          "not_fragmented": true
        },
        "notes": ["窗框、百叶、玻璃和洞口作为一个可安装窗组件"]
      },
      "reference_pack": {
        "geometry": ["preview/references/window_01/geometry_front.png"],
        "appearance": ["preview/references/window_01/concept.png"],
        "review_only": ["preview/references/window_01/building_review.png"],
        "audit": {
          "status": "pass",
          "source_views": [
            "concepts/D01/views/front.png",
            "concepts/D01/views/left.png",
            "concepts/D01/views/front_left_45.png"
          ],
          "checks": {
            "crop_complete": true,
            "boundary_isolated": true,
            "matches_multi_view": true,
            "attachment_visible": true,
            "no_hidden_context": true
          },
          "notes": ["裁剪保留完整窗框、百叶、侧厚和安装背面"]
        }
      },
      "prompt": {
        "positive_en": "One isolated architectural window...",
        "negative_en": "complete building, environment...",
        "positive_zh": "单一独立建筑窗...",
        "negative_zh": "完整建筑、环境..."
      },
      "generation": {
        "status": "generated",
        "provider": "configured_provider",
        "input_mode": "image_to_3d",
        "references_used": ["preview/references/window_01/concept.png"],
        "candidate_count": 1,
        "paid_retries": 0,
        "source_path": "raw/window_01_v1.glb",
        "source_version": 1
      },
      "qa": {
        "comparison_path": "preview/qa/window_01/comparison.png",
        "differences": ["missing top cap", "muted wood color"],
        "repairs": ["rebuilt top cap", "relit PBR wood material"],
        "result": "pass"
      },
      "review": {
        "single_object": true,
        "clean_background": true,
        "interface_clean": true,
        "style_aligned": true,
        "structure_legible": true,
        "surface_quality": true,
        "construction_logic": true
      }
    }
  ]
}
```

`decision` 允许 `ai_3d`、`library`、`parametric` 或 `reuse`。

所有 `part` 必须有具体 `type` 和 `asset_class`。`asset_class` 允许：

- `architectural_component`：门、窗、栏杆、柱和门廊。
- `decorative_ornament`：浮雕、木雕、线脚、徽章、铁艺和雕塑。
- `vegetation`：花簇、草、藤蔓、灌木和树。
- `site_element`：壁灯、花盆、长椅、标牌和小喷泉。
- `structure`：墙段、屋面、楼板和楼梯。

`visual_inventory` 记录从用户视图中识别出的建筑组件和非结构表现资产。即使最终决定使用贴图、参数化或复用，也应保留盘点项和原因，避免浮雕、花草在拆件时直接从视野中消失。

### components.parametric_registry

7.15 起，`components.json` 顶层必须记录参数合同文件：

```json
{
  "parametric_registry": "internal/parametric_components.json"
}
```

每个 `part` 必须记录：

```json
{
  "part_id": "tall_window_assembly",
  "parametric_contract_id": "tall_window_assembly"
}
```

参数合同清单的完整结构见 [parametric-components.md](parametric-components.md)。一份合同至少包含 `generator_id`、生成器类型和版本、`parameters`、`parameter_schema`、`constraints`、`outputs`、`material_bindings`、`quality_gate` 和 `last_build`。

已通过视觉验收的组件合同状态必须为 `generated` 或 `pass`。`last_build.parameters_hash` 必须等于当前参数、材质绑定和外部参数文档计算的 SHA-256；不一致表示参数已修改但尚未重新生成和验收。`last_build.audit_path` 和 `last_build.material_review_path` 必须存在。

合同审批范围固定为 `per_parameters_hash`。新参数或新材质必须重新完成几何、材质、贴图映射、实际渲染和视觉对照，不能继承旧变体的通过状态。

### components.reference_models

`reference_models` 记录拆件前生成的整栋三维侦察模型。它不是最终组件，也不能直接作为交付几何：

```json
[
  {
    "reference_model_id": "whole_building_reference_01",
    "status": "pass",
    "role": "reference_only",
    "reference_only": true,
    "input_mode": "single_image_to_3d",
    "source_views": [
      "concepts/D04/views/front_right_45.png"
    ],
    "selection_reason": "三视角度同时展示正面、入口、屋顶和侧向体量。",
    "authority_policy": {
      "primary_geometry": "reference_model",
      "primary_component_reference": "model_derived_views",
      "original_views_role": "validation_and_surface_detail"
    },
    "model_derived_views": {
      "top": "preview/reference-models/derived-views/top.png",
      "bottom": "preview/reference-models/derived-views/bottom.png",
      "left": "preview/reference-models/derived-views/left.png",
      "right": "preview/reference-models/derived-views/right.png",
      "front": "preview/reference-models/derived-views/front.png",
      "back": "preview/reference-models/derived-views/back.png",
      "front_left_45": "preview/reference-models/derived-views/front_left_45.png",
      "front_right_45": "preview/reference-models/derived-views/front_right_45.png",
      "back_left_45": "preview/reference-models/derived-views/back_left_45.png",
      "back_right_45": "preview/reference-models/derived-views/back_right_45.png"
    },
    "provider": "configured_provider",
    "model": "provider_specific_model",
    "provider_quality": "provider_specific_quality",
    "provider_face_limit_exposed": false,
    "raw_triangles": 1427770,
    "decimated_triangles": 149999,
    "max_triangles": 150000,
    "decimation_method": "collapse + triangulate",
    "source_blend": "out/reference_source.blend",
    "decimated_blend": "out/reference_decimated.blend",
    "decimated_glb": "raw/reference_decimated.glb",
    "preview": "preview/reference-models/reference.png",
    "comparison": "preview/reference-models/comparison.jpg",
    "audit": "preview/reference-models/audit.json",
    "normalization": {
      "status": "pass",
      "verified_views": [
        "concepts/D04/views/front.png",
        "concepts/D04/views/front_right_45.png"
      ]
    },
    "feature_extraction": {
      "status": "pass",
      "component_map": [
        {
          "part_id": "tall_window_assembly",
          "primary_source": "model_derived_views",
          "reference_observations": [
            "窗台外突约0.08米",
            "窗套有侧返口",
            "窗洞有实际安装厚度"
          ],
          "views_checked": [
            "concepts/D04/views/front.png",
            "concepts/D04/views/front_right_45.png"
          ]
        }
      ]
    },
    "analysis_ready": true
  }
]
```

进入 `COMPONENTS`、`REFERENCES`、`GENERATION` 或 `ASSEMBLY` 前，至少要有一个 `analysis_ready=true` 的整栋参考模型。`analysis_ready` 要求 `status=pass`、`normalization.status=pass`、`feature_extraction.status=pass`，且 `component_map` 覆盖项目全部 `part_id`。

`model_derived_views` 必须包含固定十视图，并由参考模型实际渲染得到。组件拆分首先读取这些视图；原始十视图不再用于反向修正整栋模型，而是用于发现模型幻觉、缺项、比例问题和补充可靠材质/纹理。`authority_policy` 的三个字段值固定为 `reference_model`、`model_derived_views` 和 `validation_and_surface_detail`。

单图生成的模型必须记录 `input_mode=single_image_to_3d`，不能声称其他视图参与了同一任务。多图生成则至少记录两个真实来源。参考模型必须减面并单独保存，`reference_only` 不得改为 false。

### 7.13 参考质量、相机轨道与网格分段

每个整栋参考模型还必须记录以下字段：

```json
{
  "reference_quality": {
    "status": "pass",
    "checks": {
      "mesh_exists": true,
      "main_massing_complete": true,
      "roof_present": true,
      "openings_present": true,
      "attachment_relations_legible": true
    },
    "limitations": [
      "单图生成的不可见背立面为模型推断",
      "开放壳体不作为最终水密拓扑"
    ]
  },
  "camera_rig": {
    "status": "pass",
    "shared_center": true,
    "center": [0.0, 0.0, 2.9],
    "resolution": [1200, 800],
    "ortho_scale": 10.5,
    "perspective": "orthographic",
    "framing_ratio": "3:2",
    "views": {
      "front": {
        "camera": "CAM_REF_RIG_front",
        "location": [0.0, -50.0, 2.9],
        "direction": [0.0, -1.0, 0.0],
        "up_axis": "Z",
        "ortho_scale": 10.5
      }
    }
  },
  "derived_view_validation": {
    "status": "pass",
    "camera_rig_status": "pass",
    "reliable_views": [
      "front",
      "back",
      "left",
      "right",
      "front_left_45",
      "front_right_45",
      "back_left_45",
      "back_right_45"
    ],
    "low_confidence_views": ["top", "bottom"],
    "reasons": {
      "top": "开放壳体导致顶面读形不稳定",
      "bottom": "参考模型没有完整楼底板"
    },
    "checks": {
      "all_views_exist": true,
      "all_views_nonempty": true,
      "camera_rig_consistent": true,
      "same_building_identity": true,
      "scale_and_framing_consistent": true
    },
    "visual_evidence": "preview/reference-models/canonical-v5/view_validation.json",
    "contact_sheet": "preview/reference-models/canonical-v5/contact_sheet.jpg"
  },
  "feature_extraction": {
    "segmentation_report": "preview/reference-models/canonical-v5/reference_model_report.json",
    "component_map": [
      {
        "part_id": "tall_window_assembly",
        "mesh_island_ids": [12, 29, 56, 100],
        "primary_source": "model_derived_views",
        "views_checked": ["front", "front_right_45", "right"],
        "reference_observations": [
          "候选岛提供窗框和窗台的三维位置",
          "多视图确认窗台纳入窗户边界"
        ]
      }
    ]
  }
}
```

`camera_rig.views` 必须覆盖固定十视图；每个视图使用共享中心和同一 `ortho_scale`，只改变固定观察方向。`derived_view_validation.reliable_views` 至少包含六个有效视图，项目应从正、背、左右和四个 45 度视图选择主要拆件证据。顶部/底部若不可靠，写入 `low_confidence_views` 并解释原因，不能静默删除或强行用于组件识别。

`reference_quality.limitations` 必须是非空字符串数组，明确记录单图推断、开放壳体、碎片、模型尺寸与合同尺寸差异等已知边界。参考质量通过不代表模型可以进入最终导出。

`mesh_island_ids` 是网格连通岛的候选追溯编号，不表示该岛就是完整语义组件。最终组件范围必须经过至少两个模型派生有效视图和原始视图回查；候选报告可以保留噪声，不能用错误语义把每个岛强行命名。

### route_assessment

整栋参考模型和组件特征映射完成后，才处理每个组件的执行方案。`ai_3d` 组件仍保留已批准的 `route_assessment`，但它现在是后置执行决策，不是项目的起点：

```json
{
  "status": "approved",
  "recommended_route": "blender_procedural",
  "selected_route": "blender_procedural",
  "decision_summary": "重复 21 次的规则窗，用 Blender 参数化后实例化。",
  "repeat_count": 21,
  "precision_demand": "exact",
  "blender_effort": "low",
  "ai_3d_expected_benefit": "low",
  "ai_3d_token_risk": "high",
  "reference_quality": "high",
  "evidence": ["窗格和接口由尺寸合同锁定", "重复实例超过 5 个"]
}
```

允许路线：`blender_procedural`、`blender_manual`、`library`、`ai_3d`。新项目使用提供方中立的 `ai_3d`；旧项目中的厂商特定路线名继续兼容读取，但不作为新记录的默认。

- `status` 允许 `pending`、`approved`、`rejected`。
- `precision_demand` 允许 `exact`、`design_guided`、`organic`。
- `blender_effort`、`ai_3d_expected_benefit`、`ai_3d_token_risk`、`reference_quality` 允许 `low`、`medium`、`high`。旧项目的厂商特定收益/风险字段可继续读取。
- `recommended_route` 与 `selected_route` 必须一致。
- 选择 `ai_3d` 时，组件 `decision` 必须为 `ai_3d`，`precision_demand` 不能为 `exact`，`ai_3d_expected_benefit` 不能为 `low`，`reference_quality` 不能为 `low`。
- 选择 AI 3D 路线时，还必须包含通过的 `reference_sufficiency`、`triangle_budget` 和 `low_poly_strategy`。精确门、窗、栏杆和格栅至少需要两个可用构件视角，并同时具备正面与侧面/45 度参考。
- 新记录应包含 `provider_selection.candidates` 和 `selected_provider`。未选择实际提供方时可以保持 `pending`，但不得提交生成任务。
- 当前提供方没有目标面数参数时，`low_poly_strategy.provider_face_limit_exposed=false`；生成后按预算做减面/重拓扑并重新验收，不能把任何质量档名称当作低面数保证。

### reference_consensus

`reference_consensus` 是每个组件开始参数化建模或 AI 3D 生成前必须通过的多参考门禁：

```json
{
  "status": "pass",
  "confidence": "high",
  "authority_policy": {
    "primary_geometry": "reference_model",
    "primary_component_reference": "model_derived_views",
    "original_views_role": "validation_and_surface_detail"
  },
  "source_views": [
    "concepts/D04/views/front.png",
    "concepts/D04/views/left.png",
    "concepts/D04/views/front_left_45.png"
  ],
  "crops": [
    "preview/material-consensus/part/front.png",
    "preview/material-consensus/part/left.png"
  ],
  "model_crops": [
    "preview/detail-scan-model-derived/crops/window_front.png"
  ],
  "observations": [
    {
      "view": "front",
      "silhouette": "高窄窗，三主分区",
      "structure": "中央区再分两列",
      "material": "深褐木框与暖色石套"
    },
    {
      "view": "left",
      "silhouette": "侧厚和窗台一致",
      "structure": "背面安装面可解释",
      "material": "木框保持深暖褐色"
    }
  ],
  "material_samples": [
    {
      "view": "front",
      "role": "frame",
      "method": "dominant dark warm-pixel sample",
      "mean_rgb": [63, 54, 43]
    },
    {
      "view": "left",
      "role": "frame",
      "method": "dominant dark warm-pixel sample",
      "mean_rgb": [71, 55, 42]
    }
  ],
  "consensus": {
    "frame": "deep brown low-sheen wood",
    "trim": "warm pale stone",
    "glass": "muted dark glazing"
  },
  "checks": {
    "identity_consistent": true,
    "silhouette_consistent": true,
    "structure_consistent": true,
    "material_consistent": true,
    "attachment_consistent": true,
    "lighting_variation_explained": true
  },
  "unresolved": [],
  "confirmed_before_generation": true
}
```

`source_views` 和 `crops` 至少各有两个原始图校验来源；`model_crops` 至少包含一个参考模型派生裁剪；`material_samples` 至少覆盖两个视角并记录 `mean_rgb`。所有六项一致性检查必须通过，`unresolved` 为空。参考模型控制三维几何和组件边界，原始图用于验证模型幻觉并补充可靠表面细节。

### boundary_review

`boundary_review` 防止把一个有厚度、有突出物的三维组件误做成只有一个平面的窗片、门片或墙贴：

```json
{
  "status": "pass",
  "source_views": [
    "concepts/D04/views/front.png",
    "concepts/D04/views/front_right_45.png",
    "concepts/D04/views/left.png"
  ],
  "overall_dimensions_m": [1.2, 0.34, 1.5],
  "mounting_interface_dimensions_m": [1.2, 0.24, 1.5],
  "surfaces": {
    "front": true,
    "back": true,
    "left": true,
    "right": true,
    "top": true,
    "bottom": true
  },
  "attachments": [
    {
      "id": "stone_window_sill",
      "type": "protruding_stone_window_sill",
      "disposition": "included_in_component",
      "geometry_included": true,
      "material": "warm weathered stone",
      "projection_m": 0.10,
      "evidence_views": [
        "concepts/D04/views/front.png",
        "concepts/D04/views/front_right_45.png"
      ]
    }
  ],
  "material_zones": [
    {"role": "frame", "material": "deep brown wood"},
    {"role": "sill", "material": "warm weathered stone"},
    {"role": "glass", "material": "muted glazing"}
  ],
  "checks": {
    "volume_complete": true,
    "all_surfaces_accounted": true,
    "attachments_inventory_complete": true,
    "attached_geometry_included": true,
    "material_zones_complete": true,
    "interface_vs_overall_bounds_verified": true
  },
  "unresolved": []
}
```

`overall_dimensions_m` 包含附着结构，`mounting_interface_dimensions_m` 只描述装配接触范围，两者不得混用。每个 `attachments` 项至少要有两个证据视角；纳入组件的附件必须记录几何和材质，独立拆出的附件必须引用真实 `part_id`。

窗类组件的附件清单必须包含窗台，窗台默认纳入窗户组件，并明确记录为 stone 材质。只有参考确认其是完全独立、可单独安装的构件时，才允许使用 `separate_component`。
- 选择 `blender_procedural` 或 `blender_manual` 时，组件不能保持 `ai_3d`。
- 选择 `library` 时，组件 `decision` 必须为 `library`。

`generation_route_audit.py` 写出 `internal/generation_route_review.json` 作为启发式证据，但不会自动修改组件或批准付费生成。

### qa.material_review

组件几何 QA 通过后，必须使用最终材质和贴图渲染，并记录：

```json
{
  "status": "pass",
  "rendered_views": [
    "preview/qa/part/material_front.png",
    "preview/qa/part/material_three_quarter.png"
  ],
  "reference_comparison": "preview/qa/part/material_comparison.png",
  "polyhaven_checked": true,
  "polyhaven_addon_available": false,
  "polyhaven_assets": [],
  "texture_source": "project_pbr",
  "generated_textures": [],
  "checks": {
    "reference_match": true,
    "base_color_match": true,
    "roughness_match": true,
    "texture_scale_match": true,
        "texture_projection_valid": true,
    "surface_quality": true
  },
      "texture_audit": {
        "status": "pass",
        "audit_path": "preview/qa/part/blender_audit.json",
        "mapping_mode": "box",
        "views_checked": ["front", "side", "three_quarter"],
        "checks": {
          "source_image_loaded": true,
          "projection_axis_valid": true,
          "physical_scale_consistent": true,
          "no_visible_stretch_across_faces": true,
          "normal_and_roughness_aligned": true
        },
        "risk_findings": []
      },
  "notes": ["木材和石材颜色、粗糙度与参考匹配"]
}
```

`texture_source` 允许 `project_pbr`、`polyhaven`、`generated`、`existing`。`status=pass` 时至少有两个实际渲染视图、参考对照图、`polyhaven_checked=true`，六项材质检查全部为 true。`texture_audit` 必须指向本次 Blender 审计，记录映射方式、至少两个已检查视图、五项贴图检查和空的风险列表。映射模式可以是 `uv`、`box`、`validated_generated` 或项目内明确说明的等价模式。使用 Poly Haven 时记录 `polyhaven_assets`；生成本地贴图时记录 `generated_textures`。

`blender_audit.py` 的顶层 `texture_mapping_audit` 必须通过。出现 `flat_3d_coordinate_projection` 或 `non_positive_texture_mapping_scale` 时，材质审查不能通过。若颜色、法线和粗糙度使用不同投影，也要在组件记录中说明并验证没有错位。

任何 `qa.result=pass` 或 `parametric_build.status=pass` 的组件都受此门禁约束。

### fine_structure_review

窗、门、栏杆和格栅不能只凭整窗视觉问答的总数通过。已建模或已通过 QA 的窗类组件必须记录放大后的重复拓扑：

```json
{
  "status": "pass",
  "confidence": "high",
  "evidence": {
    "closeup": "preview/detail-scan/crops/window_front_detail_4x.png",
    "observation": "三个主竖向分区，中央分区再分成两列，共四列四行。",
    "reidentification": "正面和一个斜视图的放大裁剪一致；独立回答确认中央双窄窗。"
  },
  "source_views": [
    "concepts/D04/views/front.png",
    "concepts/D04/views/front_left_45.png"
  ],
  "material_cues": {
    "frame": "aged black-brown painted timber",
    "trim": "warm pale stone",
    "glass": "muted blue-grey"
  },
  "pattern": {
    "major_vertical_sections": 3,
    "columns": 4,
    "rows": 4,
    "pane_count": 16,
    "horizontal_bars": 3,
    "central_split": {
      "enabled": true,
      "sub_columns": 2
    }
  },
  "unresolved": []
}
```

`status=pass` 时至少需要两个不同源视图、存在的放大近景、可信度和材质线索。`pane_count` 必须等于 `columns × rows`；中央分区再分列时，`columns` 必须等于 `major_vertical_sections - 1 + central_split.sub_columns`。

参数化或已生成组件还必须把 `parametric_build.grid_columns`、`grid_rows` 和 `pane_count` 与 `pattern` 对齐。只确认总数、但没有确认中央是否再分列，不能通过。

### detail_audit

`components.detail_audit` 是 7.3 起引入并继续沿用的 `COMPONENTS` 门禁数据。它记录逐张十视图扫描后发现的细节特征，避免烟囱、屋脊饰、托架、檐沟、台阶、五金和装饰小件在只拆大构件时被遗漏：

```json
{
  "status": "pass",
  "scan_views": [
    "concepts/D04/views/top.png",
    "concepts/D04/views/bottom.png",
    "concepts/D04/views/left.png",
    "concepts/D04/views/right.png",
    "concepts/D04/views/front.png",
    "concepts/D04/views/back.png",
    "concepts/D04/views/front_left_45.png",
    "concepts/D04/views/front_right_45.png",
    "concepts/D04/views/back_left_45.png",
    "concepts/D04/views/back_right_45.png"
  ],
  "coverage": {
    "roof_and_skyline_scanned": true,
    "openings_and_frames_scanned": true,
    "trim_and_ornament_scanned": true,
    "attachments_and_services_scanned": true,
    "site_and_vegetation_scanned": true,
    "surface_and_material_patterns_scanned": true
  },
  "features": [
    {
      "feature_id": "chimney_front_right",
      "category": "attachments_and_services",
      "type": "chimney",
      "views": [
        "concepts/D04/views/front.png",
        "concepts/D04/views/right.png",
        "concepts/D04/views/front_right_45.png"
      ],
      "quantity": 1,
      "visual_impact": "silhouette",
      "geometry_required": true,
      "disposition": "part",
      "part_id": "chimney_front_right",
      "observation": "烟囱改变屋面天际线，侧面视图可确认深度和墙体/屋面交接。"
    }
  ],
  "unresolved": []
}
```

可选的 `evidence` 用于记录视觉诊断证据，而不是替代门禁判断：

```json
{
  "evidence": {
    "method": "Florence-2 detailed captions and phrase grounding; ViLT crop VQA",
    "diagnostic_only": true,
    "audit_json": "preview/detail-scan/detail_vision_audit.json",
    "focused_json": "preview/detail-scan/focused_detail_audit.json",
    "annotated_overview": "preview/detail-scan/annotated-overview.jpg",
    "unresolved_disagreements": [
      "两处高处构件被模型分别描述为烟囱和塔"
    ]
  }
}
```

视觉模型可以提出对象、位置和数量候选，但不能自动写入 `status=pass`。至少使用两个视角或两个独立模型交叉核对；不一致项必须留在 `unresolved`。

`status=pass` 时：

- `scan_views` 必须覆盖选中方向的全部十视图。
- `coverage` 的六个类别必须全部为 `true`。
- `features` 不能为空，每个特征至少有 `feature_id`、`category`、`type`、两个 `views`、`quantity`、`visual_impact`、`geometry_required`、`disposition` 和 `observation`。
- `category` 允许 `roof_and_skyline`、`openings_and_frames`、`trim_and_ornament`、`attachments_and_services`、`site_and_vegetation`、`surface_and_material_patterns`。
- `visual_impact` 允许 `silhouette`、`near_view`、`surface_only`。
- `disposition` 允许 `part`、`parametric`、`reuse`、`material`；`part` 必须声明 `geometry_required=true` 并引用现有 `part_id`。
- `geometry_required=true` 的特征不能使用 `material`。
- `unresolved` 必须为空。

旧项目缺少 `detail_audit` 时可以继续读取，但不能通过新的 `COMPONENTS` 门禁。

### quantity_audit

`components.quantity_audit` 是 7.20 起的数量前置门禁。它先于拆件、生成和装配回答关键特征“有多少”，并与参数合同、实时装配和正视图审计交叉核对。

```json
{
  "status": "pass",
  "revision": 6,
  "source_views": [
    "assets/raw/concepts/D01/views/front.png",
    "assets/raw/concepts/D01/views/back.png",
    "assets/raw/concepts/D01/views/left.png",
    "assets/raw/concepts/D01/views/right.png",
    "assets/raw/concepts/D01/views/top.png",
    "assets/raw/concepts/D01/views/front_left_45.png"
  ],
  "counts": {
    "main_windows": {
      "expected": 21,
      "actual": 21,
      "unit": "window_instance",
      "part_id": "tall_window_assembly",
      "count_scope": "live_part_instances",
      "facade_breakdown": {
        "front": {"lower": 3, "upper": 4, "total": 7},
        "back": {"lower": 3, "upper": 4, "total": 7},
        "left": {"lower": 1, "upper": 2, "total": 3},
        "right": {"lower": 2, "upper": 2, "total": 4}
      },
      "evidence": ["internal/wall_openings_v2.json"]
    },
    "attic_dormer_roofs": {
      "expected": 1,
      "actual": 1,
      "unit": "small_roof",
      "part_id": "attic_window_assembly",
      "count_scope": "embedded_geometry",
      "evidence": ["assets/preview/components/attic_window_assembly/geometry_audit_v2.json"]
    },
    "metal_chimney_flues": {
      "expected": 0,
      "actual": 0,
      "unit": "flue",
      "part_id": "stone_chimney_primary",
      "count_scope": "removed_feature",
      "evidence": ["assets/preview/components/stone_chimney_primary/geometry_audit_v2.json"]
    }
  },
  "checks": {
    "facade_by_floor_window_matrix_verified": true,
    "repeated_features_counted_separately": true,
    "live_assembly_counts_match": true
  },
  "unresolved": []
}
```

规则：

- `counts` 不能为空；每项至少包含非负整数 `expected`、`actual`、计数单位 `unit`、计数范围 `count_scope` 和非空证据数组。
- `status=pass` 时每个数量项的 `expected == actual`，`checks` 全部为 `true`，`unresolved` 为空。
- 窗门有立面或楼层差异时必须有 `facade_breakdown`；每面各层数量相加必须等于该面 `total`，所有面 `total` 之和必须等于 `main_windows.expected`。
- 主屋顶、阁楼/老虎窗小屋顶、塔帽和门廊屋顶必须分开计数。烟囱石柱、石帽、金属烟管/陶管分别计数。
- `count_scope=live_part_instances` 时，`quantity_census_audit.py` 用 `assembly.json` 或实时正视图报告核对实例数；嵌入式构件和明确删除的构件使用 `embedded_geometry` 或 `removed_feature`，必须指向具体几何审计。
- `components.decomposition_review.checks.quantity_verified=true`。用户纠正数量后，先更新数量审计和洞口/参数合同，再重建几何。

### attachment_integrity_audit

`components.attachment_integrity_audit` 是 7.21 起的宿主连接门禁。它防止屋顶窗只有正窗和屋顶片、凸窗只有正面、雨棚或阳台没有支撑、装饰构件悬空等情况。

```json
{
  "status": "pass",
  "revision": 7,
  "source_views": [
    "assets/raw/concepts/D01/views/front.png",
    "assets/raw/concepts/D01/views/front_left_45.png",
    "assets/raw/concepts/D01/views/right.png"
  ],
  "items": [
    {
      "attachment_id": "attic_dormer_body",
      "part_id": "attic_window_assembly",
      "attachment_type": "enclosed_dormer_body",
      "host_part_ids": [
        "main_roof_assembly",
        "attic_window_assembly"
      ],
      "has_volume": true,
      "has_back_enclosure": true,
      "has_side_enclosure": true,
      "front_plane_only": false,
      "host_contact_verified": true,
      "body_projection_beyond_host_m": 0.41,
      "front_eave_setback_m": 0.04,
      "roof_covers_body_rear": true,
      "host_contact_evidence": [
        "assets/preview/components/attic_window_assembly/geometry_audit_v3.json"
      ],
      "evidence_views": [
        "assets/preview/components/attic_window_assembly/attic_window_assembly_v3_three_quarter.png",
        "assets/preview/components/attic_window_assembly/attic_window_assembly_v3_side.png"
      ],
      "status": "pass"
    }
  ],
  "checks": {
    "attachments_inventoried": true,
    "front_plane_only_rejected": true,
    "host_contacts_verified": true,
    "side_back_volume_verified": true
  },
  "unresolved": []
}
```

`attachment_integrity_audit.py` 会检查以下内容：

- `part_id` 和所有 `host_part_ids` 必须对应真实组件。
- 每个附着项必须有体积、背面、侧面和宿主接触布尔事实。
- `front_plane_only=false`、`host_contact_verified=true`，且 `body_projection_beyond_host_m > 0.05`；独立老虎窗体量通常应大于 0.20 m，不能与宿主墙/屋面共面。
- `front_eave_setback_m >= 0`，附着屋顶不能超出宿主主檐；`roof_covers_body_rear=true`，屋顶后沿必须覆盖附着体量后墙顶部。
- 至少两个正面/侧面/45 度证据视图，以及包含真实网格接触或相交结果的 `host_contact_evidence`。
- `status=pass` 时所有 checks 为 true，`unresolved` 为空。

屋顶窗和老虎窗还必须单独记录窗组、双坡/单坡顶和老虎窗体量三个对象或明确的子构件范围。仅靠正面图片、AABB 重叠或文字声明不能通过。

`library_metadata` 是可选字段，用于补充模型库需要的名称、标签、复用方式、材质和许可证。没有该字段时，脚本会从 `purpose`、`guided`、`locked` 和 QA 记录提取。跨项目模型库的完整结构、文件布局和检索方式见 [model-library.md](model-library.md)。

每个组件必须通过 `decomposition_audit`：`source_views` 至少包含两个选中方向的原多视图路径，确认拆件范围完整、多视图一致、安装关系可解释，并且拆件后不会成为孤立碎块。`reference_pack.audit` 再检查实际裁剪图没有截断目标、没有带入相邻构件或环境，并保留安装面和侧厚。两者都必须在相应阶段为 `pass`。

对 `ai_3d` 组件：

- 必须有非空 `locked`、`guided` 和 `free`。
- 必须有 `geometry` 和 `appearance` 参考图。
- `review_only` 不能同时出现在 `geometry` 或 `appearance`。
- 有参考图时 `generation.input_mode` 必须是 `image_to_3d` 或 `multiview_to_3d`；纯文字生成必须提供 `text_only_reason`。
- `generation` 必须记录实际使用的参考图、候选数和付费重试次数。
- `qa.comparison_path` 必须指向实际生成的参考对照图；`qa.differences` 和 `qa.repairs` 必须来自查看结果后的记录。
- 生成阶段必须有来源文件、完整 QA 记录和全部视觉检查为 `true`；其中 `surface_quality` 与 `construction_logic` 不能省略。

使用模型库资产时，`decision` 为 `library`，并记录：

```json
{
  "decision": "library",
  "library_source": "scene_kit_model_library",
  "library_ref": {
    "asset_id": "storybook-stone-relief-a1b2c3d4",
    "version": 1,
    "library_root": "~/.scene-kit/model-library",
    "model": "assets/storybook-stone-relief-a1b2c3d4/model.glb",
    "selected_at": "2026-11-12T20:10:00+08:00"
  }
}
```

## internal/assembly.json

```json
{
  "schema_version": 1,
  "object_id": "B01",
  "blend_path": "out/B01.blend",
  "screenshots": [
    "preview/finishing/B01_hero.png",
    "preview/finishing/B01_front.png",
    "preview/finishing/B01_three_quarter.png"
  ],
  "instances": [
    {
      "instance_id": "B01-window-01",
      "part_id": "window_01",
      "position_m": [1.5, -0.1, 0.9],
      "rotation_deg": [0.0, 0.0, 0.0]
    }
  ],
  "artifact": {
    "revision": 3,
    "blend_sha256": "64-character-sha256-of-current-blend",
    "rendered_at": "2026-11-13T15:30:00+08:00"
  },
  "finishing": {
    "status": "pass",
    "result": "pass",
    "revision": 3,
    "analysis_summary": "对照十视图、入口近景和整栋三视图完成表面与构造逻辑检查。",
    "views": {
      "hero": "preview/finishing/B01_hero.png",
      "front": "preview/finishing/B01_front.png",
      "three_quarter": "preview/finishing/B01_three_quarter.png",
      "closeups": [
        "preview/finishing/B01_eave_portal_closeup.png"
      ]
    },
    "comparison_paths": [
      "preview/finishing/B01_reference_comparison.png"
    ],
    "inspected_views": [
      "hero",
      "front",
      "three_quarter",
      "eave_portal_closeup"
    ],
    "checks": {
      "reference_match": true,
      "surface_quality": true,
      "mesh_integrity": true,
      "material_quality": true,
      "lighting_quality": true,
      "assembly_seams": true,
      "construction_logic": true,
      "all_asset_sources_covered": true
    },
    "issues": [
      {
        "id": "F01",
        "severity": "high",
        "status": "fixed",
        "observation": "入口屋檐与门廊墙面之间缺少连续支撑，近景呈松垮悬空",
        "disposition": "延长屋面连接、补墙体嵌入和梁端托座，重新渲染近景"
      }
    ],
    "logical_relationships": [
      {
        "id": "R01",
        "relationship": "entrance_eave_to_wall_and_portal",
        "assessment": "屋檐与墙体、门廊之间曾存在可见缝隙，无法解释受力与防水",
        "result": "repaired",
        "repair": "补齐结构接触、墙内嵌入、梁端和收口，确认没有悬空和黑缝"
      }
    ]
  },
  "accepted": true,
  "accepted_at": "2026-11-13T16:00:00+08:00",
  "accepted_revision": 3
}
```

`ASSEMBLY` 只要求空间关系完整。进入 `REVIEW` 前，`finishing.status/result` 必须均为 `pass`，`artifact.revision` 与 `finishing.revision` 一致，`artifact.blend_sha256` 必须等于当前 `.blend` 文件哈希。

`finishing.checks` 必须覆盖所有资产来源、参考匹配、表面、网格、材质、灯光、接缝和构造逻辑。`issues` 中的 `blocker/high` 只能为 `fixed`；`medium/low` 可 `deferred` 但必须写明处理方式。`logical_relationships` 记录智能分析过的连接和受力逻辑；`repaired` 项必须有实际修复说明。

用户在 `REVIEW` 明确确认后执行 `advance --confirmed-by-user`，脚本同时写入 `accepted_at` 和 `accepted_revision`。返工使用 `reopen`，它会清除验收状态并记录 `progress.history`，不能手改阶段字段。
