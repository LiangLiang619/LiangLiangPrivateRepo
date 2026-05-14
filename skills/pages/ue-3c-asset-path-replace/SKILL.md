---
name: ue-3c-asset-path-replace
description: >-
  Scan and replace hardcoded UE asset path references in Lua, INI, C++, Python,
  CSV, JSON files after 3C asset migration to /Game/LetsGo3C. Reads from the
  cumulative 3CAssetsMigrationRecords.md or direct old/new path pairs, and
  maintains a single cumulative replace record at
  LetsGo3C/Migration/AssetsMigration/3CAssetsPathReplaceRecords.md.
  Use when prompted by ue-3c-asset-migration, or when the user asks 3C硬编码路径替换,
  3C路径替换, 3C资产迁移后路径修复, fix 3C hardcoded references.
---

# UE 3C Asset Path Replace

Scan and replace hardcoded asset path references in code/config files after 3C asset migration to `/Game/LetsGo3C/`. Driven by the cumulative migration record produced by `ue-3c-asset-migration`, or by direct user input. Maintains a single cumulative replace record with idempotent merge.

## Phase 0 — Workspace-Adaptive Resolution

Resolve project layout at the start of every run:

1. Find `PROJECT_ROOT`: nearest ancestor containing `*.uproject`. If the workspace itself is `Content/`, `PROJECT_ROOT` is its parent.
2. Derive:

```
PROJECT_ROOT  = <directory containing *.uproject>
CONTENT_ROOT  = PROJECT_ROOT/Content
CONFIG_ROOT   = PROJECT_ROOT/Config
PLUGINS_ROOT  = PROJECT_ROOT/Plugins
```

3. If a derived directory does not exist, skip it during scanning and note in the report.

## Phase 1 — Collect Replacement Pairs (Two Modes)

### Mode A — From cumulative 3C migration record (default)

```bash
python scripts/parse_migration_record.py "<CONTENT_ROOT>/LetsGo3C/Migration/AssetsMigration/3CAssetsMigrationRecords.md"
```

The script:
1. Parses the markdown table written by `ue-3c-asset-migration`
2. Keeps rows where `迁移状态` is `成功` or `已重定向（再次搬迁）`
3. Outputs JSON to stdout: `[{ "asset_name": "...", "old_path": "/Game/LetsGo/...", "new_path": "/Game/LetsGo3C/..." }, ...]`

If the record file is missing/empty, suggest the user run `ue-3c-asset-migration` first, or switch to Mode B.

### Mode B — Direct list

User provides old/new path pairs in any of:
- `old_path -> new_path` lines
- A two-column table (Source / Destination)
- A single pair

Normalize to UE internal format (`/Game/...`).

## Phase 2 — Path Variant Generation

For each `(old_path, new_path)` pair, generate two search/replace variants. The **replace value is taken from the record verbatim**, not derived from rules (so 3C subdir judgements are not re-done here).

| Variant | Search example | Replace example |
|---------|---------------|-----------------|
| `ue_path` | `/Game/LetsGo/Foo/Bar` | `/Game/LetsGo3C/Assets/Base/Character/Animation/Bar` |
| `content_relative` | `Content/LetsGo/Foo/Bar` | `Content/LetsGo3C/Assets/Base/Character/Animation/Bar` |

The Content-relative variant is derived mechanically by stripping the leading `/Game/` and prepending `Content/` on both sides. See [reference.md](reference.md) for details.

## Phase 3 — Scan Matrix

Scan each directory below **individually** with one `Grep` call per pattern per directory (do **not** scan from workspace root in a single call — `.gitignore`/ripgrep rules may silently exclude files).

| Directory | What to look for |
|-----------|------------------|
| `Content/LetsGo/Script/` | Lua scripts |
| `Content/Feature/` | Feature mod Lua scripts |
| `Content/LetsGo3C/Script/` | 3C internal Lua (if exists) |
| `Content/LetsGoSDK/Script/` | SDK Lua scripts |
| `Config/` | Engine/game configs |
| `Plugins/` | C++ hardcoded paths |
| `ArtResourceCheck/` | Python tool scripts |
| `BuildConfig/` | Build/pak CSV/JSON |
| `Content/` (non-recursive) `*.csv`, `*.json` | Top-level config files |

