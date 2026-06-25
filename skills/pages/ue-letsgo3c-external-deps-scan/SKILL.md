---
name: ue-letsgo3c-external-deps-scan
description: >-
  扫描 LetsGo3C（或任意 UE 仓库子目录）下所有资产的一级正向依赖，过滤出
  非 /Game/<repo>/ 的外部依赖，输出"明细 CSV（每行=本仓资产+其外部依赖）"
  和"聚合 CSV（每行=外部资产+反向被哪些本仓资产引用）"。Use when the user
  asks 扫描 LetsGo3C 外部依赖, letsgo3c 高内聚检查, 仓库外部依赖扫描,
  scan external deps, 列出外部资产依赖, 3C外部依赖, 仓库高内聚检查.
---

# UE 仓库外部依赖扫描

扫描指定 UE Content 子目录下所有资产的一级正向依赖，筛选出依赖了本仓之外
`/Game/` 路径的"外部依赖"，帮助评估仓库高内聚程度并提供修复清单。

---

## Step 1 — 与用户确认参数

必须向用户确认以下参数（括号内为默认值）：

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--repo-root` | 仓库根目录绝对路径 | `E:\Dev2\LetsGoDevelop\LetsGo\Content\LetsGo3C\` |
| `--content-root` | UE 项目 Content 目录 | 从 `repo-root` 向上查找含 `\Content\` 的路径段自动推导 |
| `--game-prefix` | 本仓在 /Game 下的前缀 | 从 `repo-root` 相对 `content-root` 自动推导，如 `/Game/LetsGo3C/` |
| `--output-dir` | CSV 输出目录 | `<repo-root>\Migration\ExternalDepsScan\<yyyyMMdd-HHmm>\` |

若用户已在请求中给出了 repo-root，直接确认推导结果即可，无需逐个追问。

---

## Step 2 — 资产发现

运行 `discover_assets.py` 扫描本地文件系统，列出仓库下所有资产的 `/Game/` 路径：

```bash
python scripts/discover_assets.py \
  --repo-root "E:\Dev2\LetsGoDevelop\LetsGo\Content\LetsGo3C" \
  --content-root "E:\Dev2\LetsGoDevelop\LetsGo\Content" \
  --out assets.txt
```

输出 `assets.txt`，每行一个 `/Game/...` 路径。脚本会：
- 递归扫描 `.uasset` 和 `.umap` 文件
- 自动跳过 `_BuiltData.uasset`、`.umap_BuildData` 等构建产物
- 将文件系统路径转换为 `/Game/` 前缀的 UE 路径

---

## Step 3 — 批量扫描一级正向依赖（MCP）

读取 `assets.txt`，分批通过 `ue_batch` 调用 `editor.get_asset_dependencies`。

- 每批 **50 个 action**（`ue_batch` 上限 50），`continue_on_error: true`
- 每批返回结果保存为 JSON 文件，路径记录到 `batch_files.txt`

单个 action 格式：

```json
{"action_id": "editor.get_asset_dependencies", "params": {"asset_path": "/Game/LetsGo3C/..."}}
```

MCP 调用示例（每批 50 个资产）：

```python
actions = []
for asset_path in batch:
    actions.append({
        "action_id": "editor.get_asset_dependencies",
        "params": {"asset_path": asset_path}
    })

result = ue_batch(actions=actions, continue_on_error=True)
```

**进度估算**：
- 1000 资产 ≈ 20 批 ≈ 20–60 秒
- 5000 资产 ≈ 100 批 ≈ 2–5 分钟

每批返回的 JSON 需要保存到临时文件（如 `batch_001.json`），并将文件路径追加到
`batch_files.txt` 中，供 Step 4 使用。

**注意**：如果 MCP 返回的结果在 `content` 字段中（而非结构化 JSON），
需要解析 `content[0].text` 获取实际 JSON 数据。每批结果应保存为一个 JSON 文件，
格式为 `{"results": [...]}` 数组。

---

## Step 4 — 解析 + 过滤 + 输出双 CSV

运行 `gen_external_deps_csv.py` 解析所有批次结果，过滤外部依赖，输出两份 CSV：

```bash
python scripts/gen_external_deps_csv.py \
  --batch-files batch_001.json batch_002.json ... \
  --game-prefix "/Game/LetsGo3C/" \
  --out-dir "E:\Dev2\LetsGoDevelop\LetsGo\Content\LetsGo3C\Migration\ExternalDepsScan\20260622-1700"
