# Scene Kit 7.2 安装说明

Scene Kit 是一个概念图优先的模块化建筑工作流：

1. 用文生图探索整栋建筑方向。
2. 由用户选择一个概念。
3. 把设计语言拆成可复用组件。
4. 用中性轮廓控制接口，用概念图和提示词保留 AI 3D 的造型创造力。
5. 把浮雕、植物等非结构表现资产拆成独立模型。
6. 拆件图片回到原始多视图复核，确认完整、合理、可连续装配。
7. 在 Blender 中归一化、实例化、装配，再做最终面片、材质和构造逻辑精修。
8. 既和参考图比较，也做屋檐/门窗/支撑等智能逻辑分析，自行修补悬空和松脱。
9. 通过当前 revision 的最终验收并导出。
10. 把用户确认复用价值的资产加入跨项目模型库。

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

`scene-kit.standalone.md` 用于只能读取单文件的规则系统，内容不随多文件版本自动更新。

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
```

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
- 装配完成不等于可交付；必须通过 `FINISHING` 的面片、材质、接缝和构造逻辑审查。
- 屋檐、门廊、老虎窗、凸窗、塔楼、栏杆和檐沟等出现悬空或松脱时必须自行修补，不能留给用户在验收时发现。
- 尺寸最终由 Blender 中的锁定接口校准，不由图片像素决定。
- 没有实际工具结果时，不得声称模型、图片或截图已经生成。
