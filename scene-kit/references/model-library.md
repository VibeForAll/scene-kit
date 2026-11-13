# 跨项目模型库

模型库用于保存已经通过项目 QA、值得在后续项目中复用的独立 3D 资产。它解决两类问题：

1. 用户上传的视图中，浮雕、木雕、铁艺饰件、花簇、藤蔓、盆栽和场地点景等非结构表现资产不能被墙体或植物贴图吞掉，需要拆成可独立生成的模型。
2. 多个项目反复需要门窗、栏杆、浮雕或植物时，先检索已有资产，由用户决定复用还是重新生成。

模型库只保存用户明确同意入库的资产。生成完成、QA 通过和项目验收都不等于自动授权入库或跨项目复用。

## 默认位置

默认目录：

```text
~/.scene-kit/model-library/
  catalog.json
  assets/
    <asset_id>/
      model.glb
      comparison.png
```

可以用环境变量 `SCENE_KIT_LIBRARY` 指定其他位置，或在每条命令中传 `--library <目录>`。多个项目应指向同一个模型库目录。

## 资产分类

组件拆解时必须同时记录建筑组件和非结构表现资产。允许的 `asset_class`：

| `asset_class` | 典型内容 | 处理原则 |
|---|---|---|
| `architectural_component` | 门、窗、栏杆、柱、门廊、檐口构件 | 锁定接口优先，可参数化或 AI 3D |
| `decorative_ornament` | 浮雕、木雕、线脚、徽章、铁艺花纹、雕塑 | 从墙面或构件中独立出来，保留清楚正面和安装背面 |
| `vegetation` | 花簇、草、藤蔓、灌木、树、垂植 | 生成有代表性的单株或小簇，再实例化；不为每片叶子单独生成 |
| `site_element` | 壁灯、花盆、长椅、标牌、小喷泉 | 独立放置，记录地面或墙面锚点 |
| `structure` | 墙段、屋面、楼板、基础、楼梯 | 优先参数化或库复用，避免逐块 AI 生成 |

`type` 记录具体语义，例如 `window`、`door`、`stone_relief`、`flower_cluster`、`vine` 或 `wall_lantern`。不能只写笼统的 `decoration`。

## 从用户视图拆出资产

在 `COMPONENTS` 阶段，逐张查看选中方向的十视图，不只寻找门窗和屋架。至少扫描以下内容：

- 门、窗、栏杆、柱、檐口、托架、门廊和屋顶构件。
- 有实际厚度的浮雕、木雕、徽章、线脚和铁艺花纹。
- 花箱、花簇、草、藤蔓、灌木、树和垂植。
- 壁灯、花盆、长椅、标牌等可移动或可单独安装的场地点景。

以下情况应拆成独立资产：

- 轮廓能从建筑背景中辨识，能通过裁剪或正交视图描述正面和侧厚。
- 可以独立生成、缩放、替换材质、镜像或实例化。
- 与墙体或屋顶合并后会限制后续复用或修改。
- 用户明确要求保留其造型、材质或装饰价值。

以下情况不拆分：

- 纯平面颜色、污渍、抹灰颗粒或没有几何厚度的表面图案，优先用 PBR 贴图或法线贴图。
- 大面积连续石墙纹理和屋面瓦纹，属于材质或参数化结构。
- 相互重叠成一片、无法判断单体边界的密集植物。先生成有代表性的花簇或藤蔓模块，再在 Blender 中布置。

在 `components.json` 的 `visual_inventory` 记录盘点结果：

```json
{
  "item_id": "relief_01",
  "part_id": "stone_relief_01",
  "source_view": "concepts/D01/views/front.png",
  "asset_class": "decorative_ornament",
  "type": "stone_relief",
  "decision": "ai_3d",
  "observation": "raised floral relief above the entrance, clearly separable",
  "instances": 1
}
```

`part_id` 表示已经进入组件清单；如果判断为贴图或参数化，也应保留盘点项并把 `decision` 设为对应方式。

## 浮雕与植物单体规则

### 浮雕和装饰件

- 参考图必须裁剪到单个浮雕或一组不可再分的装饰件，不能把整面墙一起交给 AI 3D。
- `locked` 记录整体宽度、高度、厚度、正面朝向和安装背面。
- 如果安装面不规则，记录接触区域或挂点，而不是强行假设完整平面。
- 提示词排除墙体、门窗、周围线脚、环境和重复装饰。
- 同一浮雕重复使用时通过实例、镜像或尺寸变体完成。

### 花草和藤蔓

- 先判断交付目标。实时场景优先生成一个代表性花簇、灌木模块或藤蔓段落，再由 Blender 实例化，不为每朵花调用一次 AI。
- 参考图至少要有清楚的正面轮廓；需要控制厚度时补侧面或俯视裁剪。
- `locked` 记录代表模块的包围盒、地面或花箱接触面、朝向和允许缩放范围。
- `free` 可交给 AI 发挥花朵密度、叶片分布、枝干走势和自然不规则性。
- 通过 QA 后检查破洞、漂浮叶片、异常尖刺、错误透明面、法线和面数。实时项目不为远景植物保留不可见细节。

