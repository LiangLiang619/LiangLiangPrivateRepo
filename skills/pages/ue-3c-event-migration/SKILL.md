---
name: ue-3c-event-migration
description: >-
  Migrate event keys (both flat and subtable form) from LetsGo / Feature
  repositories into LetsGo3C's own LetsGo3CEvents.lua, with a one-time hook
  upgrade that deep-merges subtables so listeners / dispatchers in source
  repos keep working untouched. Generates analysis, plan, and migration record
  documents at each phase. Use when the user asks 事件迁移到3c, 把事件入3c,
  3C事件解耦, EventEnum 迁移, migrate events to LetsGo3C, 3C 事件枚举,
  3c event migration, 外部事件迁入3c, or provides a list of event keys to
  move into LetsGo3C.
---

# 事件迁移到 LetsGo3C（3C Event Migration Skill）

> **定位**：本 Skill 是外部事件 key 迁入 LetsGo3C EventEnum 的**唯一操作权威来源**，AI 执行 3C 事件迁移时以本文件为准。
> **理念依据**：依赖倒置原则——3C 仓库自主持有其所需的事件枚举，不依赖外部仓库声明。
> **核心承诺**：迁移后源仓库的 listener / dispatcher 代码**零改动**，通过 string value 匹配实现透明兼容。

## 形态与同生态边界

| 场景 | 工具 | 形态 |
|------|------|------|
| **事件 key 迁入 LetsGo3C**（本 Skill） | `ue-3c-event-migration` | Cursor Skill |
| Lua 代码搬入 LetsGo3C | `ue-3c-lua-migration` | Cursor Skill |
| 资产搬入 LetsGo3C | `ue-3c-asset-migration` / `ue-bp-3c-migration-analysis` | Cursor Skill |
| 3C 外部依赖扫描 | `ue-3c-external-deps-scan` / `ue-letsgo3c-external-deps-scan` | Cursor Skill |

**关键边界**：本 Skill 只管 **EventEnum key 的声明与注入机制**；事件的 dispatch / register 代码本身若需搬迁，请走 `ue-3c-lua-migration`。

## 触发条件

当用户提到以下关键词时，本 Skill 自动生效：
- 事件迁移到3c / 把事件入3c / 3C事件解耦 / EventEnum 迁移
- migrate events to LetsGo3C / 3C event migration / 3C 事件枚举
- 外部事件迁入3c / 事件依赖倒置

## 动手前：先读规范（必须）

**在执行任何迁移操作之前，必须先并行读取以下文件**，确保理解完整机制后再动手：

| 优先级 | 文件 | 内容 |
|--------|------|------|
| **P0** | **本文件**（`SKILL.md`） | 3C 事件迁移操作的唯一权威来源 |
| **P0** | [`refs/subtable-merge-design.md`](./refs/subtable-merge-design.md) | 子表事件的双 Hook 合并机制设计（BeforeInitEvents + PostInitEvents） |
| **P0** | [`refs/event-classification-rules.md`](./refs/event-classification-rules.md) | 事件归属 3C 的判断准则 |
| **P1** | [`refs/migration-record-template.md`](./refs/migration-record-template.md) | Phase 4 落档模板 |
| **P0** | `Content/LetsGo3C/Script/Core/Event/LetsGo3CEvents.lua` | 当前已有事件枚举（避免重复添加） |
| **P0** | `Content/LetsGo3C/Script/Hooks/Event/CommonEventEnumInitEventsHook.lua` | 当前 BeforeInitEvents Hook |
| **P0** | `Content/LetsGo3C/Script/HookConfig/OverrideSDK/SDK_HookConfig.lua` | 当前 Hook 注册配置 |
| **P0** | `Content/LetsGoSDK/Script/Core/Event/CommonEventEnum.lua`（L698-783） | SDK 的 `AppendEvents` + `InitEvents` + `POST_INIT_EVENTS` 实现 |

