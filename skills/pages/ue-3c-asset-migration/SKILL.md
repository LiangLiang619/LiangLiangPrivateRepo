---
name: ue-3c-asset-migration
description: >-
  Execute UE 3C asset migration from /Game/LetsGo or /Game/Feature into
  /Game/LetsGo3C based on a path-mapped CSV (output of ue-3c-migration-path-mapper).
  Splits an input xlsx by sheet, filters rows by "搬迁方式" whitelist, verifies the
  engine-side AssetRenameManager.cpp patch (auto-applies if missing), runs the
  migration via UE Editor MCP keeping redirectors, and maintains a single
  cumulative migration record at LetsGo3C/Migration/AssetsMigration/3CAssetsMigrationRecords.md.
  Use when the user asks 3C资产搬迁, 3C资产迁移, LetsGo3C仓库搬迁, execute 3C migration,
  or provides a 3C-mapped CSV/xlsx with 搬迁方式 column.
---

# UE 3C Asset Migration

Migrate 3C-related assets into `/Game/LetsGo3C/` via UE Editor MCP, preserving redirectors at original locations. Driven by a CSV that contains source/destination paths and a `搬迁方式` filter column (typically output of `ue-3c-migration-path-mapper`).

## Prerequisites

- UE Editor running with MCP plugin active
- Python 3.8+ with `openpyxl` (only for xlsx splitting)

## Phase 0 — Input Normalization

### 0.1 Excel input

If user provides `.xlsx`, run the split script:

```bash
python scripts/split_xlsx.py "<input.xlsx>"
```

List the generated CSV files and ask the user which one to use.

### 0.2 CSV input

If user provides `.csv` directly, skip splitting.

### 0.3 Column validation

Verify the CSV contains **all** required columns:
- `外部资产名`
- `外部资产完整路径`
- `3C仓库目标路径`
- `搬迁方式`

If any column is missing, stop and suggest re-running `ue-3c-migration-path-mapper`.

## Phase 1 — Filter & Confirm

### 1.1 Run filter script

```bash
python scripts/filter_csv.py "<csv_path>"
```

The script:
1. Reads every row of the CSV
2. Keeps rows where `搬迁方式` is exactly `资产已调整，可以搬迁` or `直接搬迁`
3. Among kept rows, validates `3C仓库目标路径` starts with `/Game/LetsGo3C/` and is not `[待确认]` or empty — invalid rows go to `skipped`
4. Outputs JSON to stdout: `{ "to_migrate": [...], "skipped": [...] }`

### 1.2 Present confirmation table

Render `to_migrate` as a markdown table:

```
| # | 外部资产名 | 源路径 | 目标路径 | 搬迁方式 | 负责人 |
```

If `skipped` is non-empty, list those separately with reasons.

Ask:
> "请确认以上迁移映射。回复 **confirm** 继续执行，或提供修正。"

**DO NOT proceed to Phase 2 until user explicitly confirms.**

## Phase 2 — Engine Patch Verification

The engine must have a modified `FixReferencesAndRename` that skips reference fix-up and always creates redirectors.

### 2.1 Locate the engine file

Resolve relative to workspace root:

```
<workspace>/../ue4_tracking_rdcsp/Engine/Source/Developer/AssetTools/Private/AssetRenameManager.cpp
```

If the file does not exist, ask the user for the correct engine source path.

### 2.2 Check patch status

```bash
python scripts/check_engine_patch.py "<cpp_path>"
```

The script searches `FixReferencesAndRename` for the UGit redirector block (marker comment + `bCreateRedirector = true` + `ReferencingPackageNames.Empty()`).

- Output `PATCHED` → proceed to Phase 3
- Output `NOT_PATCHED` → proceed to 2.3

### 2.3 Auto-apply patch

```bash
python scripts/apply_engine_patch.py "<cpp_path>"
```

The script:
1. Creates a `.bak` backup of the original file
2. Locates the insertion point (after the CDO warning block, before `UpdatePackageStatus`)
3. Inserts the reference code block from [reference.md](reference.md)

After successful patch, tell the user:

> "已自动修改 AssetRenameManager.cpp（已备份为 .bak）。**请关闭 UE 编辑器并重新编译引擎（Development Editor / Win64），编译完成后回复 `recompiled` 继续。**"

