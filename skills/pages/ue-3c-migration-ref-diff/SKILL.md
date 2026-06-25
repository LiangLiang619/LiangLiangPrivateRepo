---
name: ue-3c-migration-ref-diff
description: >-
  Compare "referenced-by-others" counts for LetsGo3C-migrated assets before vs
  after migration using two xlsx snapshots (RefByOthersAssetTable). Reads the
  authoritative old→new path mapping from 3CAssetsMigrationRecords.md, scans
  on-disk assets for rename fallback, then outputs an xlsx report flagging any
  lost references. Use when the user asks 3C引用对比, 迁移前后引用数量,
  引用是否丢失, 3C ref count diff, 引用丢失检查, 迁移引用校验, or provides
  before/after RefByOthersAssetTable xlsx files for comparison.
---

# 3C 迁移资产引用数量对比

对比 LetsGo3C 仓库中迁移资产在**迁移前后被其他资产引用的数量**是否减少或丢失
（可能由重定向器修复或其他原因导致），输出一张带状态判定的 xlsx 对比结果表。

## 何时使用

用户出现以下意图时触发：

- 「3C 引用对比」「迁移前后引用数量」「引用是否丢失」
- 「3C ref count diff」「迁移引用校验」
- 提供了两份 `RefByOthersAssetTable` xlsx 要求对比

## 前置条件

1. Python 3.8+ 且 `openpyxl` 已安装（`pip install openpyxl`）
2. 两份 `RefByOthersAssetTable_*.xlsx`，列结构：
   `资产名称 | 资产路径 | 引用数量 | 引用资产`（引用资产为逗号拼接的引用方路径）
3. 迁移记录 `3CAssetsMigrationRecords.md` 存在（默认位于
   `Content/LetsGo3C/Migration/AssetsMigration/3CAssetsMigrationRecords.md`）
4. `Content/LetsGo3C/Assets/` 目录包含已迁移的 `.uasset/.umap` 文件

## 工作流

### Step 1 — 与用户确认参数

- **迁移前 xlsx 路径**（`--before`）
- **迁移后 xlsx 路径**（`--after`）
- **迁移记录 md 路径**（`--migration-record`，默认自动定位）
- **LetsGo3C 磁盘根目录**（`--letsgo3c-root`，默认
  `E:/Dev2/LetsGoDevelop/LetsGo/Content/LetsGo3C`）
- **输出 xlsx 路径**（`--out`，默认与 `--after` 同目录
  `3C迁移引用对比_<时间戳>.xlsx`）

若用户已经在请求里给出路径，直接采用、不必再问。

### Step 2 — 运行对比脚本

```bash
python scripts/compare_ref_counts.py \
  --before "<迁移前 xlsx>" \
  --after "<迁移后 xlsx>" \
  --migration-record "<md 路径>" \
  --letsgo3c-root "<LetsGo3C 磁盘根>" \
  --out "<输出 xlsx>"
```

脚本执行步骤：

1. 解析迁移记录 md，提取 `资产名 / 源路径 / 目标路径 / 搬迁方式 / 负责人`
2. 扫描 `LetsGo3C/Assets/` 磁盘目录获取真实 `.uasset` 路径，
   用于校正记录中已二次改名的资产（记录目标 → 磁盘名兜底）
3. 流式读取两份 xlsx（`read_only` 模式），仅捕获命中路径的行
4. 计算每个迁移资产的引用数量变化与引用方差集
5. 输出 xlsx 结果 + 终端简报

### Step 3 — 检查输出

确认输出 xlsx 包含全部迁移资产；重点检查：

- `状态` 列为 `疑似丢失` 的资产 — 需要人工排查原因
- `源路径未匹配(人工确认)` / `新路径未匹配(人工确认)` 的资产 — 迁移记录与 xlsx
  不一致，需核对

## 输出表列

| 列名 | 含义 |
|------|------|
| 资产名 | 迁移记录中的外部资产名 |
| 旧路径(源) | 迁移前路径 |
| 新路径(当前) | 迁移后路径（优先磁盘真实路径） |
| 搬迁方式 | 迁移记录中的搬迁方式 |
| 负责人 | 迁移记录中的负责人 |
| 迁移前引用数 | before xlsx 中旧路径的引用数量 |
| 迁移后引用数(新路径) | after xlsx 中新路径的引用数量 |
| 旧路径重定向器残留 | after xlsx 中旧路径仍存在的引用数量（重定向器未清理） |
| 迁移后合计(新+重定向) | 新路径 + 重定向器残留 |
| 严格差值 | 迁移后新路径 − 迁移前 |
| 合计差值 | 迁移后合计 − 迁移前 |
| 丢失引用方数 | before 有但 after 没有的引用方个数 |
| 丢失引用方列表 | 逗号分隔的丢失引用方路径 |
| 新增引用方数 | after 有但 before 没有的引用方个数 |
| 状态 | 判定结果（见下方说明） |
| 备注 | 迁移记录中的备注 |

### 状态判定规则

| 状态 | 条件 |
|------|------|
| 正常(无减少) | 迁移后合计 >= 迁移前，且丢失引用方数 == 0 |
| 正常(有新增) | 迁移后合计 > 迁移前 |
| 减少(走重定向器兜底) | 迁移后新路径 < 迁移前，但合计 >= 迁移前 |
| 疑似丢失 | 迁移后合计 < 迁移前，或丢失引用方数 > 0 |
| 源路径未匹配(人工确认) | before xlsx 中找不到旧路径 |
| 新路径未匹配(人工确认) | after xlsx 中找不到新路径 |

## 故障排查

| 现象 | 处理 |
|------|------|
| `ModuleNotFoundError: openpyxl` | `pip install openpyxl` |
| 解析迁移记录失败 | 检查 md 文件格式是否被手动修改过 |
| 大量"源路径未匹配" | 检查 before xlsx 是否为迁移前导出的快照 |
| 大量"新路径未匹配" | 检查 LetsGo3C 磁盘目录是否正确 |
| 运行时间过长 | xlsx 约 90 万行，预计 60-90s 完成两次扫描 |
