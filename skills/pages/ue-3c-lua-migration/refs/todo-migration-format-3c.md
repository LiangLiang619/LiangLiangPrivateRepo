# 搬迁 TODO 标记规范（LetsGo3C 仓库专用变体）

> **一句话**：搬迁过程中所有待处理事项，统一用 `-- TODO(Migration/标签):` 写在代码里（3C 仓库专用变体）。
>
> **与 SDK 版的差异**：6 个标签（SDK 版 5 个 + 第 6 个 `Subclass`）、负责人路径改 3C、示例代码全部换为 3C 范例。
>
> **母本**：[Content/LetsGoSDK/Script/CodingRules/todo-migration-format.md](../../../../LetsGoSDK/Script/CodingRules/todo-migration-format.md)

---

## 核心设计

### 为什么 TODO 写在代码里

搬迁是多人 + 多 AI 长期协作过程，TODO 如果记在外部文档（Wiki、表格、Issue）里：
- 代码改了但忘记更新外部文档 → **丢失**
- 外部文档没人看 → **遗忘**
- 换人接手时找不到上下文 → **低效**

**写在代码里的好处**：
1. **不丢失**——TODO 跟随代码提交到 Git，不会因为换人/换工具而丢失
2. **有上下文**——TODO 紧贴相关代码，打开文件就能看到问题和方案
3. **可扫描**——统一格式 + 脚本自动扫描，一键生成全量报告
4. **跨仓库可见**——其他仓库的开发者打开文件就能看到"3C 侧需要我做什么"

---

## 统一格式

```lua
-- TODO(Migration/标签): 简述问题 | 方案: 怎么解决 | @负责人
```

| 组成部分 | 说明 | 必填 |
|---------|------|------|
| `TODO(Migration/标签)` | 固定前缀 + 分类标签 | ✅ |
| 简述问题 | 一句话说清楚什么问题 | ✅ |
| `方案: xxx` | 怎么解决 | ✅ |
| `@负责人` | 从 `Content/LetsGo3C/Intermediate/user.json` 读取 | ✅ |

**向后兼容**：旧格式 `TODO(Migration):` 等价于 `TODO(Migration/Dep):`，扫描脚本两种都识别。

---

## 六种标签【3C 版：SDK 5 种 + 新增 Subclass】

搬迁过程中产生的 TODO 有且仅有六种，用标签区分：

### 1. `Migration/Fill` — 空壳待填充

搬迁阶段（Phase 1）创建的空壳文件，等待 Phase 2 填充真正实现。

```lua
-- 文件：LetsGo3C/Script/Base/Character/Components/CharRPCComponentBase.lua（空壳）
--[[
    @module CharRPCComponentBase
    @description 角色 RPC 组件基类
    @subclass_contract
    - 推荐 override：HandleBusinessRPC

    @todo_migration
    - 来源: LetsGo/Script/Community/Components/CharRPCComponent.lua
    - 状态: 空壳占位
    - 负责人: @yuliangjing
]]

-- TODO(Migration/Fill): CharRPCComponentBase 空壳待填充完整实现 | 方案: 从原仓库搬迁通用 RPC 分发逻辑，业务部分留虚方法由子类 override | @yuliangjing
local CharRPCComponentBase = {}
function CharRPCComponentBase:OnRegister() end
function CharRPCComponentBase:HandleCommonRPC(msg) end
function CharRPCComponentBase:HandleBusinessRPC(msg) end  -- 虚方法，子类 override
return CharRPCComponentBase
```

### 2. `Migration/Dep` — 依赖未就绪

当前文件 require 了一个尚未搬迁的模块，或通过 `_MOE.xxx` 跨仓库访问尚未搬迁的全局单例（最常见的类型）。

**3C 版 Dep 文案铁律**【硬性】：**禁止默认指向 SDK**。3C 是 LetsGo / LetsGoSDK / LetsGo3C 三仓库格局，跨仓库依赖的真实归宿可能是 LetsGoSDK、Data 仓库、业务侧独立搬迁、或搬到 LetsGo3C 内部，**写文案时必须按依赖性质给出真实可能去向**，不能套 SDK 版的默认 SDK 化模板。

固定句式：
```
依赖名 跨仓库依赖（性质括号说明） | 方案: 视性质决定，<可能去向 1>，<可能去向 2>，独立搬迁后改最终 require | @负责人
```