**DO NOT proceed to Phase 3 until user replies `recompiled`.**

## Phase 3 — Migration Execution via UE Editor MCP

### 3.1 Connectivity check

```
CallMcpTool(server="user-ue-editor-mcp", toolName="ue_ping", arguments={})
```

If ping fails, stop and ask user to launch UE Editor with MCP plugin.

### 3.2 Discover rename action

```
CallMcpTool(server="user-ue-editor-mcp", toolName="ue_actions_search",
            arguments={"query": "rename asset move"})
```

Then get the schema:

```
CallMcpTool(server="user-ue-editor-mcp", toolName="ue_actions_schema",
            arguments={"action_id": "<found_action_id>"})
```

### 3.3 Execute migration

**Option A — Native rename action found:**

Use `ue_batch` (max 50 per batch):

```
CallMcpTool(server="user-ue-editor-mcp", toolName="ue_batch", arguments={
    "actions": [
        {"action_id": "<rename_action>", "params": {"source": "<src>", "destination": "<dst>"}},
        ...
    ],
    "continue_on_error": true
})
```

**Option B — Python fallback:**

```python
import unreal

migrations = [
    ("/Game/LetsGo/Assets/Foo", "/Game/LetsGo3C/Assets/Base/Character/Animation/Foo"),
]

results = []
for src, dst in migrations:
    ok = unreal.EditorAssetLibrary.rename_asset(src, dst)
    results.append((src, dst, "OK" if ok else "FAILED"))

for src, dst, status in results:
    unreal.log(f"[3C-Migration] {src} -> {dst}: {status}")
```

### 3.4 Constraints

- **NEVER** call any fix-up or redirector cleanup actions
- On failure, log and continue with remaining assets
- After batch completes, check `ue_logs_tail` for errors

### 3.5 Post-execution verification

For each migrated asset, verify:
1. Destination `.uasset` exists on disk (use `Glob`)
2. Source `.uasset` still exists (redirector preserved)

Report discrepancies.

## Phase 4 — Migration Record (Cumulative Update)

### 4.1 Record file

Fixed location:
```
<workspace>/LetsGo3C/Migration/AssetsMigration/3CAssetsMigrationRecords.md
```

### 4.2 Run update script

Collect the batch results into a JSON file `<batch_result>.json`:

```json
[
  {
    "asset_name": "Foo",
    "source_path": "/Game/LetsGo/Assets/Foo",
    "dest_path": "/Game/LetsGo3C/Assets/Base/Character/Animation/Foo",
    "migration_method": "直接搬迁",
    "owner": "someone",
    "status": "成功",
    "note": ""
  }
]
```

Then run:

```bash
python scripts/update_record.py --record "<record_md_path>" --batch "<batch_result>.json"
```

The script performs an **idempotent merge** keyed by `source_path`:
- Existing row → update status, dest_path, owner, method, latest_time; preserve first_time
- New row → insert with first_time = latest_time = now
- Rewrite the entire file sorted by first_time ascending
- Regenerate the summary block at the top

### 4.3 Record table schema

```
| # | 外部资产名 | 源路径 | 目标路径 | 搬迁方式 | 负责人 | 迁移状态 | 首次迁移时间 | 最近更新时间 | 备注 |
```

`迁移状态` values: `成功` / `失败: <reason>` / `已重定向（再次搬迁）`

## Phase 5 — Summary

Report to user:
- Batch success/failure counts
- Record file path
- Failed asset details (if any)
- Prompt: suggest running `ue-asset-path-replace` to fix hardcoded references in Lua/INI/C++ files

## Error Handling

| Scenario | Action |
|----------|--------|
| UE Editor not connected (`ue_ping` fails) | Stop, ask user to launch UE Editor with MCP |
| Engine patch missing & auto-patch fails | Show manual patch instructions from [reference.md](reference.md), stop |
| CSV missing required columns | Error, point to `ue-3c-migration-path-mapper` |
| Destination path already has asset | Warn user, ask skip or overwrite |
| Record file parse failure | Backup as `*.broken.<timestamp>.md`, rebuild from current batch |
| MCP timeout | Retry once, then report error |
