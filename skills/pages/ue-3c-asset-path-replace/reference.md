# Reference: UE 3C Asset Path Replace

## Scan Directory Matrix

All paths relative to `PROJECT_ROOT` (directory containing `*.uproject`).

| Directory | File types | Notes |
|-----------|-----------|-------|
| `Content/LetsGo/Script/` | all text | Main project Lua scripts |
| `Content/Feature/` | all text | Feature mod Lua scripts |
| `Content/LetsGo3C/Script/` | all text | 3C repo internal Lua (may reference legacy paths during transition) |
| `Content/LetsGoSDK/Script/` | all text | SDK Lua scripts that may reference 3C assets |
| `Config/` | all text | `*.ini`, `*.cfg`, etc. |
| `Plugins/` | all text | Plugin source: C++, Lua, configs |
| `ArtResourceCheck/` | all text | Python art validation scripts |
| `BuildConfig/` | all text | Build/pak CSV/JSON |
| `Content/` (non-recursive) | `*.csv`, `*.json` only | Top-level config files |

**Always exclude** hits whose file path contains:
- `Content/LetsGo3C/Migration/AssetsMigration/` (this skill's own record files)
- `Content/LetsGoSDK/Migration/` (previous SDK migration record files)

## Grep Invocation Pattern

For each `(search_pattern, scan_dir)` pair, issue one `Grep` call:

```
Grep(
    pattern=<literal search string, escaped if needed>,
    path=<absolute scan_dir>,
    output_mode="content",
    -n=true
)
```

Notes:
- Do NOT set `glob` or `type` — let Grep search all text files; ripgrep's binary detection skips `.uasset`/`.umap`.
- Do NOT search from `PROJECT_ROOT` in a single call — `.gitignore` / ripgrep ignore rules can silently exclude files.
- Run multiple Grep calls in parallel (one message, multiple tool calls) for throughput.

## Path Variant Generation

Given `old_path = /Game/X/...` and `new_path = /Game/LetsGo3C/...`:

| Variant | Search | Replace |
|---------|--------|---------|
| `ue_path` | `<old_path>` (verbatim) | `<new_path>` (verbatim) |
| `content_relative` | `Content/<X>/...` (replace leading `/Game/` with `Content/`) | `Content/LetsGo3C/...` (same transform on `<new_path>`) |

Example for `/Game/LetsGo/Assets/Foo` → `/Game/LetsGo3C/Assets/Base/Character/Animation/Foo`:

| Variant | Search | Replace |
|---------|--------|---------|
| `ue_path` | `/Game/LetsGo/Assets/Foo` | `/Game/LetsGo3C/Assets/Base/Character/Animation/Foo` |
| `content_relative` | `Content/LetsGo/Assets/Foo` | `Content/LetsGo3C/Assets/Base/Character/Animation/Foo` |

For Feature assets (e.g. `/Game/Feature/System/Assets/Foo` → `/Game/LetsGo3C/Assets/...`), the same mechanical transform applies to both variants — `Content/Feature/System/Assets/Foo` searches the corresponding `Content/` form.

**Important**: The replace value always comes verbatim from the migration record's `目标路径` column (or user-provided pair). Do **not** re-derive 3C subdir classification here — that was already decided by `ue-3c-migration-path-mapper`.

## Classification Heuristics

| Classification | Heuristic |
|----------------|-----------|
| `comment_only` | Line stripped of leading whitespace begins with `--`, `//`, `#`, `;`, or `*` |
| `manual_review` | Line contains any of: `string.format`, `FString::Printf`, `.. "/Game"`, `concat`, `..`, `%s` near the matched path |
| `auto_replace` | All other hits |

## 3CAssetsPathReplaceRecords.md Schema

File: `<CONTENT_ROOT>/LetsGo3C/Migration/AssetsMigration/3CAssetsPathReplaceRecords.md`

### Header

```markdown
# 3C 资产硬编码路径替换记录

> 本文件由 `ue-3c-asset-path-replace` skill 自动维护，请勿手动编辑表格数据。

## 统计

- **累计条目数**: N
- **涉及文件数**: M
- **最近批次时间**: YYYY-MM-DD HH:MM:SS
- **最近批次成功**: X
- **最近批次失败**: Y
- **最近批次跳过**: Z

## 替换明细
```

### Table columns

| Column | Key | Description |
|--------|-----|-------------|
| `#` | — | Auto-increment row number |
| `文件相对路径` | **PK part 1** | Path relative to `PROJECT_ROOT`, forward slashes |
| `原路径` | **PK part 2** | `/Game/...` source path |
| `新路径` | — | `/Game/LetsGo3C/...` destination path (taken from migration record) |
| `变体` | — | `ue_path` / `content_relative` / `ue_path+content_relative` (when both apply) |
| `累计替换次数` | — | Cumulative count across all runs |
| `最近状态` | — | `成功` / `失败: <reason>` / `跳过(人工)` |
| `首次替换时间` | — | First successful replacement timestamp (never overwritten) |
| `最近更新时间` | — | Latest run timestamp |
| `备注` | — | Free-form notes (e.g. `重复扫描无新增`) |

### Merge rules (primary key = `(文件相对路径, 原路径)`)

- **Existing row, new run hits same key**:
  - `累计替换次数 += occurrences_this_run`
  - Update `新路径`, `变体`, `最近状态`, `最近更新时间`
  - Preserve `首次替换时间`
  - If `occurrences_this_run == 0` and `最近状态 == 成功` → append `备注 = 重复扫描无新增`
- **New row** (key never seen):
  - `首次替换时间 = 最近更新时间 = now`
  - `累计替换次数 = occurrences_this_run`

Sort ascending by `首次替换时间` when rewriting.

### Example row

```
| 1 | Content/LetsGo/Script/Game/Foo.lua | /Game/LetsGo/Assets/Foo | /Game/LetsGo3C/Assets/Base/Character/Animation/Foo | ue_path | 2 | 成功 | 2026-05-14 17:00:00 | 2026-05-14 17:00:00 | |
```

## Common Pitfalls

- **Forgetting CRLF**: `StrReplace` matches verbatim; Windows-style files keep `\r\n`. Don't transform line endings in your replacement string.
- **Forgetting per-directory Grep**: A single workspace-root Grep call can silently miss `.lua` under `.gitignore`-ed `Script/` dirs.
- **Re-deriving target path**: Always read `新路径` from the record / user input. Re-deriving from rules risks mismatch with what was actually moved.
- **Touching migration record files**: Always exclude `Content/LetsGo3C/Migration/AssetsMigration/` and `Content/LetsGoSDK/Migration/` from scan results.
