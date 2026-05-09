---
name: ue-lua-rebind
description: >-
  Rebind Widget Blueprint assets' Lua script paths after code migration to LetsGoSDK.
  Checks UIWndNameToLuaPath config and Blueprint View property, verifies new SDK script
  exists, smart-detects requireLuaView compatibility, and updates bindings via UE Editor
  MCP. Generates a timestamped rebind report. Use when the user asks to rebind scripts,
  换绑脚本, 替换资产绑定路径, update widget Lua binding, fix script binding after migration,
  脚本换绑, 资产脚本绑定替换, or provides a list of widgets needing rebind.
---

# UE Lua Script Rebind

Rebind Widget Blueprint assets' Lua script `View` property and/or `UIWndNameToLuaPath` config entries after Lua code has been migrated into `LetsGoSDK/Script/`. Verifies the new script file exists and that the runtime path resolver (`requireLuaView`) can handle the new path format.

## Workspace-Adaptive Directory Resolution

1. Find `PROJECT_ROOT`: nearest ancestor containing `*.uproject`. If workspace is `Content/`, parent is `PROJECT_ROOT`.
2. Derive:

```
CONTENT_ROOT  = PROJECT_ROOT/Content
```

## Prerequisites

- UE Editor running with MCP plugin active
- Verify: `ue_ping` on server `user-ue-editor-mcp`

## Phase 1: Input & Asset Filtering

### Mode A -- From Migration Records

Parse migration records under:

```
CONTENT_ROOT/LetsGoSDK/Migration/AssetMigrationRecord/AssetMigration/migration_*.md
```

1. Use `Glob` to find all `migration_*.md` files
2. If multiple, use the latest timestamp or ask user to pick
3. Read the markdown table under `## Migration Details` or `## 迁移明细`
4. Extract rows where `Result` is `OK` or `成功`
5. **Filter to Blueprint/Widget assets only**: keep rows where:
   - `Asset Type` column = `WidgetBlueprint` or `Blueprint`, OR
   - Asset name starts with `UI_` / `WBP_` / `BP_` (heuristic when no type column)
6. For rows **without** `Asset Type` column, verify each candidate via UE Editor MCP:

```
CallMcpTool(server="user-ue-editor-mcp", toolName="ue_actions_run",
  arguments={"action_id": "blueprint.get_summary", "params": {"blueprint_name": "<name>"}})
```

If `parent_class` includes `UserWidget` / `MoeUserWidgetBase` / `MoeUserWidgetItem` / `MoeUserWidgetDrag`, it is a widget that may have a `View` binding.

### Mode B -- Direct Asset List

User provides asset names or UE paths directly. Normalize to `(asset_name, ue_asset_path)` tuples.

## Phase 2: requireLuaView Compatibility Check

Read `CONTENT_ROOT/LetsGoSDK/Script/Core/Common/GlobalLuaSettings.lua` and locate the `requireLuaView` function body.

**Detection logic**: Search the function body for a branch handling `LetsGoSDK` prefix. Patterns to look for:

- `string.startwith(script, "LetsGoSDK")` or `script:find("LetsGoSDK")`
- A direct `require(script)` branch (instead of `"LetsGo.Script." .. script`) that covers SDK paths

Set `supports_sdk_prefix = true` if any such branch exists.

### If NOT supported

Warn the user:

> "当前 `requireLuaView` 不支持 `LetsGoSDK` 前缀路径的直接解析。设置 `View = "LetsGoSDK.Script.xxx"` 会导致运行时 `require("LetsGo.Script.LetsGoSDK.Script.xxx")` 错误拼接。
>
> 可选方案：
> 1. **跳过 View 替换** — 保持现有重定向链（旧路径 → redirect stub → SDK 文件），功能正常但有额外跳转
> 2. **仅更新 UIWndNameToLuaPath** — 在配置表中使用完整 `LetsGoSDK.Script.xxx` 路径（绕过 `requireLuaView`，由 `GetLuaViewPathByWndNameOrWidget` 直接返回给调用方，但需确认上游调用方是否也走 `requireLuaView`）
> 3. **先修改 requireLuaView 再执行本 skill** — 推荐
>
> 请选择方案或输入 'abort' 中止。"

**STOP and wait for user response.** If user chooses option 1, mark all assets as `skipped_view_requireLuaView`. If option 2, only update UIWndNameToLuaPath. If option 3, abort and let user fix first.

