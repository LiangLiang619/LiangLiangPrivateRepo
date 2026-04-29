---
name: ue-asset-migration
description: >-
  Migrate UE assets from /Content/LetsGo or /Content/Feature into /Content/LetsGoSDK
  using UE Editor MCP, preserving redirectors at the original location. Generates a
  timestamped migration record after completion. Use when the user asks to migrate assets
  to LetsGoSDK, move assets to SDK, 资产搬迁, 资产迁移, SDK资产迁移, or provides an
  asset list for migration.
---

# UE Asset Migration

Migrate UE assets from `/Content/LetsGo` or `/Content/Feature` into `/Content/LetsGoSDK` via UE Editor MCP. Original paths retain redirectors (no fix-up). Produces a migration record for traceability.

## Prerequisites

- UE Editor must be running with the MCP plugin active
- Verify connectivity: call `ue_ping` on server `user-ue-editor-mcp` before starting
- The user's engine has a custom modification to `AssetRenameManager.cpp` that preserves redirectors at the original location without fix-up

## Phase 1: Input & Path Normalization

### 1.1 Accept Asset List

The user provides a list of asset paths. Two formats are accepted:

| Format | Example |
|--------|---------|
| UE internal path | `/Game/LetsGo/Assets/Effect/VFX_Foo` |
| Disk path | `Content/LetsGo/Assets/Effect/VFX_Foo.uasset` |

### 1.2 Normalize Paths

Convert every path to UE internal format (`/Game/...`):