**不要跳过这一步。** 尤其 `CommonEventEnum.lua` 中的 `POST_INIT_EVENTS` 合并逻辑
是子表迁移的关键基础设施——必须确认其行为后再进入 Phase 1。

---

## 核心机制说明

### EventEnum 注入流程

```
SDK CommonEventEnum.InitEvents()
  │
  ├─ 1. hookSystem:Mixin(CommonEventEnum, "CommonEventEnum")
  │
  ├─ 2. TriggerHook("BeforeInitEvents") ── 各仓库向 EventsFileName 注入路径
  │     ├─ LetsGo Hook → EventsFileName["LetsGoBaseEvents"] = "LetsGo.Script.Core.Event.EventEnum"
  │     ├─ LetsGo Hook → EventsFileName["GlobalEvents"] = "LetsGo.Script.Core.Event.GlobalEvents"
  │     ├─ LetsGo3C Hook → EventsFileName["LetsGo3CEvents"] = "LetsGo3C.Script.Core.Event.LetsGo3CEvents"
  │     └─ ... 其他仓库
  │
  ├─ 3. for each EventsFileName: require + AppendEvents（⚠️ 子表整表覆盖）
  │     └─ CommonEventEnum[k] = v  ← flat string OK；table 会覆盖同名 table
  │
  ├─ 4. TriggerHook("PostInitEvents") ── 各仓库追加后置事件
  │     └─ LetsGo3C PostInitEvents Hook → push subtable events to EventsList
  │
  └─ 5. for each EventsList: 合并
        ├─ table value → SDK.TableUtils.Merge（✅ 深度合并，不覆盖）
        └─ string value → 赋值 + 冲突检测
```

### 两种注入路径

| 事件形态 | 注入时机 | 文件 | 合并行为 |
|----------|---------|------|---------|
| **Flat key**（`KEY = "value_string"`） | `BeforeInitEvents` | `LetsGo3CEvents.lua` | `AppendEvents` 平铺到 `CommonEventEnum[KEY]` |
| **Subtable key**（`SubTable.Key = "value"`） | `PostInitEvents` | `LetsGo3CSubtableEvents.lua` | `SDK.TableUtils.Merge` 深度合并到 `CommonEventEnum[SubTable]` |

### `MOE_3C.EventEnum` 与 `_MOE.EventEnum` 的关系

`MOE_3C.EventEnum` 通过 metatable `__index` 回退到 `_MOE.EventEnum`（即 `CommonEventEnum`）。
迁移完成后两者访问同一张表的同一 key，value string 完全一致，listener / dispatcher 零改动。

---

## 执行流程（4 Phase）

```
Phase 0 — 前置：读规范 + 校验 SDK PostInitEvents 机制可用性
    │
Phase 1 — 分析：输入事件列表 → 三仓库定位 → flat/subtable 分类 → dispatch/listener 扫描
    │
    ⏸️ 人工决策点 1（硬性门禁）：归属确认 / 子表策略 / 重名冲突处理
    │
Phase 2 — 设计：LetsGo3CEvents.lua 差异补丁 + Hook 升级补丁 + 源仓库删除清单
    │
    ⏸️ 人工确认点 2（硬性门禁）：设计文档定稿
    │
Phase 3 — 实施：改 LetsGo3CEvents.lua / 新增 SubtableEvents / 改 Hook / 3C 代码 MOE_3C 切换
    │
Phase 4 — 验收：反向扫描 + 冒烟检查清单 + 写迁移记录
```

### 文档实时落地原则（铁律）

**文档是多人多次协作的载体，不是最后补的总结。** AI 无状态，换个对话/换个人只能从文件读取上下文。

**核心规则：先写文件，再请求确认。"输出到聊天" ≠ "生成文档"。**

每个阶段的产出必须**用工具写入文件**，然后在聊天里告知文件路径并请求确认：

