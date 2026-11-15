# 项目交付目录与过程证据

本规范约束 `COMPLETE` 前的项目整理，也适用于用户中途要求“清理目录”。目标是让最终模型容易找到，同时保留原始输入、参考分析、材质对照和 GitHub 过程插图。

## 推荐结构

```text
project/
|-- README.md
|-- scene.json
|-- progress.json
|-- components/
|   |-- README.md
|   |-- index.json
|   |-- <part_id>.blend
|   `-- <part_id>.glb
|-- assembly/
|   |-- README.md
|   |-- <building>_assembly.blend
|   `-- <building>_assembly.glb
|-- reference/
|   |-- <reference_model>.blend
|   |-- <reference_model>.glb
|   `-- <structured_reports>.json
|-- assets/
|   |-- raw/
|   |   |-- concepts/
|   |   |-- generation-inputs/
|   |   `-- manifest.json
|   `-- preview/
|       |-- concepts/
|       |-- reference/
|       |-- components/
|       |-- assembly/
|       `-- manifest.json
|-- concepts/
|   `-- manifests, prompts, reviews
|-- internal/
|-- textures/
`-- scripts/
```

`raw/` 和 `preview/` 不作为最终项目根目录的并列文件夹。它们统一放在 `assets/` 下。模型最终交付文件也不在 `assets/` 中重复复制。

## 每类文件只放一处

- 原始概念视图、生成输入裁剪和未经重绘的来源图：`assets/raw/`。
- 参考模型派生视图、组件参考裁剪、单件材质 QA、整栋审阅图和近景：`assets/preview/`。
- 最终组件 Blender 源文件与 GLB：`components/`。
- 最终整栋 Blender 源文件与 GLB：`assembly/`。
- 参考模型 Blender/GLB 及结构化报告：`reference/`。
- 尺寸合同、组件合同、门禁和哈希记录：`internal/`。

同一图片被审计 JSON、组件 README 和项目 README 引用时，保留一个文件，通过相对路径重复引用，不复制副本。缩略图或拼图只有在尺寸和用途确实不同、且能说明它们是派生图时才单独保存。

## GitHub 插图

根 `README.md` 至少展示：

1. 当前整栋 hero 或装配总览。
2. 选中的参考十视图总览。
3. 关键构件参考对照，例如局部误判修正或材质共识。

使用仓库相对路径，例如：

```markdown
![装配总览](assets/preview/assembly/assembly_contact_sheet.jpg)
![参考十视图](assets/preview/reference/canonical-vN/canonical_ten_view_contact_sheet.jpg)
![关键构件对照](assets/preview/components/part_id/part_id_material_comparison.jpg)
```

`components/README.md` 列出每件组件的类型、三角面、Blender 源文件、GLB 和一张最终 QA 对照入口。过程图用于人理解设计依据，不代表它可以替代结构化质量门禁。

## 清理与迁移规则

1. 先读取 `progress.json`、组件合同、装配记录和 README 引用，生成“保留 / 移动 / 删除”清单。
2. 原始输入、参考分析、最终 QA 和用户查看过的对照图默认保留；不要因为目录整理而删除唯一过程证据。
3. 只有以下内容可以删除：重复副本、明确被最终 revision 取代的旧构建、临时缓存、失败中间文件、已经完成迁移的旧路径容器。
4. 删除或移动前确认目标都在项目根目录内，并检查目标路径不存在冲突。
5. 移动文件后同步更新 JSON、Markdown 和资产索引中的相对路径；不要只移动图片。
6. 写 `internal/media_structure_vN.json` 或等价迁移记录，说明 raw、preview、最终源文件和交付文件的去向。
7. 重新运行 `scene_kit.py validate`、参数合同验证、关键导入检查和相对路径断链扫描。
8. 根 README 展示最终结果与少量关键过程图；其余过程图保存在 `assets/preview/`，不把大量截图堆到项目根目录。

## 版本迭代清理

“删除迭代版本”指删掉已经被当前 revision 完整取代的构建、重复 QA 图组、`.blend1`、临时缓存和错误嵌套路径，不是删除 `assets/raw/` 与 `assets/preview/` 的过程证据。

- 原始图、生成输入和用户明确要求保留的 before/after 对照，只保留一份，继续用于验收和 README/GitHub 插图。
- 每个被修改的组件在源文件、材质或尺寸发生变化后，生成一套当前 QA 和审计；新套件通过后，再删除同一组件被完整取代的旧图组，避免新旧版本并列。
- 未变化的组件继续保留其当前 QA，不因为其他组件升级而整体删除。
- 用户提出的重要返工保留一张精简“问题 → 修复”过程图，例如漏掉的屋顶、错误数量或穿插关系；不保留每一轮全分辨率截图。
- 清理前用 JSON/Markdown 引用扫描确认当前有效文件；迁移记录中的 `removed` 列表属于历史，不应反过来作为断链扫描的必需文件清单。
- 根 README 展示最终整栋、参考十视图、关键过程对照；`components/README.md` 展示最终组件表。图片通过相对路径复用，不复制第二份。

## 完成条件

- 根目录没有临时 `raw/`、`preview/`、`out/`、`export/` 工作区。
- `components/` 中每件组件都有可追溯的 Blender 源文件、GLB、参数合同和 QA 入口。
- `assembly/`、`reference/`、`assets/raw/`、`assets/preview/` 的职责清楚且无重复资产。
- JSON、README 和图片链接全部有效。
- GitHub README 能直接展示最终成果、参考依据和关键过程节点。
