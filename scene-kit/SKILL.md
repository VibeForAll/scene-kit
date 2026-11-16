---
name: scene-kit
description: 以概念图和整栋参考模型优先的方式设计建筑，为墙体、屋面、门窗、栏杆、台阶、装饰和植物建立可重建的参数化组件合同，再完成多视图审计、材质贴图校验、装配与精修。适用于建筑、街区和既有项目的组件化设计、变体生成、有机植物、面片精修与资产复用；不用于角色、纯贴图绘制或单张平面图。
metadata:
  version: "7.23"
  updated: "2026-11-16"
  workflow: "reference_model_primary_component_reconstruction"
  short-description: "参考模型优先、数量前置、参数组件、背面连接、实时遮挡、有机植物与材质门禁"
---

# Scene Kit 7.23 · 参数化组件、有机植物与逐版本质量门禁

## 目标

先让概念图决定“建筑是什么样”，再生成整栋三维参考模型，并由模型派生十视图。后续组件识别、空间关系、边界和拆件以参考模型为主；原始十视图用于验证模型是否离谱，并补充模型没有可靠表达的材质和微细节。

整栋 AI 3D 模型是 `reference_only` 三维基准，不是最终交付网格。模型派生视图是组件识别和拆分的主图；原图不再用来反向修改整栋模型几何。最终精确组件仍需重拓扑或参数化重建。

## 固定分工

- 文生图：探索整栋气质、配色、材料、构图、门窗和装饰语言。
- Blender：记录关键尺寸、门窗洞、体量关系、接口、实例、装配、最终面片与构造逻辑精修、验收视图和导出。灰盒只保留判断空间关系所需的信息。
- AI 3D 整栋参考：从特征最完整的单视图或多视图先生成一个整栋三维基准模型，并由它派生标准十视图。
- AI 3D 单件：只对整栋参考模型确认后仍有独立造型价值的有机或雕刻构件生成单件资产。
- 复用与参数化：承担重复墙段、楼板、台阶、标准门窗和结构件，不重复付费生成。

所有尺寸的最终权威是项目里的结构化尺寸合同，不是概念图或生成图中的像素比例。

## 质量与效率

- 先满足尺寸、接口、可构建和交付平台预算等硬约束；此后按“目标视角效果匹配与表面质量 → 其他优化 → 渲染时间和 token 消耗”取舍。时间、额度和重试次数不是放过可见 `blocker/high` 缺陷的理由。
- 组件正式生成前，先完成通过门禁的整栋三维参考模型。参考模型必须保持 `reference_only=true`，减面后用于多视图归一化和组件特征映射。
- 7.13 把“参考模型本身是否可用”提前为独立门禁：先验证网格、主体体量、屋顶、洞口和附着关系，再验证统一缩放、固定共享中心的正交相机轨道和十视图可信度。不能先渲染视图、再假设模型几何正确。
- 默认保持模型原始轴向比例，只允许统一缩放。非均匀拉伸只有在用户明确给出三轴尺寸并确认使用该尺寸时才可以执行，且必须记录原因；不能用估算占地把模型压成“看起来正确”的比例。
- 顶视和底视对开放壳体、无完整楼底的 AI 模型天然不可靠。它们可以是低置信辅助视图，但主要组件识别必须依赖正面、背面、左右侧和四个 45 度视图。
- 7.14 把贴图投影作为每次组件生成的强制门禁。只看颜色和粗糙度不够；必须检查贴图是否加载、使用何种投影/UV、真实平铺尺寸、法线和粗糙度是否同步，以及正面、侧面和 3/4 视角是否出现方向错误或拉伸。
- 7.15 要求每个组件都有参数化合同。合同记录生成器、可编辑参数、约束、材质绑定、输出对象和上一次构建的参数指纹。参数或材质变化后，旧构建和旧审计立即失效，必须重新生成并完成几何、材质、贴图和多视图检查。
- 7.18 要求整栋装配和精修阶段执行正视图组件可见性审计。不能只比较包围盒；必须为每个组件实例渲染正面透明轮廓遮罩，叠加当前正视图，并检查实际遮挡、插入、悬空和相互穿插。结构上相邻的构件可以进入允许关系表，但塔楼/窗、门/装饰、同层洞口等非预期重叠必须修复后才能通过。
- 7.19 要求正视图审计以实时 `.blend` 中的组件实例为权威，不从旧 `assembly.json` 的根对象列表推断覆盖面。审计前必须核对记录实例数与实时实例数、各组件实例数、立面层数窗口数量和植物可见性；立面有明确槽位合同时，正面一/二层的窗数、门轴跳过规则和墙洞合同必须硬校验。Blender 自动生成的 `.001` 名称或过期根对象不得造成静默漏检。旧对象记录只能用于映射辅助，不能作为审计通过的证据。
- 7.20 要求把数量识别前置到拆件与建模之前。先从参考十视图和整栋参考模型建立 `components.quantity_audit`，按立面、楼层、屋顶类型和重复附件分别计数，再开始组件实现。窗门必须记录每个立面的逐层数量矩阵，主屋顶、老虎窗/阁楼小屋顶、塔帽和门廊屋顶必须分开计数；烟囱的石柱、石帽和金属烟管也必须分开计数，用户明确删除的附件记录为 `expected=0`。总数必须由分项相加得出，不能用“约”“若干”或一个总数代替分项。实时装配数量、参数合同和数量审计不一致时，不能进入装配通过或最终验收。
- 7.21 要求前置立面构件和屋面构件必须具有可解释的背面、体积和宿主连接。窗、门、老虎窗/阁楼窗、凸窗、阳台、门廊、雨棚、烟囱和其他附着物不能只做正面窗片或屋顶片；正面可见的构件必须在侧面和 45 度视图中能解释其墙体、侧板、背板、安装面，以及与主墙/主屋面的接触或嵌入关系。屋顶上的窗组必须有对应老虎窗体量与主屋面连续连接。审计写入 `components.attachment_integrity_audit`，禁止用“正面看着有”替代可建造的三维连接。
- 用户指出的每个可见错误都必须回灌为可执行门禁：漏构件先修 `visual_inventory`、`detail_audit` 和 `quantity_audit`；遮挡/干涉先修当前实时轮廓审计；颜色对但材质错时重新打开材质与贴图门禁；尺寸变更后重新核对独立组件源与整栋装配，而不是只改截图或在下一次任务里依赖记忆。
- AI 3D 生成提供方不预设。当前可用插件、外部平台、API、模型库或用户指定的服务都可以成为候选；路线评估比较的是 Blender/复用与“AI 3D”这一执行类别，具体厂商在提交任务前按能力、成本、授权和接口另行选择。
- 整栋参考模型通过后，再依据多视图和三维深度完成拆件；组件的 AI 3D/Blender 执行方式评估是拆件后的后置步骤，不是流程起点。
- 默认每个构件先做一个候选。重复构件通过镜像、实例和材质复用完成；只有候选存在可确认的轮廓、构造或风格缺陷，且本地修面无法达到目标时，才申请有明确目标的重试。新的付费生成仍需用户确认。
- 能通过 Blender 修复的比例、原点、接口、破洞、法线、拓扑、材质和装配逻辑问题，必须先在本地修到位。不得为了节省时间或 token 跳过最终精修。
- 修复后必须重新执行当前版本的静态审计，并重新渲染受影响的材质 QA 视图，不能沿用修复前截图。
- 生成前完成账号区域、API 根地址、Key 和余额检查，避免失败尝试消耗额度。

完整规则见 [cost-and-repair.md](references/cost-and-repair.md)。

### AI 3D 提供方选择

`ai_3d` 是执行类别，不是厂商名。不同的内置生成器、外部 API、用户网页端和模型库都只能作为当前环境中的候选。不要因为技能示例、某个 MCP 当前可用或历史上成功过一次，就把某个厂商写成默认或必经路线。

提交 AI 3D 前读取当前环境和用户授权，记录：

- `provider_selection.candidates`：当前真实可用的提供方。
- `provider_selection.selected_provider`：本次选择的提供方；未选择时保持 `pending`。
- `provider_model`、区域、质量档、面数接口、成本和交付格式。
- 为什么该提供方比 Blender、复用或其他 AI 3D 候选更合适。

