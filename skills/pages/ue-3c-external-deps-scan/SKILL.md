---
name: ue-3c-external-deps-scan
description: >-
  Scan all external dependencies in the LetsGo3C repository across 8 categories:
  (1) Lua require + UE4.Class inheritance cross-repo refs,
  (2) hardcoded /Game/ asset paths,
  (3) implicit global coupling (_MOE.* + MOE_3C metatable fallback fields),
  (4) UE asset imports outside 3C/SDK,
  (5) Config/Tables registration source audit,
  (6) EventEnum key origin audit,
  (7) UI/WindowName coupling in 3C base code,
  (8) business keyword presence in functions/paths.
  Outputs 8 CSV detail files + 1 Markdown overview report.
  Aligned with ue-3c-lua-migration skill isolation requirements.
  Use when the user asks 扫描 3C 外部依赖, LetsGo3C 外部依赖, 3C 仓库内聚扫描,
  3C 跨仓库引用, scan letsgo3c external deps, 3C 高内聚检查,
  LetsGo3C external dependency audit.
---

# LetsGo3C External Dependency Scanner

> 只读扫描 LetsGo3C 仓库内所有依赖外部代码的位置，输出 8 份 CSV + 1 份 Markdown 综览。
> **不修改任何文件**。
> 与 `ue-3c-lua-migration` skill 的隔离规则对齐（铁律六 + 外部内容依赖深度分析）。

## 触发关键词

- 扫描 3C 外部依赖 / LetsGo3C 外部依赖 / 3C 仓库内聚扫描
- 3C 跨仓库引用 / scan letsgo3c external deps
- 3C 高内聚检查 / LetsGo3C external dependency audit

## 前置条件

1. Python 3.9+
2. 模式 A（默认/离线）需要 `uasset_mcp` 包（自动探测顺序见 `ue-recursive-deps-scan`）
3. 模式 B（`--asset-mode editor-mcp`）需要 UE Editor 在线 + `user-ue-editor-mcp` 可用

## 白名单规则

详见 [refs/whitelist.md](refs/whitelist.md)。核心逻辑：

- **Lua require 白名单**：`LetsGo3C.*` / `LetsGoSDK.*` / `UE4.*` / `UnLua.*` / Lua 标准库
- **资产路径白名单**：`/Game/LetsGo3C/` / `/Game/LetsGoSDK/` / `/Game/Engine/` / `/Script/` / `/Engine/`
- **全局变量白名单**：`MOE_3C.*`（本仓库专属命名空间）— 但 MOE_3C 中已知回退到 `_MOE` 的字段仍会报告
- **MOE_3C 外部回退字段**：`DsInstance` / `LobbyUtils` / `ItemEffectUtil` / `HomeGame` / `UGC` / `WindowName` / `SocketNameEnum` / `UGCGameStatic` / `GasAbilityManager`
- **业务关键词**（3C 不应包含）：`Farm` / `Arena` / `UGC` / `Chase` / `Chest` / `Home` / `StarP` / `Community` / `Lobby` / `Commercial`

不在白名单中的即为「外部依赖」，按 `LetsGo` / `Feature` / `ProjectT` / `Other` 分类。

## CLI 参数

```bash
python scripts/scan_external_deps.py \
  --repo-root "<绝对或相对路径>" \
  [--content-root "<UE Content 目录>"] \
  [--out-dir "<输出目录>"] \
  [--asset-mode binary|editor-mcp] \
  [--whitelist-extra "Prefix1,Prefix2"] \
  [--lua-globs "Script/**/*.lua,StartUp/**/*.lua"] \
  [--skip-categories "globals,assets,config,events,ui,biz"] \
  [--moe3c-fallback-fields "DsInstance,LobbyUtils,..."] \
  [--biz-keywords "Farm,Arena,UGC,..."]
```

| 参数 | 默认 | 说明 |
|------|------|------|
| `--repo-root` | `Content/LetsGo3C` | 3C 仓库根；相对路径基于 CWD |
| `--content-root` | `<repo-root>/..` | UE Content 目录 |
| `--out-dir` | `<repo-root>/Migration/Analysis/ExternalDeps` | 输出目录 |
| `--asset-mode` | `binary` | `binary`（离线）或 `editor-mcp` |
| `--whitelist-extra` | `""` | 追加自定义白名单前缀，逗号分隔 |
| `--lua-globs` | `Script/**/*.lua,StartUp/**/*.lua,...` | 受扫 Lua 路径模板 |
| `--skip-categories` | `""` | 跳过类别：`require,hardpath,globals,assets,config,events,ui,biz` |
| `--moe3c-fallback-fields` | 内置集合 | 覆盖 MOE_3C 回退字段列表 |
| `--biz-keywords` | 内置 10 个 | 覆盖业务关键词列表 |

