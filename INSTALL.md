# Scene Kit 7.23 安装说明

Scene Kit 是一个概念图优先的模块化建筑工作流：

1. 用文生图探索整栋建筑方向。
2. 由用户选择一个概念。
3. 从特征完整的视图先生成整栋三维参考模型。
4. 先验证参考模型质量，再用统一缩放和固定正交相机轨道派生十视图。
5. 从网格连通岛和模型派生多视图建立可追溯的组件候选，再把三维空间关系和附属结构映射到每个组件。
6. 用中性轮廓控制接口，用概念图和提示词保留单件造型创造力。
7. 把浮雕、植物等非结构表现资产拆成独立模型。
8. 拆件图片回到原始多视图复核，确认完整、合理、可连续装配。
9. 在 Blender 中归一化、实例化、装配，再做最终面片、材质和构造逻辑精修。
10. 既和参考图比较，也做屋檐/门窗/支撑等智能逻辑分析，自行修补悬空和松脱。
11. 通过当前 revision 的最终验收并导出。
12. 把用户确认复用价值的资产加入跨项目模型库。

7.18–7.20 新增的门禁：

- 7.18：整栋精修阶段必须为实时组件实例生成正面透明轮廓遮罩，检查塔楼、窗、门套和装饰之间的真实遮挡与穿插。
- 7.19：正视图审计从当前 `.blend` 枚举实例，不依赖可能过期的旧装配 JSON；同时核对实例数量、植物可见性和立面层数窗数。
- 7.20：数量先于几何。`quantity_audit` 按立面 × 楼层记录窗门，分开统计主屋顶、小屋顶、烟囱石柱/石帽/烟管和重复装饰；数量不一致时不能通过。

7.21：所有前置构件必须说明背面、侧向体积、前凸深度和宿主连接。屋顶窗和老虎窗不能只做正面窗片、屋顶片或与宿主共面的薄墙；附着屋顶不能越过主檐，必须覆盖房体后墙顶部。审计写入 `attachment_integrity_audit`。

7.22：固定十视图仍是必查主视图。若某个细节仍不明确，可以从同一归一化参考模型临时补拍局部近景或斜向诊断视角；这些图片可以只用于识别、不要求保存，也不进入参考包或最终交付。相关观察仍需与既有十视图或原始素材交叉确认。

7.23：所有藤蔓、盆栽、花簇、灌木和草本模块统一采用“藤蔓级”有机标准。不得用直杆枝条、重复扁平菱形叶片、单色叶冠或只有正面的贴片植物交付。程序化模块必须通过弯曲渐细枝网、密集小叶、三档叶色、叶尖芽和冠层填充门禁；AI 3D 与模型库资产也必须完成同等含义的多视图视觉检查并写入 `organic_quality`。薄叶片允许开放壳，但无线边、零面积面、漂浮叶和错误透明面仍不能通过。

## 安装

把整个 `scene-kit/` 目录复制到目标工具的 skill 目录：

- Codex：`~/.codex/skills/scene-kit/`
- Claude Code：`~/.claude/skills/scene-kit/`
- Trae 项目级：`<项目根>/.trae/skills/scene-kit/`

必须同时复制以下内容：

```text
scene-kit/
  SKILL.md
  agents/openai.yaml
  references/
  scripts/
```

不能只复制 `SKILL.md`。

## 初始化项目

```powershell
python C:\path\to\scene-kit\scripts\scene_kit.py init .\scene-project --name "二层欧式小楼"
python C:\path\to\scene-kit\scripts\scene_kit.py validate .\scene-project
```

## 核心命令

