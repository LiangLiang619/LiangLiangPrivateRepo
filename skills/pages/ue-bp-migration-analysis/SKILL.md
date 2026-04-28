---
name: ue-bp-migration-analysis
description: >-
  Analyzes UE Blueprint asset migration plans and produces structured Markdown analysis
  documents. Covers inheritance, component graph, asset references, Blueprint communication
  patterns, load chains, lifecycle, and migration decisions aligned with SDK isolation goals.
  Use when the user asks to analyze Blueprint migration, BP migration analysis, 蓝图迁移方案,
  evaluate moving Blueprint assets into SDK, or assess BP feasibility for LetsGo/LetsGoSDK split.
---

# UE Blueprint 迁移分析

对一组 `Blueprint`（`.uasset` 中的 Widget/Actor/Component/AnimBP 等）做**迁移方案全景分析**，输出与 DataTable 迁移分析**同构的 Markdown 文档**（章节顺序一致），但 **2.1 表格列**与 **2.2 每个资产的详细小节**按 Blueprint 特性定制。

## 输入

用户提供：

1. 待分析的 **Blueprint 资产路径列表**（UE 路径，如 `/Game/LetsGo/Blueprints/UI/WBP_Example`）
2. 可选：**分析范围说明**（仅 UI / 仅关卡 Actor / 混合）、**已知对接人**

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
| 对象 | 资产路径 | 蓝图类型 | 父类 | 是否属于基建能力 | 是否包含业务逻辑 | 是否迁移 | 对接人 |
```

- **对象**：Blueprint 资产名（反引号包裹）
- **蓝图类型**：`Widget` / `Actor` / `ActorComponent` / `AnimBP` / `GameMode` / `Function Library` / `Macro Library` / `其他`
- **父类**：C++ 基类名或 BP 父类资产路径（未知则 `待确认`）
- **是否属于基建能力**：是否在**基建关键流程**（`启动 → 登录 → 进入大厅`）中被依赖，附一句理由
- **是否包含业务逻辑**：是否含特定玩法/模式逻辑或强业务资源依赖，附一句理由
- **是否迁移**：四选一：`迁移进SDK` / `不迁移` / `废弃` / `待确认`；与 2.2 详细分析第 7 小节结论一致
- **对接人**：未知填 `待确认`

## 2.2 详细分析（每个 Blueprint 固定 7 个小节）

对每个资产单独一节 `#### 2.2.x <资产名>`，编号递增。每节**必须**含以下子标题（层级固定为 `#####`）：

1. `##### 1. 蓝图类型与继承关系`
2. `##### 2. 组件构成与资产引用`
3. `##### 3. 使用方与关联关系`
4. `##### 4. 当前加载链路与现状`
5. `##### 5. 生命周期`
6. `##### 6. 使用范围`
7. `##### 7. 迁移判断`

各小节必填内容、固定背景文、资产列表示例、**四、方案总结**表头与迁移决策树见 [bp-migration-template.md](bp-migration-template.md)。

## 执行流程

1. **确认资产路径**：列表完整、路径为 `/Game/...` 形式。
2. **按资产搜索证据**（不可凭空调侃）：
   - 仓库内 **Grep**：资产短名、路径片段、`UIManager` / `CreateWidget` / `LoadAsset` / `AssetLoadUtils` / `AssetMgr` 等
   - 如用户可提供 **UE 内依赖/被引用** 信息或 AssetRegistry 扫描结果，纳入「组件与引用」「使用方」
3. **每个 Blueprint** 按 7 小节填写；**2.1 总览表**与最后 **| 资产 | 结论 |** 表与详细分析一致。
4. **三、当前问题重新归纳**：从多资产中抽象共性问题（如硬编码路径、基类在业务仓、整包预加载等）。

## 分析原则（与 DataTable 迁移目标对齐）

1. 必须基于**代码搜索与（如有）资产引用**；缺证据处标 `待确认`。
2. 基建 vs 业务：核心标准是该 BP 是否被**基建关键流程**依赖。
3. 迁移判断（与 DataTable 一致）：
   - 纯业务/玩法且基建不依赖 → 一般不迁入 SDK
   - 基建核心能力 → 考虑迁入 SDK
   - 已废弃 → 标废弃
   - 依据不足 → `待确认` + 待确认问题列表
4. 改造方向需支持：各玩法独立维护资源、**按当前玩法动态加载**、退出后卸载。
5. **Blueprint 专项**：
   - **继承链**：C++/BP 父类若在 SDK/业务侧不同仓，会显著影响迁移成本。
   - **组件与引用**：子资产（Mesh/Material/其他 BP）是隐性耦合面，需显式列出。
   - **通信方式**：`Interface` / 事件 优于硬 `Cast`；硬 Cast 多 → 解耦成本高。
   - **Widget**：注意 `UIManager`、UI 配置、资源映射表中的**硬编码路径**。

## 与 DataTable 迁移分析的关系

- **目标与判断标准**与项目内 DataTable 迁移规范一致（SDK 干净、副玩法隔离、新玩法自维护资源）。
- DataTable 分析由 `.cursor/rules/datatable-migration-analysis.mdc` 驱动；本 Skill 专用于 **Blueprint**，**不要**用 DataTable 的 6 小节结构写 BP 报告。

## 详细规范

- 完整章节模板、固定「一、背景」原文、各小节细则与决策树：[bp-migration-template.md](bp-migration-template.md)
