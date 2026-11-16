# 组件参数化合同

## 目标

组件化不能只把整栋模型切碎。每个可生成组件还必须说明：

- 由什么生成器产生。
- 哪些参数可编辑。
- 参数变化会更新哪些几何。
- 哪些接口、风格和构造约束不能破坏。
- 当前输出对应哪个参数指纹。
- 这次输出通过了哪些几何、材质、贴图和多视图审计。

7.15 起，项目使用 `internal/parametric_components.json` 保存合同。`components.parts` 中每个组件必须用 `parametric_contract_id` 指向自己的合同。

## 生成器分类

| 类型 | 典型组件 | 主要参数 |
|---|---|---|
| `facade_grid_wall` | 墙体、立面、塔身 | 宽深高、墙厚、楼层带、槽位、洞口宽高、窗台、随机 seed、合法槽位权重 |
| `floor_slab_grid` | 楼板、地坪 | 外轮廓、内缘退让、厚度、楼层高度、楼梯洞、分区 |
| `base_ring` | 基座、压顶、门槛 | 外轮廓、内轮廓、主体高度、压顶外挑、入口缺口、分段长度 |
| `roof_system` | 坡屋面、屋脊、檐口 | 檐口宽深、屋脊高度、坡度、瓦距、挑檐、山墙切口 |
| `window_assembly_grid` | 高窗、阁楼窗 | 接口宽高、框厚、框深、列数、行数、中央分列、窗台、窗套、玻璃内嵌 |
| `door_assembly` | 拱门、侧门 | 洞宽高、拱半径、门扇数、板格、五金、门槛、门套 |
| `railing_array` | 木栏杆、铁栏杆 | 长度、高度、立柱距、扶手截面、栏板/栏杆模式、终端连接 |
| `trim_array` | 窗套、腰线、檐线 | 截面 profile、路径、转角规则、外挑、接缝、实例间距 |
| `quoin_array` | 转角石 | 单块尺寸、层高节奏、交替宽窄、转角数、封边方式 |
| `step_array` | 台阶 | 踏步宽、踢面高、踏面深、总高、平台、扶手接口 |
| `porch_frame` | 木门廊 | 平台宽深、柱距、柱高、梁截面、披檐坡度、支撑关系 |
| `chimney_generator` | 烟囱 | 截面、总高、出屋面高度、收分、烟囱帽、砖石模数 |
| `lantern_generator` | 壁灯 | 灯体包围盒、支架长度、玻璃、灯臂、安装面 |
| `vegetation_cluster` | 藤蔓、灌木、花簇、盆栽 | 包围盒、主枝数、侧枝级数、叶片/花簇密度、叶长叶宽、卷曲与杯状、三档色、末梢芽、随机 seed、实例数 |
| `ornament_wrapper` | AI 雕刻、浮雕、装饰 | 缩放、镜像、实例、安装姿态、材质覆盖；不假装修改不可控 AI 拓扑 |
| `library_wrapper` | 库资产复用 | 包络尺寸、接口缩放、实例、镜像、材质替换、许可和来源 |

AI 3D 和模型库资产也要有合同，但只能承诺可控的包装参数。不得把“重新生成整个 AI 网格”伪装成实时拓扑参数。

## 合同结构

```json
{
  "part_id": "tall_window_assembly",
  "generator_id": "tall_window_assembly__window_assembly_grid",
  "generator_version": 1,
  "generator_type": "window_assembly_grid",
  "implementation": "blender_python",
  "variant_policy": "regenerate_geometry",
  "status": "pass",
  "revision": 3,
  "parameter_document": "internal/window_layout.json",
  "parameters": {
    "interface_width_m": 1.2,
    "interface_height_m": 1.5,
    "frame_thickness_m": 0.06,
    "pattern": {
      "major_vertical_sections": 3,
      "columns": 4,
      "rows": 4,
      "pane_count": 16,
      "central_split": {"enabled": true, "sub_columns": 2}
    }
  },
  "parameter_schema": {
    "interface_width_m": {
      "type": "number",
      "unit": "m",
      "minimum": 0.8,
      "maximum": 1.8,
      "step": 0.05,
      "editable": true
    },
    "pattern": {
      "type": "object",
      "editable": true
    }
  },
  "constraints": [
    {
      "id": "pane_count_matches_grid",
      "rule": "pane_count = columns * rows",
      "enforced_by": "scene_kit.py validate"
    },
    {
      "id": "interface_matches_wall_opening",
      "rule": "Window mounting interface equals wall opening after tolerance.",
      "enforced_by": "assembly audit"
    }
  ],
  "outputs": {
    "root_object": "SK_tall_window_v5_ROOT",
    "collection": "SK_COL_AI",
    "blend_path": "out/tall_window_assembly_parametric_textured_v5.blend",
    "source_path": "raw/tall_window_assembly_parametric_v5.glb"
  },
  "material_bindings": {
    "texture_source": "polyhaven",
    "polyhaven_assets": ["fine_grained_wood"],
    "material_review": "pass"
  },
  "quality_gate": {
    "approval_scope": "per_parameters_hash",
    "require_geometry_audit": true,
    "require_material_audit": true,
    "require_texture_mapping_audit": true,
    "require_multiview_render": true,
    "require_component_qa": true
  },
  "last_build": {
    "status": "pass",
    "revision": 3,
    "parameters_hash": "sha256 of generator inputs",
    "audit_path": "preview/qa/tall_window_assembly/blender_audit_v5_texture.json",
    "material_review_path": "preview/qa/tall_window_assembly/v5_component_boundary_comparison.jpg",
    "built_at": "2026-11-14T22:00:00+08:00"
  }
}
```

