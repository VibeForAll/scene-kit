# Blender 执行、审阅与交付

在操作现有 `.blend`、通过 Blender MCP 修改场景、制作阶段审阅图或执行最终导出检查时读取本文件。它补足设计门禁之外的现场执行纪律，不替代 `progress.json`、尺寸合同和 `FINISHING` 记录。

## 执行前

动手前先取得真实场景状态：

- 当前 `.blend` 路径、Blender 版本、场景单位与单位比例。
- 对象、集合、相机、灯光、材质和外部图片的数量与当前可见状态。
- 现有模型是否已经完成部分装配或精修。已有文件默认在原文件上修改，不因任务描述简单就从头重建。
- 当前 revision 的基准截图。需要比较修复效果时，保留修复前截图作为证据。

Blender MCP 可用时直接查询和修改场景，不只向用户描述界面操作。MCP 不可用时，才给出最小可执行的手动步骤。每次较大的建模、材质、灯光、装配或修复操作后重新查询场景状态；没有工具结果时，不声称场景已经改变。

破坏性操作前保存工作副本或版本化备份。不要用未经验证的批量删除、全局重命名、应用修改器或清除材质覆盖用户资产。

## 扩展预检

开始参数化建模、AI 3D 后处理、装配或精修前，运行：

```bash
blender --background --python scripts/ensure_modeling_extensions.py -- \
  --install --output <项目>/internal/toolchain.json
```

只有 `ready=true` 才能继续依赖该工具链的步骤。默认检查并安装 Archimesh、MeasureIt、3D Print Toolbox、LoopTools、Edit Mesh Tools、CAD Sketcher、Surface Diagnostics 和 CurioMesh。脚本使用官方扩展目录、按当前平台选包、校验 SHA-256 并启用；安装失败的扩展必须明确记录，不能用其他未经验证的工具冒充。详细说明见 [modeling-extensions.md](modeling-extensions.md)。

## 组织与命名

新项目和新建对象使用以下默认规则；旧项目不为了整齐而强制重命名，只需把现有名称映射到项目数据。

```text
SK_COL_Structure       结构、墙、屋面、楼板
SK_COL_AI              AI 3D 单体
SK_COL_Library         模型库复用资产
SK_COL_Ornament        浮雕、木雕、铁艺和雕塑
SK_COL_Vegetation      植物
SK_COL_Site            花盆、壁灯、长椅和场地点景
SK_COL_Finish          最终补件和收口
SK_COL_Lights          灯光
SK_COL_Cameras         审阅与交付相机
SK_COL_Review          地面、背景和审阅辅助物
SK_COL_Reference       不可进入交付的参考物
SK_COL_Debug           重复、碰撞和临时检查物
```

默认命名：

- 对象：`SK_<PartID>_<Role>_<Variant>`。
- 材质：`MAT_<Project>_<Surface>_<Variant>`。
- 审阅相机：`CAM_Review_<Front|Back|Left|Right|Top|FrontLeft45|Hero|Closeup>`。
- 灯光：`LGT_<Key|Fill|Rim|Practical>_<Purpose>`。
- 导出集合与临时审阅物分开，参考物、调试物和隐藏对象不得混入最终导出。

一个完整组件可以由父对象和多个按材质/功能划分的子对象组成。例如窗户可包含木框、玻璃、石窗套和向外突出的石窗台；这些子对象都应归入同一组件层级，并分别保留材质槽。不要把窗台留在墙体里、把玻璃做成无厚度面片，或只导出正面框格。

## 阶段审阅视图

任何视觉结论都要有当前 revision 的截图支持。不要复用修复前或旧版 `.blend` 的截图。

| 场景 | 最低截图 |
|---|---|
| 单件生成后的 QA | 中性正面、侧面、3/4；有对应参考时再加同角近景和并排对照 |
| ASSEMBLY | 正面或背面正交、侧面正交、俯视正交、hero 3/4 |
| FINISHING | 当前 hero 3/4、正面/背面、关键近景，以及问题区域的线框或材质检查视图 |
| 参考图对照 | 与参考同方向、同镜头感和近似构图的当前截图；必要时并排或叠放 |
| REVIEW | 当前 revision 整栋图、关键局部、参考对照和面片近景 |

建筑比例和接口优先用正交视图判断；用户效果判断用校正透视的 hero 视图。相机角度、镜头和主体占比在比较前固定，避免每轮换机位后误判“已经修好”。

审阅至少分开检查：

- 轮廓、比例、体量和门窗节奏是否与选中概念一致。
- 目标镜头下的表面质量和材质是否可信。
- 支撑、连接、收口、洞口和装配关系是否能解释。
- 隐藏对象、参考物、灯光辅助物和导出对象是否被误纳入了画面或交付。

### 正视图组件遮挡与干涉审计

整栋装配和 `FINISHING` 必须单独检查正面正交投影。最终截图不能代替逐组件检查，因为相邻构件在渲染中可能只显示最前面的一层，无法看出后方的窗、门套、栏杆或装饰是否被不合理遮挡。