按依赖性质举例：

```lua
-- 通用工具类（可能搬 SDK 或 3C 内部）
-- TODO(Migration/Dep): MoeCharUtils 跨仓库依赖（角色工具类） | 方案: 视性质决定，可能搬 LetsGoSDK 或 LetsGo3C/Script/Base/Character/Utils，独立搬迁后改最终 require | @yuliangjing
local MoeCharUtils = require("LetsGo.Script.Core.Managers.MoeAssetsManager.MoeCharUtils")

-- 业务数据表（绝不进 SDK，由 Data 仓库或业务方处理）
-- TODO(Migration/Dep): _MOE.Tables.PropConfigTable 跨仓库依赖（业务道具配置表） | 方案: 视性质决定，Data 仓库独立搬迁后改最终 require | @yuliangjing

-- 业务 Model（不进 SDK，业务侧处理）
-- TODO(Migration/Dep): _MOE.Models.InLevelControlModel 跨仓库依赖（业务 Model） | 方案: 业务侧后续独立处理或拆虚方法供业务子类 override | @yuliangjing

-- 通用 Manager（很可能进 SDK）
-- TODO(Migration/Dep): _MOE.GameOptimizeSettingManager 跨仓库依赖（性能优化设置管理） | 方案: 视性质决定，可能搬 LetsGoSDK（通用 Manager） | @yuliangjing
```

**典型错误**（避免重复犯）：
```lua
-- ❌ 错误（套了 SDK 版默认偏向，但 PropConfigTable 是业务表不会进 SDK）：
-- TODO(Migration/Dep): _MOE.Tables.PropConfigTable 待迁 SDK | 方案: SDK 化时改为 require LetsGoSDK 路径 | @yuliangjing
```

### 3. `Migration/Config` — 跨仓库配置待创建

3C 侧通过 BP 蓝图资产驱动加载业务子类，但 BP 资产或配置文件还没创建。

```lua
-- TODO(Migration/Config): UGC 业务 BP 子类资产待创建 | 方案: UGC 仓库需新建 BP_CommunityCharRPCComponent 继承 BP_CharRPCComponentBase，并在 Community Game Character SCS 中替换 | @ugcteam
```

### 4. `Migration/Cleanup` — 原仓库待清理

搬迁完成后，原仓库的旧文件需要改为透明转发或 error()。**这个 TODO 写在 3C 侧，标注需要原仓库配合。**

```lua
-- TODO(Migration/Cleanup): 原仓库 LetsGo/Script/Community/Components/CharRPCComponent.lua 需改为 require 转发到 3C | 方案: 原仓库文件改为 do return require("LetsGo3C.Script.Base.Character.Components.CharRPCComponentBase") end | @ugcteam
local Base = require("LetsGo3C.Script.Base.Character.Components.CharRPCComponentBase")
```

### 5. `Migration/Deprecated` — 废弃待确认

搬到 `_Deprecated/` 的代码，需要确认是否真的废弃。

```lua
-- 文件：LetsGo/_Deprecated/Character/LegacyCharComponent.lua
-- TODO(Migration/Deprecated): LegacyCharComponent 疑似废弃 | 方案: 观察 2 周，若无报错则确认废弃 | @yuliangjing
function LegacyCharComponent:OldEntry()
    -- 原始完整实现保留在这里
end
```

### 6. `Migration/Subclass` — 业务子类待创建【3C 版新增】

3C 基类暴露 abstract / virtual 方法，业务仓库需要在自己仓库内创建子类继承基类并 override 业务逻辑，子类创建前会缺失业务能力。**这个 TODO 写在 3C 基类侧，标注需要业务团队配合在自家仓库建子类**。

```lua
-- 文件：LetsGo3C/Script/Base/Character/Components/CharRPCComponentBase.lua
-- TODO(Migration/Subclass): UGC 仓库需创建 CharRPCComponent_UGC.lua 继承 CharRPCComponentBase | 方案: 在 LetsGo/Script/UGC/Components/CharRPCComponent_UGC.lua 中通过 setmetatable 继承基类，override HandleBusinessRPC 注入业务 RPC 转发逻辑 | @ugcteam
function CharRPCComponentBase:HandleBusinessRPC(msg)
    -- 默认 noop，业务子类 override
end
```

