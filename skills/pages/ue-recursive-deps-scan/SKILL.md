---
name: ue-recursive-deps-scan
description: >-
  Recursively scan all-level indirect dependencies of UE assets from a user-supplied
  CSV of root assets, by directly parsing .uasset files (imports table + FName
  table, covering hard refs and soft/class refs), following ObjectRedirector
  through the LetsGo3C migration map, then emitting an 18-column CSV with full
  multi-hop reference chains ("Root -> A -> B -> Parent"). Use when the user
  asks 扫描递归依赖, 扫描间接依赖, 扫描资产依赖链, generate indirect deps csv,
  recursive UE asset dep scan, or provides a CSV of root assets to expand.
---

# UE Recursive Asset Dependency Scanner

把任意「根资产」CSV 扩展为「全量递归间接依赖」CSV。基于 `uasset_mcp.UAssetParser`
直接解析 `.uasset` 二进制，**同时**从 imports 表抓硬引用、从 FName 表抓
软引用 / SoftObjectPath / 类引用；跟随 ObjectRedirector 到迁移后的真实位置；
输出与项目历史 CSV 同结构的 18 列结果，链路字段为 BFS 完整多跳。

## 何时使用

用户出现以下意图时触发：

- 「递归扫描 / 间接依赖 / 依赖链」+ 提供了一份 CSV
- 「重新扫描一遍所有间接依赖」
- 「把这份直接依赖 CSV 扩展成间接依赖」
- 资产搬迁前评估外部依赖体量

## 前置条件

1. `uasset_mcp` 已安装（脚本会按以下顺序自动定位）：
   - `F:\F4\LetsGoEditor\Editor\LetsGo\Tools\Python311\Lib\site-packages`
   - 当前 Python 解释器自带
   - 环境变量 `UASSET_MCP_SITE_PACKAGES` 指定的目录
   若都没找到，请先：
   ```bash
   pip install --index-url https://mirrors.tencent.com/pypi/simple/ uasset_mcp
   ```
2. 输入 CSV 至少包含两列：`外部资产名`、`外部资产完整路径`
3. （可选）`Content/LetsGo3C/Migration/AssetsMigration/3CAssetsMigrationRecords.md`
   存在 — 用于把 `/Game/LetsGo3C/...` 回写为 `/Game/LetsGo/...` 显示路径

## 工作流

### Step 1 — 与用户确认参数

- **根 CSV 路径**：用户给的输入 CSV
- **输出 CSV 路径**：默认与输入同目录，文件名 `新【间接依赖】<同名>.csv`
- **排除根资产**（可选）：英文逗号分隔的资产名，BFS 不从它们出发也不展开
- **是否保留 ProjectT**（极少需要）：默认排除 `/Game/Feature/ProjectT/` 子树

若用户已经在请求里给出排除资产名（例如「排除 BP_BillboardComponent 和
BP_CharExclusiveVehicleComponent」），直接采用、不必再问。

### Step 2 — 运行扫描

```bash
python scripts/scan_recursive_deps.py \
  --root-csv "<根 CSV 绝对路径>" \
  --output-csv "<输出 CSV 绝对路径>" \
  --exclude "<可选：用逗号分隔的资产名>"
```

常用可选参数：
- `--content-root`：UE 项目 Content 目录，默认 `F:\F3\LetsGoDevelop\LetsGo\Content`
- `--migration-record`：迁移记录 md，默认 `Content/LetsGo3C/Migration/AssetsMigration/3CAssetsMigrationRecords.md`
- `--cache-file`：BFS 节点解析缓存（首次 ~10s，二次秒级）。默认放在
  `Content/.cursor/skills/ue-recursive-deps-scan/dep_cache.json`
- `--keep-projectt`：保留 ProjectT 子树（默认排除）

**首次运行**或**资产被改动后重新扫描**：删除 `dep_cache.json` 再跑一次即可。

### Step 3 — 校验输出

读取输出 CSV 头一行核对 18 列名称和顺序：