执行顺序：

1. 固定 `CAM_ASM_front_ortho` 的中心、方向和正交尺度，不逐组件重新取景。
2. 从当前 `.blend` 枚举实际组件实例和网格；`assembly.json` 或 `components.json` 中的旧根对象只能辅助映射 `part_id`，不能决定本次审计覆盖哪些实例。实例根对象应能以 `_ROOT` 识别或带有明确实例元数据；不能把同一层级下的材质子网格重复当成实例。
3. 先比较合同实例总数与实时实例数，再按 `part_id` 比较每类实例数量。窗、植物和关键建筑体量必须达到合同数量；空遮罩不能算“已经摆放”。
4. 立面存在槽位/洞口合同（如 `wall_openings_vN.json`）时，按实例的立面、楼层和轴线位置硬校验每面每层窗数、门轴跳过规则和洞口合同；发现数量不符时停止并以合同和参考图重新排布，不靠移动塔楼掩盖错误。
5. 为每个实时组件实例渲染独立透明轮廓遮罩，只显示该实例的网格。
6. 在当前正面渲染上叠加组件轮廓包围框、组件名和实例名。
7. 计算不同组件遮罩之间的真实重叠像素，同时记录前后方向上的世界空间深度范围。
8. 使用项目允许关系表区分墙体/窗洞、屋面/墙体、植物/附着面等预期接触，以及塔楼/窗、门套/装饰、同层洞口等异常重叠。新发现的非预期重叠应修几何或位置，不应只把关系表改成 allowed。
9. `tower_window_overlaps`、空实例遮罩、数量不一致或任何未解释的 `review_required` 重叠都必须修复，并重新生成当前 revision 的遮罩和正视图。

```bash
blender --background <整栋.blend> --python scripts/assembly_front_visibility_audit.py -- --project <项目>
python scripts/analyze_front_visibility.py --project <项目>
```

输出至少包括：

- `<项目>/internal/assembly_front_visibility_audit.json`
- `<项目>/assets/preview/assembly/front_component_visibility_overlay.jpg`

报告还应记录实时实例数、合同实例数、各 `part_id` 实例数、立面层数窗数、窗轴中心、植物遮罩可见像素和所有空遮罩。包围盒重叠只能作为粗筛。尤其对圆塔、锥顶、斜屋面、弧形栏杆等形体，必须使用实际轮廓遮罩或网格相交结果；不能用包围盒扫到窗就宣布干涉，也不能因为包围盒没交点就宣布安全。Blender 给重复对象自动添加 `.001` 等后缀时，应统一实例根名称或使用实例元数据识别；不能因为名称匹配失败而静默缩小审计范围。

## 参考图对照循环

有参考图时，先写分析，再改模型：

1. 记录主体、主要体块、比例、相机、镜头感、主体占画面比例、主光方向、材质、5–8 个代表色和必须出现的特征。
2. 先锁定审阅相机和构图，再比较 Tier 1 大轮廓、Tier 2 进深与构件分层、Tier 3 窗格、线脚和雕花。
3. 当前截图与参考同图幅展示，按“相机 → 轮廓/比例 → 体块进深 → 材质/色彩 → 灯光/曝光 → 关键特征”顺序列最多五个差异。
4. 只修当前最上层差异，重新截图后再进入下一层。
5. 记录仍存在的差异及严重度。`blocker/high` 未修复时不能通过；`medium/low` 只能是明确记录后的残余差异。

这个循环用于本地修面、材质、灯光和构造关系，不能用来掩盖缺失结构。需要新的付费 AI 3D 生成时，仍按 `cost-and-repair.md` 判断，不以截图轮数作为重生成理由。

## 返工回归检查

用户指出漏构件、数量、干涉、材质或构造错误后，先把反馈写成回归事实，再修当前场景：

- 检查整栋参考模型的 `component_map`、`detail_audit`、`quantity_audit` 和实时装配是否都包含该对象或数量。
- 所有尺寸变更只应用一次。比较独立组件源和装配层级的包围盒、对象数量、三角面、原点与材质绑定；优先重新生成或从已验证装配重建源文件，避免二次缩放。
- 颜色、材质语义和纹理方向分别验收。颜色采样通过不能替代石板/木板/金属等表面类型与真实平铺尺度检查。
- 修复后重新运行数量、正视遮罩、网格/贴图、组件 QA 和整栋当前视图。只更新一张最终截图不算完成。

## 材质与贴图复审

每个组件完成后必须赋最终材质、完成静态材质与投影审计，并渲染至少正面、侧面和 3/4 中的两个视图与参考对比。渲染图保存在项目中；是否逐张放进聊天只影响展示，不影响门禁。

材质不匹配时：

