---
name: ue-asset-path-replace
description: >-
  Scan and replace hardcoded UE asset path references across Lua, INI, C++, Python,
  CSV, and JSON files after asset migration. Reads migration records or accepts direct
  old/new path pairs. Use when the user asks to replace hardcoded paths, fix asset
  references after migration, 替换硬编码路径, 扫描资产引用, 迁移后路径替换, or when
  prompted by the ue-asset-migration skill after completing a migration.
---

# UE Asset Path Replace

Scan and replace hardcoded asset path references in code/config files after UE assets have been migrated. Supports reading from migration records or direct user input.

## Workspace-Adaptive Directory Resolution

This skill is installed at the user level and must adapt to any workspace. At the start of every execution, resolve the project layout:

1. Find `PROJECT_ROOT`: locate the nearest ancestor of the current workspace that contains a `*.uproject` file. If the workspace itself is the `Content/` directory, `PROJECT_ROOT` is its parent.
2. Derive key directories:

```
PROJECT_ROOT  = <directory containing *.uproject>
CONTENT_ROOT  = PROJECT_ROOT/Content
CONFIG_ROOT   = PROJECT_ROOT/Config
PLUGINS_ROOT  = PROJECT_ROOT/Plugins
```

3. If any directory does not exist, skip it during scanning and note it in the report.

## Input (Two Modes)

### Mode A -- From Migration Record

Parse the latest (or user-specified) migration record at:

```
CONTENT_ROOT/LetsGoSDK/Migration/AssetMigrationRecord/AssetMigration/migration_*.md
```

Read the `## Migration Details` table. Extract every row where `Result = OK`. Each row provides a `Source Path` and `Destination Path` pair.

**Parsing logic:**
1. Use `Glob` to find all `migration_*.md` files in the record directory
2. If multiple files exist, use the one with the latest timestamp in the filename (or ask user to pick)
3. Read the file, find the markdown table after `## Migration Details`
4. For each row, extract columns: `Source Path` (column 2) and `Destination Path` (column 3)
5. Skip rows where `Result` is not `OK`

### Mode B -- Direct List

User provides old/new path pairs. Accept formats:
- A list of `old_path -> new_path` lines
- A table with Source and Destination columns
- A single pair for quick replacement

Normalize all paths to UE internal format (`/Game/...`) using the same rules as `ue-asset-migration` Phase 1.2.

## Path Variant Generation

For each `(old_path, new_path)` pair, generate search/replace variants. The **asset name does not change**, only the directory prefix.

### Variant Table

| Variant | Search pattern | Replace pattern | Example |
|---------|---------------|-----------------|---------|
| UE path | `/Game/LetsGo/Foo/Bar` | `/Game/LetsGoSDK/Foo/Bar` | Matches inside `Redirector()`, `Blueprint'...'`, `Class'...'`, raw strings |
| Content-relative | `Content/LetsGo/Foo/Bar` | `Content/LetsGoSDK/Foo/Bar` | Matches `Content/Feature/...` -> `Content/LetsGoSDK/...` too |

For **Feature** assets where the mapping strips `Feature/<ModName>/`:
- Old: `/Game/Feature/System/Assets/Foo` -> New: `/Game/LetsGoSDK/Assets/Foo`
- UE variant: search `/Game/Feature/System/Assets/Foo`, replace `/Game/LetsGoSDK/Assets/Foo`
- Content variant: search `Content/Feature/System/Assets/Foo`, replace `Content/LetsGoSDK/Assets/Foo`

**Important:** The search is a plain substring match. All contexts (quoted strings, `TEXT()` macros, `Redirector()` wrappers, comments, INI values) are covered because the `/Game/...` portion itself is invariant across contexts.

## Scan Targets

Search the following directories (all relative to `PROJECT_ROOT`):

| Directory | File types | What to look for |
|-----------|-----------|------------------|
| `Content/LetsGo/Script/` | all text | Lua script asset references |
| `Content/Feature/` | all text | Feature mod Lua scripts |
| `Content/LetsGoSDK/Script/` | all text | SDK Lua scripts (may reference old paths) |
| `Config/` | all text | Engine/game config references |
| `Plugins/` | all text | C++ hardcoded paths |
| `ArtResourceCheck/` | all text | Python tool scripts |
| `BuildConfig/` | all text | Build/pak config CSVs |
| `Content/` (non-recursive, `*.csv` / `*.json` only) | `*.csv`, `*.json` | Top-level config files |

### CRITICAL: Grep Scanning Rules

**The workspace `.gitignore` or ripgrep ignore rules may silently exclude files** (e.g. `.lua` files, `Script/` directories). To avoid missed results:

1. **MUST set the `path` parameter to each specific subdirectory above** -- do NOT search from `PROJECT_ROOT` or `CONTENT_ROOT` in a single call
2. **Do NOT use the `glob` parameter for file type filtering** when searching code directories -- let Grep search all text files by omitting `glob` and `type`
3. **Run one Grep call per scan directory per search pattern** -- this ensures no directory is skipped by ignore rules
4. **Also search `CONTENT_ROOT/LetsGoSDK/`** -- SDK scripts may already reference old paths that need updating
5. **Exclude migration record files** from results (paths under `Migration/AssetMigrationRecord/`)

## Execution Workflow

### Step 1: Gather Replacements

Parse migration records (Mode A) or user input (Mode B) into a list of `(old_path, new_path)` pairs.

