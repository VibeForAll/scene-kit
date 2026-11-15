# Scene Kit 7.4 单体参考包审查

## 状态

- 8 个 AI 单体的 geometry、appearance、review_only 和双语提示词已建立。
- 所有 `reference_pack.audit.status` 暂为 `pending`。
- 尚未进入 AI 3D 生成。

## 参考图角色

- `geometry_*.png`：中性正侧轮廓、厚度和安装接口示意，只控制外形和装配。
- `appearance_*.png`：选中十视图中的局部裁剪，用来传递木框、石材、玻璃、栏杆和植物风格。
- 整栋联系图和标注总览：只进入 `review_only`，不能作为图生 3D 输入。

## 单体状态

| 单体 | 主生成输入 | 参考判断 |
|---|---|---|
| `tall_window_assembly` | 正面单窗裁剪 | 轮廓、木框、白窗台和黑窗条可辨 |
| `attic_window_assembly` | 正面双联阁楼窗 | 两个窗洞、浅色宽窗套和小披檐可辨 |
| `entrance_portal` | 正面拱门裁剪 | 拱券、木门和石质洞口可辨 |
| `stone_chimney_primary` | 正面单个烟囱裁剪 | 窄石砌主体与顶盖可辨 |
| `wall_lantern_primary` | 正面单盏壁灯 | 原图尺度较小，主要控制灯体比例和支架 |
| `porch_railing_primary` | 右侧门廊栏杆 | 直线扶手、立柱和木质表现可辨 |
| `climbing_vine_module` | 正面藤蔓模块 | 可按代表性叶簇和枝干生成，不逐叶复刻 |
| `porch_planter_primary` | 正面盆栽裁剪 | 盆体与绿植轮廓可辨 |

## 已知限制

- 壁灯和烟囱在原图中像素尺度较小，裁剪能够表达大轮廓和材质，但不能保证细小装饰完全复刻。
- 几何图为中性接口示意，不是最终风格图。
- 任何裁剪只能在通过当前审查后进入生成；生成后仍需正面、侧面和 3/4 对照。

## 审阅入口

- `overview.jpg`
- 各单体目录下的 `review.jpg`
- 各单体目录下的 `prompts.txt`
