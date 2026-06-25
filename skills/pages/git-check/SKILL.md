---
name: git-check
description: >-
  Check whether a list of migration source-file paths has any non-whitelist
  modifications in the current branch since a given date. Use when the user
  wants to audit migrated lua file paths for the LetsGo3C repository, asks
  "搬迁前的文件有没有非白名单的修改", "检查搬迁文件修改", needs to check git
  history of migration source files, or provides a file list (txt/csv) and a
  start date for migration audit.
disable-model-invocation: true
---

# git-check

检查一组「搬迁前文件路径」自指定日期起在当前分支是否有非白名单人员的修改记录。

> 本 skill 为 LetsGo3C 仓库适配版本。实际脚本和配置位于 `Content/LetsGo3C/AITools/skills/git-check/`。

## 何时使用

- 用户提供一份文件列表（txt / csv / 直接全量扫描 `MigratedFiles.lua`）
- 想知道这些文件从某个日期开始到现在，是否有白名单之外的人改过

## 必备前置信息

调用脚本前必须先获得：

1. **输入模式 + 输入源**
   - `txt`：纯文本文件，一行一个搬迁前路径
   - `csv`：CSV 文件（带表头），需指定路径所在列名或列号
   - `migrated`：不需要输入文件，直接扫描项目内 `MigratedFiles.lua` 的所有 key
2. **起始日期**（`--since`），格式 `YYYY-MM-DD`
   - 如果用户没明确提供日期，**必须先向用户询问**起始日期，不要擅自假设

白名单作者维护在 `Content/LetsGo3C/AITools/skills/git-check/config.json` 的 `whitelist_authors` 字段。

## 使用步骤

1. 确认用户给的输入模式（txt / csv / migrated）和起始日期
2. 用 Shell 执行对应命令（见下方），工作目录为项目根 `LetsGo/`
3. 把结果 CSV 的路径返回给用户

### txt 模式

```bash
python Content/LetsGo3C/AITools/skills/git-check/scripts/check_modifications.py \
  --mode txt \
  --input <path/to/files.txt> \
  --since <YYYY-MM-DD> \
  --output <path/to/result.csv>
```

### csv 模式

```bash
python Content/LetsGo3C/AITools/skills/git-check/scripts/check_modifications.py \
  --mode csv \
  --input <path/to/list.csv> \
  --path-column <列名 或 1-based 列号> \
  --since <YYYY-MM-DD> \
  --output <path/to/result.csv>
```

### migrated 模式（全量扫描 MigratedFiles.lua）

```bash
python Content/LetsGo3C/AITools/skills/git-check/scripts/check_modifications.py \
  --mode migrated \
  --since <YYYY-MM-DD> \
  --output <path/to/result.csv>
```

## 输出格式

默认输出三列 CSV（UTF-8 BOM）：

| 原文件路径 | `<since>`至今是否有非白名单人员修改记录 | 非白名单修改人(多个用;分隔) |
|---|---|---|

加 `--detailed` 输出六列，额外多出：推断搬迁前路径、仓库、仓库内路径。

## 配置 / 自定义

- 配置文件：`Content/LetsGo3C/AITools/skills/git-check/config.json`
- 白名单：`whitelist_authors` 字段
- MigratedFiles.lua 路径：`migrated_files_lua` 字段
- 项目根：`project_root` 字段

## 详细说明

- [USAGE.md](../../LetsGo3C/AITools/skills/git-check/USAGE.md)：面向最终用户的使用指南
- [reference.md](../../LetsGo3C/AITools/skills/git-check/reference.md)：实现细节
