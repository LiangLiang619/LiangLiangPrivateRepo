# 解耦重构核心理念：代码归位（LetsGo3C 仓库专用变体）

> **定位**：本文件是重构/搬迁的**理念层**文档（3C 仓库专用变体），回答"为什么这么做"和"原则是什么"。
> **母本**：[.cursor/rules/refactoring-philosophy.mdc](../../../../../.cursor/rules/refactoring-philosophy.mdc)（SDK 版，与本文件共享 90% 内容）。
> **操作层**（"AI 怎么执行 3C Lua 迁移"）的唯一权威来源是 [../SKILL.md](../SKILL.md)（`ue-3c-lua-migration`）。
> **差异点**：铁律六（扩展机制）、四种去向 ①（仓库名）、职责-归属对照表（模块清单）。其余 90% 内容与 SDK 版一致。

## 一句话总结

**解耦重构的本质是为每一行代码找到它应该存在的位置。**

## 七条铁律

### 铁律一：每行代码都有原因
```
原来的每一行代码不一定是合理的，但一定是有原因的。
```
即使代码看起来多余、不清晰、像 bug，也不要轻易判定为"可删除"。

### 铁律二：不删除，只搬迁
```
❌ 错误：看起来没用 → 直接删除
✅ 正确：看起来没用 → 搬迁到 _Deprecated/ 目录
```
废弃代码也必须有归属地，那就是 `_Deprecated/` 目录。

### 铁律三：废弃接口保留报错
```lua
-- 原接口保留，实现改为报错
function OldModule:DoSomething()
    error("[DEPRECATED] OldModule:DoSomething() 已废弃。" ..
          "如果看到此错误，说明功能仍在使用！" ..
          "原实现位置：_Deprecated/OldModule.lua")
end
```
**好处**：如果搬迁判断错误，会立即报错暴露，而不是静默失败。

### 铁律四：搬迁要追踪
```
每个搬迁文件头部必须有 @todo_migration 注解，说明来源、状态、负责人。
```
追踪信息直接写在文件里，而不是外部表格，确保代码和文档不分离。

TODO 标记的具体格式和标签定义见：[todo-migration-format-3c.md](./todo-migration-format-3c.md)。

### 铁律五：路径先行，一步到位
```
代码搬迁时，文件的 require 路径在第一天就写对、写到位。
哪怕目标模块还没有真正实现，也先创建空壳文件占好位置。
调用方永远不需要因为搬迁而回来改代码。
```
**为什么**：空壳占位使得调用方从第一天起就是最终形态，后续只需往空壳里填充实现。具体做法见 [../SKILL.md](../SKILL.md) Phase 3。

### 铁律六：子类继承，禁止反向 require + 禁全局注入【3C 版重写，与 SDK 版分歧点】
```
3C 通过 BP 基类 + Lua 基类暴露扩展接口。
业务仓库（LetsGo / Feature / UGC 等）通过 BP 子类 + Lua 子类继承基类并 override 业务方法接入业务。
3C 仓库内部代码禁止反向 require 业务仓库。
3C 仓库内部代码禁止使用 _MOE.xxx 全局注入。
```

**原因**（与 SDK 版相同的核心顾虑）：
1. 多 mod 并行运行时，`_MOE` 写入会互相覆盖，行为不确定
2. 3C 在底层先启动，业务仓库 Lua 代码可能还未加载，时序不可控
3. 全局命名空间无隔离，安全性差
4. 反向 require 会形成"3C → 业务 → 3C"循环依赖，与 3C 仓库"通用基础"的定位冲突

**`_MOE` 的正确用途**：仅用于 C++ 侧注入的引擎单例（如 `_MOE.AssetMgr`），3C 内部代码不直接写 `_MOE.xxx`，统一通过显式 `require("LetsGo3C.Script.X")` 访问。

**与 SDK 的关键差异**：SDK 通过配置驱动（`PlatformManager`/`OverrideConfigLoader`/`StartUpHookSystem`/`AppTiming`）实现跨仓库扩展点。3C **不引入这套配置驱动机制**，而是依赖 OOP 语言原生的子类继承。

**3C 跨仓库扩展的正确接入方式**：

| 扩展需求 | 3C 基类提供 | 业务子类实现 |
|---------|------------|------------|
| 业务 RPC 转发 | `HandleBusinessRPC(self, msg)` 虚方法（默认 noop） | 子类 override，写业务分发逻辑 |
| 业务专属生命周期事件 | `OnBusinessReady(self)` 虚方法（默认 noop） | 子类 override，写业务初始化 |
| 业务依赖的资产路径 | 基类不知道，由业务子类内部处理 | 业务子类内部硬编码或读配置 |

**共同特点**：
- 基类不感知业务，子类位于原仓库
- BP 侧通过类继承关系树（BP_CommunityCharRPCComponent extends BP_CharRPCComponentBase）保持可读性
- Lua 侧通过 `setmetatable` 或 `requireLuaView` 继承基类
- 不需要业务仓库 Lua 已加载