## 生成前先检索

完成 `visual_inventory` 后，用 `asset_class`、`type`、标签和风格关键词检索模型库：

```bash
python scripts/scene_kit.py library-search "floral stone relief" \
  --asset-class decorative_ornament

python scripts/scene_kit.py library-search "flower cluster vine" \
  --asset-class vegetation

python scripts/scene_kit.py library-search "double casement window" \
  --asset-class architectural_component --type window
```

把匹配结果作为候选展示给用户，说明：

- 资产名称、类型、来源项目和预览图。
- 尺寸、原点、朝向和已有接口。
- 材质、风格和允许复用方式。
- 与当前项目的差异，以及直接复用、缩放、换材质或仅作为参考的成本。

用户确认前不得把候选设为项目组件，也不得覆盖当前设计合同。确认后执行：

```bash
python scripts/scene_kit.py library-link <项目目录> <part_id> <asset_id> \
  --confirmed-by-user
```

没有合适候选时再生成新模型。不要为了用库而降低当前项目的风格、尺寸或接口要求。

模型库资产在本项目中仍需经过 `FINISHING`。复用不会自动继承旧项目的装配合理性，必须重新检查当前模型的面片、材质、洞口、接缝、支撑和安装关系。

## 生成后询问入库

每个 AI 组件通过单件 QA 后，再询问用户是否加入模型库。这里的 QA 包括参考匹配、面片与表面质量、接口和构造逻辑。组件较多时可以在 `GENERATION` 阶段结束前集中列出所有已通过资产，但必须给出明确选择：

```text
以下组件已通过 QA：石质花浮雕、花簇模块、百叶窗。
是否将其中通过复用的资产加入模型库，供后续项目使用？
```

用户同意后逐个执行：

```bash
python scripts/scene_kit.py library-add <项目目录> <part_id> \
  --confirmed-by-user
```

脚本会把模型文件复制到模型库、计算文件哈希，并记录来源、分类、尺寸、接口、材质、风格、许可证和 QA。同一模型文件不会重复入库。

## 资产元数据

模型库的 `catalog.json` 中每个资产至少包含：

```json
{
  "asset_id": "storybook-stone-relief-a1b2c3d4",
  "name": "Storybook stone relief",
  "version": 1,
  "status": "active",
  "asset_class": "decorative_ornament",
  "type": "stone_relief",
  "tags": ["stone", "floral", "storybook", "entrance"],
  "description": "Raised floral relief for an entrance wall.",
  "source_project": {
    "project_id": "european-villa-01",
    "object_id": "B01",
    "part_id": "stone_relief_01"
  },
  "files": {
    "model": "assets/storybook-stone-relief-a1b2c3d4/model.glb",
    "preview": "assets/storybook-stone-relief-a1b2c3d4/comparison.png"
  },
  "geometry": {
    "dimensions_m": {
      "width": 1.4,
      "height": 0.6,
      "depth": 0.12
    },
    "origin": "bottom_center",
    "forward": "-Y",
    "interfaces": {
      "mounting_face": "back"
    }
  },
  "materials": ["warm grey limestone"],
  "style": {
    "keywords": ["soft storybook European", "restrained floral carving"],
    "palette": ["warm grey", "ivory"]
  },
  "reuse": {
    "allowed": true,
    "mode": "placement_variants",
    "constraints": ["preserve front relief silhouette"]
  },
  "license": {
    "kind": "project_generated",
    "attribution": ""
  },
  "technical": {
    "format": "glb",
    "sha256": "64-character-sha256",
    "polygon_count": 12000
  },
  "qa": {
    "result": "pass",
    "checked_at": "2026-11-12T20:00:00+08:00",
    "comparison": "assets/storybook-stone-relief-a1b2c3d4/comparison.png"
  },
  "created_at": "2026-11-12T20:00:00+08:00"
}
```

复用方式：

- `direct`：保持尺寸和材质直接实例化。
- `scale_variants`：保持主要轮廓，允许按比例和接口重新校准。
- `placement_variants`：保持构件本体，允许改变安装位置和朝向。
- `reference_only`：只作为造型参考，不复用原始网格。

## 项目内记录

组件使用模型库资产后，`components.json` 中记录：

```json
{
  "part_id": "stone_relief_01",
  "asset_class": "decorative_ornament",
  "type": "stone_relief",
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

生成后加入库但项目仍使用本模型时，保留 `decision: "ai_3d"`，另写 `library_ref.status: "added"`。

## 校验

```bash
python scripts/scene_kit.py library-list
python scripts/scene_kit.py library-validate
```

校验包括重复 ID、分类和类型、尺寸、复用模式、许可证、来源、模型格式、文件存在性以及 SHA-256 哈希一致性。没有通过校验的资产不能作为当前项目组件使用。