| 阶段 | 产出物 | AI 动作 | 文件路径 |
|------|--------|---------|---------|
| Phase 1 分析 | 事件分析表 | **先 write_to_file**，再聊天摘要 | `Content/LetsGo3C/Migration/Analysis/EventMigration/<batch_name>_analysis.md` |
| ⏸️ 确认后 | 开发人员决策结果 | **用 replace_in_file 更新**分析文档 | 同上（更新） |
| Phase 2 设计 | 迁移方案文档 | **先 write_to_file**，再聊天摘要 | `Content/LetsGo3C/Migration/Analysis/EventMigration/<batch_name>_plan.md` |
| Phase 4 验收 | 迁移记录 | **先 write_to_file** | `Content/LetsGo3C/Migration/Records/EventMigration_<batch_name>_<YYYYMMDD>.md` |

---

## Phase 0 — 前置

**目标**：确认基础设施就绪。

1. **并行读取**"动手前"表中所有 P0 文件
2. **校验以下三件事**，在分析文档顶部记录结论：
   - `CommonEventEnum.AppendEvents` 是否仍为简单赋值（`CommonEventEnum[k] = v`）——确认子表覆盖风险存在
   - `POST_INIT_EVENTS` Hook 是否暴露（检查 `CommonEventEnum.Hooks.POST_INIT_EVENTS` 和 `InitEvents` 中的 `TriggerHook` 调用）——确认子表深度合并通道可用
   - `MOE_3C.EventEnum` 的 metatable fallback 链是否完整——确认 3C 代码能访问全局 EventEnum
3. 如果 `POST_INIT_EVENTS` 不可用，参照 `refs/subtable-merge-design.md` 的 Fallback 方案执行

---

## Phase 1 — 分析

**输入**：事件 key 列表（CSV 文件路径 / 聊天直接给出 / 从 external_deps 扫描结果读取）

**对每个事件 key 执行以下分析：**

### 1.1 定位声明来源

在以下文件中搜索 key 的**声明**（定义 KV 对的位置）：

| 搜索位置 | 典型文件 |
|----------|---------|
| LetsGo | `Script/Core/Event/EventEnum.lua`、`GlobalEvents.lua`、`MainGameEvents.lua`、`FPSGameEvents.lua` |
| Feature/Community | `Script/Core/Event/CommunityEvents.lua` |
| Feature/System | `Script/Core/Event/SystemEvents.lua` |
| LetsGoSDK | `Script/Core/Event/CommonEventEnum.lua` |
| LetsGo3C | `Script/Core/Event/LetsGo3CEvents.lua`（检查是否已迁入） |

记录：声明文件路径、行号、key 名、value string、是 flat 还是 subtable 形态。

### 1.2 扫描 dispatch / listener

**必须扫描以下三类 API 调用**，覆盖所有 workspace 路径：

| 调用类型 | 模式（Grep） |
|----------|-------------|
| Dispatch | `DispatchEvent.*<KEY>` 或 `DispatchEvent.*<VALUE_STRING>` |
| Register | `RegisterEvent.*<KEY>` 或 `RegisterEvent.*<VALUE_STRING>` |
| Unregister | `UnRegisterEvent.*<KEY>` |
| UI 封装 | `AddEventListener.*<KEY>` / `RemoveEventListener.*<KEY>` |

**搜索范围**（所有 workspace 路径）：
- `E:\Dev2\LetsGoDevelop\LetsGo\Content\LetsGoSDK\Script`
- `E:\Dev2\LetsGoDevelop\LetsGo\Content\LetsGo3C\Script`
- `E:\Dev2\LetsGoDevelop\LetsGo\Content\LetsGo\Script`
- `E:\Dev2\LetsGoDevelop\LetsGo\Content\Feature\Community\Script`
- `E:\Dev2\LetsGoDevelop\LetsGo\Content\Feature\System\Script`

### 1.3 分类判定