### 铁律七：源文件只加标记，不删内容
```
被迁移的源文件，只在文件头加迁移标记 + 透明转发 + 注释化历史方案。
原文件的全部内容原封不动保留在转发之后，不会被执行。
```
**为什么不删**：保留 git blame/log 历史追溯能力；需要回滚时删掉标记块即可恢复；透明转发保证旧调用方平滑过渡，注释化保留原 `error` 阻断方案以备紧急回滚。

具体的留桩格式见 [../SKILL.md](../SKILL.md) Phase 4。

## 核心原则

### 1. 重构 = 修改结构 + 优化实现

- 核心工作是识别代码职责，然后搬到正确位置
- 每行代码都必须有明确归属（搬迁到正确模块 或 搬迁到 _Deprecated）
- **绝不直接删除任何代码**

### 2. 三步归位法

对每一行/每一段代码：

1. **职责识别**：这行代码是做什么的？它存在的原因是什么？
2. **归属判断**：这个职责应该属于哪个模块？
3. **实施搬迁**：搬迁代码，更新调用方（废弃代码搬到 _Deprecated 并报错）

### 3. 每行代码的四种去向【3C 版微调，仅 ① 描述不同】

| 去向 | 含义 | 关键原则 |
|------|------|---------|
| ① **3C 本仓库** | 归位到已有或新建的 3C 基类模块 | 空壳占位，路径一步到位 |
| ② 其他仓库 | 归位到业务仓库（LetsGo / Feature / UGC / SDK）模块 | **业务相关** → 业务仓库自建子类继承 3C 基类；**SDK 通用能力** → 引用 LetsGoSDK |
| ③ _Deprecated/ | 疑似废弃的代码 | 完整实现搬到 `_Deprecated/`，原接口保留 `error()` |
| ④ 就地保留 | 本来就属于当前模块 | 无需搬迁 |

### 4. 搬迁策略：只搬 1 层，空壳切断依赖链

**核心原则**：只搬当前文件的直接依赖（1 层），为每个依赖创建零依赖的空壳文件。**绝不递归搬迁整棵依赖树**——那会把原仓库大半代码拉进 3C，违背"3C 轻量通用"的初衷。

搬迁分两阶段：搬迁阶段（调用方一步到位 + 空壳占位）→ 填充阶段（各模块独立完善实现）。搬迁阶段绝不处理深层依赖。

### 5. 职责-归属对照表【3C 版完全重写】

| 代码职责 | 应归属模块 |
|---------|-----------|
| 角色基类、角色组件、角色 RPC、网络同步 | `LetsGo3C/Script/Base/Character/Components/` |
| 角色动画、ABP、IK、动画状态机 | `LetsGo3C/Script/Base/Character/Animation/` |
| 角色 BP 主体、骨骼网格、Avatar 装配 | `LetsGo3C/Script/Base/Character/Blueprint/` |
| 物理碰撞、推挤、ReceiveHit、Footprint | `LetsGo3C/Script/Base/Character/Components/`（物理类组件） |
| 移动控制、Locomotion、输入到位移转换 | `LetsGo3C/Script/Base/Controller/Movement/` |
| 输入采样、键鼠/手柄/触屏归一化 | `LetsGo3C/Script/Base/Controller/Input/` |
| 相机 BP 主体、SpringArm、FOV、视角控制 | `LetsGo3C/Script/Base/Camera/Blueprint/` |
| 业务玩法代码（含 UGC/Arena/Community/Lobby/Farm/Chase/Chest/Home/StarP/Commercial 等关键词） | **留 LetsGo 原仓库的业务子类，不进 3C** |
| 通用 SDK 能力（日志/网络/平台/存档/配置） | **走 LetsGoSDK，不进 3C** |
| 疑似废弃/用途不明 | **`_Deprecated/`（接口保留报错）** |

> 与 SDK 版的对比：SDK 版列举的是基础设施模块（PlatformAdaptor / Logger / NetworkManager 等），3C 版列举的是 Character/Controller/Camera 三类基础能力 + "不进 3C" 的边界。

> ⚠️ **AI 绝对禁止**：永远不要输出"建议删除"！对于疑似废弃代码，必须输出"_Deprecated（接口报错）"。

## 参考文档

- 操作手册（本仓库专用）：[../SKILL.md](../SKILL.md)（`ue-3c-lua-migration`）
- TODO 标记规范（本仓库专用）：[todo-migration-format-3c.md](./todo-migration-format-3c.md)
- SDK 版理念母本：[.cursor/rules/refactoring-philosophy.mdc](../../../../../.cursor/rules/refactoring-philosophy.mdc)
- 详细说明（共享）：`Content/LetsGoSDK/Script/CodingRules/refactoring-code-homing.md`（SDK 版深度参考，3C 可借鉴方法学但仓库名按 3C 替换）