```powershell
python ...\scene_kit.py validate .\scene-project
python ...\scene_kit.py prompts .\scene-project
python ...\scene_kit.py advance .\scene-project
python ...\scene_kit.py advance .\scene-project --confirmed-by-user
python ...\scene_kit.py reopen .\scene-project FINISHING --reason "返工原因" --confirmed-by-user
blender --background .\scene-project\internal\<模型>.blend --python ...\blender_audit.py -- --output .\scene-project\preview\finishing\blender_audit.json
python ...\detail_vision_audit.py .\scene-project --output-dir .\scene-project\preview\detail-scan
python ...\generation_route_audit.py .\scene-project
python ...\parametric_components.py validate .\scene-project
python ...\parametric_components.py hash .\scene-project <part_id>
python ...\parametric_components.py refresh-build .\scene-project <part_id>
python ...\polyhaven_search.py "dark oak wood" --type textures --limit 10 --output .\scene-project\internal\polyhaven-dark-oak.json
python ...\reference_feature_scan.py .\scene-project\preview\reference-models\canonical-v5\reference_model_report.json --output .\scene-project\internal\reference_feature_candidates.json
blender --background <参考模型.blend> --python ...\reference_model_views.py -- --object <对象名> --output-dir .\scene-project\preview\reference-models\canonical-v5
blender --background <墙体.blend> --python ...\generate_wall_envelope.py -- --project .\scene-project --parameters .\scene-project\internal\wall_variant.json --material-name MAT_wall_envelope_OldStoneWall_v1 --output-blend .\scene-project\out\wall_variant.blend
blender --background <窗体.blend> --python ...\generate_window_assembly.py -- --project .\scene-project --parameters .\scene-project\internal\window_variant.json --stone-material <石材> --wood-material <木材> --glass-material <玻璃> --output-blend .\scene-project\out\window_variant.blend
blender --background <屋面.blend> --python ...\generate_roof_system.py -- --project .\scene-project --parameters .\scene-project\internal\roof_variant.json --roof-material <石板> --gable-material <山墙石材> --ridge-material <屋脊石材> --fascia-material <檐木> --gutter-material <天沟金属> --output-blend .\scene-project\out\roof_variant.blend
blender --background <烟囱.blend> --python ...\generate_stone_chimney.py -- --project .\scene-project --parameters .\scene-project\internal\chimney_variant.json --stone-material <石材> --cap-material <帽石> --flue-material <金属> --moss-material <苔藓> --output-blend .\scene-project\out\chimney_variant.blend
blender --background <入口.blend> --python ...\generate_entrance_portal.py -- --project .\scene-project --parameters .\scene-project\internal\entrance_variant.json --stone-material <门套石材> --wood-material <门扇木材> --iron-material <暗铁五金> --output-blend .\scene-project\out\entrance_variant.blend
blender --background --python ...\ensure_modeling_extensions.py -- --install --output .\scene-project\internal\toolchain.json
```

`blender_audit.py` 只读统计当前场景的网格、拓扑、缩放、材质和外部图片状态，并写出 JSON 报告。它不修改 `.blend`，也不能代替设计、构造或导出验收；执行规范见 `references/blender-production.md`。

7.14 起报告还包含 `texture_mapping_audit`，逐个图片节点记录图片分辨率、投影方式、坐标来源、映射缩放和拉伸风险。每次组件生成或材质修改后都要运行该审计；`FLAT` 配 `Object/Generated` 坐标在厚墙和多个朝向的物体上会漏掉轴向，必须改为经过验证的 UV、Box Projection 或逐面映射。

`detail_vision_audit.py` 是本机视觉诊断工具，用来补足烟囱、屋面附件、托架、窗型、灯、栏杆、台阶和植物等小尺度细节。默认使用 Florence-2 做十视图描述和短语定位，再用可选的 ViLT VQA 做代表性裁剪复核；窗类构件会额外保存 4 倍近景并输出线位候选。脚本还保留同一标签的多视图裁剪和调色板，供 `reference_consensus` 交叉验证。它只写 `preview/detail-scan/` 证据，不修改项目状态，也不能自动把 `detail_audit`、`fine_structure_review` 或 `reference_consensus` 判为通过。依赖隔离、模型缓存和判定规则见 `references/detail-vision-audit.md`。