## 扫描类别（8 类）

### 1. Lua require + UE4.Class 跨仓库引用 [HIGH]

扫所有 `.lua` 中 `require("xxx")` 和 `UE4.Class("xxx")` 目标不在白名单内的。
UE4.Class 继承构成运行时强耦合。

### 2. Lua 中硬编码 UE 资产路径 [MEDIUM]

扫字符串 `"/Game/..."` 指向 3C/SDK/Engine 之外的外部目录。

### 3. Lua 隐式全局变量耦合 [HIGH]

扫 `_MOE.*` / `_G.LetsGo*` / `_G.Feature*` 以及 `MOE_3C.<fallback_field>` 访问。
MOE_3C 的部分字段在运行时通过 `__index` 回退到 `_MOE`，本质仍是跨仓库依赖。

### 4. UE 资产 imports 外部依赖 [MEDIUM]

扫 `.uasset` 的 imports 表 + FName 表中引用外部 `/Game/...` 包的条目。

### 5. Config/Tables 注册来源审计 [AUDIT]

扫 `MOE_3C.Config.X` / `MOE_3C.Tables.X` 访问。虽通过 SDK 代理，但表的注册方可能在业务仓库。
输出审计清单供人工验证。

### 6. EventEnum Key 来源审计 [AUDIT]

扫 `(MOE_3C|_MOE).EventEnum.X` 访问。EventManager 宿主虽在 SDK，但事件 Key 的定义可能在
LetsGo `GlobalEvents.lua`。需确认每个 Key 定义位置决定处置方式：
- 已在 SDK/3C → 直接使用
- 在 LetsGo 且属 3C 通用能力 → 迁入 LetsGo3CEvents.lua
- 在 LetsGo 且属业务 → 下沉到业务子类

### 7. UI/WindowName 耦合 [HIGH]

扫 `(MOE_3C|_MOE).UIManager:OpenWindow/IsWindowOpened/CloseWindow` 和 `WindowName.X` 访问。
按 3C migration skill 规则，3C 基类原则上不应包含 UI 调用。

### 8. 业务关键词命中 [HIGH]

扫函数定义名、require 路径、文件路径中出现的 10 个业务关键词。
命中即表示业务逻辑残留在 3C 基类，应下沉到业务子类。

## 工作流

1. **Phase 0** — 解析参数，校验路径，探测 `uasset_mcp`
2. **Phase 1** — Lua 全 8 类扫描
3. **Phase 2** — 资产 imports 扫描（binary 或 editor-mcp 模式）
4. **Phase 3** — 写 8 CSV + 1 MD 综览 + 控制台简报

## 输出

输出到 `<out-dir>/`：

| 文件 | 严重等级 | 内容 |
|------|----------|------|
| `external_deps_lua_require.csv` | HIGH | require + UE4.Class 外部引用 |
| `external_deps_lua_hardpath.csv` | MEDIUM | 硬编码 /Game/ 路径 |
| `external_deps_lua_globals.csv` | HIGH | _MOE.* + MOE_3C fallback 全局变量 |
| `external_deps_assets.csv` | MEDIUM | .uasset 外部 imports |
| `external_deps_config_tables.csv` | AUDIT | Config/Tables 表名审计 |
| `external_deps_event_keys.csv` | AUDIT | EventEnum Key 来源审计 |
| `external_deps_ui_coupling.csv` | HIGH | UI/WindowName 调用 |
| `external_deps_biz_keywords.csv` | HIGH | 业务关键词命中 |
| `LetsGo3C_External_Deps_Report.md` | - | 综览 + Top N + 修复优先级 |

详见 [refs/output-schema.md](refs/output-schema.md)。

## 与同生态 skill 的关系

| Skill | 关系 |
|-------|------|
| `ue-3c-lua-migration` | 扫描结果对齐其 Phase 1 分析阶段所需的检查表（_MOE 检查/事件/UI） |
| `ue-recursive-deps-scan` | 复用 `UAssetParser` |
| `ue-migration-deps-scan` | 复用 MCP 批量框架（模式 B） |
| `ue-3c-lua-scan` | 可复用 Lua 索引；本 skill 不做绑定关系 |
