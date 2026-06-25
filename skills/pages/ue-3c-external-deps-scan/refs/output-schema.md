# 输出 CSV 列定义

## 1. external_deps_lua_require.csv

包含 require 外部引用 + UE4.Class 继承外部引用。

| # | 列名 | 类型 | 说明 |
|---|------|------|------|
| 1 | file | string | Lua 文件相对于 repo-root 的路径 |
| 2 | line | int | 行号 |
| 3 | require_module | string | require/UE4.Class 目标模块点号路径 |
| 4 | category | enum | `LetsGo` / `Feature` / `ProjectT` / `Other` |
| 5 | suggested_action | string | 建议操作（搬迁 / 替换为 3C 路径 / 解耦继承） |

UE4.Class 继承条目的 suggested_action 会标注"（UE4.Class 继承）"。

## 2. external_deps_lua_hardpath.csv

| # | 列名 | 类型 | 说明 |
|---|------|------|------|
| 1 | file | string | Lua 文件相对于 repo-root 的路径 |
| 2 | line | int | 行号 |
| 3 | hardcoded_path | string | 硬编码的 `/Game/...` 路径 |
| 4 | category | enum | `LetsGo` / `Feature` / `ProjectT` / `Other` |
| 5 | suggested_action | string | 建议操作 |

## 3. external_deps_lua_globals.csv

包含 `_MOE.*` + `_G.*` + `MOE_3C.<fallback_field>` 访问。

| # | 列名 | 类型 | 说明 |
|---|------|------|------|
| 1 | global_expr | string | 全局表达式，如 `_MOE.EventEnum` / `MOE_3C.DsInstance` |
| 2 | usage_count | int | 使用次数 |
| 3 | files | string | 使用位置列表，`\|` 分隔，每项 `file:line` |
| 4 | suggested_action | string | 建议操作 |

`MOE_3C.*` 条目的 suggested_action 为"运行时回退到 _MOE，需替换为 SDK 来源或本地实现"。

## 4. external_deps_assets.csv

| # | 列名 | 类型 | 说明 |
|---|------|------|------|
| 1 | asset_path | string | 本仓库 .uasset 相对于 repo-root 的路径 |
| 2 | external_dep_path | string | 外部依赖的 `/Game/...` 路径 |
| 3 | category | enum | `LetsGo` / `Feature` / `ProjectT` / `Other` |
| 4 | via_redirector_from | string | 若经 ObjectRedirector 跟随，填原始路径；否则空 |

## 5. external_deps_config_tables.csv [AUDIT]

需人工验证每个表名的注册来源是否在 SDK/3C 内。

| # | 列名 | 类型 | 说明 |
|---|------|------|------|
| 1 | table_name | string | 表名（如 `BackpackItemEffectTable`） |
| 2 | access_type | enum | `Config` / `Tables` |
| 3 | usage_count | int | 访问次数 |
| 4 | files | string | 访问文件列表，`\|` 分隔 |
| 5 | status | string | 默认"待验证"，人工审计后可改为"SDK注册"/"业务注册" |

## 6. external_deps_event_keys.csv [AUDIT]

需人工确认每个事件 Key 的定义位置。

| # | 列名 | 类型 | 说明 |
|---|------|------|------|
| 1 | event_key | string | 事件 Key（如 `ON_CHARACTER_CHANGE_SKIN` / `MoeCharacterEvents.OnXxx`） |
| 2 | usage_type | enum | `Register` / `Dispatch` / `UnRegister` / `Access` |
| 3 | usage_count | int | 访问次数 |
| 4 | files | string | 访问文件列表，`\|` 分隔 |
| 5 | status | string | 默认"待验证"，审计后可改为"SDK定义"/"3C定义"/"LetsGo定义-需迁入"/"业务定义-需下沉" |

与 `ue-3c-lua-migration` Phase 1 事件处置矩阵对应：
- "SDK定义"/"3C定义" → 情形 ① 直接使用
- "LetsGo定义-需迁入" → 情形 ② 迁入 LetsGo3CEvents.lua
- "业务定义-需下沉" → 情形 ③ 下沉到业务子类

## 7. external_deps_ui_coupling.csv [HIGH]

3C 基类原则上不应包含 UI 调用。

| # | 列名 | 类型 | 说明 |
|---|------|------|------|
| 1 | file | string | Lua 文件相对于 repo-root 的路径 |
| 2 | line | int | 行号 |
| 3 | call_type | string | `OpenWindow` / `IsWindowOpened` / `CloseWindow` / `WindowName.X` / `WindowName[dynamic]` |
| 4 | window_name | string | 窗口名（如能提取）；动态访问时为 `(dynamic)` |
| 5 | suggested_action | string | 默认"3C 基类不应包含 UI 调用，下沉到业务子类 override" |

## 8. external_deps_biz_keywords.csv [HIGH]

业务逻辑不应存在于 3C 基类。

| # | 列名 | 类型 | 说明 |
|---|------|------|------|
| 1 | file | string | Lua 文件相对于 repo-root 的路径 |
| 2 | line | int | 行号（0 表示文件路径级别命中） |
| 3 | keyword | string | 命中的业务关键词 |
| 4 | context | string | 命中上下文：`function:FuncName` / `require_path:xxx` / `file_path:xxx` |
| 5 | suggested_action | string | 建议操作 |

## 9. LetsGo3C_External_Deps_Report.md

Markdown 综览，包含：

- 扫描时间 + 参数
- 8 类外部依赖汇总数量（含严重等级）
- 各类 Top 20/30 高频项
- Config/Tables 审计清单
- EventEnum Key 审计清单
- UI/WindowName 耦合清单
- 业务关键词命中清单
- 动态 require 告警清单
- 修复优先级建议（7 级）