旧项目中的厂商特定路由和收益/风险字段允许兼容读取，但新记录使用 `ai_3d`、`ai_3d_expected_benefit` 和 `ai_3d_token_risk`。兼容旧字段不等于把任何厂商设为默认。

### 材质 QA 渲染与聊天展示

材质与贴图渲染是每个组件的强制 QA，不因 token、时间或用户只说“继续”而省略。每个组件完成几何后至少渲染两个视图，新项目优先保存到 `assets/preview/qa/<part_id>/`，制作参考对照，补齐 `qa.material_review` 后才能标记 `pass`。旧项目的 `preview/qa` 可在交付整理时迁移。

“是否在聊天中展示图片”与“是否执行 QA 渲染”是两件事：

- 默认把渲染保存在项目中，最终回复只给摘要和文件链接。
- 多张图片、全分辨率近景、重复发送或高成本展示渲染属于可选展示，可先询问用户是否需要。
- 用户不需要逐张看图，不代表组件可以不渲染、不比较或不做贴图拉伸检查。
- 需要用户判断设计时，优先制作一张压缩对照图，而不是连续发送多张原图。

`scene.json.render_policy` 只记录展示偏好，不能关闭强制材质 QA。默认值为：

```json
{
  "qa_render": "required",
  "display_mode": "summary_only",
  "display_requires_confirmation": true,
  "extra_presentation_renders_require_confirmation": true
}
```

## 开始前

1. 已有项目时先读取 `progress.json` 和当前阶段产物。
   7.1–7.14 项目允许继续读取；进入 `COMPONENTS` 门禁前补齐 `reference_models`、`detail_audit` 与两项细节检查。7.8 的窗门等精确构件还必须补齐 `fine_structure_review`；7.9 的所有组件在建模或生成前都必须补齐 `reference_consensus`；7.10 还必须通过 `boundary_review`。7.12 以参考模型派生十视图作为主要识别输入，原图只做校验和表面细节补证；7.13 要求 `reference_quality`、固定 `camera_rig`、`derived_view_validation`、网格分段报告和组件 `mesh_island_ids`；7.14 要求每个已构建组件的 `qa.material_review.texture_audit` 通过；7.15 还要求每个组件具有当前参数指纹有效的 `parametric_contract_id`；7.20 要求 `components.quantity_audit` 通过，关键特征数量和分项矩阵确认后才能拆件或生成；7.21 要求 `components.attachment_integrity_audit` 通过，附着构件的背面、体积和宿主连接可解释。`analysis_ready=true` 后才能拆件或生成。
2. 新项目使用脚本初始化，不手工复制旧项目：

   ```bash
   python scripts/scene_kit.py init <项目目录> --name <项目名>
   ```

3. 每次改变状态或资产记录后运行：

   ```bash
   python scripts/scene_kit.py validate <项目目录>
   ```

4. 只在当前阶段完成后使用 `advance`。用户确认、澄清或提问不等于自动进入下一步。

## Blender 执行基线

开始操作已有 `.blend` 前，先读取真实场景：文件路径、Blender 版本、场景单位和比例、对象/集合/相机/灯光/材质/外部图片状态，以及当前 revision 的基准截图。已有模型默认在原文件上修改，不因任务描述简单就从头重建。

Blender MCP 可用时直接执行和查询场景，不只描述 UI 操作；MCP 不可用时才给最小手动步骤。破坏性操作前保存工作副本或版本化备份。较大的建模、材质、灯光、装配或修复之后重新查询场景；没有工具结果时，不得声称已经改动、渲染或导出。

新建项目使用 `SK_COL_Structure`、`SK_COL_AI`、`SK_COL_Library`、`SK_COL_Ornament`、`SK_COL_Vegetation`、`SK_COL_Site`、`SK_COL_Finish`、`SK_COL_Lights`、`SK_COL_Cameras`、`SK_COL_Review`、`SK_COL_Reference` 和 `SK_COL_Debug` 分离模型、审阅物与临时物。旧项目不为了整齐而强制重命名。

阶段审阅和最终交付必须使用当前 revision 的截图，至少覆盖正交比例视图、hero 3/4、关键近景和参考对照；结构问题区域再补线框或材质检查。完整执行、命名、截图、网格审计和导出检查见 [blender-production.md](references/blender-production.md)。

### 建模扩展预检

在参数化建模、AI 3D 后处理、装配或精修前，运行：

```bash
blender --background --python scripts/ensure_modeling_extensions.py -- --install --output <项目目录>/internal/toolchain.json
```

必须确认报告 `ready=true`。默认扩展为 Archimesh、MeasureIt、3D Print Toolbox、LoopTools、Edit Mesh Tools、CAD Sketcher、Surface Diagnostics 和 CurioMesh。脚本从官方扩展目录按平台选包、校验 SHA-256、安装并启用。缺少扩展时先安装；安装失败时停止依赖该扩展的建模，不得声称可用。详细边界见 [modeling-extensions.md](references/modeling-extensions.md)。

插件是效率工具，不是质量结论。Archimesh 生成的窗门、CurioMesh 的自动重拓扑和各类清理结果都必须重新按项目锁定尺寸、多视图和构造逻辑验收。

## 阶段

| 阶段 | 阶段名 | 核心产物 | 进入下一阶段的条件 |
|---|---|---|---|
| 1 | `BRIEF` | 设计目标、空间边界、关键尺寸、交付目标 | 关键约束清楚 |
| 2 | `CONCEPTS` | 3 个真正不同的概念方向、十视图提示词包和一致性审查 | 用户选中方向且十视图一致性通过 |
| 3 | `DESIGN` | 设计语言、风格合同、材质与配色规则 | 用户认可设计方向 |
| 4 | `COMPONENTS` | 整栋三维参考模型、组件特征映射、建筑组件、细节盘点、多视图拆件审查和自由区 | 参考模型可分析、用户认可拆分，细节完整且可连续装配 |
| 5 | `REFERENCES` | 每个 AI 单体的中性轮廓、风格参考、双语提示词和裁剪图审查 | 用户确认参考包，拆件图片完整 |
| 6 | `GENERATION` | 逐件 AI 3D 模型与基础检查 | 所有必需单体可用 |
| 7 | `ASSEMBLY` | 归一化、实例、整栋 Blender 骨架与基础视图 | 整栋空间关系完整 |
| 8 | `FINISHING` | 面片、法线、材质、灯光、接缝、构造逻辑精修与最终对照 | 智能检查通过，无未修复 blocker/high |
| 9 | `REVIEW` | 当前版本最终图和用户验收记录 | 用户明确通过 |
| 10 | `COMPLETE` | 导出和项目收尾 | — |

阶段细节见 [workflow.md](references/workflow.md)。

## 概念优先

概念阶段同时提出 3 个方向。方向必须在体量处理、立面节奏、材料语言或构件设计上有明显差别，不能只换颜色。

每个方向至少包含：

- 一句核心设计主张。
- 完整英文和中文概念提示词，以及负面提示词。
- 十张整栋视图的完整中英文提示词，顺序固定为：上、下、左、右、前、后、左前侧 45 度、右前侧 45 度、左后侧 45 度、右后侧 45 度。
- 每张图独立生成一张，不得用拼图、九宫格或一张多视图合页代替。
- 门窗、栏杆、入口或屋顶等关键构件细节图，只在选中方向后作为额外补充。
- 哪些空间关系必须保留、哪些造型可以自由发挥。

提示词只描述相对比例、设计语言和构图；精确米数写入尺寸合同。概念图的生成、选型和风格合同见 [concept-production.md](references/concept-production.md)。

每个方向都必须自动生成一份可直接复制的纯文本提示词包，默认放在 `concepts/<direction_id>/prompts.txt`。在 AI 生图阶段，不能只给 3 个视图；提示词包必须完整给出十张独立视图及固定顺序：`top`、`bottom`、`left`、`right`、`front`、`back`、`front_left_45`、`front_right_45`、`back_left_45`、`back_right_45`。每张图都包含中英文完整正向与负向提示词、明确镜头、同一栋建筑的一致性规则、推荐 3:2 横图比例和单图槽位的分批执行说明。使用：

```bash
python scripts/scene_kit.py prompts <项目目录>
```