## Phase 3: Lua Script Migration Verification

For each asset from Phase 1, find the old binding and the new SDK script path.

### 3.1 Determine Current Binding Source

Check in priority order (matches runtime resolution):

**A. UIWndNameToLuaPath lookup**

1. Search `CONTENT_ROOT/LetsGo/Script/Config/UIWndNameToLuaPath.lua` for `["<asset_name>"]`
2. Search for feature-specific files: `CONTENT_ROOT/Feature/*/Script/Config/UIWndNameToLuaPath_*.lua` for `["<asset_name>"]`
3. If found, record `binding_source = "UIWndNameToLuaPath"` and `old_lua_path = <value>`

**B. Widget View property**

If no UIWndNameToLuaPath entry found, query via UE Editor MCP:

```
CallMcpTool(server="user-ue-editor-mcp", toolName="ue_actions_run",
  arguments={"action_id": "blueprint.get_summary",
             "params": {"blueprint_name": "<asset_name>"}})
```

Check if `variables` contains `View` of type `string`. The View default value is the binding path. To read it, there is no dedicated "get default" action, so note that the value will be set in Phase 5.

Record `binding_source = "View"`.

### 3.2 Find New SDK Script Path

Search for the migrated script in multiple ways (stop at first match):

1. **Redirect stub**: Read the old Lua file and look for `do return require("LetsGoSDK.Script....")`. Extract the target path.
   - Old file location: derive from `old_lua_path` by converting dot notation to path. E.g.:
     - `Feature.System.Script.System.Login.UI_Login` → `CONTENT_ROOT/Feature/System/Script/System/Login/UI_Login.lua`
     - `System.Login.UI_Login` → `CONTENT_ROOT/LetsGo/Script/System/Login/UI_Login.lua`

2. **MigratedFiles.lua**: Search `CONTENT_ROOT/LetsGoSDK/Script/Core/Guard/MigratedFiles.lua` for the old require path. The value is the new path.

3. **Glob search**: `Glob` for `CONTENT_ROOT/LetsGoSDK/Script/**/<asset_name>.lua`. If exactly one match, use it as the new script. If multiple matches, present to user for selection.

### 3.3 Verify New File Exists

Convert the new require path (e.g. `LetsGoSDK.Script.Login.UI.UI_Login`) to filesystem path (`CONTENT_ROOT/LetsGoSDK/Script/Login/UI/UI_Login.lua`) and verify via `Read` or `Glob`.

### 3.4 Classify Each Asset

| Status | Condition |
|--------|-----------|
| `rebindable` | New SDK script found and verified on disk |
| `already_on_sdk` | Current binding already points to `LetsGoSDK` path |
| `no_migration_found` | No redirect stub, no MigratedFiles entry, no matching file in SDK |
| `file_missing` | New path identified but `.lua` file not found on disk |

## Phase 4: Confirmation

Present findings to user:

```
## 换绑预览

- **requireLuaView 兼容**: 是/否
- **可换绑资产**: X
- **已在SDK**: Y
- **未找到迁移**: Z
- **文件缺失**: W

| # | 资产名 | 绑定来源 | 旧路径 | 新路径 | 状态 |
|---|--------|----------|--------|--------|------|
| 1 | UI_Login | View | Feature.System.Script.System.Login.UI_Login | LetsGoSDK.Script.Login.UI.UI_Login | rebindable |
| 2 | UI_MessageBox | UIWndNameToLuaPath | System.Common.UI_MessageBox | (not found) | no_migration_found |
```

Ask: **"请确认以上换绑计划。回复 confirm 继续，或提供修正。"**

**DO NOT proceed until user confirms.**

## Phase 5: Execute Binding Updates

### 5.1 Update View Property (via UE Editor MCP)

For each `rebindable` asset where `binding_source = "View"` or View also needs updating:

```
CallMcpTool(server="user-ue-editor-mcp", toolName="ue_actions_run",
  arguments={"action_id": "variable.set_default",
             "params": {"blueprint_name": "<asset_name>",
                         "variable_name": "View",
                         "default_value": "<new_lua_path>"}})
```

Then compile and save:

```
CallMcpTool(server="user-ue-editor-mcp", toolName="ue_actions_run",
  arguments={"action_id": "blueprint.compile",
             "params": {"blueprint_name": "<asset_name>"}})
```

Use `ue_batch` when processing multiple assets for performance.