**该标签与 BP 子类的对应关系**：
- 通常每个 `Migration/Subclass` Lua TODO 对应一个 BP 子类资产（已由 `ue-3c-asset-migration` Skill 在资产侧创建）
- Lua 子类 + BP 子类共同构成完整的业务侧接入点

---

## 标签速查表【3C 版 6 行】

| 标签 | 含义 | 谁负责 | 哪个阶段处理 |
|------|------|--------|-------------|
| `Fill` | 空壳待填充 | 3C 开发者 | Phase 2 填充阶段 |
| `Dep` | 依赖未就绪 | 3C 开发者 | Phase 1 搬迁阶段 |
| `Config` | 跨仓库配置待创建 | 业务团队 | Phase 1 搬迁阶段 |
| `Cleanup` | 原仓库待清理 | 业务团队 | Phase 1 完成后 |
| `Deprecated` | 废弃待确认 | 3C 开发者 | 观察期后 |
| **`Subclass`** | **业务子类待创建** | **业务团队** | **业务侧响应** |

---

## 查看所有未完成事项

### 方式一：让 AI 扫描（推荐）

直接对 AI 说：
- "检查 3C 所有未完成事项"
- "列出 3C 所有迁移 TODO"
- "查看 3C 迁移进度"
- "列出所有空壳待填充"（按标签筛选）
- "列出所有跨仓库 TODO"（筛选 Config + Cleanup + Subclass）
- "**列出所有业务子类待创建**"（筛选 Subclass）

AI 会自动调用 TODO 扫描脚本（与 SDK 共享 `list-migration-todo` Skill）并生成详细报告。

### 方式二：手动运行脚本

```bash
python ".codebuddy/skills/list-migration-todo/scripts/list_migration_todo.py" "Content/LetsGo3C/Script"
```

### 方式三：IDE 全局搜索

```
# 搜索所有搬迁 TODO
TODO(Migration

# 按标签搜索
TODO(Migration/Fill)       -- 所有空壳待填充
TODO(Migration/Dep)        -- 所有依赖未就绪
TODO(Migration/Config)     -- 所有跨仓库配置待创建
TODO(Migration/Cleanup)    -- 所有原仓库待清理
TODO(Migration/Deprecated) -- 所有废弃待确认
TODO(Migration/Subclass)   -- 所有业务子类待创建
```

### 输出内容

脚本会输出完整的执行报告，包括：
- **执行信息**：时间、Python 版本
- **采用规则**：本文档定义的 TODO 格式
- **扫描范围**：扫描路径、文件类型、排除目录
- **扫描结果**：文件数、TODO 数、按标签/负责人/文件统计
- **输出文件**：CSV 报告路径（可用 Excel 打开）

---

## 负责人填写规则

`@负责人` **必须从 `Content/LetsGo3C/Intermediate/user.json` 文件中读取 `user` 字段**，不得硬编码。

文件格式：
```json
{"user": "你的名字"}
```

如果该文件不存在，需先创建后再添加 TODO。

跨仓库 TODO（`Config` / `Cleanup` / **`Subclass`**）的负责人写 `@业务团队` 或具体业务团队名（如 `@ugcteam` / `@communityteam` / `@arenateam` / `@lobbyteam`）。

---

## TODO 生命周期

```
创建 → 写在代码里，提交到 Git
  ↓
扫描 → 脚本/AI 定期扫描，生成报告
  ↓
处理 → 负责人解决问题
  ↓
关闭 → 删除 TODO 注释行（代码里不再需要标记）
```

**TODO 不会丢失的保证**：
- 写在代码里 → 跟随 Git 版本控制
- 统一格式 → 一行正则扫全仓库
- 分类标签 → 按类型/负责人/阶段筛选

---

## 记忆口诀

> **TODO(Migration/标签) + 问题 + 方案 + @谁（从 Content/LetsGo3C/Intermediate/user.json 读取）**
>
> 六个标签：**Fill（填充）、Dep（依赖）、Config（配置）、Cleanup（清理）、Deprecated（废弃）、Subclass（业务子类）**
>
> 跨仓库 TODO（写 3C 侧、由业务团队响应）：**Config / Cleanup / Subclass**