在聊天中展示概念方向、准备文生图或把任务交给用户的外部生图工具时，必须明确列出十个视图及顺序，并给出完整可复制的十段提示词；不能只说“已生成提示词文件”或只展示其中三张。完整英文和中文段落可以分段发送，但不得省略、调换顺序或用一张多视图合页代替。

用户在比较方向时，每个方向至少要有足够判断设计语言的图片和完整十视图提示词包；用户选定方向后，只要求该方向实际形成上、下、左、右、前、后及四个 45 度斜角的十张独立视图，再进入设计阶段。关键构件细节图是额外补充，不替代十张标准视图。未选方向不要求继续生成十张图片，后续工作也不得反复催促用户补齐未选方向。

十张图存在不等于一致。进入设计阶段前必须逐张对照，确认它们仍是同一栋建筑、同一体量比例、同一屋顶与构件语言，并且没有无法建造的矛盾。审查结果写入选中方向的 `consistency_review`；任一关键视图矛盾时先修正或重新生成，不能带着矛盾进入拆件。

概念数据使用 `view_paths` 记录十张图的实际路径。选中方向进入设计阶段前，脚本必须校验十张图全部存在；不能用旧版 `hero_path`、`front_path`、`details_path` 三张图绕过。

用户选中方向后，先把设计语言固化为 `internal/design_contract.json`。后续每个单体的提示词必须原样包含其中的固定正向、负向和视角段落。

提交设计合同时，必须在聊天中同时给出人类可读摘要，不能只给 JSON 链接。摘要开头先说明合同用途：它固定概念图中选定的设计语言，约束后续 Blender 拆分与尺寸落实、单件提示词和最终装配；它不是整栋图生 3D 的硬几何模板，也不是施工图。摘要再说明选中方向、核心主张、体量关系、门窗与屋顶规则、材质配色、构件自由边界和原始约束。

## 整栋三维参考模型优先

设计合同认可后，在拆件前先建立整栋三维参考模型并写入 `components.reference_models`：

1. 从选中方向中挑选特征最完整的一张视图。优先 3/4 视图：同时能看到主立面、入口、屋面和至少一个侧向体量；纯正视图缺少深度，纯侧视图缺少立面构件关系。
2. 如果生成器真实支持同一对象的多视图输入，优先使用正面、背面、左侧、右侧四张；如果只支持单图，必须如实记录 `input_mode=single_image_to_3d`，不能把其他视图说成参与了同一次生成。
3. 使用真实 Provider、模型、区域和质量档位生成。默认先做一个标准质量候选，不以数量换准确度。
4. 原始模型保存后做参考级减面，记录 `raw_triangles`、`decimated_triangles`、`max_triangles` 和 `decimation_method`。减面目标是让 Blender 可操作，不要求它成为最终拓扑。
5. 把模型标记为 `reference_only=true`，沿用独立集合和审阅材质；它不得进入最终导出、组件实例或模型库成品。
6. 从归一化模型渲染固定十视图，写入 `model_derived_views`：上、下、左、右、前、后和四个 45 度。它们是后续组件识别和拆件的主图。
7. 使用同一模型中心、同一正交尺度、同一分辨率和固定视角定义渲染十视图；把每个相机的名称、位置、方向、上轴和正交尺度写入 `camera_rig`。固定十视图的相机不得逐视图重新取景；补充诊断相机不属于这组固定相机。
8. 先检查视图是否存在、是否非空、是否同一建筑、比例和取景是否一致，再把结果写入 `derived_view_validation`。只允许 `reliable_views` 参与主要拆件；低可信视图必须写明原因。
9. 对每个组件记录模型派生十视图中的深度、突出量、遮挡、前后关系、安装面和附属结构，形成 `feature_extraction.component_map`，并用 `mesh_island_ids` 追溯网格候选。
10. 原始十视图只做校验：检查派生视图是否明显变形、丢失主要特征或产生不合理结构，并补充可信的材质和微细纹理。不能用原始图反向牵动整栋模型的几何。
11. `analysis_ready=true` 才能开始拆件和组件实现。它要求参考模型 `status=pass`、`reference_quality.status=pass`、`normalization.status=pass`、`camera_rig.status=pass`、`derived_view_validation.status=pass`、`feature_extraction.status=pass`、十张派生视图齐全，并覆盖当前全部 `part_id`。

整栋参考模型是组件几何和边界的主基准，但仍是由一张或多张视图推断出的三维假设，可能把窗棂、窗台、檐口和墙体融在一起。模型派生视图之间可以互相确认深度和遮挡；原始图只用于识别模型明显的幻觉、缺项或材质错误，并记录为校验分歧。

### 细节不清时的补充诊断视角

标准十视图仍是必查主视图和交付门禁。若某个局部特征在十视图中仍不明确，例如屋顶与墙体交接、被遮挡的背面、门窗深度、栏杆连接、附着结构或重复构件数量，可以从同一归一化参考模型额外渲染局部近景或斜向诊断视角。补充视角用于识别和交叉确认，不替换、增补或重排 `model_derived_views` 的固定十视图。

- 补充诊断视角可以只作为临时检查，不要求保存或进入 README、参考包和最终交付；不因保存成本而跳过本应执行的识别检查。
- 若保留图片，放在明确的诊断目录并标记为非 canonical 证据；若临时删除，只记录“由哪个补充视角确认了哪项特征”的简短结论和用途，不虚构资产路径。
- 将补充视角观察与至少一个既有十视图或原始素材交叉确认。仍冲突时写入 `unresolved`，不能仅凭一个新机位直接改写组件数量、边界或宿主连接。

### 参考模型质量与网格分段

`reference_quality` 至少检查：

- `mesh_exists`：减面后的目标对象真实存在、可渲染并且不是空集合。
- `main_massing_complete`：主体层数、塔楼或侧翼等主要体量没有整块缺失。
- `roof_present`：屋面、屋脊和主要坡面可辨认，未把屋面截成薄片。
- `openings_present`：门窗洞口和主要框套没有被模型整体融死。
- `attachment_relations_legible`：烟囱、门廊、窗台、檐口、台阶等能看出突出、退进和连接方向。

同时把已知局限写入 `limitations`，例如单图不可见部分属于推断、壳体开放、网格碎片多、模型深度与项目合同尺寸不同。质量通过不等于模型是水密或生产拓扑。

运行参考视图脚本时，优先使用：

```bash
blender --background <参考模型.blend> --python scripts/reference_model_views.py -- \
  --object <对象名> --output-dir <项目目录>/preview/reference-models/canonical-vN \
  --uniform-scale <统一缩放> --ortho-scale <正交尺度> --blend-out <输出.blend>
python scripts/reference_feature_scan.py <项目目录>/preview/reference-models/canonical-vN/reference_model_report.json \
  --output <项目目录>/internal/reference_feature_candidates.json
```

网格连通岛报告是三维定位候选，不是语义组件。`window_candidates`、`door_candidates` 和 `chimney_candidates` 只提供空间与尺寸线索，可能包含墙体碎片、瓦片、栏杆段或同一构件的多个断开块。扫描脚本还会按三维包围盒邻接关系输出 `candidate_clusters`，用于把同一窗框或烟囱的碎片收拢为空间候选组；聚类仍然不是语义判定。必须再用模型派生的至少两个有效视图确认身份、范围、附着和数量，才能写入最终 `component_map`。禁止把一个候选岛或一个空间聚类直接声明为完整窗、门或烟囱。

组件实现方式在整栋参考模型和模型派生组件参考完成之后才决定：精确、重复或可由 Blender 稳定构建的组件优先重建；有机雕刻和植物可以作为 AI 3D 单件候选，但是否生成、使用哪个提供方仍由当前任务决定。不要再用“原始十视图拆件，再判断某个 AI 厂商还是 Blender”作为流程起点。

### 数量优先清点

在拆件、编写组件生成器或装配之前，先完成关键特征数量清点并写入 `components.quantity_audit`。这一步回答“有多少”，不受后续几何实现方式影响。

必须分项记录：

