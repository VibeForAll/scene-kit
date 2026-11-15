# Blender 建模扩展预检

## 规则

在开始参数化建筑建模、AI 3D 后处理、装配或精修之前，先检查以下官方免费扩展是否已安装并启用。缺少时必须先安装；安装失败则停止使用依赖该插件的工作流，并说明具体错误。

扩展只提高建模、测量、清理和诊断效率，不能修正概念错误，也不能把多次付费生成当作替代手工模型的手段。

## 推荐扩展

| 包 ID | 名称 | 主要用途 |
|---|---|---|
| `archimesh` | Archimesh | 参数化房间、门、窗和建筑基础件 |
| `measureit` | MeasureIt | 尺寸、距离和施工比例检查 |
| `print3d_toolbox` | 3D Print Toolbox | 非流形、退化面、厚度和网格完整性 |
| `looptools` | LoopTools | 环线圆化、放松、桥接和视图平面化 |
| `edit_mesh_tools` | Edit Mesh Tools | 边面挤出、选择、切割和局部整理 |
| `CAD_Sketcher` | CAD Sketcher | 约束驱动的精确二维轮廓 |
| `surface_diagnostics` | Surface Diagnostics | 曲率、表面和法线质量诊断 |
| `curiomesh` | CurioMesh | 扫描和游戏资产的四边形重拓扑辅助 |

`Archimesh` 只用于建立可编辑基础件。精确窗格、窗框和洞口仍应按项目锁定尺寸检查，不能直接接受默认参数。

暂不默认安装：

- `Bonsai`：完整 BIM/IFC 平台，安装体积约 140–170 MB；只有项目确实需要 IFC/BIM 时再启用。
- `UVgami Lite`：安装体积约 90–120 MB；当前重复建筑构件优先使用可控的简单 UV 和纹素密度检查。
- [Poly Haven Assets](https://github.com/Poly-Haven/polyhavenassets)：官方 Blender Asset Browser 集成，但插件本身需要购买或 Patreon 支持。不要从 GitHub 绕过授权安装。若用户已有授权 ZIP，可安装；否则使用 `polyhaven_search.py` 公开 API 搜索免费 CC0 资产并手动导入。

## 自动检查与安装

先运行检查：

```powershell
blender --background --python scripts/ensure_modeling_extensions.py -- `
  --output <项目目录>\internal\toolchain.json
```

如果存在缺失，在用户授权安装后运行：

```powershell
blender --background --python scripts/ensure_modeling_extensions.py -- `
  --install --output <项目目录>\internal\toolchain.json
```

脚本会：

1. 打开 Blender 的在线扩展访问。
2. 从 `https://extensions.blender.org/api/v1/extensions/` 获取官方元数据。
3. 按当前平台选择正确的安装包，例如 `windows-x64`。
4. 校验官方 SHA-256。
5. 通过 `bpy.ops.extensions.package_install_files` 安装到 `user_default`。
6. 启用 `bl_ext.user_default.<package_id>`。
7. 写出 `toolchain.json`；只有全部扩展已启用时 `ready=true`。

脚本退出码：

- `0`：全部扩展已安装并启用。
- `1`：仍有扩展缺失、禁用或安装失败。
- `2`：不在 Blender Python 中运行。

## 生成前门禁

在 `GENERATION`、`ASSEMBLY` 或任何参数化建模前：

1. 读取当前项目的 `internal/toolchain.json`。
2. 确认 `ready=true`。
3. 确认 `blender_version` 与当前 Blender 一致。
4. 若工具链变化，重新运行预检。

以下任一情况不能开始依赖该工具链的建模：

- `ready=false`
- 扩展显示 `enabled=false`
- 当前平台包不兼容
- 下载 SHA-256 不匹配
- Blender 在线访问被关闭且缺少本地安装包

## 使用边界

- Archimesh 生成的窗户、门和房间必须按项目锁定尺寸复核。
- CAD Sketcher 约束图只用于精确轮廓，不替代最终装配检查。
- LoopTools、Edit Mesh Tools 和 CurioMesh 的自动结果必须重新检查窗格、边框和接口。
- 3D Print Toolbox 与 Surface Diagnostics 是诊断工具，不能判断概念相似度或构造逻辑。
- 插件启用成功不代表生成的资产可用；仍须执行单件 QA、参考对照和终审。
- Poly Haven 插件的存在是可选项，不影响八项免费扩展的 `ready` 状态；PBR 资产是 CC0，但插件软件本身有独立获取条件。
