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
  "skill_version": "7.2",
  "concept_first": true,
  "delivery": {
    "profile": "unity_realtime",
    "camera_use": "street_three_quarter"
  },
  "created_at": "2026-11-12T00:00:00+08:00"
}
```

`delivery.profile` 允许 `unity_realtime`、`offline_render` 或 `concept_blockout`。

当前脚本兼容读取 `7.1` 和 `7.2`。7.1 项目首次进入后续门禁时会收到迁移警告，必须补齐 `quality_target`、多视图拆件审查和 `finishing` 数据后才能验收；更新旧项目时不要把历史验收直接迁移为 7.2 通过。

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
      "assembly_not_fragmented": true
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
        "provider": "tripo",
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