- 门和窗：每个立面的下层、上层数量以及合计；有门轴时记录该轴位是否跳过。总数必须等于四面分项之和。
- 屋顶系统：主屋顶、阁楼窗小屋顶/老虎窗屋顶、塔帽、门廊屋顶分别计数，不能把“主屋顶存在”当作所有小屋顶都存在。
- 烟囱和端子：石烟囱数量、每个烟囱的帽/管数量、金属烟管或陶管数量分别记录；用户要求删除的构件保留为 `expected=0` 的数量事实。
- 重复附件：窗套、阁楼窗对、壁灯、栏杆、台阶、花盆和植物模块分别记录实例数或组件内embedded数量。
- 每个关键构件的最小轮廓、顶部结构、附着面和可见附属结构都要在数量表中说明其计数单位。

数量来源至少覆盖正面、背面、左、右和能看清屋顶的俯视/45 度视图。视角互相遮挡时记录“可见下限”，再用整栋参考模型和装配实时数据补齐，不能直接把可见下限当最终数量。任何用户指出的数量错误都成为新的参考事实，必须同步更新 `quantity_audit`、洞口/参数合同、组件实例和装配审计。

```bash
python scripts/quantity_census_audit.py <项目目录>
```

`quantity_census_audit.py` 会检查分项合计、数量事实的 expected/actual、与 `assembly` 实例记录的对应关系，并在存在实时正视图审计时核对逐立面逐层窗数。数量审计未通过时不得开始组件建模或把装配标为通过。

### 全量构件清单与返工闭环

数量清点前先建立三层清单，避免“只拆标准窗墙、漏掉独立体量和小附件”：

1. **宏构件与体量**：主体墙、主要屋面、侧翼、塔楼、凸窗、老虎窗/阁楼小屋顶、烟囱、门廊。即使只出现一次，也必须进入 `visual_inventory` 和 `detail_audit`。
2. **重复模块**：窗、门、壁灯、栏杆段、台阶、花盆、藤蔓和其他实例化资产。必须记录逐立面/逐层数量、实例根、接口和替换规则。
3. **附着与端子细节**：窗台、窗套、披檐、屋顶、屋脊、托架、檐沟、烟囱帽、金属/陶制烟管、苔藓和五金。用户要求去掉的附件记录为 `expected=0`，不能从记录里静默消失。

用户提出返工时执行同一闭环：

- 先把用户反馈当作新的参考事实，更新 `detail_audit`、`quantity_audit`、边界/参数合同和组件实例。
- 对漏项检查整栋参考模型的 `component_map` 是否也漏了同一对象；如果参考模型误分类，记录纠正原因，不只给最终模型打补丁。
- 对干涉问题重新生成实时组件遮罩并与前后深度比较；禁止仅把非预期关系写入允许表。
- 修改组件后同时检查独立源文件、GLB 和整栋装配；三者尺寸、对象数量和材质绑定不一致时不得通过。
- 重新渲染当前 revision 的受影响组件、整栋、正视叠加和参考对照，旧 QA 立即失效。

## 组件与自由区

拆件时，每个组件必须写清三类信息：

- `locked`：接口包围盒、门窗洞、厚度、原点、朝向和必须匹配的结构。
- `guided`：构件类型、主要轮廓、材料倾向、色彩和设计年代。
- `free`：允许 AI 发挥的雕花、格栅、线脚、窗格、栏杆花纹和表面细节。

没有自由区的组件不值得交给 AI 3D；直接使用参数化或复用。没有锁定区的组件不能进入精确装配。

具体要求见 [component-generation.md](references/component-generation.md)。

## 组件参数化合同

所有结构件、门窗、栏杆、线脚、台阶、门廊、烟囱、灯具、植物和装饰资产都必须在 `components.parts[*].parametric_contract_id` 指向一份参数合同。项目合同默认存放在 `internal/parametric_components.json`，完整结构与操作见 [parametric-components.md](references/parametric-components.md)。

每个合同至少记录：

- `generator_id`、版本、生成器类型和实现方式。
- 可编辑参数及参数 schema：类型、单位、范围、步长和是否暴露。
- 接口、构造、风格、格数和实例约束。
- 输出根对象、集合、Blend/GLB 路径。
- 材质绑定和贴图来源。
- `quality_gate`，审批范围固定为 `per_parameters_hash`。
- `last_build`：参数指纹、构建 revision、审计和材质对照路径。

生成器类型必须按组件实际能力选择。墙体使用立面槽位和洞口生成器，窗体使用宽高、框料和窗格生成器，屋面使用坡面/檐口/屋脊参数，栏杆、踏步、线脚和转角石使用阵列参数。AI 3D、模型库和有机植物也要有包装合同，但只承诺实际可控的实例、包络、镜像、材质和 seed，不假装能够实时改写 AI 拓扑。

参数指纹包含参数、材质绑定、约束和外部参数文档哈希。任何一项变化后，旧构建即时失效。必须重新生成几何，并重新执行：

- 接口、边界、支撑、收口和构造检查。
- 网格审计。
- 材质来源与 Poly Haven 检查。
- 贴图投影、物理尺度和跨立面拉伸检查。
- 正面、侧面、3/4 或组件关键角度的多视图渲染和参考对照。
- 组件 QA。

不得把上一参数的材质截图、贴图审计或 QA 结果继承给新变体。`last_build.parameters_hash` 与当前合同不一致时，`scene_kit.py validate` 必须阻止通过。

墙体和窗体联动时，墙体洞口与窗体安装接口由同一组参数生成。删除窗洞应重建连续墙体，不在洞口塞补片；增加窗洞只能使用满足墙角、楼层带、最小墙墩和门洞约束的槽位；随机增减必须带 seed 并可复现。窗体宽高变化时重新计算框料、中梃、横档、窗格、石窗套和窗台，不直接非均匀缩放整个窗体。

尺寸变更只能传播一次。墙体加宽后，如果整栋装配已经应用了宽度比例，独立组件源不得再次乘同一比例；优先用新参数重新生成，或从已验证装配层级重建独立源。每次尺寸变更应记录组件源与装配的包围盒、对象数量、三角面和材质绑定对照，避免“整栋是 11 m、组件库却是 14 m”这类双重建模。

## 组件边界与附着结构

组件是可在装配中整体移动的三维构件，不是图片上的一个平面色块。拆件时必须根据正面、侧面、背面和 45 度视图共同确定边界；在一个视图中被遮挡或看似贴着墙面的结构，要到其他视图中确认厚度、突出量和背面关系。

每个组件写入 `boundary_review`：

- `surfaces`：正面、背面、左、右、顶部和底部六个面的形态是否已解释。
- `overall_dimensions_m`：包含所有附着结构后的真实包围盒。
- `mounting_interface_dimensions_m`：与墙体、楼板或相邻构件接触的接口，不得和整体包围盒混为一谈。
- `attachments`：窗台、窗套、披檐、盖板、压顶、托架、铰链、框料和返口等子结构。每个附件记录多个证据视图、是否纳入当前组件、材质和突出量。
- `material_zones`：一个组件可以有木材、石材、玻璃和金属多个材质区，不能把组件整体压成一种材质。
- 六项边界检查全部通过，`unresolved` 为空，才允许建模、生成或装配。

例如窗组件通常至少包括正面框料、侧向厚度、背面安装面、窗套和向外突出的石质窗台。只把窗格做成零厚度平面是错误组件；如果窗台与其他附件跟随窗户一起安装，应纳入窗户组件并保留独立材质，而不是因为位于“下方”就遗漏。

门头、雨棚和入口披檐必须从参考模型正面、侧面和 45 度视图共同判断是单坡、双坡、平挑檐还是上层阳台底面，不能默认做成覆盖整段台阶的大雨棚。可用局部屋面法线分布核对坡向：双坡通常出现一组近似镜像的 ±X/±Z 法线，单坡主要沿一个进深方向倾斜。高度、宽度、支撑方式和是否落地立柱也必须由同一组多视图证据决定。檐柱、柱础、柱帽、柱顶横梁、随坡屋面托木、墙装托架、封檐板、山墙百叶或三角窗只要在有效参考中可辨认，就必须在首次拆件时作为该门头组件的附属结构登记并进入参数合同；不得先删掉这些可见结构，再让用户逐项指出。多视图身份清楚后直接纳入生成与审计，只有证据互相矛盾或新增付费资产时才需要再次询问。

不能为了缩小包围盒而删除外侧突出物。整体尺寸用于碰撞和镜头判断，安装接口用于装配；两者分别记录。若附着结构确实是独立可拆资产，必须用 `separate_component` 声明并链接真实 `part_id`，不能静默丢掉。

