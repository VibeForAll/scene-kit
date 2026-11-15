# 整栋三维参考模型与组件执行路线

## 强制规则

流程顺序固定为：

1. 根据选中设计合同生成一个整栋三维参考模型。
2. 为将要落地的组件登记参数化合同，明确生成器、参数、约束、输出和参数指纹。
3. 验证参考模型质量，满足实际网格、主体体量、屋顶、洞口和附着关系要求。
4. 使用统一缩放和固定共享中心的相机轨道，从模型实际渲染十视图并验证可信度。
5. 生成网格连通岛分段报告，建立整栋空间关系、组件特征映射和可追溯候选岛。
6. 基于三维参照和多视图完成拆件、材质分区和组件边界。
7. 最后才为每个组件选择执行方式：Blender 重建、模型库复用或有机构件的 AI 3D 生成。

不能再从“这个组件用某个 AI 厂商还是 Blender 直接生成”开始。组件执行路线是整栋参考模型完成后的后置步骤，不能跳过整栋模型直接生成单件。`ai_3d` 是执行类别，具体提供方在提交前选择。

整栋参考模型的记录结构见 [data-model.md](data-model.md#componentsreference_models)。最低要求：

- 选择一张特征最完整的 3/4 视图；若 Provider 支持同一对象多图，优先使用正、背、左、右四视图。
- 记录 `input_mode`、Provider、模型、区域、质量、Task ID、原始面数和减面后面数。
- 保存原始与减面 Blender 文件、GLB、审阅图、输入对照和网格审计。
- `reference_only=true`，禁止进入最终导出和装配。
- 默认只做统一缩放；非均匀拉伸必须有明确三轴尺寸、使用授权和原因记录。
- 保存 `reference_quality`，检查真实网格、主体体量、屋顶、主要洞口和附着关系。
- 保存 `camera_rig`，固定共享中心、正交尺度、分辨率和十个视角相机；不得逐视图重新取景。
- 保存 `derived_view_validation`，区分可靠视图与低可信视图。顶部/底部通常只作辅助，不能作为主要组件识别来源。
- 保存 `feature_extraction.segmentation_report`，为每个组件记录 `mesh_island_ids`、深度、突出、附着、退进和遮挡观察。
- 网格连通岛只提供候选位置，不能自动成为语义组件；至少两个模型派生有效视图确认后才能写下最终拆件结论。
- `analysis_ready=true` 后才能拆件与生成组件，且它必须同时满足参考质量、归一化、相机轨道、视图验证和组件映射门禁。

整栋参考模型是组件几何、边界和拆件的主三维基准，但不是最终网格。模型派生十视图应作为组件识别主输入；原始十视图用于校验模型幻觉、缺项和比例问题，并补充可靠材质与微细纹理。不能用原始图反向修改整栋模型几何。若派生视图之间互相矛盾，先回查相机轨道、模型轴向比例和网格分段，再判断是否为参考模型本身的推断错误。

## 组件执行评估

整栋参考模型和组件映射通过后，每次组件执行评估必须写入 `route_assessment`：

```json
{
  "status": "approved",
  "recommended_route": "blender_procedural",
  "selected_route": "blender_procedural",
  "decision_summary": "窗口重复 21 次，窗格和接口精确，Blender 可一次参数化后实例化。",
  "repeat_count": 21,
  "precision_demand": "exact",
  "blender_effort": "low",
  "ai_3d_expected_benefit": "low",
  "ai_3d_token_risk": "high",
  "reference_quality": "high",
  "evidence": [
    "窗格和框厚由尺寸合同锁定",
    "重复实例超过 5 个",
    "自由区只有窗棂细节"
  ]
}
```

当组件路线为 `ai_3d` 时，还必须同时写明它如何使用整栋参考模型、参考充足性和面数预算。旧项目的厂商特定路线名继续兼容读取；新项目统一记录 `ai_3d`，并在 `provider_selection` 中记录实际候选和选择：

```json
{
  "reference_model_id": "whole_building_reference_01",
  "provider_selection": {
    "status": "pending",
    "candidates": [
      "blender_mcp_generator",
      "user_external_platform",
      "model_library"
    ],
    "selected_provider": null
  },
  "reference_sufficiency": {
    "status": "pass",
    "usable_views": [
      "preview/references/part/appearance_front.png",
      "preview/references/part/appearance_side.png"
    ],
    "has_front": true,
    "has_side_or_three_quarter": true
  },
  "triangle_budget": {
    "target_total": 35000,
    "hard_max": 60000,
    "basis": "实时场景近景预算，扣除实例后的单件上限"
  },
  "low_poly_strategy": {
    "provider_quality": "standard",
    "provider_face_limit_exposed": false,
    "postprocess": ["decimation", "retopology"],
    "preserve": ["silhouette", "UV seams", "material boundaries"]
  }
}
```

精确门、窗、栏杆和格栅至少需要正面与一个侧面/45 度参考。只有一张局部图时，参考不足以约束框料层级和安装厚度，应停止 AI 3D 路线。单图可以用来支持有机小件的风格判断，但不能当作精确重复结构的全部依据。

所有组件的 `reference_consensus` 都必须先通过。即使路线是 Blender 参数化，也至少需要模型派生组件裁剪、两个原始图校验视角和材质样本。生成后优先与多个模型派生裁剪比较，再用原图确认材质和清晰微细节。

任何路线还必须通过 `boundary_review`。如果侧面或 45 度视图显示窗台、托架、披檐、盖板或安装返口，它们应纳入当前组件的真实包围盒和附件清单；不能只生成正面平面后再由墙体或其他组件临时补贴。

提供方的质量档名称不等于已经设置目标面数。无论是 Blender MCP 内置 AI 生成器、外部平台还是 API，只要无法从实际接口确认目标面数或面数上限，就记录 `provider_face_limit_exposed=false`。生成后在 Blender 中减面或重拓扑，检查轮廓、UV 接缝、材质边界和目标视角，未达到 `triangle_budget` 不得通过。

## 优先 Blender

以下条件越多，越应使用 Blender：

- 精确尺寸、洞口、接口、原点或朝向必须匹配。
- 组件重复出现，尤其是 5 个以上实例。
- 可由基础几何、Bevel、Solidify、Array、Mirror、Boolean 或 Geometry Nodes 建立。
- 拓扑、UV、游戏面数和导出需要严格控制。
- 自由造型区很少，AI 只能产生额外的不可控几何。
- 参考图分辨率不足以清楚描述内部细节。
- 精确结构只有一个可用视角，无法约束侧厚或框料层级。
- 已有模型库或先前通过的同类资产可复用。

典型组件：墙段、楼板、基础、屋面、规则窗、标准门、台阶、檐沟、栏杆、简单壁灯和标准线脚。

## 优先 AI 3D

只有同时满足以下多数条件时才选择 AI 3D；具体厂商另按当前工具、成本和授权选择：

- 造型具有明显雕刻、有机分支或手工不规则价值，Blender 手工成本高。
- 该组件通常不应重复几十次，或可先生成一次再实例复用。
- 主要轮廓和设计语言可从单件或局部参考中清楚辨认。
- 接口与结构部分可以独立由 Blender 控制，AI 结果可本地修整。
- 生成后能够检查网格完整性、法线、UV、材质和安装面。
- 付费生成带来的造型价值明确高于额外清理成本。
- 已写清面数预算和本地减面/重拓扑方案。

典型组件：复杂木雕、石雕徽章、独特柱头、铁艺花纹、代表性灌木/花簇、藤蔓模块、特殊场地点景。



## 小尺度有机构件的文生 3D 例外（7.16）

默认仍然是“有参考图先图生 3D，纯文字是最后方案”。但藤蔓、花簇、盆栽、苔藓等小尺度有机构件经常只有在境裁剪（同框包含石墙、窗户、地面或花盆）。把这种裁剪交给图生 3D 时，提供方倾向于把环境一起建成网格，事后无法可靠拆回单体；程序化重建又容易退化成扁平贴图叶片加木棍枝条，造型抽象。满足下列任一信号时，该组件允许并应优先选择纯文生 3D：

- `reference_pack` 没有隔离单体参考（`isolated_asset_available=false` 或缺失），可用图片全部是在境裁剪。
- 已有图生 3D 尝试因串入建筑/环境被标记 `ai_3d_attempt.result=not_used/failed`，原因包含 context/building/surrounding 或“串景/串入建筑”。
- 组件 `asset_class=vegetation` 或属于 `ORGANIC_TYPES`，且接口尺寸可以完全由 Blender 后处理锁定。

`generation_route_audit.py` 对每个 AI 组件输出 `input_mode_guidance`：有机且只有在境参考或图生失败时给出 `preferred=text_to_3d`；已有隔离单体或非有机构件仍推荐 `image_to_3d/multiview_to_3d`。该字段是诊断建议，最终输入模式仍需写入 `route_assessment` 并取得用户当次确认。

### 文生 3D 提示词合同

- 正向必须先声明“one isolated <asset> on a plain neutral background”，再描述枝干走向、叶片/花簇形态、扁平贴墙轮廓、根部附着和 PBR 材质，最后声明“the asset alone is the subject, centered as a standalone 3D asset”。
- 负面必须显式排除：wall, building, house, window, stone, pot, planter, ground plane, soil, flowers/grass/tree（按构件取舍）, landscape, people, text, labels, watermark, extra objects, plastic/glossy toy material, cartoon look。
- 不写绝对尺寸；尺寸在 Blender 中按锁定包络校准。
- 单次只提交 1 个候选、不做付费重试；提示词超过提供方上限（如 Tripo 1024 字符）时先精简措辞，不拆成多次生成。

### 生成后强制后处理

1. 导入后先确认场景只有单体网格、无环境几何，并记录原始三角面数。
2. 烘焙旋转到网格数据，使宽面跨 X、深度跨 Y、高度跨 Z；不要只改对象旋转。
3. UV 边界约束的 Collapse 减面到 `triangle_budget.target_total`，超出硬上限必须二次减面。
4. 均匀缩放拟合锁定高度，再单向压缩深度到 `locked.depth_m`，验证完整包络不超限。
5. 固化底部中心原点，底座落在 z=0，前向保持 -Y。
6. 从 GLB 容器无损提取 Color/ORM/NormalGL 图集，外置到项目 `textures/` 并保持节点引用；需要向参考色调收敛时优先加非破坏性 HSV 节点，不改写原始贴图文件。
7. 删除减面残留的无线边和游离点；开放壳边界边是叶片等薄型植物的固有形态，记录为预期发现，不做实体化封装。
8. 补建正交审阅相机，重渲染正面、侧面、3/4 和近景四视图，制作参考对照合页并跑 `blender_audit.py` 与几何审计。

### 记录要求

- `generation.input_mode="text_to_3d"` 且存在参考图时，`generation.text_only_reason` 必填，说明在境参考为何不能直接图生 3D。
- `ai_3d_attempt` 记录 provider、model、task_id、input_mode、提示词存档、原始面数、最终面数、`result=used` 与采用理由；失败的图生尝试保留为历史记录不删除。
- 参数化合同使用 `generator_type=vegetation_cluster`、`implementation=ai_wrapper`、`variant_policy=wrapper_only`，`parameter_document` 记录任务 ID 与包络参数，`last_build.parameters_hash` 由 `canonical_contract_hash` 重新计算。
- 文生 3D 不豁免任何质量门禁：几何、材质、贴图映射、多视图和组件 QA 与图生路线完全一致。

## 路由门禁

`route_assessment.status` 必须为 `approved`。`recommended_route` 与 `selected_route` 必须一致。

当路线为 `ai_3d` 时：

- `precision_demand` 不能为 `exact`。
- `ai_3d_expected_benefit` 不能为 `low`；旧项目的厂商特定收益字段仅作兼容。
- `reference_quality` 不能为 `low`。
- 组件 `decision` 必须为 `ai_3d`。
- 新记录应包含 `provider_selection`。提供方未选定时可保持 `pending`，但不得提交实际生成任务。

当路线为 `blender_procedural` 或 `blender_manual`：

- 组件 `decision` 必须改为参数化、复用或相应的 Blender 资产方式，不能继续保持 `ai_3d`。

当路线为 `library`：

- 组件 `decision` 必须为 `library`，并需要有用户确认的库资产。

## 辅助脚本

先建立并分析整栋参考模型，再运行组件执行评估：

```bash
python scripts/generation_route_audit.py <项目目录>
```

只检查一个组件：

```bash
python scripts/generation_route_audit.py <项目目录> --part <part_id>
```

脚本输出 `internal/generation_route_review.json`。如果整栋参考模型尚未 `analysis_ready`，报告状态为 `blocked_reference_model_required`，此时组件评分只是预备信息，不能开始生成。

参考模型门禁通过后，报告才给出各 `ai_3d` 组件的 Blender/AI 3D 评分、实例数、自由区、token 风险和推荐执行路线。脚本不预设厂商，不自动修改 `components.json`，也不批准付费生成。

## 提交组件 AI 3D 任务前

1. 确认整栋参考模型 `analysis_ready=true`，且当前组件已有三维特征映射。
2. 运行组件执行评估。
3. 确认推荐路线是 `ai_3d` 或兼容的具体 AI 路线，并在 `route_assessment.reference_model_id` 引用整栋参考模型。
4. 根据当前环境选择实际提供方，展示主生成图、提示词、模型端点、候选数和成本。
5. 对精确构件确认至少正面与侧面/45 度可用参考。
6. 确认 `triangle_budget` 和 `low_poly_strategy` 已填写。
7. 得到用户本次付费确认后再提交。
8. 生成或参数化建模完成后，运行 `blender_audit.py` 的贴图映射审计；在 `qa.material_review.texture_audit` 通过前不得把组件标记为可用。

若推荐路线为 Blender，不得先做一次“便宜的 AI 3D 试试”。这类试用会消耗 token，并产生不符合精确接口和拓扑要求的网格。

旧项目中的厂商特定路线名和收益/风险字段继续可读，但迁移后的新记录以 `ai_3d` 和 `ai_3d_*` 为主。某个提供商当前恰好可用，不构成默认推荐。
