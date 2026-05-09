---
name: ue-bp-3c-migration-analysis
description: >-
  Analyzes UE Blueprint asset migration plans for the Common 3C Repository and produces
  structured Markdown analysis documents. Covers inheritance, component graph, asset
  references (with dependency form classification), Lua code references,
  and migration decisions aligned with 3C isolation goals.
  Use when the user asks to analyze Blueprint 3C migration, BP 3C migration analysis,
  蓝图3C迁移方案, 3C迁移分析, 3C仓库迁移, evaluate moving Blueprint assets into 通用3C仓库,
  or assess BP feasibility for Common 3C repository.
---

# UE Blueprint 3C仓库迁移分析

对一组 `Blueprint`（`.uasset` 中的 Widget/Actor/Component/AnimBP 等）做**迁移至通用3C仓库的全景分析**，输出结构化的 Markdown 文档。**2.1 表格列**与 **2.2 每个资产的详细小节**按 Blueprint 特性与3C仓库定位定制。

## 输入

用户提供：

1. 待分析的 **Blueprint 资产路径列表**（UE 路径，如 `/Game/LetsGo/Blueprints/Character/BP_Example`）
2. 可选：**分析范围说明**（仅角色 / 仅镜头 / 仅操控 / 战斗技能 / 混合）、**已知对接人**

若仅给出短名或缺少路径，应先补全或请用户确认路径后再分析。

## 产出

单一 Markdown 文档，章节与顺序**必须**符合下方「输出文档结构」。全文使用**中文**。

## 输出文档结构（必须包含，顺序不可变）

```markdown
## 资产列表
## 一、背景
## 二、资源功能分析
  ### 2.1 分析结论总览
  ### 2.2 详细分析
    #### 2.2.x 每个 Blueprint 一个子章节
## 三、当前问题重新归纳
## 四、方案总结
```

## 2.1 分析结论总览（固定表头）

```markdown
| 对象 | 资产路径 | 蓝图类型 | 父类 | 是否属于通用3C能力 | 是否包含业务逻辑 | 是否迁移 | 对接人 |
```

- **对象**：Blueprint 资产名（反引号包裹）
- **蓝图类型**：`Widget` / `Actor` / `ActorComponent` / `AnimBP` / `GameMode` / `Function Library` / `Macro Library` / `其他`
- **父类**：C++ 基类名或 BP 父类资产路径（未知则 `待确认`）
- **是否属于通用3C能力**：是否在角色/镜头/操控/战斗/技能/武器/动画等通用3C链路中被多玩法共用，附一句理由
- **是否包含业务逻辑**：是否含特定玩法/模式逻辑或强业务资源依赖，附一句理由
- **是否迁移**：四选一：`迁移进3C仓库` / `不迁移` / `废弃` / `待确认`；与 2.2 详细分析第 7 小节结论一致
- **对接人**：未知填 `待确认`

## 2.2 详细分析（每个 Blueprint 固定 7 个小节）

对每个资产单独一节 `#### 2.2.x <资产名>`，编号递增。每节**必须**含以下子标题（层级固定为 `#####`）：

1. `##### 1. 蓝图类型与继承关系`
2. `##### 2. 组件构成分析`
3. `##### 3. 本BP依赖了谁（出向依赖）`
4. `##### 4. 谁依赖了本BP（入向依赖）`
5. `##### 5. Lua 代码引用分析`
6. `##### 6. 使用范围`
7. `##### 7. 迁移判断`

各小节必填内容、固定背景文、资产列表示例、**四、方案总结**表头与迁移决策树见 [bp-3c-migration-template.md](./bp-3c-migration-template.md)。

## 执行流程

1. **确认资产路径**：列表完整、路径为 `/Game/...` 形式。
2. **定位 `.uasset` 文件**：将 `/Game/...` 路径转换为磁盘路径（`Content/...`），确认文件存在。
3. **分析组件构成**（**必须步骤**，不可跳过）：
   - 对 **Actor BP**：调用 `uasset_exports` 查找 `SCS_Node` / `SimpleConstructionScript` 导出项，获取 BP Components 面板中添加的组件列表；检查父级 BP 的 SCS 获取继承的组件。
   - 对 **所有 BP 类型**：Grep C++ 父类源码中的 `CreateDefaultSubobject`，获取 C++ 构造函数中创建的默认子对象。
   - Grep Lua / C++ 代码中的 `NewObject` / `CreateComponent` / `AddComponent` / `RegisterComponent`，识别运行时动态创建的组件。
   - 填入第 2 小节「组件构成分析」，每个组件注明来源层级（引擎/3C/业务）和创建方式。