### 宿主连接与背面体量

凡是向前突出的立面或屋面构件，都必须在 `surfaces.front/back/left/right/top/bottom` 之外说明它是如何“长在建筑上”的：

- 屋顶窗、老虎窗和阁楼窗必须包含或连接一个真实老虎窗体量；窗框不能直接贴在屋面上。体量应具有侧墙/侧板、底面或底板、背面封口或屋面内腔接口，并与主屋面网格存在实际接触或相交。
- 凸窗、阳台、门廊、雨棚、烟囱、壁灯、招牌和装饰平台必须记录主墙/主屋面的宿主构件、安装面、背面或支撑结构。
- 只从正面可见、但从侧面和 45 度无法解释厚度、背面或支撑的构件，保持 `repair_required`。
- 把关键连接写入 `components.attachment_integrity_audit`，至少记录 `part_id`、`attachment_id`、`host_part_ids`、`has_volume`、`has_back_enclosure`、`has_side_enclosure`、`front_plane_only=false`、`host_contact_verified=true`、`body_projection_beyond_host_m`、`front_eave_setback_m`、`roof_covers_body_rear`、两个以上证据视图和宿主接触证据。
- `body_projection_beyond_host_m` 必须大于 0.05 m；对需要形成独立小房体的老虎窗，通常应达到 0.20 m 以上。仅与宿主墙/屋面共面、只有极薄前脸或被正面图误读成窗片的体量不能通过。
- 附着屋顶的前沿不得越过宿主主檐，`front_eave_setback_m` 必须大于等于 0；小屋顶深度必须覆盖附着体量的后墙顶部，`roof_covers_body_rear=true`。不得只用一个短屋顶片盖住前部而让后墙顶部露天。
- `attachment_integrity_audit.status=pass` 时所有检查为 true、`unresolved` 为空。`front_plane_only=true`、宿主不存在、宿主接触仅由文字声明、只有正面截图或前凸量不足时不能通过。

```bash
python scripts/attachment_integrity_audit.py <项目目录>
```

屋顶老虎窗的合格结果应同时具备：位于房体前脸的窗组、从宿主墙/屋面前凸的封闭房体、向后退入主屋面的侧墙/底板、背面结构、双坡顶或单坡顶、位于主檐以内的屋顶前沿、覆盖后墙顶的屋顶深度，以及与主屋面可验证的网格接触。单纯补一个窗、屋顶片、与宿主共面的薄墙或盖不到后墙的短屋顶仍然不合格。

## 细节特征盘点

`COMPONENTS` 不能只识别墙体、屋面、门窗和塔楼等大构件。必须先对参考模型派生的十视图逐张做细节扫描，把会影响最终轮廓、近景可信度或构件数量的特征写入 `components.detail_audit`。烟囱、屋脊压顶、尖顶饰、老虎窗、檐沟、落水管、托架、牛腿、山墙装饰、窗框变体、百叶、门五金、台阶、栏杆、浮雕、木雕、壁灯、花盆、藤蔓和苔藓都不能因为尺寸较小而在拆件阶段消失。

每个细节特征至少记录：

- `category`：`roof_and_skyline`、`openings_and_frames`、`trim_and_ornament`、`attachments_and_services`、`site_and_vegetation` 或 `surface_and_material_patterns`。
- `views` 和 `quantity`：至少两个真实多视图来源，并记录可辨认数量。
- `visual_impact`：`silhouette`、`near_view` 或 `surface_only`。
- `geometry_required`：是否必须由几何承载；需要几何的细节不能只交给材质。
- `disposition`：`part`、`parametric`、`reuse` 或 `material`；选择 `part` 时必须声明 `geometry_required=true` 并链接现有 `part_id`。
- `observation`：说明该细节为何存在、在哪里、如何影响最终效果。

`detail_audit.scan_views` 必须覆盖选中方向的全部十视图，`coverage` 必须覆盖六类扫描，`unresolved` 通过时必须为空，`status` 必须为 `pass`。`components.decomposition_review.checks` 还必须包含并确认 `detail_features_complete` 与 `detail_geometry_decisions_verified`。任何需要几何但只写进材质、未链接到组件，或仍有未解决特征的项目，都不能离开 `COMPONENTS`。

简单接口示意图只用于控制安装关系，不能替代细节造型参考。若某一特征在所有视图中都不存在，记录扫描结论即可，不得凭空补造。

### 窗格与微结构复核

门、窗、栏杆和格栅不能只记录“有几扇”或一个笼统的总格数。特别是窗格，必须在放大裁剪上逐个确认框料层级和重复拓扑，并写入组件 `fine_structure_review`：

- 主竖向分区数、中央分区是否再次分列、每个中央分区的列数。
- 总列数、总行数、横档数量、由拓扑相乘得到的总格数。
- 主梃、中央细分梃和横档的粗细层级，顶部是否有独立横窗或亮窗。
- 框、压条、窗套、玻璃的基础颜色、粗糙度和材质身份；深色木框不能默认做成高光樱桃木。
- 至少两个多视图来源、一个放大近景、视觉再识别证据、可信度和未解决项。

`pattern.pane_count` 必须等于 `pattern.columns × pattern.rows`。中央分区再分列时，`columns` 必须等于“主竖向分区数 - 1 + 中央分列数”。参数化或 AI 模型完成后，`parametric_build`/生成记录中的列数、行数和格数必须与这份结构指纹一致。只凭整窗 VQA 回答一个总数不算完成；必须同时用放大裁剪、边框线位或框料轮廓核对怎么分。

### 视觉模型辅助复核

当小尺度细节较多、仅靠文字盘点容易漏项时，可运行：

```bash
python scripts/detail_vision_audit.py <项目目录> --output-dir <项目目录>/preview/detail-scan
python scripts/detail_vision_audit.py <项目目录> --view-dir <参考模型派生十视图目录> --output-dir <项目目录>/preview/detail-scan-model-derived
blender --background --python scripts/ensure_modeling_extensions.py -- --install --output <项目目录>/internal/toolchain.json
```

对参考模型派生十视图运行时使用 `--view-dir` 或 `--view-map`。脚本使用 Florence-2 对十视图做详细描述和短语定位，对窗等代表性裁剪生成 4 倍近景并运行独立 VQA；同时输出去向梯度线位候选。它只生成诊断证据、标注图和 JSON，不修改项目状态，也不自动写入 `detail_audit` 或 `fine_structure_review` 通过。

必须把模型结果当作候选证据：两个以上视角或多模型一致时可提高可信度；烟囱/塔帽、数量或安装关系冲突时写入 `unresolved`。视觉模型配置、依赖固定、输出结构和判定顺序见 [detail-vision-audit.md](references/detail-vision-audit.md)。

## 拆件与图片完整性

拆件不是只给构件起名。每个 `part` 的几何身份、三维范围和附着关系先由参考模型派生视图与网格岛候选确认；再回到选中方向的原始多视图中复核，至少使用正面/背面、侧面和 45 度视图中的两个真实来源，记录在 `decomposition_audit.source_views`。原始来源必须是选中方向的 `view_paths`，不能拿无关构图的局部图充数。

检查拆件范围是否完整、是否误把相邻构件并进来、是否遗漏安装背面/侧厚/顶部或底部、多视图之间是否对得上，以及拆下后是否仍能被连续装配。一个在单视图里合理、但其他视图无法解释的裁剪，必须先修拆件，不能直接生成。

在 `REFERENCES` 阶段，`geometry` 和 `appearance` 图片还必须经过 `reference_pack.audit`：裁剪不能截断目标构件，不能带入相邻构件或隐藏环境，必须与原始多视图一致，并保留可判断安装关系的边缘。图片完整不只看分辨率，还要看构件语义和安装逻辑是否完整。

整栋拆件总审查写入 `components.decomposition_review`，至少确认：资产和细节特征盘点完整、多视图一致、安装关系可解释、几何处理方式已验证、拆件后不会被装配成散件。任何一项未通过，都要回到多视图修正后再进入生成。

## 非结构表现资产