参照 [`refs/event-classification-rules.md`](./refs/event-classification-rules.md) 给出归属建议。

### 1.4 输出格式

**写入文件** `Content/LetsGo3C/Migration/Analysis/EventMigration/<batch_name>_analysis.md`：

```markdown
# <batch_name> 事件迁移分析

## Phase 0 校验结论
- AppendEvents 子表覆盖风险：<是/否>
- POST_INIT_EVENTS 可用：<是/否>
- MOE_3C.EventEnum fallback 完整：<是/否>

## 事件分析表

| # | event_key | 形态 | value string | 当前声明文件:行 | dispatch 位置 | listener 位置 | 已在3C? | 归属建议 | 决策（待确认） |
|---|-----------|------|-------------|----------------|--------------|--------------|---------|---------|---------------|
| 1 | `KEY` | flat/subtable | `"VALUE"` | `file:line` | `file:line` | `file:line` | 是/否 | 进3C/不进 | ⏳ |
```

### 1.5 聊天请求确认

在文件写入后，聊天里输出**精简摘要**（不要复制全表）：
- 总计 N 个事件，建议 X 个进 3C、Y 个不进、Z 个已在 3C
- 子表型事件 M 个，需要启用 PostInitEvents Hook
- 列出需要人工判断的**边缘案例**（如有）
- 告知分析文档路径

### ⏸️ 人工决策点 1（硬性门禁）

**AI 必须在此暂停，等待用户逐项或整体确认后才能进入 Phase 2。**

用户可能的回复方式：
- "确认" / "LGTM" → 全部采纳 AI 建议
- 逐项调整（如"第 3 个不迁"）→ AI 更新分析文档中对应行的"决策"列
- "这几个也要进 3C" → AI 调整并更新

**确认后**：用 `replace_in_file` 把分析文档中所有 `⏳` 更新为 `✅ 进3C` / `❌ 不进` / `⏭️ 已有`。

---

## Phase 2 — 设计

**输入**：Phase 1 确认后的分析文档

**输出**：`Content/LetsGo3C/Migration/Analysis/EventMigration/<batch_name>_plan.md`

### 2.1 LetsGo3CEvents.lua 差异补丁

列出需要追加到 `LetsGo3CEvents.lua` 的 flat key，格式与现有文件风格一致：

```lua
-- ====== <YYYY-MM-DD> @<handle> 从 <batch_name> 事件迁移批次迁入 ======

-- <注释说明 dispatch 签名>
KEY_NAME = "value_string",
```

**铁律**：value string 必须与源仓库声明**字符精确一致**。

### 2.2 LetsGo3CSubtableEvents.lua 差异补丁

列出需要追加到 `LetsGo3CSubtableEvents.lua` 的 subtable key。如果该文件不存在，给出完整新文件内容。

```lua
local LetsGo3CSubtableEvents = {
    SubTableName = {
        KeyName = "value_string",
    },
}
return LetsGo3CSubtableEvents
```

### 2.3 Hook 升级补丁（仅首次引入子表事件时）

如果本批有子表事件且 `PostInitEvents` Hook 尚未注册：

**(a)** 新文件 `LetsGo3C/Script/Hooks/Event/CommonEventEnumPostInitEventsHook.lua`：

```lua
local CommonEventEnumPostInitEventsHook = {}

function CommonEventEnumPostInitEventsHook:Execute(ctx)
    local EventsList = ctx.EventsList
    local subtableEvents = require("LetsGo3C.Script.Core.Event.LetsGo3CSubtableEvents")
    EventsList[#EventsList + 1] = subtableEvents
end

return CommonEventEnumPostInitEventsHook
```

**(b)** `SDK_HookConfig.lua` 追加条目：

```lua
{
    HookName    = "CommonEventEnum.PostInitEvents",
    Source      = "LetsGo3C",
    HandlerPath = "LetsGo3C.Script.Hooks.Event.CommonEventEnumPostInitEventsHook",
    Priority    = 100,
},
```