## 参数指纹与失效

参数指纹包含：

- 生成器 ID、版本、实现方式和变体策略。
- `parameters` 和 `material_bindings`。
- 约束列表。
- 外部参数文档的路径与 SHA-256。

只要参数、材质或外部参数文档变化，旧参数指纹就失效。`last_build.parameters_hash` 必须由生成完成后重新计算。参数变化但未重建时，`scene_kit.py validate` 必须报错。

不得把旧版本材质渲染继续用在新建变体上。每个参数指纹对应一套新审计：

1. 重建几何。
2. 重新检查接口、边界和构造连接。
3. 重新赋材质并检查 Poly Haven/贴图来源。
4. 重新运行 `blender_audit.py`，确认贴图映射无风险。
5. 强制重新渲染正面、侧面、3/4 或该构件最有意义的至少两个视角，并制作参考对照。聊天中是否展示图片不影响该步骤。
6. 重新通过组件视觉 QA 后，才能把新指纹写成 `last_build.status=pass`。未渲染的组件不得写成 pass。

## 墙体和洞口

墙体合同应保存立面槽位和每个洞口的参数：

```json
{
  "facades": {
    "front": {
      "grid": {"columns": 5, "rows": 2},
      "opening": {"width_m": 1.2, "height_m": 1.5},
      "random": {
        "enabled": true,
        "seed": 17,
        "keep_probability": 0.75,
        "minimum_pier_m": 0.35
      },
      "overrides": [
        {"slot": "upper_02", "enabled": false},
        {"slot": "lower_04", "width_m": 1.0}
      ]
    }
  }
}
```

删除洞口时重建连续墙体，不在洞口塞补片。新增洞口时只在合法槽位中启用，不侵入墙角、楼层带、门洞或最小墙墩。随机必须可复现。

## 窗体

窗体不直接非均匀缩放。宽高改变后重新计算：

- 主竖向分区和中央细分。
- 框料与中梃厚度。
- 横档数量、行数和总格数。
- 石窗套、外突窗台和玻璃内嵌深度。
- 墙体洞口与窗体安装接口。

如果参数导致框料厚度、格数或风格超出允许范围，生成器必须拒绝该值或请求设计决定。

## 操作

```bash
python scripts/parametric_components.py scaffold <项目目录>
python scripts/parametric_components.py validate <项目目录>
python scripts/parametric_components.py hash <项目目录> <part_id>
python scripts/parametric_components.py refresh-build <项目目录> <part_id>
blender --background <墙体.blend> --python scripts/generate_wall_envelope.py -- \
  --project <项目目录> --parameters internal/wall_variant.json \
  --material-name MAT_wall_envelope_OldStoneWall_v1 \
  --output-blend out/wall_variant.blend
blender --background <窗体.blend> --python scripts/generate_window_assembly.py -- \
  --project <项目目录> --parameters internal/window_variant.json \
  --stone-material <石材> --wood-material <木材> --glass-material <玻璃> \
  --prefix SK_tall_window_parametric_v1 \
  --output-blend out/window_variant.blend
blender --background <阁楼窗.blend> --python scripts/generate_attic_window.py -- \
  --project <项目目录> --parameters internal/attic_window_v1.json \
  --stone-material <石材> --wood-material <木材> --glass-material <玻璃> \
  --output-blend out/attic_window_variant.blend
blender --background <屋面.blend> --python scripts/generate_roof_system.py -- \
  --project <项目目录> --parameters internal/roof_variant.json \
  --roof-material <石板> --gable-material <山墙石材> \
  --ridge-material <屋脊石材> --fascia-material <檐木> \
  --gutter-material <天沟金属> --output-blend out/roof_variant.blend
blender --background <烟囱.blend> --python scripts/generate_stone_chimney.py -- \
  --project <项目目录> --parameters internal/chimney_variant.json \
  --stone-material <石材> --cap-material <帽石> \
  --flue-material <金属> --moss-material <苔藓> \
  --output-blend out/chimney_variant.blend
blender --background <入口.blend> --python scripts/generate_entrance_portal.py -- \
  --project <项目目录> --parameters internal/entrance_variant.json \
  --stone-material <门套石材> --wood-material <门扇木材> \
  --iron-material <暗铁五金> --output-blend out/entrance_variant.blend
blender --background <台阶.blend> --python scripts/generate_entrance_steps.py -- \
  --project <项目目录> --parameters internal/entrance_steps_variant.json \
  --material-name <石材> --output-blend out/entrance_steps_variant.blend
blender --background <壁灯.blend> --python scripts/generate_wall_lantern.py -- \
  --project <项目目录> --parameters internal/wall_lantern_variant.json \
  --metal-material <暗金属> --glass-material <暖玻璃> \
  --output-blend out/wall_lantern_variant.blend
blender --background <木廊.blend> --python scripts/generate_timber_porch.py -- \
  --project <项目目录> --parameters internal/porch_variant.json \
  --wood-material <木材> --roof-material <屋面> --stone-material <石材> \
  --output-blend out/porch_variant.blend
blender --background <门头.blend> --python scripts/generate_entrance_gable_hood.py -- \
  --project <项目目录> --parameters internal/entrance_hood_variant.json \
  --wood-material <木材> --roof-material <屋面> --glass-material <玻璃> \
  --output-blend out/entrance_hood_variant.blend
blender --background <栏杆.blend> --python scripts/generate_porch_railing.py -- \
  --project <项目目录> --parameters internal/railing_variant.json \
  --material-name <深色木材> --output-blend out/railing_variant.blend
blender --background <线脚.blend> --python scripts/generate_stone_facade_trim.py -- \
  --project <项目目录> --parameters internal/stone_trim_variant.json \
  --material-name <石材> --output-blend out/stone_trim_variant.blend
blender --background <植被.blend> --python scripts/generate_vegetation_module.py -- \
  --project <项目目录> --parameters internal/vegetation_variant.json \
  --prefix SK_vegetation_variant --output-blend out/vegetation_variant.blend
```

