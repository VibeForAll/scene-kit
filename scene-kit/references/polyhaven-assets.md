# Poly Haven 资产使用

## 定位

Poly Haven 提供免费的 CC0 HDRI、PBR 纹理和模型，适合在生成本地贴图前检查是否有更可靠的现成材质。

官方 Blender Asset Browser 插件仓库：

- <https://github.com/Poly-Haven/polyhavenassets>

插件代码元数据为 GPL-3.0，版本 `1.2.3`，但官方 README 说明插件本身需要从 Superhive 购买或通过 Patreon 获取。不要绕过授权，也不要把这个插件加入“缺失即自动下载”的免费扩展列表。

## 使用顺序

1. 检查 Blender 是否已经安装并启用 Poly Haven Assets 插件。
2. 已安装：在 Asset Browser 中用它搜索并拖入纹理、HDRI 或模型。
3. 未安装：不阻塞项目。使用公开 API 搜索免费资产，再从资产页面下载合适的 PBR 文件。
4. 只有 Poly Haven 没有合适资产时，才生成本地贴图或继续使用项目 PBR。

`ensure_modeling_extensions.py` 的报告可以记录 Poly Haven 插件是否存在，但它不影响八项免费建模扩展的 `ready` 状态，也不会自动安装该付费插件。

## 无插件搜索

运行：

```bash
python scripts/polyhaven_search.py "dark oak wood" \
  --type textures --limit 10 \
  --output internal/polyhaven-dark-oak.json
```

可搜索：

```text
textures
models
hdris
all
```

结果包含：

- Poly Haven slug。
- 资产页面 URL。
- 标签、分类、描述和最大分辨率。
- 缩略图 URL。
- 自定义匹配分数。

示例：

- 深色木框：`dark oak`, `dark wood`, `old wood`
- 石材：`weathered limestone`, `rough stone`, `sandstone`
- 屋面：`slate roof`, `black tiles`, `mossy slate`
- 墙面：`cream plaster`, `aged stucco`
- 玻璃：优先项目 PBR，Poly Haven 通常不提供可直接代替建筑玻璃的完整模型

## 分辨率

- 普通建筑近景和游戏场景优先 1K 或 2K。
- 大幅墙面、地面或最终高清近景再考虑 4K。
- 不要默认下载 8K；文件体积和 Unity 内存成本通常不必要。
- 下载法线、粗糙度、AO 和置换时使用 Non-Color。
- 实时资产通常不启用置换和自适应细分。

## 纹理尺度

应用纹理后必须设置真实世界尺寸。例如一块木纹应在横梃和竖梃上保持相同的木纹密度。检查 UV 拉伸、纹理旋转和接缝；不能只因为贴图已经加载就判定通过。

推荐使用项目材质节点、UV 或 `Texel Density Checker` 检查纹理密度。

## 记录

使用 Poly Haven 后，在组件的 `qa.material_review` 中记录：

```json
{
  "polyhaven_checked": true,
  "polyhaven_addon_available": false,
  "texture_source": "polyhaven",
  "polyhaven_assets": [
    "dark_wood"
  ],
  "notes": [
    "使用 dark_wood 2K Diffuse/Normal/Roughness",
    "木纹按组件实际尺寸映射"
  ]
}
```

同时记录资产页面 URL 或项目素材路径，保留 CC0 来源信息。