### 2.4 源仓库删除清单（可选）

| 原文件 | key | 操作建议 | 理由 |
|--------|-----|---------|------|
| `file:line` | `KEY` | 删除/保留 | <说明> |

**默认策略：保留源仓库声明**。双份声明不会冲突（同一 value string），3C 拿到独立来源即完成依赖倒置。
用户可显式要求"完全删除源仓库声明"以减少冗余。

### 2.5 3C 代码内引用切换清单

列出 3C 仓库内仍使用 `_MOE.EventEnum.<已迁移KEY>` 的位置，计划改为 `MOE_3C.EventEnum.<KEY>`。

### 2.6 聊天请求确认

写入文件后，聊天输出精简摘要 + 文件路径。

### ⏸️ 人工确认点 2（硬性门禁）

**AI 必须在此暂停，等待用户确认后才能开始 Phase 3 的文件修改。**

---

## Phase 3 — 实施

**前提**：Phase 2 方案已获用户确认。

### 3.1 修改 LetsGo3CEvents.lua

按 Phase 2 补丁追加 flat key。遵循现有文件风格：
- 注释分区标记（`-- ====== 日期 @handle 迁入说明 ======`）
- 每个 key 上方有 dispatch 签名注释
- value string 精确匹配

### 3.2 创建/修改 LetsGo3CSubtableEvents.lua（如有子表事件）

文件路径：`Content/LetsGo3C/Script/Core/Event/LetsGo3CSubtableEvents.lua`

### 3.3 创建 PostInitEvents Hook（如首次引入）

创建 `CommonEventEnumPostInitEventsHook.lua` 并在 `SDK_HookConfig.lua` 注册。

### 3.4 源仓库删除（按用户决策）

如用户要求删除，使用 `replace_in_file` 移除对应 KV 行。

### 3.5 3C 代码内引用切换

把 3C 仓库内对已迁移 key 的 `_MOE.EventEnum.XXX` 引用改为 `MOE_3C.EventEnum.XXX`。

---

## Phase 4 — 验收

### 4.1 反向扫描

对所有已迁移的 key，在 3C 仓库内搜索是否还有残留的 `_MOE.EventEnum.<KEY>`（应为 0）。

### 4.2 value string 一致性校验

对每个迁移的 key，验证 `LetsGo3CEvents.lua`（或 `LetsGo3CSubtableEvents.lua`）中的
value string 与源仓库声明完全一致。

### 4.3 写迁移记录

按 [`refs/migration-record-template.md`](./refs/migration-record-template.md) 模板写入：
`Content/LetsGo3C/Migration/Records/EventMigration_<batch_name>_<YYYYMMDD>.md`

### 4.4 冒烟检查清单

在迁移记录中包含以下检查项（由用户手动验证）：

- [ ] PIE 启动无 `attempt to index a nil value (field 'EventEnum')` 报错
- [ ] 抽样 flat key：`_MOE.EventEnum.<KEY>` 与 `MOE_3C.EventEnum.<KEY>` 取值一致
- [ ] 抽样 subtable key：`_MOE.EventEnum.<SubTable>.<Key>` 与 `MOE_3C.EventEnum.<SubTable>.<Key>` 取值一致
- [ ] listener 仍能收到 dispatch（抽样验证高频事件）
- [ ] `LetsGo3CEvents.lua` 内无重复 key
- [ ] `LetsGo3CSubtableEvents.lua`（如有）中 value string 与源声明完全一致
- [ ] 3C 代码内不再有 `_MOE.EventEnum.<已迁移KEY>`，统一使用 `MOE_3C.EventEnum`

---

## 输入 / 输出契约

### 输入

用户提供以下任意一种：
- 事件 key 列表（聊天文本 / CSV 文件路径）
- `external_deps_event_keys.csv` 或 `external_deps_event_keys_reviewed.csv`（3C 外部依赖扫描产物）
- 单个/少量事件 key（如在 `ue-3c-lua-migration` 中发现的新外部事件依赖）