**Always exclude** hits inside `Content/LetsGo3C/Migration/AssetsMigration/` (record files) and `Content/LetsGoSDK/Migration/`.

Use `output_mode: "content"` to get file path + line number + matched line. Run scans in parallel by issuing multiple Grep calls in a single message.

## Phase 4 — Classify & Confirm

Classify each hit:

| Classification | Criteria | Default action |
|----------------|----------|----------------|
| `auto_replace` | Substring match in static string/path literal | Auto-replace |
| `comment_only` | Hit on comment line (`--`, `//`, `#`, `;`) | Auto-replace (keep comments accurate) |
| `manual_review` | Inside `string.format` / `FString::Printf` / concatenation / ambiguous | Defer to user |

Present a summary table:

```
## 扫描结果

- 命中总数: N
- 可自动替换: X
- 注释内: Y
- 需人工确认: Z

### 自动替换预览
| # | 文件 | 行号 | 替换前(摘要) | 替换后(摘要) |
...

### 需人工确认
| # | 文件 | 行号 | 内容 | 原因 |
...
```

Ask: **"请确认以上自动替换。对于需人工确认的项，回复行号也一并替换，或回复 'skip' 跳过。"**

**DO NOT proceed to Phase 5 until user confirms.**

## Phase 5 — Execute Replacements

For each confirmed replacement:
1. Read file
2. Use `StrReplace` with the matched line as `old_string` and the path-replaced line as `new_string`
3. If non-unique, extend context until unique
4. On final failure, mark as `失败: <reason>` and continue

Process files sequentially; within a file, apply replacements top-to-bottom.

While executing, collect per-replacement results into an in-memory batch list. Each entry:

```json
{
  "file_rel_path": "Content/LetsGo/Script/Game/Foo.lua",
  "old_path": "/Game/LetsGo/Assets/Foo",
  "new_path": "/Game/LetsGo3C/Assets/Base/Character/Animation/Foo",
  "variant": "ue_path",
  "occurrences_this_run": 2,
  "status": "成功"
}
```

`status` values: `成功` / `失败: <reason>` / `跳过(人工)`.

Per `(file_rel_path, old_path)` aggregate across the run: sum `occurrences_this_run`, take the worst status (`失败` > `跳过(人工)` > `成功`).

## Phase 6 — Cumulative Record Update

Write the batch list to a temporary JSON, then merge:

```bash
python scripts/update_replace_record.py \
    --record "<CONTENT_ROOT>/LetsGo3C/Migration/AssetsMigration/3CAssetsPathReplaceRecords.md" \
    --batch  "<batch_result>.json"
```

Merge rules (primary key = `(file_rel_path, old_path)`):

- **Existing row** → add `occurrences_this_run` to `累计替换次数`; update `新路径` / `变体` / `最近状态` / `最近更新时间`; preserve `首次替换时间`. If the new run produced zero new replacements while status remains `成功`, append note `重复扫描无新增`.
- **New row** → insert with `首次替换时间 = 最近更新时间 = now`, `累计替换次数 = occurrences_this_run`.

Re-write the entire table sorted ascending by `首次替换时间`. Regenerate the top statistics block.

See [reference.md](reference.md) for the full table schema and example rows.

## Phase 7 — Summary Report

Output to the user:
- Batch stats: hits, success, failed, skipped
- Record file path
- Set of files modified this run
- Any failed/skipped entries (so the user can follow up)

## Error Handling

| Scenario | Action |
|----------|--------|
| `3CAssetsMigrationRecords.md` missing or table empty | Suggest running `ue-3c-asset-migration` first, or switch to Mode B |
| Record file parse failure (corrupted by manual edit) | Backup as `*.broken.<timestamp>.md`, rebuild from current batch |
| Scan directory not found | Skip, note in summary |
| `StrReplace` non-unique match | Extend context once; if still failing record `失败: 非唯一匹配` and continue |
| `.uasset` / `.umap` binary file in hits | Never modify; binary files should not surface in Grep but guard anyway |
| File read-only / locked | Record error, continue with remaining files |

## Notes

- Do not change file encoding or line endings.
- Comment-line hits are auto-replaced to keep docs accurate.
- INI `+Key=...` array entries: replace only the value portion, keep the `+Key=` prefix intact.
- Same line containing multiple path matches: use a single `StrReplace` on the whole line.