```

也可以用 `batch_files.txt` 代替逐个指定：

```bash
python scripts/gen_external_deps_csv.py \
  --batch-list batch_files.txt \
  --game-prefix "/Game/LetsGo3C/" \
  --out-dir "<output-dir>"
```

### 外部依赖判定规则

仅保留满足以下条件的依赖：
- `package_name` 以 `/Game/` 开头
- 且 **不以** `--game-prefix`（如 `/Game/LetsGo3C/`）开头

自动忽略（非 `/Game/` 前缀的路径不算外部依赖）：
- `/Script/...`、`/Engine/...`、`/Memory/...`、`/Paper2D/...` 等引擎/原生路径

### 输出文件

**1. Detail CSV**（`External_Deps_Detail.csv`）

每行 = 一个本仓资产 + 它的外部依赖列表。

| 列名 | 说明 |
|------|------|
| 本仓资产名 | 资产路径末段 |
| 本仓资产路径 | 完整 `/Game/` 路径 |
| 外部依赖数量 | 该资产引用的外部资产去重数 |
| 外部依赖资产列表 | `\|` 分隔的外部资产路径 |
| 外部依赖根目录分布 | 按 `/Game/` 下第一段分组统计，如 `LetsGo:5;Feature:2` |

仅输出有外部依赖的资产（外部依赖数量 > 0）。

**2. Aggregate CSV**（`External_Deps_Aggregate.csv`）

每行 = 一个外部资产 + 被哪些本仓资产引用，按被引次数降序排列。

| 列名 | 说明 |
|------|------|
| 外部资产名 | 资产路径末段 |
| 外部资产路径 | 完整 `/Game/` 路径 |
| 外部资产根目录 | `/Game/` 下第一段（如 `LetsGo`、`Feature`） |
| 被本仓资产引用次数 | 被多少个本仓资产依赖 |
| 被引用的本仓资产列表 | `\|` 分隔的本仓资产路径 |

### 简报输出

脚本执行完毕后在控制台打印简报：

```
========== 外部依赖扫描简报 ==========
本仓资产总数:           1234
含外部依赖的资产数:      567
外部依赖资产 (unique):   890

Top 5 外部根目录:
  LetsGo:    450
  Feature:   230
  ...

Top 5 被引最多的外部资产:
  /Game/LetsGo/Foo/Bar:  23 次
  ...
======================================
```

---

## 注意事项

- MCP 每批最多 50 个 action，超出必须拆分
- 如果输出文件被 Excel 占用导致写入失败，先写到 `_new.csv`，再由用户手动替换
- 本 skill 只扫正向依赖（dependencies），不扫反向依赖（referencers）
- 不需要 ObjectRedirector 合并处理（只看正向依赖，本仓资产即为最新位置）
- 所有参数走命令行 argparse，脚本中不硬编码任何仓库名称

---

## 故障排查

| 现象 | 处理 |
|------|------|
| `ue_batch` 返回 error | 检查 UE Editor 是否已启动并加载了项目 |
| 大量资产返回空依赖 | 可能是路径格式不对（需要 `/Game/` 前缀而非文件系统路径）|
| 输出 CSV 中文乱码 | 确认用 Excel 打开（编码为 `utf-8-sig`），或用 VS Code |
| 资产数量为 0 | 检查 `--repo-root` 和 `--content-root` 是否正确 |
| MCP 调用超时 | 减小每批资产数（改为 25/批），增大超时时间 |
| 某些依赖显示为 `/Game/LetsGo3C/...` | 这是本仓内部依赖，不属于外部依赖，已自动过滤 |