1. 检查 Poly Haven Assets 插件是否已授权安装。
2. 无插件时运行 `polyhaven_search.py` 搜索免费 CC0 纹理、模型或 HDRI。
3. 使用合适素材并设置真实世界纹理尺度；检查图片节点的投影方式、坐标来源，以及颜色、法线、粗糙度是否使用同一套映射。
4. 没有合适素材时才生成本地贴图或程序化材质。
5. 运行 `blender_audit.py`，读取 `texture_mapping_audit`。`FLAT + Object/Generated` 用在厚墙或多个朝向的物体上时，必须确认没有漏掉竖向轴；有拉伸时改用 UV、Box Projection 或按面建立的可验证投影。
6. 重新渲染当前 revision 的正面、侧面和 3/4，并把渲染图、对照图、Poly Haven 检查、材质来源、贴图映射证据和检查结果写入 `qa.material_review`。

详见 [material-texture-validation.md](material-texture-validation.md) 和 [polyhaven-assets.md](polyhaven-assets.md)。

## 场景审计

`scripts/blender_audit.py` 是只读辅助脚本，用来把目测问题变成可复查的现场数据：

```bash
blender --background <模型.blend> --python scripts/blender_audit.py -- \
  --output <项目>/preview/finishing/blender_audit.json
```

在 Blender MCP 中可执行：

```python
import importlib.util
from pathlib import Path

script = Path(r"<skill>/scripts/blender_audit.py")
spec = importlib.util.spec_from_file_location("scene_kit_audit", script)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
report, report_path = audit.audit_scene(r"<项目>/preview/finishing/blender_audit.json")
```

脚本在无法确定输出位置时，会把报告写到当前 `.blend` 同级的 `preview/finishing/blender_audit.json`。它统计场景单位、对象与集合、三角面数、零面积面、非流形边、边界边、线边、孤立顶点、重复边面、零/负缩放、缺失材质槽和丢失的外部图片，并列出审阅相机。7.14 起还输出 `texture_mapping_audit`：每个图片节点的图片、分辨率、投影、坐标来源、映射缩放和拉伸风险。

审计报告是证据，不是验收结论。脚本无法判断：

- 建筑是否长得像选中概念；
- 屋檐、门廊、老虎窗和凸窗是否具有合理的受力与构造逻辑；
- 构件比例是否正确，门窗是否为真实洞口；
- 材质是否符合设计合同，PBR 尺度和贴图投影是否合理；
- 目标平台是否接受最终面数、材质和导出格式。

这些仍要结合当前截图、项目数据和用户目标人工判断。报告中出现计数时，先确认它属于真实缺陷还是允许的开放面、临时参考物或有意保留的独立壳，再进行修复。

## 最终检查

导出前至少确认：

- 场景单位和真实尺寸正确；建筑垂直方向与项目轴一致。
- 关键对象原点、朝向和接触面与 `locked` 数据一致；异常负缩放和零缩放已处理。
- 每个前置构件都有可解释的背面、侧向体积和宿主连接；屋顶窗不能是悬浮窗片，雨棚/阳台不能缺少支撑，宿主接触有网格或几何审计证据。
- 每个被修改组件的独立源文件与整栋装配具有一致的尺寸、对象数量和材质绑定，未发生重复横向缩放。
- 目标视角没有破洞、零面积面、翻转法线、黑缝、Z-fighting、明显 UV 拉伸或孤立碎片。
- 墙体、屋面、门窗洞、台阶、檐沟、栏杆和装饰件具有合理连接、支撑和安装面。
- 正面透明轮廓遮罩审计通过；没有未解释的组件遮挡或穿插，当前正视叠加图已登记。
- 重复构件使用实例、集合实例或共享材质；高清模型没有无理由复制成大量独立副本。
- 审阅相机、参考物、调试物和临时地面没有误入导出集合。
- 外部图片、贴图和链接文件存在；材质槽没有明显缺失或误用。
- 按目标格式完成一次实际导出，并在重新导入或目标查看器中验证单位、轴向、材质和贴图。
- 通过同一 revision 的 `.blend`、截图和参考对照复核导出的对象，而不是只检查旧截图。

## 判定

最终记录使用：

- `PASS`：当前 revision 的关键视图无 `blocker/high`，必备截图和审计证据齐全，构造关系可解释。
- `REPAIR_REQUIRED`：存在可见高严重度缺陷、缺失证据、构造断开或导出失败，必须继续修复。
- `USER_DECISION_REQUIRED`：只剩会改变设计意图、交付范围或许可的歧义，需用户明确选择。

以下情况自动不允许 `PASS`：

- 没有当前 revision 的关键截图，或截图中可见 `blocker/high` 问题。
- 审计记录、`.blend` 哈希和 `FINISHING` revision 不对应。
- 屋檐、门廊、凸窗、塔楼、栏杆或屋檐排水关系明显悬空、断开或无法收口。
- 用挡片、贴图、灯光或隐藏对象掩盖结构缺陷。
- 未实际导出或未验证时声称目标平台已经可用。
