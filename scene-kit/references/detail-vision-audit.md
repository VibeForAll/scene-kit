# 视觉模型辅助细节复核

## 用途

当建筑十视图包含大量小尺度细节，单靠文字清单容易漏掉烟囱、屋脊附件、托架、壁灯、五金、植物或不同窗型时，使用本流程生成可追溯的诊断证据。

视觉模型是辅助审阅工具，不是验收权威：

- 可以提出候选对象、包围盒、数量和材质线索。
- 不能用单次模型输出直接把 `components.detail_audit.status` 写成 `pass`。
- 模型之间或模型与多视图之间矛盾时，必须写入 `unresolved`。
- 最终身份、数量、安装关系和几何处理方式仍由十视图与用户确认决定。

## 推荐组合

- `microsoft/Florence-2-base-ft`：详细描述和短语定位。适合找烟囱、门、窗、栏杆、灯、台阶、植物等候选区域。
- `dandelin/vilt-b32-finetuned-vqa`：独立视觉问答。适合对代表性裁剪做“是不是、是否木质、是否存在”的第二意见。

Florence-2 的定位结果常把烟囱、塔、塔帽或整栋建筑混在一起。遇到这类冲突，保留“烟囱或塔帽”复合名称，不能擅自选一个。

## 窗格与微结构专项

整窗详细描述和“总格数”问答不足以识别窗棂。窗、门、栏杆和格栅必须再从原始多视图裁出代表性构件，做一次近景复核：

1. 从正面和一个侧面/45 度视图分别定位同类构件。
2. 裁切时保留完整外框和安装边缘，把窗格区域放大 3–4 倍。
3. 先用 Florence-2 重新描述近景，再用 ViLT 分别确认主分区、中央再分列、行数、横向亮窗和材质身份。
4. 运行线位分析，记录可能的竖梃/横档位置；线位只是候选，不能自动指定格数。
5. 人工根据放大图和框料轮廓写出 `pattern`，至少包含主竖向分区、中央分列、总列数、总行数、横档数和总格数。
6. 检查 `总格数 = 总列数 × 总行数`，以及有中央分列时的列数关系。

示例：三个主竖向分区，中间分区再分成两列，四行，共 `4 × 4 = 16` 格。即使整窗 VQA 同时回答“12”和“16”，也必须继续检查哪一问与放大后的框料层级一致，不能取最高分直接通过。

`detail_vision_audit.py` 会把代表性 `window` 也加入局部裁剪，生成 `window_<view>_detail_4x.png`，并写出 `fine_structure_candidates.json`。其中 `vertical_line_ratios` 和 `horizontal_line_ratios` 是梯度峰值的归一化位置，用作复核线索。

最终把结果写入组件 `fine_structure_review`。`status=pass` 需要至少两个源视图、放大裁剪、视觉再识别说明、`confidence`、框/套/玻璃材质线索和空 `unresolved`。已建模组件的 `parametric_build.grid_columns`、`grid_rows`、`pane_count` 必须与 `pattern` 完全一致。

## 多参考材质共识

同一标签在十个视图中检测到多个实例时，脚本会为每个视角至少保留一个代表性裁剪，写入 `crops/multi_view/`，并生成每个标签的多视图接触表和 `multi_view_evidence.json`。每个裁剪同时输出最多 8 个主色、16 进制值和样本占比。

这些证据用于组件生成前的 `reference_consensus`：

1. 同一个组件的两个以上视角必须分别观察轮廓、结构、附着和材质。
2. 对主要材质角色比较各视角主色；木框不能只写“深色”，应区分暖褐、灰褐、红褐和黑漆。
3. 视觉模型的定性描述必须和多视图色相、放大裁剪、线位/尺寸证据交叉验证。
4. 某个视图过暗、过曝、被植物遮挡或白平衡明显不同，要解释它是否仍可用于材质判断。
5. 生成完成后，再与这些多个参考裁剪比较，不能只挑一张最接近的图确认通过。

## 隔离环境