### 5.2 Update UIWndNameToLuaPath Config

For each `rebindable` asset where `binding_source = "UIWndNameToLuaPath"`:

1. Read the config file containing the entry
2. Use `StrReplace` to update the value:
   - `old_string`: `["<asset_name>"] = "<old_lua_path>"`
   - `new_string`: `["<asset_name>"] = "<new_lua_path>"`
3. If entry is in a feature-specific file, update that file

### 5.3 Record Results

For each asset, record: `success` / `failed` / `skipped` with error details if any.

## Phase 6: Report Generation

### 6.1 Report Location

```
CONTENT_ROOT/LetsGoSDK/Migration/AssetMigrationRecord/ScriptRebind/rebind_YYYYMMDD_HHMMSS.md
```

Create the directory if it does not exist.

### 6.2 Report Template

```markdown
# Lua 脚本换绑记录

- **日期**: YYYY-MM-DD HH:MM:SS
- **关联迁移记录**: migration_YYYYMMDD_HHMMSS.md（或 "用户直接输入"）
- **资产总数**: N
- **成功换绑**: X
- **跳过**: Y
- **失败**: Z

## requireLuaView 兼容性

- **支持 LetsGoSDK 前缀**: 是/否
- **GlobalLuaSettings.lua 路径**: CONTENT_ROOT/LetsGoSDK/Script/Core/Common/GlobalLuaSettings.lua
- **处理方式**: 直接换绑 / 仅更新配置表 / 跳过 View

## 换绑明细

| # | 资产名 | 资产路径 | 绑定来源 | 旧路径 | 新路径 | 结果 | 备注 |
|---|--------|----------|----------|--------|--------|------|------|
| 1 | UI_Login | /Game/LetsGoSDK/.../UI_Login | View | Feature.System...UI_Login | LetsGoSDK.Script...UI_Login | 成功 | |
| 2 | UI_MessageBox | /Game/LetsGoSDK/.../UI_MessageBox | UIWndNameToLuaPath | System.Common.UI_MessageBox | LetsGoSDK.Script...UI_MessageBox | 成功 | |

## 已修改文件

| # | 文件路径 | 修改类型 | 修改数 |
|---|----------|----------|--------|
| 1 | UI_Login.uasset (via MCP) | View 属性 | 1 |
| 2 | UIWndNameToLuaPath.lua | 配置表项 | 1 |

## 未处理资产

| # | 资产名 | 原因 |
|---|--------|------|
| 1 | UI_GM | no_migration_found: 未找到 LetsGoSDK 下的迁移脚本 |

## 汇总

- 绑定更新方式: View 属性 (UE Editor MCP) + UIWndNameToLuaPath 配置表
- requireLuaView 兼容性检查: 已执行
- 新脚本文件验证: 已验证存在于磁盘
```

### 6.3 Notify User

After generating the report, inform the user:
- Report file path
- Summary: success / skipped / failed counts
- List all modified files
- If any assets were skipped, explain why

## Exception Handling

| Scenario | Action |
|----------|--------|
| UE Editor not connected (`ue_ping` fails) | Stop; ask user to launch UE with MCP |
| `GlobalLuaSettings.lua` not found | Warn user; skip requireLuaView check; proceed with caution |
| Blueprint has no `View` variable | Asset uses a different binding mechanism; log as `skipped_no_view` |
| `variable.set_default` fails | Log error; continue with remaining assets |
| `blueprint.compile` fails | Log compile errors; continue |
| Old Lua file not found (no redirect stub) | Fall back to MigratedFiles.lua or Glob search |
| Multiple Lua files match Glob | Present matches to user for selection |
| UIWndNameToLuaPath `StrReplace` fails | Expand context and retry; if still fails, log and skip |
| Migration record table uses Chinese headers | Handle both `## Migration Details` / `## 迁移明细` and `Result = OK` / `结果 = 成功` |

## Notes

- This skill modifies `.uasset` files **only via UE Editor MCP** (never directly on disk).
- Text config files (`UIWndNameToLuaPath*.lua`) are modified via `StrReplace`.
- Always verify the new `.lua` script file exists on disk before attempting any rebind.
- The `requireLuaView` compatibility check is critical; do NOT skip it.
- This skill is complementary to `ue-asset-migration` (moves UE assets) and `ue-asset-path-replace` (updates hardcoded `/Game/...` strings). This skill specifically handles the **Lua script module path binding** on Widget Blueprints.
