# 单件材质与贴图验证

## 规则

每完成一个组件，都要先用最终材质和贴图完成静态审计并实际渲染、对照参考，之后才能把组件标为 `pass`。几何通过不等于组件通过。

最低要求：

1. 将设计合同中的木材、石材、抹灰、玻璃、金属和植物材质实际赋给组件。
2. 使用米制纹理尺度；颜色贴图使用 sRGB，粗糙度、法线、AO 和置换贴图使用 Non-Color。
3. 在固定中性灯光下准备正面、侧面和 3/4 相机；至少选择两个视图进入材质审查。
4. 与已批准参考对比轮廓、基色、粗糙度、纹理尺度、色温、塑料感和材质关系。
5. 在决定生成本地贴图或继续重试前，先检查 Poly Haven 是否已有合适资产。
6. 检查图片节点的投影方式、坐标来源、物理平铺尺寸，以及颜色/法线/粗糙度是否使用同一映射。
7. 材质不匹配时先替换素材、调整 UV/映射或生成贴图，再重新审计。需要重新渲染时使用新的获批批次，不能沿用修复前截图。

## 强制 QA 渲染与聊天展示

材质 QA 渲染是组件门禁的一部分，不能被用户“继续项目”“少花 token”或“不用发图”关闭。每次组件生成或参数变化后，必须把当前 revision 至少两个视图和参考对照渲染到项目目录，并完成材质、贴图映射和可见拉伸检查。

聊天展示是另一项可选行为：

- 默认只返回摘要和文件链接，不逐张嵌入图片。
- 用户要求看细节时，优先展示一张压缩对照图。
- 大量原图、全分辨率近景或额外的展示性渲染可能增加 token，开始前可以询问用户是否需要。
- 不展示图片不代表可以跳过渲染；未渲染的组件不能写 `pass`。

## 强制投影与拉伸检查

每次组件生成后都必须运行 Blender 审计，不能只凭一张渲染图判断贴图正确；随后必须用实际渲染验证可见拉伸：

```bash
blender --background <组件.blend> --python scripts/blender_audit.py -- \
  --output <项目>/preview/qa/<part_id>/blender_audit.json
```

读取报告中的 `texture_mapping_audit`。若图片节点使用 `FLAT` 并直接连接 `Object` 或 `Generated` 坐标，报告会标记 `flat_3d_coordinate_projection`。这种组合在立方体、厚墙和多个朝向的立面上会只采样两个轴，容易把石纹、砖缝或木纹沿缺少的轴拉成长条。

可通过的映射方案：

- 正确展开并统一缩放的真实 UV。
- 经正面、侧面和 3/4 渲染验证的 Box Projection。
- 明确按面或材质区建立的投影，并证明每个主视角纹理密度一致。

不能通过的情况：

- 图片节点使用 `FLAT + Object/Generated`，且在侧面或竖向出现拉伸。
- 颜色贴图已修正，但法线或粗糙度仍沿用旧映射。
- 贴图分辨率正确，但实际石块、砖块或木板尺度与参考明显不符。
- 只调整灯光、曝光或对比度掩盖错误的投影方向。

## 参数变体

参数化组件的审批范围是 `per_parameters_hash`。参数、材质绑定、生成器版本或外部参数文档任一变化后，旧材质审查和贴图审计立即失效。新变体必须重新生成几何、重新运行 `blender_audit.py`、重新渲染关键视图，并重新写入完整的 `texture_audit` 与 `qa.material_review`。

不得因为相邻参数版本外观接近就复制旧截图或复用旧参数哈希。参数化减少的是重复建模，不是重复渲染验收。

## 材质审查记录

每个已通过组件必须包含：

```json
{
  "qa": {
    "material_review": {
      "status": "pass",
      "rendered_views": [
        "preview/qa/part/material_front.png",
        "preview/qa/part/material_three_quarter.png"
      ],
      "reference_comparison": "preview/qa/part/material_comparison.png",
      "polyhaven_checked": true,
      "polyhaven_addon_available": false,
      "polyhaven_assets": [],
      "texture_source": "project_pbr",
      "generated_textures": [],
      "checks": {
        "reference_match": true,
        "base_color_match": true,
        "roughness_match": true,
        "texture_scale_match": true,
        "texture_projection_valid": true,
        "surface_quality": true
      },
      "texture_audit": {
        "status": "pass",
        "audit_path": "preview/qa/part/blender_audit.json",
        "mapping_mode": "box",
        "views_checked": ["front", "side", "three_quarter"],
        "checks": {
          "source_image_loaded": true,
          "projection_axis_valid": true,
          "physical_scale_consistent": true,
          "no_visible_stretch_across_faces": true,
          "normal_and_roughness_aligned": true
        },
        "risk_findings": []
      },
      "notes": [
        "深橡木和石材颜色、粗糙度与参考匹配",
        "颜色、法线和粗糙度使用同一投影，三个视角没有拉伸或塑料感"
      ]
    }
  }
}
```

`texture_source` 允许：

- `project_pbr`：由项目已有节点或统一材质完成。
- `polyhaven`：使用 Poly Haven 的免费 CC0 资产。
- `generated`：没有合适现成素材时生成本地贴图。
- `existing`：复用已验收的本地材质。

`status=pass` 时：

- `polyhaven_checked` 必须为 `true`。
- 两个以上实际渲染图必须存在。
- 参考对照图必须存在。
- 六项材质检查全部为 `true`。
- `texture_audit.status=pass`，审计文件存在，至少两个角度已检查，五个贴图检查全部为 `true`，`risk_findings` 为空。

## 不匹配时的顺序

1. 先判断问题属于基色、粗糙度、法线、纹理尺度、投影方向、UV、灯光还是几何。
2. 记录至少两个参考视角中实际可见的色相、明度和光泽。深色窗框可能是深褐木、灰木、黑漆木、红木或蓝灰金属；不能根据“dark”“black”或单一模型描述直接归类。
3. 把各视角的基色样本与候选贴图打印或量化比较。若参考是深暖褐，优先比较 `fine grained wood`、`dark wooden planks`、`weathered_planks`；只有跨视图明确是低饱和黑漆时才用 `black painted wood`。
4. 有合适 CC0 素材时直接使用，并记录 slug、分辨率和来源。
5. 只有没有合适素材时才生成本地贴图；记录生成原因和输出文件。
6. 修改后重新运行贴图审计，并重新渲染当前 revision 的正、侧、3/4 和对照图。
7. 不得用灯光、曝光或后期掩盖错误材质。

窗框、窗套和玻璃的基础材质线索应在组件 `fine_structure_review.material_cues` 中先记录；最终 `qa.material_review` 必须证明实际赋给模型的材质与这些线索一致。

单张参考上的“深木色”不足以决定材质。组件必须先通过 `reference_consensus` 的多视角颜色采样；材质审查时再把成品正面、侧面或 3/4 渲染与这些样本对比。若视觉模型的颜色判断互相矛盾，以多视图色相一致性、参考放大图和可解释的光照差异为准，并保留未解决项。

Poly Haven 工作流见 [polyhaven-assets.md](polyhaven-assets.md)。