拆件时必须读取选中方向的用户视图和十张概念图，不只识别门、窗、墙和屋顶。浮雕、木雕、徽章、铁艺花纹、雕塑、花簇、草、藤蔓、灌木、树、花盆和壁灯等，不应默认烘进墙面、合并进门窗或只做贴图。它们应作为独立的 `decorative_ornament`、`vegetation` 或 `site_element` 资产，记录 `type`、来源视图、尺寸、锚点、实例数量和生成方式。

有真实厚度、可独立取轮廓、需要重复、替换材质或后续调整位置的装饰件，优先拆成单独模型。没有几何厚度的表面图案继续使用 PBR 或法线贴图；密集到无法分辨单体边界的植物，先生成一个代表性花簇、灌木或藤蔓模块，再在 Blender 中实例化。不要把每片叶子或每朵花重复提交给 AI 3D。

在 `components.json.visual_inventory` 记录扫描结果，并在每个 `part` 中写明 `asset_class` 和具体 `type`。至少区分：

- `architectural_component`：门、窗、栏杆、柱、门廊。
- `decorative_ornament`：浮雕、木雕、线脚、徽章、铁艺和雕塑。
- `vegetation`：花簇、草、藤蔓、灌木和树。
- `site_element`：壁灯、花盆、长椅和标牌。
- `structure`：墙段、屋面、楼板和楼梯。

### 有机植物资产标准（7.23）

所有藤蔓、盆栽、花簇、灌木和草本模块都以 revision-2 攀援藤蔓作为最低造型标准。不得用直杆枝条、重复扁平菱形叶片、单色整片叶冠或只有正面的贴片植物通过 QA。这里的“藤蔓标准”指有机生长逻辑，不要求所有植物采用同一种叶形或同一轮廓。

植物至少要有：

- 连续弯曲、从基部到末端渐细的枝干，以及可读的主枝、侧枝和末梢层级。
- 足够细、足够密并随视角变化的叶片或花簇；叶片应有弯曲、杯状起伏、翻面与不同方向，而不是等距复制。
- 三档以上同色系自然变化，例如深色内层、中间叶色和受光末梢；枝干、叶面、花/芽/土须有独立材质区或明确材质边界。
- 不规则但连续的冠层轮廓，基部稳定落地或种入花盆，不出现漂浮叶、悬空枝和机械同心排列。
- 契约记录枝条数、分枝路径、叶片/花簇数、叶尖芽、曲率、渐细比、冠层填充和 seed；参数或 seed 改变后必须重生成并重新审计。

`generate_vegetation_module.py` 的模块级硬门禁为：分枝路径不少于主枝数的 2 倍，茎干最大转折至少 4°，末梢/基部半径比不大于 0.4，叶片数不少于 `max(40, 主枝数 × 12)` 且平均叶长不超过模块高度的 12%，至少三档叶色，每条枝路有末梢芽，二维冠层网格填充率至少 0.3，所有叶冠位于种植基部以上。AI 3D 或模型库植物不套用这些精确数值，但必须通过同等含义的多视图视觉检查，并写入 `organic_quality`。

薄叶片允许保留开放壳边界；无线边、零面积面、异常尖刺、错误透明面、漂浮叶和漏光仍必须为零或全部解释。植物重生成后，必须同时检查独立源文件、GLB、整栋装配、正面遮罩和入口近景，不能只替换组件全家福图片。

## 跨项目模型库

组件拆完先检索模型库，避免用户在不同项目中重复付费生成同类门窗、浮雕或植物。匹配结果只作为候选，必须展示预览、尺寸、接口、材质、风格和来源，由用户决定复用、缩放、换材质、仅作参考或重新生成。没有用户明确确认，不得把候选设为项目组件。

每个 AI 组件通过单件 QA 后，必须询问用户是否加入模型库。组件较多时可以集中询问，但不得自动入库。用户同意后保存模型、参考对照图、资产分类、具体类型、尺寸、原点、朝向、接口、材质、风格、标签、来源项目、许可证、复用方式和文件哈希。同一模型文件不重复入库。

模型库默认位于 `~/.scene-kit/model-library`，也可以通过 `SCENE_KIT_LIBRARY` 或 `--library` 指定。完整分类、元数据和操作规则见 [model-library.md](references/model-library.md)。

## 参考图规则

整栋参考模型的源图和每个 AI 3D 单体的生成资料必须分开记录。单体只能使用以下三类资料：

1. `geometry`：中性正侧轮廓、接口和厚度，用于控制外形与装配。
2. `appearance`：选中的整栋概念图局部、单件概念图或风格锚，用于传递设计语言。
3. `review_only`：整栋灰盒、完整审阅渲染或装饰过度的三视图，只能给人看，不能作为生成参考。

不要把 `review_only` 图片放进几何参考。不要把整栋精修图当作单件图。整栋参考模型本身也属于 `reference_only`，只能用于空间和特征分析。生成器只支持一张图时，优先使用“单件正交概念图”；其次使用“中性轮廓 + 文字提示 + 风格锚”。

### 多参考交叉验证

任何组件在开始参数化建模或 AI 3D 生成前，必须先从参考模型派生视图制作组件裁剪，再用原始视图验证，并把结果写入 `reference_consensus`。单张裁剪不能独立确认轮廓、结构、安装关系或材质。

最低复核范围：

- 身份：两个视角都确认是同一类构件，没有把相邻构件或另一种窗型混入。
- 轮廓与结构：宽度、高度、侧厚、框料层级、重复分格和安装面能相互解释。
- 材质：对每个主要材质角色分别记录至少两个视角的采样结果；木框要区分深褐木、灰木、黑漆木和红木，不能只根据模型描述里的“dark”判断。
- 光照差异：不同视角的明暗、白平衡和遮挡要解释；光照造成的变化不能当作材质换色。
- 分歧：视角不足、身份冲突、颜色冲突或安装关系不明时写入 `unresolved`，保持 `repair_required`，不开始生成。

`reference_consensus.model_crops` 至少有一个参考模型派生裁剪；`source_views` 和 `crops` 仍然保留原始图校验来源。`authority_policy` 必须明确：几何主源为 `reference_model`、组件参考主源为 `model_derived_views`、原图角色为 `validation_and_surface_detail`。`material_samples` 至少覆盖两个视角并记录 `mean_rgb`；六项一致性检查全部通过，`confirmed_before_generation=true`，才允许生成或建模。

运行视觉扫描后，优先使用 `detail-scan/multi_view_evidence.json`、每个构件的多视图裁剪和调色板；再与整栋参考模型中的对应区域交叉检查。视觉描述、局部 VQA、跨视图调色板、放大图和三维深度应相互印证，不能用一个模型的单次回答直接通过。

## 生成与装配