1. Strip leading drive letter or workspace prefix (e.g. `F:\F3\LetsGoDevelop\LetsGo\Content\` or `Content\`)
2. Replace backslashes with forward slashes
3. Strip `.uasset` / `.umap` extension if present
4. Prepend `/Game/` if path starts with `LetsGo/` or `Feature/`
5. If path already starts with `/Game/`, keep as-is

Examples:
- `Content/LetsGo/Assets/Foo.uasset` --> `/Game/LetsGo/Assets/Foo`
- `/Game/Feature/Maps/Bar` --> `/Game/Feature/Maps/Bar`
- `Content\Feature\UI\Widget.uasset` --> `/Game/Feature/UI/Widget`

### 1.3 Validate Paths

Optionally verify that each source asset exists:
- Use `Glob` to check if the corresponding `.uasset` file exists on disk under the workspace `Content/` directory
- Report any paths that cannot be found and ask the user whether to skip or abort

## Phase 2: Mapping & Confirmation

### 2.1 Path Mapping Rules

Compute the destination path for each asset:

| Source prefix | Destination prefix | Subdirectory preservation |
|---------------|--------------------|---------------------------|
| `/Game/LetsGo/` | `/Game/LetsGoSDK/` | Everything after `LetsGo/` is kept |
| `/Game/Feature/<ModName>/` | `/Game/LetsGoSDK/` | `Feature/<ModName>/` is stripped; everything after it is kept |

`<ModName>` is the first-level directory under `Feature/`, representing the mod/副玩法 name (e.g. `System`, `Racing`, `Community`).

Examples:
- `/Game/LetsGo/Assets/Effect/VFX_Foo` --> `/Game/LetsGoSDK/Assets/Effect/VFX_Foo`
- `/Game/Feature/System/Assets/Login/Widget` --> `/Game/LetsGoSDK/Assets/Login/Widget`
- `/Game/Feature/Racing/Maps/TestMap` --> `/Game/LetsGoSDK/Maps/TestMap`

### 2.2 Present Confirmation Table

Display a Markdown table to the user and **STOP to wait for explicit confirmation**:

```
| # | Source Path | Destination Path |
|---|-------------|------------------|
| 1 | /Game/LetsGo/Assets/Effect/VFX_Foo | /Game/LetsGoSDK/Assets/Effect/VFX_Foo |
| 2 | /Game/Feature/System/Assets/Login/Widget | /Game/LetsGoSDK/Assets/Login/Widget |
```

Ask:
> "请确认以上迁移映射。回复 **confirm** 继续执行，或提供修正。"

**DO NOT proceed to Phase 3 until the user explicitly confirms.**

## Phase 3: Migration Execution via UE Editor MCP

### 3.1 Discover Available Actions

Search for the rename/move action:

```
CallMcpTool(server="user-ue-editor-mcp", toolName="ue_actions_search",
            arguments={"query": "rename asset move"})
```

Then get the schema for the matching action:

```
CallMcpTool(server="user-ue-editor-mcp", toolName="ue_actions_schema",
            arguments={"action_id": "<found_action_id>"})
```

### 3.2 Execute Migration

**Option A -- Native rename action found:**

Use `ue_batch` for performance (max 50 actions per batch). Build the batch array:

```
CallMcpTool(server="user-ue-editor-mcp", toolName="ue_batch", arguments={
    "actions": [
        {"action_id": "<rename_action>", "params": {"source": "<src>", "destination": "<dst>"}},
        ...
    ],
    "continue_on_error": true
})
```

**Option B -- No native rename action; use Python fallback:**

Search for a Python execution action:

```
CallMcpTool(server="user-ue-editor-mcp", toolName="ue_actions_search",
            arguments={"query": "python execute run script"})
```

Then execute a Python snippet for each asset (or batch them in a single script):

```python
import unreal

migrations = [
    ("/Game/LetsGo/Assets/Foo", "/Game/LetsGoSDK/Assets/Foo"),
    # ...
]

results = []
for src, dst in migrations:
    ok = unreal.EditorAssetLibrary.rename_asset(src, dst)
    results.append((src, dst, "OK" if ok else "FAILED"))

for src, dst, status in results:
    unreal.log(f"[Migration] {src} -> {dst}: {status}")
```

### 3.3 Important Constraints

- **DO NOT** call any fix-up or redirector cleanup actions. Redirectors at the original path must remain.
- If an asset fails to migrate, log the failure and continue with the remaining assets.
- After the batch completes, check `ue_logs_tail` on server `user-ue-editor-mcp` for any error messages.

### 3.4 Post-Execution Verification

For each migrated asset, verify success by checking:
1. The destination `.uasset` file exists on disk (use `Glob` on the workspace)
2. The source path now contains a redirector (the original `.uasset` still exists on disk)

Report any discrepancies to the user.

## Phase 4: Migration Record

### 4.1 Record Location

Generate the record file at:

```
<workspace>/Content/LetsGoSDK/Migration/AssetMigrationRecord/AssetMigration/migration_YYYYMMDD_HHMMSS.md
```

Create the directory if it does not exist.

### 4.2 Record Template

```markdown
# 资产迁移记录

- **日期**: YYYY-MM-DD HH:MM:SS
- **资产总数**: N
- **成功**: X
- **失败**: Y

## 迁移明细

| # | 原路径 | 目标路径 | 资产类型 | 结果 | 备注 |
|---|--------|----------|----------|------|------|
| 1 | /Game/LetsGo/Assets/Foo | /Game/LetsGoSDK/Assets/Foo | Texture2D | 成功 | |
| 2 | /Game/Feature/Maps/Bar | /Game/LetsGoSDK/Maps/Bar | World | 失败 | 错误: ... |

## 汇总

- 原路径前缀: /Game/LetsGo/, /Game/Feature/
- 目标路径前缀: /Game/LetsGoSDK/
- 原路径 Redirector 保留: 是
- 是否执行 Fix-up: 否（引擎 AssetRenameManager.cpp 已修改）
```

### 4.3 通知用户

生成记录文件后，告知用户：
- 迁移记录文件路径
- 汇总：成功数、失败数
- 如有失败资产，逐一列出

### 4.4 硬编码路径替换联动

通知用户后，检查 `ue-asset-path-replace` skill 是否已安装（在可用 skills 列表中查找 `~/.cursor/skills/ue-asset-path-replace/SKILL.md`）。如果已安装，询问用户：

> "检测到硬编码路径替换 skill 已安装。是否扫描并替换 Lua、INI、C++ 等文件中对已迁移资产的硬编码引用？"

用户确认后，读取并执行 `ue-asset-path-replace` skill，将刚生成的迁移记录作为输入（Mode A）。

## 异常处理

| 场景 | 处理方式 |
|------|----------|
| UE 编辑器未连接（`ue_ping` 失败） | 停止并请用户启动带 MCP 插件的 UE 编辑器 |
| 源资产在磁盘上未找到 | 警告用户，询问跳过还是中止 |
| 重命名操作返回错误 | 逐资产记录，继续处理剩余资产，写入记录 |
| 目标路径已存在 | 警告用户，询问覆盖还是跳过 |
| MCP 超时 | 重试一次，仍失败则报告错误 |
