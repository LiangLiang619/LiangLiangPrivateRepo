---
name: ue-migration-deps-scan
description: >-
  扫描 UE 资产迁移前后的一级正向依赖和反向依赖（via UE Editor MCP AssetRegistry），
  自动识别并合并 ObjectRedirector 的反向依赖（扫新路径 refs → 发现 ObjectRedirector →
  扫重定向器 refs → 合并），生成迁移后 CSV；可选对比迁移前 CSV 生成差异报告。
  Use when the user asks 迁移前后依赖对比, 资产引用扫描, 迁移后依赖分析,
  ObjectRedirector 合并扫描, 正向反向依赖 CSV, migration deps scan.
---

# UE 资产迁移前后依赖扫描

完整流程分两大阶段：
- **阶段 A**：扫描迁移**后**路径，自动合并 ObjectRedirector 反向依赖，生成 `*_Deps_Refs.csv`
- **阶段 B**（可选）：扫描迁移**前**路径，生成 `*_PreMigration_Deps_Refs.csv`，并与阶段 A 结果对比生成 `*_Migration_Comparison.csv`

---

## 阶段 A：扫描迁移后资产

### A1 — 准备资产路径列表

从用户处获取所有迁移后资产的完整 `/Game/...` 路径，存入 `ASSET_LIST`（Python list）。

### A2 — 分批调用 MCP（每批 ≤ 50 个 action）

每个资产需 2 个 action：`get_asset_dependencies` + `get_asset_referencers`。
`batch_size = 25` 个资产 / 批（= 50 actions）。

```python
# action 格式
{"action_id": "editor.get_asset_dependencies", "params": {"asset_path": "/Game/..."}}
{"action_id": "editor.get_asset_referencers", "params": {"asset_path": "/Game/..."}}
```

调用 `ue_batch`（MCP tool），设 `continue_on_error: true`，保存所有返回的 JSON 文件路径。

### A3 — 检测 ObjectRedirector

运行 `scripts/find_redirectors.py`，从批次结果中找出所有
`asset_class == "ObjectRedirector"` 的反向依赖项，记录为 `redirector_map`（重定向器路径 → 所属资产路径），
保存中间状态 `_scan_state.json`。

```bash
python scripts/find_redirectors.py \
  --batch-files FILE1.txt FILE2.txt ... \
  --out-state _scan_state.json
```

### A4 — 扫描 ObjectRedirector 的反向依赖

对 A3 发现的所有重定向器路径，分批（≤ 50/批）调用 `get_asset_referencers`，保存结果文件。

### A5 — 合并生成最终 CSV

运行 `scripts/gen_deps_csv.py`：

```bash
python scripts/gen_deps_csv.py \
  --state _scan_state.json \
  --redirector-batches RFILE1.txt RFILE2.txt \
  --asset-order assets.txt \
  --out output_Deps_Refs.csv
```

**合并规则**：
- `merged_refs` = 直接 refs（去除 ObjectRedirector 条目）∪ 各 ObjectRedirector 的 refs
- 按 `package_name` 去重，同名保留先出现的

**CSV 列**：`资产名 | 资产路径 | 一级正向依赖数量 | 一级正向依赖资产列表 | 一级反向依赖数量 | 一级反向依赖资产列表`

---

## 阶段 B：扫描迁移前资产（可选）

### B1 — 准备迁移前路径映射

从用户处获取迁移后资产名 → 迁移前路径的映射（无记录填 `None`）。

### B2 — 分批扫描迁移前路径

与 A2 相同，对迁移前路径分批调用 `get_asset_dependencies` + `get_asset_referencers`（≤ 50/批）。

### B3 — 生成迁移前 CSV

```bash
python scripts/gen_deps_csv.py \
  --state _prescan_state.json \
  --asset-order assets_pre.txt \
  --out output_PreMigration_Deps_Refs.csv \
  --name-col "资产名（迁移后）" \
  --path-col "迁移前资产路径"
```

### B4 — 对比生成差异 CSV

```bash
python scripts/compare_deps.py \
  --pre output_PreMigration_Deps_Refs.csv \
  --post output_Deps_Refs.csv \
  --out output_Migration_Comparison.csv
```

对比规则（见 [scripts/compare_deps.py](scripts/compare_deps.py)）：
- 按资产名（路径末段）归一化匹配，避免同资产前后路径不同被误判为丢失
- `lost` = 在迁移前但名称不在迁移后
- `gained` = 在迁移后但名称不在迁移前

**输出 CSV 关键列**：`正向依赖丢失列表 | 反向依赖丢失列表 | 正向依赖新增列表 | 反向依赖新增列表 | 综合评估`

---

## 注意事项

- MCP 每批最多 50 个 action，超出必须拆分
- 如输出文件被 Excel 占用写入失败，先写到 `_new.csv`，再由用户手动替换
- ObjectRedirector 只在**反向依赖**（referencers）中合并；**正向依赖**不需处理（重定向器的 deps 仅指向新路径，无需合并）
- 资产被改名迁移时（如 `BP_MoePropConfig` → `BP_MoePropConfigBase`），`asset_class == "ObjectRedirector"` 比同名匹配更可靠

---

## 可复用脚本

详见以下脚本文件（可直接复制到工作目录使用）：

- [scripts/find_redirectors.py](scripts/find_redirectors.py) — 解析批次结果，检测 ObjectRedirector
- [scripts/gen_deps_csv.py](scripts/gen_deps_csv.py) — 合并 refs 并输出 CSV
- [scripts/compare_deps.py](scripts/compare_deps.py) — 对比迁移前后 CSV，输出差异报告