使用 `--view-dir <参考模型派生十视图目录>` 可直接对 `model_derived_views` 做组件定位和裁剪。模型派生视图是组件识别与拆件的主输入；原始图扫描用于验证模型幻觉并补充可靠材质和微细纹理。

`ensure_modeling_extensions.py` 在建模、AI 3D 后处理、装配或精修前检查 Archimesh、MeasureIt、3D Print Toolbox、LoopTools、Edit Mesh Tools、CAD Sketcher、Surface Diagnostics 和 CurioMesh。缺少时从 Blender 官方扩展目录按当前平台下载、校验 SHA-256、安装并启用，结果写入 `internal/toolchain.json`。只有 `ready=true` 才能继续依赖该工具链的步骤；详细说明见 `references/modeling-extensions.md`。

`generation_route_audit.py` 在提交 Tripo 前比较 Blender 参数化、手工建模、资产库和 AI 3D 路线。重复规则构件、精确接口和可由修改器稳定建立的组件优先 Blender；只有造型价值高、参考清楚、可本地清理且无需精确尺寸时才选 Tripo。精确门窗和栏杆至少需要正面与侧面/45 度参考，并提前写 `triangle_budget` 与 `low_poly_strategy`。报告写入 `internal/generation_route_review.json`，最终理由写入组件 `route_assessment`；完整规则见 `references/generation-routing.md`。

7.11 起，组件执行评估前必须先完成整栋三维参考模型和组件特征映射。参考模型从特征完整的 3/4 视图或同一对象多视图生成，减面后标记为 `reference_only`。7.12 规定模型派生十视图成为组件识别主输入；7.13 进一步要求先用 `reference_quality` 验证实际网格、主体体量、屋顶、洞口和附着关系，再用统一缩放与共享中心固定正交相机轨道渲染视图，并把结果写入 `camera_rig` 和 `derived_view_validation`。顶部/底部视图遇到开放壳体或缺底时应标为低可信，不能用于主要组件识别。7.14 要求每个组件完成贴图映射、物理尺度和跨立面拉伸审计。只有参考质量、归一化、相机轨道、视图验证和组件映射全部通过且 `analysis_ready=true`，脚本才允许进入拆件、参考包、组件生成和装配。

7.15 要求所有组件登记参数化合同。`parametric_components.py scaffold` 可为项目建立合同骨架，`validate` 检查每个组件是否有当前有效的参数指纹、输出文件、几何审计和材质对照。参数或材质变化后，旧审计失效，新变体必须重新生成并重新验收。详细结构见 `references/parametric-components.md`。

`reference_model_views.py` 从同一个模型中心渲染固定正交十视图，生成相机记录、网格连通岛报告和可选组件裁剪。默认只做统一缩放，禁止用估算占地非均匀拉伸模型。`reference_feature_scan.py` 输出窗、门、烟囱、屋顶和墙体的诊断候选池，并按三维包围盒邻接关系生成 `candidate_clusters`；聚类只用于收拢同一构件的碎片，不能直接当作最终语义组件。最终拆件必须用至少两个模型派生有效视图和原始多视图交叉确认。

`polyhaven_search.py` 使用 Poly Haven 公开 API 搜索免费 CC0 纹理、模型和 HDRI，不需要付费 Blender 插件。每完成一个组件后，必须赋最终材质并重新渲染至少两个视图；有材质差异时先检索 Poly Haven，没有合适素材才生成本地贴图。结果写入 `qa.material_review`，`polyhaven_checked` 必须为 true。Poly Haven Blender 插件需要购买或 Patreon 支持；若用户已有授权 ZIP，可自行安装，技能不会绕过授权。详见 `references/material-texture-validation.md` 和 `references/polyhaven-assets.md`。

## 跨项目模型库

默认模型库位于 `~/.scene-kit/model-library`。可以设置环境变量 `SCENE_KIT_LIBRARY`，或在每条命令中使用 `--library <目录>`。