- 先完成整栋三维参考模型和组件特征映射，再逐个落地组件；重复组件通过 Blender 实例复用。
- 整栋参考模型门禁通过后再运行 `generation_route_audit.py`，评估的是“这个已映射组件如何实现”，而不是是否要先绕开整栋参考、直接单独试生成。
- 只有 Blender 参数化或手工建模成本明显更高、组件具有独立造型价值、参考质量足够且不要求精确尺寸时，才考虑 AI 3D 路线。
- 重复窗、台阶、规则栏杆、墙段、屋面和其他可由 Blender 修改器或 Geometry Nodes 稳定建立的构件优先使用 Blender；不能保持 `ai_3d` 去“先试一次”。
- 精确门、窗、栏杆和格栅若仍选择 AI 3D，`reference_sufficiency` 至少要有正面和一个侧面/45 度组件参考，并写明每张参考的用途；只有一张局部图时停止该路线，不把“多试几次模型”当作补齐结构信息的办法。
- 任何组件生成前必须有通过的 `boundary_review`。侧面、45 度或背面出现额外厚度、窗台、托架、檐口或安装壳时，必须纳入组件边界或明确拆为独立组件。
- 每次选择 AI 3D 前，必须写 `triangle_budget` 与 `low_poly_strategy`：目标总面数、硬上限、预算依据、提供方质量档、减面/重拓扑步骤和必须保留的轮廓、UV 接缝与材质边界。质量档名称不等于面数保证；接口没有暴露面数限制时记录 `provider_face_limit_exposed=false`，生成后必须在 Blender 中按预算处理并复检。
- 小尺度有机构件（藤蔓、花簇、盆栽、苔藓等）只有在境裁剪参考、或图生 3D 已把墙面/建筑/地面串入单体时，允许并应优先改用纯文生 3D：用隔离主体提示词和完整负面清单生成无环境单体，再在 Blender 中烘焙朝向、按预算减面、拟合锁定包络与底部中心原点、外置 PBR 贴图并复检。必须在 `generation.input_mode=text_to_3d` 同时写 `text_only_reason`，并在 `ai_3d_attempt` 记录任务 ID、原始/最终面数和采用结论。判定信号由 `generation_route_audit.py` 的 `input_mode_guidance` 给出，详见 [generation-routing.md](references/generation-routing.md)。
- 生成前展示参考图用途、输入模式和完整中英文提示词，并得到用户确认。
- 组件执行阶段可以并列说明两条路径：使用 Blender MCP 已启用的生成器，或由用户在自己的外部图生 3D 平台生成后回传 GLB/GLTF（优先）、OBJ/FBX。两条路径都必须引用同一整栋参考模型和组件映射，进入同一套比例、接口、网格、材质和视觉对照验收。
- 外部生成回传时必须说明每张图的角色、完整正负提示词、单体边界、文件格式、构件 ID 命名和回传位置；助手收到文件后负责导入、归一化、修复和 QA。
- 提交正式任务前核对账号区域、插件区域或 Domain、实际 API 根路径、Key 的来源区域和工作区、余额与低成本鉴权结果。不要把产品展示页当作 API 端点，也不要在配置未核对时消耗高成本任务。
- 生成后先做网格、接口、材质节点和贴图映射静态审计，再强制渲染单件视图，优先与参考模型派生的多视角组件裁剪对照，并用原始图验证材质和清晰微细节。是否把图片嵌入聊天不改变这项门禁。
- 生成后还要对 `boundary_review.attachments` 逐项复核；参考中存在的附着结构在成品里缺失、变成薄片、改了材质或没有连接关系时，组件不能通过。
- 单件本体在进入装配前完成修复，不只修整栋接缝。修复后重新确认比例、接口和拓扑，并重渲染受影响的材质视图。
- 每个组件通过 QA 后询问是否加入模型库；用户确认后才运行 `library-add`。不要因批量生成而跳过这一提示，也不要擅自入库。
- 整栋装配后再次检查构件与墙、屋面、楼板和其他构件的缝合，然后进入最终精修。装配完成不等于可验收。
- 原始比例不可信。导入 Blender 后按 `locked` 接口归一化，再装配。
- AI 自带纹理只在参考对照通过时保留；墙面、石材、木材、瓦面和玻璃由项目 PBR 规则统一，避免塑料感、过曝和构件间风格漂移。

生成路线规则的完整矩阵和 `route_assessment` 字段见 [generation-routing.md](references/generation-routing.md)。推荐路线和选中路线必须一致；AI 3D 路线不能接受 `precision_demand=exact`、`ai_3d_expected_benefit=low` 或 `reference_quality=low`。

## 材质与贴图验证

每完成一个组件，几何 QA 之后立即赋最终材质，完成节点、贴图路径和映射元数据审计，并强制渲染正面、侧面、3/4 中至少两个视图。可以不在聊天中逐张展示，但不能省略渲染和对照。

### 强制贴图映射审计

每次参数化建模、AI 3D 后处理、复用或库资产落地后，都必须在声明材质通过前完成贴图映射审计：

1. 运行 `blender_audit.py`，读取 `texture_mapping_audit`；该报告记录每个材质中的图片节点、来源图片、分辨率、投影方式、坐标来源、映射缩放和风险项。
2. 检查图片真实存在并已加载。颜色贴图为 sRGB，法线、粗糙度、AO 和置换为 Non-Color。
3. 检查投影与坐标来源。三维物体表面若直接使用 `FLAT + Object/Generated`，不同朝向的立面可能忽略竖向轴并把石纹、砖缝或木纹拉成长条；必须改用有控制的 Box Projection、正确 UV 或逐面映射。
4. 检查物理平铺尺寸。优先使用素材公开的 `dimensions` 元数据；没有元数据时按参考中真实石块、砖块、木板或瓦片尺寸估算。不能用一个随意缩放值代替尺度验证。
5. 对每个有贴图的组件检查正面、侧面和 3/4 的实际渲染。颜色正确但石块、砖缝或木纹方向不一致，仍然不能通过。
6. 法线、粗糙度和颜色必须使用同一套投影和尺度；只有颜色贴图正确、法线或粗糙度错位时不能通过。
7. 修改投影或尺度后必须重新运行审计并重新渲染当前 revision，不能复用修复前截图。

每个通过的组件在 `qa.material_review` 中同时写入：

- `checks.texture_projection_valid=true`。
- `texture_audit.status=pass`。
- `texture_audit.audit_path` 指向本次 Blender 审计。
- `texture_audit.mapping_mode`、`views_checked`、风险项和五项贴图检查。

必查项为 `source_image_loaded`、`projection_axis_valid`、`physical_scale_consistent`、`no_visible_stretch_across_faces` 和 `normal_and_roughness_aligned`。任何风险项未清零时，组件只能保持 `repair_required`。

材质不匹配时，顺序为：

1. 先查 Blender 是否已安装可用的 Poly Haven Assets 插件。
2. 未安装时用 `polyhaven_search.py` 搜索 Poly Haven 免费 CC0 纹理、模型或 HDRI。
3. 有合适资产时使用并记录 slug、分辨率和映射尺度。
4. 没有合适资产时才生成项目本地贴图或使用程序化 PBR。
5. 修改后重新审计并重渲染当前版本，再重新对照。

每个通过组件必须写出 `qa.material_review`，包含至少两个实际渲染图、参考对照图、`polyhaven_checked=true`、贴图来源、五项材质检查和六项贴图检查。图片是否在聊天中展示不影响这项要求。完整规则见 [material-texture-validation.md](references/material-texture-validation.md)，Poly Haven 使用条件和授权边界见 [polyhaven-assets.md](references/polyhaven-assets.md)。

窗框材质不能只凭名称判断。先从两个以上参考视角采样基色并确认色相，再搜索候选材质；深褐旧木可考虑 `fine grained wood`、`dark wooden planks`，只有跨视图明确是低饱和黑漆时才用 `black painted wood`。不要再把“上一版使用了某贴图”当作通过证据。

颜色正确不等于材质正确。屋顶颜色匹配后仍需检查它是石板瓦、木板、金属还是其他表面语言；必须同时确认纹理类型、块面尺度、坡度方向、法线和粗糙度。颜色、材质语义和几何轮廓分别通过不同检查，任一项失败都保持返工状态。

## 最终精修与智能验收

整栋装配后必须进入 `FINISHING`。质量顺序是：硬尺寸和接口先守住；在硬约束内，以目标镜头效果匹配、面片质量、材质与接缝为最高优先级；渲染时间和 token 消耗只记录，不作为提前通过的理由。

已有项目如果只需要修复最终模型，可直接 `reopen` 到 `FINISHING`，不重新经历概念图、选型、拆件和 AI 3D 生成；但当前 `.blend`、参考图、整栋图和近景仍要建立同一 revision 的精修记录。

精修必须覆盖 AI、参数化、复用和模型库资产。至少检查目标分辨率下的低模折面、三角化、法线断裂、平滑错误、重合面、Z-fighting、破洞、零面积面、孤立碎片、穿插、悬浮、黑缝、漏光、UV 拉伸和纹理尺度。

进入本阶段后先运行场景审计，取得当前文件的单位、面数、零面积面、非流形边、线边、孤立顶点、重复边面、异常缩放、缺失材质和丢失贴图数据：

```bash
blender --background <模型.blend> --python scripts/blender_audit.py -- --output <项目目录>/preview/finishing/blender_audit.json
python scripts/detail_vision_audit.py <项目目录> --output-dir <项目目录>/preview/detail-scan
```

审计报告只作为检查证据，不自动判定建筑效果或构造是否合格。先区分真实缺陷、允许的开放面和临时审阅物，再修复；需要视觉判断时，在用户批准的渲染批次中重渲染。判断标准和必拍视图见 [blender-production.md](references/blender-production.md)。

最终验收不能只做图像相似度比较。必须进行构造逻辑的智能分析，并主动检查：