```
外部资产名,外部资产完整路径,引用层级,引用链路（被谁依赖了）,当前进度,
搬迁方式,负责人,ProjectT资产路径（被该资产依赖）,直接依赖外部资产数,
直接依赖外部资产列表,递归依赖外部资产总数,递归依赖外部资产列表,
玩法依赖数量,全部引用玩法列表,资产父目录,资产子目录,引用类型,是否需要
```

简报应包含：行数、深度分布、链路质量（完整多跳 vs 单跳）、排除资产泄漏检查。

## 输出格式

每行一个间接依赖资产，关键字段含义：

| 列 | 来源 |
|----|------|
| 外部资产名 | path 末段 |
| 外部资产完整路径 | LetsGo3C → LetsGo 回写后的显示路径 |
| 引用层级 | `间接引用(深度N)` ，N 为 BFS 深度（根=0、第一层=1 …） |
| 引用链路（被谁依赖了） | 完整多跳：`Root -> A -> B -> Parent`（不含自身） |
| 直接依赖外部资产数/列表 | 该资产自身的下一层「外部」依赖 |
| 递归依赖外部资产总数/列表 | 该资产可达闭包内的外部依赖 |
| 资产父目录/子目录 | path 第 4、5 段 |
| 引用类型 | 固定 `serialized` |
| 是否需要 | 固定 `□` |

未由扫描产出的字段（当前进度、搬迁方式、负责人、ProjectT资产路径、玩法依赖数量/列表）
**留空**，由后续人工填写。

## 数据来源说明

扫描时对每个节点合并以下两类引用作为「直接依赖」：

1. **硬引用**：`.uasset` 文件 imports 表中 `class_name=Package` 的条目
2. **软引用 / 类引用**：FName 表中以 `/Game/` 开头的字符串（含
   `SoftObjectPath`、`SoftClassPath`、序列化在 property 数据里的资产 path）。
   仅取 `.` 之前的 package 段。

这两类合并后是 UE AssetRegistry `GetDependencies(packages)` 等价范围。

过滤规则：
- 仅保留 `/Game/` 开头
- 默认排除 `/Game/Feature/ProjectT/` 子树
- `/Script/`、`/Engine/`、`/Memory/` 等忽略
- 自己不算自己的依赖

## 排除资产语义

`--exclude A,B`：
- BFS 不从 A、B 这些资产出发
- BFS 过程中若任何节点的依赖列表里出现 A 或 B（按资产名匹配），也跳过、不继续展开
- 这样保证输出 CSV 中**没有任何**链路头部为 A/B，且不会含 A/B 的下游子树（除非经其他根可达）

## 典型示例

输入：`D:\backups\xxx\新【直接依赖】XX.csv`，要求排除 BP_Foo / BP_Bar。

```bash
python scripts/scan_recursive_deps.py \
  --root-csv "D:\backups\xxx\新【直接依赖】XX.csv" \
  --output-csv "D:\backups\xxx\新【间接依赖】XX.csv" \
  --exclude "BP_Foo,BP_Bar"
```

输出抽样链路（与项目历史 CSV 风格一致）：

```
AS_CH_Glider_Prop_Loop_001 → 引用层级=间接引用(深度3)
  引用链路：BP_MainCharPropComponent -> BP_MoePropConfig -> BP_SpawnedHangGlide
```

## 故障排查

| 现象 | 处理 |
|------|------|
| `[fatal] 未找到 uasset_mcp` | 按「前置条件 1」安装；或设置 `UASSET_MCP_SITE_PACKAGES` |
| 大量「未找到 .uasset」警告 | 检查 `--content-root` 是否指对项目；若资产已删除可忽略 |
| 深度只到 1-2 层 | 缓存命中了旧结果——删除 `dep_cache.json` 再跑 |
| 输出列名缺「外部」二字 | 这是新约定，列名 `直接依赖外部资产数/列表` 等；与旧版【全量间接依赖】CSV 的 `直接依赖LetsGo资产数/列表` 等价 |