### Step 2: Generate Variants

For each pair, produce the UE path variant and the Content-relative variant as described above.

### Step 3: Scan

For each search pattern, run `Grep` per scan target directory individually. Use `output_mode: "content"` to get file paths, line numbers, and matched lines. **Set the `path` parameter to the specific subdirectory** -- never rely on workspace-root-level search.

Run scans in parallel where possible (multiple Grep calls in one message, one per directory).

Collect all hits into a unified list: `(file, line_number, matched_line, search_pattern, replace_pattern, old_path, new_path)`.

Filter out hits from migration record files (`Migration/AssetMigrationRecord/`).

### Step 4: Classify Hits

For each hit, classify as:

| Classification | Criteria | Action |
|----------------|----------|--------|
| `auto_replace` | The search string appears as a simple substring in the line; replacing it produces valid code | Automatic replacement |
| `comment_only` | The line is a comment (`--`, `//`, `#`, `;`) | Replace automatically (update comments to stay accurate) |
| `manual_review` | Hit is inside a dynamically constructed path (`string.format`, `FString::Printf`, concatenation) or the context is ambiguous | Present to user for decision |

### Step 5: Present Findings

Display a summary to the user:

```
## 扫描结果

- **命中总数**: N
- **可自动替换**: X
- **注释内**: Y
- **需人工确认**: Z

### 自动替换预览

| # | 文件 | 行号 | 替换前（摘要） | 替换后（摘要） |
|---|------|------|----------------|----------------|
| 1 | .../SceneConfigExtend.lua | 339 | ..."/Game/LetsGo/Foo"... | ..."/Game/LetsGoSDK/Foo"... |

### 需人工确认

| # | 文件 | 行号 | 内容 | 原因 |
|---|------|------|------|------|
| 1 | .../SomeFile.cpp | 42 | Printf(..."/Game/LetsGo/%s"...) | 动态路径拼接 |
```

Ask: **"请确认以上自动替换。对于需人工确认的项，回复行号也一并替换，或回复 'skip' 跳过。"**

**DO NOT proceed until user confirms.**

### Step 6: Execute Replacements

For each confirmed replacement:
1. Read the file
2. Use `StrReplace` with `old_string` = the matched line content and `new_string` = the line with the path replaced
3. If `StrReplace` fails (non-unique match), use more surrounding context to make the match unique

Process files sequentially to avoid conflicts. If a file has multiple replacements, process them all together by reading the file once and applying replacements top-to-bottom.

### Step 7: Generate Report

Write the report to:

```
CONTENT_ROOT/LetsGoSDK/Migration/AssetMigrationRecord/PathReplace/replace_YYYYMMDD_HHMMSS.md
```

Create the directory if it does not exist.

**Report template:**

```markdown
# 硬编码路径替换记录

- **日期**: YYYY-MM-DD HH:MM:SS
- **关联迁移记录**: migration_YYYYMMDD_HHMMSS.md（或"用户直接输入"）
- **处理路径对数**: N
- **命中总数**: X
- **已替换**: Y
- **跳过（需人工确认）**: Z

## 替换明细

| # | 文件 | 行号 | 原路径 | 新路径 | 分类 | 结果 |
|---|------|------|--------|--------|------|------|
| 1 | Config/DefaultEngine.ini | 18 | /Game/LetsGo/RuntimeLogicLevels/... | /Game/LetsGoSDK/RuntimeLogicLevels/... | 自动替换 | 成功 |
| 2 | Plugins/.../SomeFile.cpp | 42 | /Game/LetsGo/... | /Game/LetsGoSDK/... | 需人工确认 | 跳过 |

## 已修改文件

| # | 文件路径 | 替换次数 |
|---|----------|----------|
| 1 | Config/DefaultEngine.ini | 3 |
| 2 | Content/LetsGo/Script/.../Foo.lua | 1 |

## 汇总

- 扫描目录: Content/LetsGo/Script, Content/Feature, Content/LetsGoSDK/Script, Config, Plugins, ArtResourceCheck, BuildConfig
- 搜索路径变体: UE 内部路径 (/Game/...), Content 相对路径 (Content/...)
```

### Step 8: 通知用户

生成报告后，告知用户：
- 替换记录文件路径
- 替换数与跳过数
- 列出所有被修改的文件
- 如有需人工确认的项被跳过，提醒用户后续处理

## 异常处理

| 场景 | 处理方式 |
|------|----------|
| 未找到迁移记录 | 请用户提供 Mode B 输入或指定记录路径 |
| 迁移记录中无成功条目 | 提示用户无可替换内容 |
| Grep 未命中某路径对 | 在报告中标注"未发现硬编码引用" |
| StrReplace 失败（非唯一匹配） | 扩大上下文范围重试；仍失败则记录并跳过 |
| 扫描目录不存在 | 跳过并在报告中注明 |
| 文件只读或被锁定 | 记录错误，继续处理其余文件 |

## 注意事项

- **禁止修改 `.uasset` / `.umap` 二进制文件**，仅处理文本源文件。
- **保持文件编码不变**，不改动换行符或编码格式。
- **注释中的路径也要替换**，确保文档注释保持准确。
- 同一行出现多次的路径，使用整行 `StrReplace` 一次处理。
- INI 文件中 `+` 前缀的数组项，仅替换值部分，保留 `+Key=` 前缀。