4. **使用 UE Editor MCP 分析出向资产引用**（**必须步骤**，不可跳过）：
   - 调用 `editor.get_asset_dependencies`（ue-editor-mcp），传入 `asset_path`、`include_script: true`，获取**出向依赖**列表（资产路径 + asset_class）。
   - 如需确认 Details 面板中具体哪个属性持有引用，可补充 `uasset-analyzer` 的 `uasset_properties`（CDO，parse_values=true）。
   - 将结果填入第 3 小节「本BP依赖了谁」。
5. **使用 UE Editor MCP 查询入向资产依赖**（**必须步骤**——等效 UE Reference Viewer 的 Referencers 视图）：
   - 调用 `editor.get_asset_referencers`（ue-editor-mcp），传入 `asset_path`、`dependency_type: "all"`，获取所有直接引用本 BP 的资产列表（包含 asset_class 区分 Blueprint/World/其他）。
   - 补充 Grep 搜索 `AssetNameMapping.txt`、`DefaultGame.ini` 等配置文件。
   - 将结果**按模块分组**填入第 4 小节「谁依赖了本BP」，区分 Blueprint 引用和关卡（World）引用。
6. **扫描 Lua 代码引用**（**必须步骤**）：
   - 运行 skill 目录下的 `scan_lua_refs.py` 脚本，扫描 `Content/LetsGo/Script/`、`Content/Feature/`、`Content/LetsGoSDK/Script/`。
   - 脚本自动检测 `Content` 根目录（从 cwd 向上查找），支持从任意项目层级打开。
   - 脚本支持 `--threshold N` 参数（默认 30）：引用数 ≤ 阈值时输出完整表格，> 阈值时输出**路径分布概览 + 硬耦合引用明细**。
   - 将结果填入第 5 小节「Lua 代码引用分析」。
7. **每个 Blueprint** 按 7 小节填写；**2.1 总览表**与最后 **| 资产 | 结论 |** 表与详细分析一致。
8. **三、当前问题重新归纳**：从多资产中抽象共性问题（如3C组件耦合玩法规则、父类跨仓、硬编码路径等）。

## 分析原则（通用3C仓库迁移目标）

1. 必须基于**代码搜索与（如有）资产引用**；缺证据处标 `待确认`。
2. 通用3C vs 业务：核心标准是该 BP 是否属于**通用3C能力**（角色/镜头/操控/战斗/技能/武器/动画），且**不含特定玩法模式逻辑**。
3. 迁移判断：
   - 属于通用3C能力且玩法无关 → 考虑迁入3C仓库
   - 含特定玩法规则或强依赖业务资产 → 不迁移，留业务仓
   - 已废弃 → 标废弃
   - 依据不足 → `待确认` + 待确认问题列表
4. 3C专属判断维度：
   - **玩法无关性**：该 BP 的 Character/Camera/Control/Combat 逻辑是否独立于具体玩法规则
   - **多玩法复用**：是否已被或应被多个 GameFeature 共用
5. 改造方向需支持：各玩法通过继承或组合扩展3C基座能力，而非修改3C仓库本身。
6. **Blueprint 专项**：
   - **继承链**：C++/BP 父类若在3C/业务侧不同仓，会显著影响迁移成本。需明确父类属于哪一层。
   - **组件构成**：全面分析 BP 上挂载的所有组件。每个组件标注来源层级（引擎/3C/业务），评估迁移时的跟随策略。
   - **出向依赖**（本BP依赖了谁）：通过 `editor.get_asset_dependencies`（ue-editor-mcp）获取，用单表格列出每个被依赖对象及其类型。
   - **入向依赖**（谁依赖了本BP）：通过 `editor.get_asset_referencers`（ue-editor-mcp）获取，等效 Reference Viewer 的 Referencers 视图，区分 Blueprint 和 World 引用。
   - **Lua 引用**：通过 Python 脚本扫描 Lua 代码目录，识别对 BP 的字符串引用、类名引用、路径引用。
   - **Widget**：注意 `UIManager`、UI 配置、资源映射表中的**硬编码路径**。

## 详细规范

- 完整章节模板、固定「一、背景」原文、各小节细则与决策树：[bp-3c-migration-template.md](./bp-3c-migration-template.md)
- Lua 引用扫描脚本：[scan_lua_refs.py](./scan_lua_refs.py)