```powershell
python ...\scene_kit.py library-init
python ...\scene_kit.py library-search "floral stone relief" --asset-class decorative_ornament
python ...\scene_kit.py library-add .\scene-project stone_relief_01 --confirmed-by-user
python ...\scene_kit.py library-link .\scene-project stone_relief_01 <asset_id> --confirmed-by-user
python ...\scene_kit.py library-list
python ...\scene_kit.py library-validate
```

模型库规则见 `references/model-library.md`。只有在用户明确确认后才可入库或把库资产设为当前项目组件。

需要用户明确确认的阶段：

- 完成 3 个概念方向后，选中一个方向。
- 确定组件拆分和自由区后。
- 确认单件参考包并允许进入 AI 3D 生成前。
- 组件通过 QA 后是否加入模型库。
- 是否采用模型库候选替换当前项目的生成计划。
- 整栋验收通过后。

## 验证技能

```powershell
python ...\scripts\test_scene_kit.py
python C:\path\to\skill-creator\scripts\quick_validate.py C:\path\to\scene-kit
```

## 重要边界

- 概念图不是精确施工图。
- 整栋灰盒和整栋精修图只能用于审阅和风格参考。
- AI 3D 的几何参考必须是单件中性轮廓。
- 拆件裁剪必须回到至少两个原始多视图复核，确认完整、隔离且安装关系可解释。
- `COMPONENTS` 必须完成十视图细节特征扫描，烟囱、屋脊饰、托架、檐沟、台阶、五金和装饰小件不能因尺度较小而遗漏；`detail_audit` 未通过时不得进入参考包或生成。
- 拆件前必须先完成整栋三维参考模型、减面、多视图归一化和全部组件特征映射。整栋模型只用于空间与结构侦察，不能直接当最终拆件网格。
- 参考模型质量通过不等于拓扑水密；必须记录单图推断、开放壳体、碎片和尺寸偏差等局限。
- 十视图必须使用共享中心的固定正交相机轨道。顶/底视图低可信时必须说明原因，主要拆件使用正面、背面、左右侧和四个 45 度视图。
- 网格连通岛编号只用于追溯候选。不得把一个碎片或融合面直接声明为完整窗、门或烟囱；最终组件身份、数量和边界必须多视图确认。
- 窗、门、栏杆和格栅必须用放大裁剪确认重复拓扑，并写入 `fine_structure_review`；窗格总列数、总行数和总格数必须一致，不能只凭整窗问答估算。
- 每个组件在建模或 AI 3D 生成前必须建立 `reference_consensus`：至少两个视角、两个裁剪、两个视角的材质 RGB 样本和六项一致性检查。单张参考或单个模型回答不能独立确认。
- 每个组件还必须建立 `boundary_review`：检查六个面、整体包围盒、安装接口、附件结构和材质分区。窗、门、栏杆等不能只做正面平面；窗台、窗套、托架、披檐等附着物按多视图判断纳入同一组件或明确拆分。
- 生成后的成品必须与多个视角参考对照；材质颜色不能根据“dark”“black”名称直接判断。
- 每个组件通过材质 QA 前必须写入 `texture_audit`，并确认图片已加载、投影轴有效、物理尺度一致、正视/侧视/3/4 无明显拉伸，且法线与粗糙度使用同一映射。
- Tripo 的 `quality=standard` 不是目标面数保证。接口没有面数控制时先生成，再在 Blender 中按 `triangle_budget` 减面/重拓扑并复检。
- 装配完成不等于可交付；必须通过 `FINISHING` 的面片、材质、接缝和构造逻辑审查。
- 屋檐、门廊、老虎窗、凸窗、塔楼、栏杆和檐沟等出现悬空或松脱时必须自行修补，不能留给用户在验收时发现。
- 尺寸最终由 Blender 中的锁定接口校准，不由图片像素决定。
- 没有实际工具结果时，不得声称模型、图片或截图已经生成。