`refresh-build` 只更新参数指纹，不自动证明新输出合格。生成器仍必须写入新的审计、渲染和 QA 证据。

台阶变体必须按踢面高、踏面深、级数、平台深和鼻线外挑重新计算。鼻线是组件边界的一部分，不得在锁定的整体进深之外额外增加占地；重建后还要重新检查最高踏面与入口门槛的接触，以及台阶与门扇之间的净距。

壁灯变体必须分别控制灯体宽高深、框料、玻璃内嵌、背板、支架外挑、顶盖和尖饰，并允许用 placements 数组镜像或增减实例。材质至少分成深色金属框与暖玻璃两个区域；重建后要重新核对墙面接触、入口门套净距、门头高度和顶盖外挑。

木廊与栏杆变体必须分别保留平台顶标高、台阶接口、门头净高、立柱净宽、坡屋面接触和栏杆中央洞口。将平台板、立柱、梁、椽条、屋面、扶手、横档和栏杆柱分别参数化；重建后检查平台与台阶/门槛接触、柱脚落地、屋面入墙和栏杆不侵入楼梯通道。

入口门头变体必须显式记录屋面类型（单坡、双坡、平挑檐或阳台底面）、檐口与屋脊高、宽度、出挑、坡面和支撑方式。参考模型没有的落地高柱不能作为默认值；改变门头宽度时必须重新检查是否覆盖整段台阶、是否仍能遮住入口，以及墙装支架是否落在实体墙面上。参考中可辨认的檐柱、柱础、柱帽、柱顶横梁、随坡屋面托木、封檐板、托架和山墙三角窗必须在首次合同中登记，并分别拥有可编辑的尺寸、位置、材质和接触约束；不得把已确认的附属结构省略后等待用户逐项补报。

连续石腰线变体必须按四条立面分别重建，并用上下层窗洞的垂直区间验证不穿插。若窗组件已经包含窗套和窗台，石线脚组件不得重复生成同名附件；其范围应明确限定为连续腰线、檐下带或其他尚未被其他组件覆盖的线脚。

## 有机植物

藤蔓、盆栽、花簇、灌木和草本模块的参数合同必须覆盖有机生长逻辑，而不是只锁一个包围盒。默认参数至少包含：

```json
{
  "stem_count": 6,
  "lateral_branches": 0,
  "leaf_count": 160,
  "leaf_density": 1.0,
  "leaf_width_m": 0.022,
  "leaf_height_m": 0.046,
  "leaf_curl_m": 0.01012,
  "leaf_cup_m": 0.00484,
  "stem_radius_m": 0.004,
  "seed": 11
}
```

`lateral_branches=0` 表示由生成器按植物类型和包络自动决定侧枝级数，不是“无分枝”。生成结果必须写 `organic_quality`，并满足 `SKILL.md` 的 7.23 模块级门禁：弯曲渐细枝网、至少三档叶色、足量细叶、叶尖芽、冠层填充和非漂浮基部。`seed`、密度、叶尺寸或包络变化后，必须重建独立源文件与 GLB，重新渲染正面、侧面、3/4 和近景，并重新核对整栋装配及正面可见性。

程序化植物的预期拓扑是“闭合花盆/土壤支撑面 + 开放薄叶片”。开放叶片边界必须记录为预期，不能把全部边界边误报成破洞；无线边、零面积面、异常尖刺和未连接叶柄仍是失败项。