以下示例使用 `uv` 和独立虚拟环境。模型权重体积较大，不应把依赖或权重写入技能包。

```powershell
$venv = "D:\AITools\scene-kit-vision"
uv venv $venv --python 3.14
uv pip install --python "$venv\Scripts\python.exe" `
  torch torchvision timm accelerate sentencepiece `
  "transformers==4.48.3" "tokenizers==0.21.1" "huggingface-hub<1.0" `
  truststore pillow
```

如果 Hugging Face 直连缓慢或证书异常，可在当前进程设置：

```powershell
$env:HF_ENDPOINT = "https://hf-mirror.com"
$env:HF_HUB_DOWNLOAD_TIMEOUT = "60"
```

Python 证书链异常而 PowerShell 网络正常时，在运行脚本的 Python 环境中安装并使用 `truststore`。脚本会自动调用：

```python
import truststore
truststore.inject_into_ssl()
```

## 执行

```powershell
& "$venv\Scripts\python.exe" `
  scripts/detail_vision_audit.py <项目目录> `
  --output-dir <项目目录>\preview\detail-scan
```

脚本从 `internal/concept_directions.json` 读取选中方向的 `view_paths`，要求十视图全部存在。

检查参考模型派生视图时，可绕过概念方向，直接指定模型派生十视图目录或映射文件：

```powershell
& "$venv\Scripts\python.exe" `
  scripts/detail_vision_audit.py <项目目录> `
  --view-dir <项目目录>\preview\reference-models\derived-views `
  --output-dir <项目目录>\preview\detail-scan-model-derived
```

模型派生视图是组件识别和拆件的主输入。原始概念十视图应另行扫描，作为模型幻觉、缺项和材质/纹理校验，不覆盖派生视图结论。

常用选项：

```text
--skip-vqa                 只做 Florence 描述和定位
--skip-focused-crops       只分析整栋十视图
--offline                  只使用本地缓存模型
--device cpu|cuda|auto     指定推理设备
--feature-phrases "chimney, window, door, railing, ..."
```

## 输出

输出位于 `preview/detail-scan/`：

```text
annotated-overview.jpg
annotated_<view>.jpg
detail_vision_audit.json
focused_detail_audit.json
fine_structure_candidates.json
multi_view_evidence.json
crops/
  <feature>_<view>.png
  window_<view>_detail_4x.png
  multi_view/
    <feature>_<view>.png
<feature>_multi_view_contact_sheet.jpg
```

`detail_vision_audit.json` 记录：

- 使用的模型、设备和时间。
- 十视图的详细描述。
- 十视图的短语定位框。
- 每个标签的逐视图数量和最大值。
- 代表性裁剪和独立 VQA 结果。

脚本不修改：

- `components.json`
- `progress.json`
- 阶段状态
- 用户确认记录

## 复核顺序

1. 对十视图逐张生成详细描述。
2. 用固定短语扫描 `chimney / window / door / balcony / railing / plant / vine / lantern / decoration / carving / steps / roof / tower`。
3. 优先从正、右、左、顶视图选取代表性对象并裁剪。
4. 对裁剪再次详细描述，运行针对性的独立 VQA；窗格必须补做微结构专项。
5. 将一个对象至少与两个视角或两种模型结果交叉核对。
6. 把一致结果写入 `detail_audit.features`。
7. 把数量冲突、身份冲突或安装关系不清的项写入 `detail_audit.unresolved`。
8. 只有完成这一步并得到用户确认，才允许 `detail_audit.status=pass`。

## 结果判定

- **高可信**：两个以上视图定位一致，并且详细描述/VQA 不冲突。
- **中可信**：只有一个视图定位清楚，但局部特写描述支持该对象。
- **低可信**：模型互相矛盾，或换视角后找不到对应构件。
- **不能通过**：对象身份、数量或安装关系仍未解决。

对于烟囱、塔楼、山墙尖顶等外形相近的构件，优先记录复合候选和不确定项，不要为了得到“通过”而强行分类。
