---
name: ue-asset-git-history
description: >-
  Scan git commit history (including merges) for UE asset files and output an
  incrementally-maintained CSV with committer info. Use when the user asks
  扫描资产提交记录, 资产git历史, 谁提交了这些资产, asset git history,
  资产提交人, 查询资产最近提交, or provides asset paths to look up commit authors.
---

# UE Asset Git History Scanner

根据用户提供的资产路径列表和分支名，扫描每个资产最近 N 次提交记录（含合并），
整理到可增量维护的 CSV 文件中。

## 何时使用

- 用户给出一批资产路径，想知道每个资产最近是谁提交的
- 用户说「扫描资产提交记录」「资产提交人」「asset git history」等
- 用户提供 CSV 资产清单，需要批量查询提交历史

## 输入

| 参数 | 说明 | 默认值 |
|------|------|--------|
| 资产路径 | 绝对路径列表（对话粘贴或 CSV 文件） | 必填 |
| 分支名 | git 远程分支 | `origin/develop` |
| 提交次数 | 每个资产扫描最近几次提交 | 2 |

资产路径支持两种输入方式：
1. **对话粘贴** — 用户直接贴出路径，用逗号或换行分隔
2. **CSV 文件** — 用户提供 CSV 文件路径及包含资产路径的列名

## 工作流

### Step 1 — 确认参数

向用户确认：
- 资产路径列表（或 CSV 文件路径 + 列名）
- 分支名（默认 `origin/develop`）
- 提交次数（默认 2）

### Step 2 — 运行扫描脚本

脚本位置：`scripts/scan_asset_git_history.py`（相对于本 SKILL.md）

**方式 A：直接传入资产路径**

```bash
python scripts/scan_asset_git_history.py \
  --assets "E:\path\to\BP_A.uasset,E:\path\to\BP_B.uasset" \
  --branch "origin/develop" \
  --count 2
```

**方式 B：从 CSV 文件读取**

```bash
python scripts/scan_asset_git_history.py \
  --input-csv "D:\assets_list.csv" \
  --path-column "资产路径" \
  --branch "origin/develop" \
  --count 2
```

可选 `--output` 指定输出 CSV 路径，默认为 `output/asset_git_history.csv`。

脚本会自动根据资产绝对路径向上查找 `.git` 目录定位仓库，无需手动指定。

### Step 3 — 查看结果

读取输出 CSV，向用户汇报：
- 扫描了多少资产
- 新增了多少条记录
- 按资产分组展示提交人和提交说明摘要

## CSV 列定义

| 列名 | 说明 |
|------|------|
| 资产名称 | 文件名（不含扩展名） |
| 资产完整路径 | 资产绝对路径 |
| 分支 | 扫描时使用的分支名 |
| Commit Hash | 完整 SHA |
| 提交人 | git 作者名 |
| 提交人邮箱 | git 作者邮箱 |
| 提交时间 | YYYY-MM-DD HH:MM:SS |
| 提交说明 | commit message 首行 |
| 扫描时间 | 本次扫描执行时间 |

## 增量维护策略

- CSV 以 `(资产完整路径, Commit Hash)` 为去重键
- 已存在的 CSV 会被读入，新数据追加后去重、排序再写回
- 后续扫描不会覆盖旧数据，只会补充新记录
- CSV 编码为 UTF-8 BOM，兼容 Excel 直接打开

## 示例

用户给出 3 个资产路径，扫描 develop 分支最近 2 次提交：

```bash
python scripts/scan_asset_git_history.py \
  --assets "E:\Dev2\LetsGoDevelop\LetsGo\Content\LetsGo3C\Assets\Base\Character\Components\BP_SurroundingsComponent.uasset,E:\Dev2\LetsGoDevelop\LetsGo\Content\LetsGo3C\Assets\Base\Character\BP_MainCharBase.uasset" \
  --branch "origin/develop" \
  --count 2
```

输出 CSV 示例行：

```
资产名称,资产完整路径,分支,Commit Hash,提交人,提交人邮箱,提交时间,提交说明,扫描时间
BP_SurroundingsComponent,E:\...\BP_SurroundingsComponent.uasset,origin/develop,77f58f09...,yuliangjing,yuliangjing@tencent.com,2026-05-22 23:02:43,--story=134240655 ...,2026-06-12 20:00:00
```