### 输出

| 文件 | 阶段 |
|------|------|
| `Migration/Analysis/EventMigration/<batch>_analysis.md` | Phase 1 |
| `Migration/Analysis/EventMigration/<batch>_plan.md` | Phase 2 |
| `LetsGo3C/Script/Core/Event/LetsGo3CEvents.lua`（修改） | Phase 3 |
| `LetsGo3C/Script/Core/Event/LetsGo3CSubtableEvents.lua`（新增/修改） | Phase 3（如有子表） |
| `LetsGo3C/Script/Hooks/Event/CommonEventEnumPostInitEventsHook.lua`（新增） | Phase 3（首次子表） |
| `LetsGo3C/Script/HookConfig/OverrideSDK/SDK_HookConfig.lua`（修改） | Phase 3（首次子表） |
| `Migration/Records/EventMigration_<batch>_<YYYYMMDD>.md` | Phase 4 |

---

## 禁止事项

1. **禁止修改 SDK 代码**：不得修改 `LetsGoSDK/Script/Core/Event/CommonEventEnum.lua` 或 SDK 任何文件
2. **禁止更改 value string**：迁移事件的 value string 必须与源仓库声明字符精确一致，否则 listener 断裂
3. **禁止跳过人工检查点**：两个 ⏸️ 都是硬性门禁，必须等待用户确认
4. **禁止先聊天后写文件**：必须先 write_to_file，再在聊天里摘要
5. **禁止在 LetsGo3CEvents.lua 中放子表**：子表必须走 `LetsGo3CSubtableEvents.lua` + `PostInitEvents` 路径，否则 `AppendEvents` 会覆盖源仓库的同名子表
6. **禁止删除未经确认的源仓库声明**：源仓库 KV 的删除必须在 Phase 2 由用户显式决策
7. **禁止遗漏 dispatch / listener 扫描**：Phase 1 必须扫描全部 5 个 workspace 路径的 4 类 API 调用

---

## 相关文件

| 文件 | 说明 |
|------|------|
| `Content/LetsGo3C/Script/Core/Event/LetsGo3CEvents.lua` | 3C flat 事件枚举 |
| `Content/LetsGo3C/Script/Hooks/Event/CommonEventEnumInitEventsHook.lua` | BeforeInitEvents Hook |
| `Content/LetsGo3C/Script/HookConfig/OverrideSDK/SDK_HookConfig.lua` | Hook 注册配置 |
| `Content/LetsGoSDK/Script/Core/Event/CommonEventEnum.lua` | SDK 事件枚举基座（AppendEvents / InitEvents / PostInitEvents） |
| `Content/LetsGo/Script/Core/Event/EventEnum.lua` | LetsGo 主事件枚举（~1900 key） |
| `Content/LetsGo/Script/Core/Event/GlobalEvents.lua` | LetsGo 全局事件（含子表如 PlayerInfoEvents） |
| `Content/LetsGo/Script/Core/Event/MainGameEvents.lua` | LetsGo 主玩法事件 |
| `Content/Feature/Community/Script/Core/Event/CommunityEvents.lua` | 社区事件（含子表如 Interaction） |
| `Content/LetsGo3C/Migration/Analysis/ExternalDeps/external_deps_event_keys_reviewed.csv` | 外部事件依赖审查表（含 enter_3c 判定） |

---

## 与其他 Skill 的协同

- **`ue-3c-lua-migration`**：Lua 搬迁过程中发现新的外部事件依赖时，可用本 Skill 做事件迁移
- **`ue-3c-external-deps-scan`**：扫描产物 `external_deps_event_keys.csv` 是本 Skill 的典型输入
- **`ue-asset-path-replace`**：事件迁移不涉及资产路径，但可能与资产迁移同批进行