- 屋檐、门廊、雨棚、老虎窗、凸窗、塔楼、阳台、栏杆和檐沟是否有真实连接或支撑；
- 门、窗和洞口是否与墙体吻合，台阶、花箱、壁灯和装饰件是否落在合理接触面上；
- 屋面、墙体和收口是否存在悬空、断开、穿插、无法受力或无法防水的状态；
- 各构件是否因为拆件或装配被切成散件，是否缺少连续结构、厚度或安装背面。

发现屋檐与门廊松垮、构件悬空、支撑缺失、接缝断开或明显不符合建造逻辑时，必须自行修补并重新渲染验证，不得只把问题列给用户，也不得用遮片、贴图或灯光藏起来。只有设计意图本身存在歧义、修补会改变用户要求、需要新的付费生成，或需要额外的展示性大图时才停下来询问。

通过标准：`blocker/high` 缺陷全部修复；关键区域有近景对照；整栋图、近景、参考对照图和当前 `.blend` 属于同一 revision，并通过 SHA-256 绑定；`construction_logic`、`assembly_seams`、`surface_quality` 和所有资产来源覆盖检查为通过。`medium/low` 残余差异必须明确记录。

正视图检查不能只看一张最终截图。先运行组件透明轮廓遮罩，再比较遮罩重叠像素和前后深度关系，最后把包围框与组件名称叠加到正面正交图上复核。AABB 相交、画面近似或模型自述都只能作为候选，不能替代实际轮廓重叠证据。塔楼遮挡窗、门扇穿入门套、栏杆穿过窗台、装饰件悬浮在同一洞口等关系默认失败；只有项目明确允许的结构接触才能标记为允许。

## 用户交互

默认每条回复只推进当前阶段。首行写清阶段和当前任务，然后给出：

1. 用户现在能看到什么。
2. 检查通过或未通过的一两个具体原因。
3. 用户现在需要做的选择或确认。

默认不展示哈希、状态字段、脚本名或内部 JSON。只有用户主动询问实现时再展开。

## 交付目录与过程证据

最终项目不得把 `raw/`、`preview/`、`out/`、`export/` 作为多个并列根目录。原始视图和过程图仍有验收、追溯和 GitHub 展示价值，只放在 `assets/raw/` 与 `assets/preview/` 的单一副本中；最终组件的 `.blend`/`.glb` 放 `components/`，整栋装配放 `assembly/`，参考模型放 `reference/`。

清理目录时先做引用清单。默认保留原始输入、参考分析、当前 revision QA 和用户已查看的对照图；只删除重复副本、被最终版本取代的迭代、临时缓存和已经迁移的旧路径容器。用户明确要求整理目录时，也不得把 `assets/raw/` 或 `assets/preview/` 整批删除：原始图和过程图要继续作为验收证据与 GitHub 插图，只是不能与最终模型目录并列、不能重复保存。组件目录默认只保留一份当前 QA 图组和对应审计；被新 revision 完整取代的组件图组、`.blend1`、错误嵌套路径可以删除。移动后必须同步修改 JSON/Markdown 路径，写迁移记录，并重跑项目、参数合同、断链和最终导入校验。

根 `README.md` 使用 `assets/preview/` 的相对路径展示整栋总览、参考十视图和关键构件对照；`components/README.md` 提供每件组件的源文件、GLB 和 QA 入口。详细目录合同与迁移顺序见 [project-delivery-layout.md](references/project-delivery-layout.md)。

## 脚本

```bash
python scripts/scene_kit.py init <项目目录> --name <项目名>
python scripts/scene_kit.py validate <项目目录>
python scripts/scene_kit.py advance <项目目录>
python scripts/scene_kit.py reopen <项目目录> <阶段> --reason "返工原因" --confirmed-by-user
python scripts/scene_kit.py library-init
python scripts/scene_kit.py library-search "floral stone relief" --asset-class decorative_ornament
python scripts/scene_kit.py library-add <项目目录> <part_id> --confirmed-by-user
python scripts/scene_kit.py library-link <项目目录> <part_id> <asset_id> --confirmed-by-user
python scripts/scene_kit.py library-validate
python scripts/generation_route_audit.py <项目目录> [--part <part_id>]
blender --background <整栋.blend> --python scripts/assembly_front_visibility_audit.py -- --project <项目目录>
python scripts/analyze_front_visibility.py --project <项目目录>
python scripts/quantity_census_audit.py <项目目录>
python scripts/attachment_integrity_audit.py <项目目录>
python scripts/parametric_components.py validate <项目目录>
python scripts/parametric_components.py hash <项目目录> <part_id>
python scripts/parametric_components.py refresh-build <项目目录> <part_id>
python scripts/polyhaven_search.py "dark oak wood" --type textures --limit 10 --output <项目目录>/internal/polyhaven-dark-oak.json
python scripts/detail_vision_audit.py <项目目录> --output-dir <项目目录>/preview/detail-scan
python scripts/reference_feature_scan.py <报告.json> --output <项目目录>/internal/reference_feature_candidates.json
blender --background --python scripts/ensure_modeling_extensions.py -- --install --output <项目目录>/internal/toolchain.json
blender --background <墙体.blend> --python scripts/generate_wall_envelope.py -- --project <项目目录> --parameters <洞口参数.json> --material-name <材质名>
blender --background <窗体.blend> --python scripts/generate_window_assembly.py -- --project <项目目录> --parameters <窗体参数.json> --stone-material <石材> --wood-material <木材> --glass-material <玻璃>
blender --background <阁楼窗.blend> --python scripts/generate_attic_window.py -- --project <项目目录> --parameters <阁楼窗参数.json> --stone-material <石材> --wood-material <木材> --glass-material <玻璃>
blender --background <屋面.blend> --python scripts/generate_roof_system.py -- --project <项目目录> --parameters <屋面参数.json> --roof-material <石板> --gable-material <山墙石材> --ridge-material <屋脊石材> --fascia-material <檐木> --gutter-material <天沟金属>
blender --background <烟囱.blend> --python scripts/generate_stone_chimney.py -- --project <项目目录> --parameters <烟囱参数.json> --stone-material <石材> --cap-material <帽石> --flue-material <金属> --moss-material <苔藓>
blender --background <入口.blend> --python scripts/generate_entrance_portal.py -- --project <项目目录> --parameters <入口参数.json> --stone-material <门套石材> --wood-material <门扇木材> --iron-material <暗铁五金>
blender --background <台阶.blend> --python scripts/generate_entrance_steps.py -- --project <项目目录> --parameters <台阶参数.json> --material-name <石材>
blender --background <壁灯.blend> --python scripts/generate_wall_lantern.py -- --project <项目目录> --parameters <壁灯参数.json> --metal-material <暗金属> --glass-material <暖玻璃>
blender --background <木廊.blend> --python scripts/generate_timber_porch.py -- --project <项目目录> --parameters <木廊参数.json> --wood-material <木材> --roof-material <屋面> --stone-material <石材>
blender --background <门头.blend> --python scripts/generate_entrance_gable_hood.py -- --project <项目目录> --parameters <门头参数.json> --wood-material <木材> --roof-material <屋面> --glass-material <玻璃>
blender --background <栏杆.blend> --python scripts/generate_porch_railing.py -- --project <项目目录> --parameters <栏杆参数.json> --material-name <深色木材>
blender --background <线脚.blend> --python scripts/generate_stone_facade_trim.py -- --project <项目目录> --parameters <线脚参数.json> --material-name <石材>
blender --background <植被.blend> --python scripts/generate_vegetation_module.py -- --project <项目目录> --parameters <植被参数.json> --prefix <对象前缀> --output-blend <输出.blend>
blender --background <参考模型.blend> --python scripts/reference_model_views.py -- --object <对象名> --output-dir <项目目录>/preview/reference-models/canonical-vN
blender --background <模型.blend> --python scripts/blender_audit.py -- --output <项目目录>/preview/finishing/blender_audit.json
```

需要用户选型、参考包确认或最终验收的阶段，必须带用户明确确认：

```bash
python scripts/scene_kit.py advance <项目目录> --confirmed-by-user
```

在 `REVIEW` 阶段带用户明确确认执行 `advance --confirmed-by-user` 时，脚本会同时记录验收版本和验收时间。用户提出返工时使用 `reopen`，不得手工修改阶段字段。

数据结构和阶段门禁见 [data-model.md](references/data-model.md)。
