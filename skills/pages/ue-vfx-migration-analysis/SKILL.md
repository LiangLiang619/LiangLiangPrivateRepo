---
name: ue-vfx-migration-analysis
description: >-
  Analyze UE asset directory migration cost and impact by scanning AssetRegistry
  references. Produces a migration report (Markdown) and two CSV files (detail +
  summary). Use when the user asks to analyze asset migration feasibility, scan
  asset references for a directory, or evaluate moving UE assets to a new location.
---

# UE 资产目录迁移分析

对 UE 项目中指定资产目录做**迁移可行性与成本分析**：扫描 AssetRegistry 的双向引用关系，输出 Markdown 报告 + 两份 CSV（引用明细 / 引用汇总）。

## 输入

用户提供：

1. **待分析目录的 UE 路径**（如 `/Game/LetsGo/Assets/Effect/VFX_Community`）
2. **Effect 根目录路径**（如 `/Game/LetsGo/Assets/Effect`）
3. **需保留的通用子目录名**（如 `VFX_Material`, `VFX_Mesh`, `VFX_Texture`）
4. **`ChunkConfig.csv` 路径**（用于分包归属分析；可选）
5. **背景与目标文本**（写入报告 §1；可选，用户不提供则由 agent 草拟）

## 产出

在待分析目录的同级或 `ArtResourceCheck/` 目录下生成：

| 文件 | 说明 |
|------|------|
| `<目录名>_引用明细.csv` | 逐条引用/被引用记录，含分组列 |
| `<目录名>_引用汇总.csv` | 每个资产一行，含风险等级 |
| `<目录名>_Migration_Report.md` | 完整分析报告 |

## 执行流程

### Step 1：生成 UE Python 扫描脚本

基于 [scripts/reference_scan_template.py](scripts/reference_scan_template.py) 模板，替换以下变量生成目标脚本：

- `TARGET_ROOT`：待分析目录路径
- `EFFECT_ROOT`：Effect 根目录路径
- `KEEP_DIRS`：保留的通用子目录列表
- 输出 CSV 文件名前缀

脚本逻辑：
1. 枚举 `TARGET_ROOT` 下全部资产
2. 对每个资产调用 `get_dependencies` + `get_referencers`
3. 按目标路径归类：`keep_dir_X` / `target_internal` / `effect_other` / `letsgo_non_effect` / `feature_content` / `engine` / `other`
4. 输出英文 detail CSV + summary CSV

### Step 2：在 UE 编辑器中执行扫描

告知用户在 UE 编辑器 Output Log（Python 模式）中执行：

```
exec(open(r"<脚本绝对路径>").read())
```

轮询等待 CSV 生成（检测文件出现且大小稳定）。

### Step 3：生成中文 CSV（带分组列）

基于 [scripts/csv_localize_template.py](scripts/csv_localize_template.py) 模板，生成本地化脚本并运行（系统 Python，无需 UE）。

**引用明细表列结构**（9 列）：

| 列 | 来源 |
|----|------|
| 源资产路径 | 原始数据 |
| 源资产类型 | 原始数据 |
| 源资产所属子目录 | 从路径提取第一级子目录 |
| 源资产所属分包 | 比对 ChunkConfig.csv |
| 关系方向 | `目标 → 外部（对外依赖）` / `外部 → 目标（被引用）` |
| 目标资产 | 原始数据 |
| 目标分类 | 中文化的分类 |
| 目标所属顶层模块 | 从路径提取 3~4 层 |
| 目标所属细分目录 | 从路径提取 4~5 层 |

**引用汇总表列结构**（8 列）：

| 列 | 来源 |
|----|------|
| 源资产路径 | 原始数据 |
| 源资产类型 | 原始数据 |
| 源资产所属子目录 | 同上 |
| 源资产所属分包 | 同上 |
| 对外依赖总次数 | 原 N 列求和 |
| 被外部引用次数 | 原始数据 |
| 被内部引用次数 | 原始数据 |
| 迁移风险等级 | `零引用（零风险）` / `低（1~3次）` / `中（4~10次）` / `高（>10次）` |

### Step 4：深度切片分析

用系统 Python 对明细 CSV 做以下切片（参考 [scripts/deep_analysis_template.py](scripts/deep_analysis_template.py)）：

1. 对外依赖按目标分类统计
2. 被引用按外部来源顶层模块统计
3. **Effect 树内反向引用**按子目录拆解（区分通用库 vs 其他副玩法目录）
4. 内部子目录按零引用比例排名
5. 分包归属统计（显式 vs 默认规则）
6. 高影响资产 TOP 30

### Step 5：生成 Markdown 报告

报告结构（**必须遵循**）：

```markdown
# <目录名> 迁出可行性与成本分析报告

## 术语速览
（引用次数定义）

## 1. 背景与目标
### 1.1 背景
### 1.2 目标

## 2. 结论概要
### 2.1 总体规模（表格）
### 2.2 对外依赖分布（表格 + 结论）
### 2.3 被外部引用分布（表格 + 结论，Effect 树内按通用库 vs 副玩法拆分）
### 2.4 资产所属分包（表格：显式分包 + 默认规则）
### 2.5 硬编码路径的配置文件（表格）
### 2.6 关键风险点（表格：等级 + 量级）

## 3. 数据概览
### 3.1 资产数量分布（按子目录）
### 3.2 引用次数总量（按类别）
### 3.3 依赖走向全景（mermaid 流程图）

## 4. <目录名> 对外依赖
### 4.1 ~ 4.N 按目标类别分节

## 5. <目录名> 的被引用分布
### 5.1 外部引用者全景
### 5.2 Effect 树内反向依赖（按通用库/副玩法逐项拆解）
### 5.3 ~ 5.N 按来源模块分节

## 6. 内部子目录结构与分层可拆分性
### 6.1 零引用比例排名
### 6.2 子目录对外依赖密度

## 7. 配置文件与构建链路影响清单
### 7.1 直接含有目标路径的文本文件
### 7.2 分包 chunk 业务语义（如有 ChunkConfig）
### 7.3 间接受影响的打包配置
### 7.4 Redirector / 兼容机制现状

## 8. 关键风险点（表格）

## 9. 附录
```

**报告编写原则**：

- §2 全部用**数据表格**呈现结论，不写长段文字
- 被引用表中 `/Effect/` 必须按**通用库 vs 其他副玩法**逐行拆分
- `.uasset` 内的二进制引用标注"Redirector 自动兜底"
- 配置文件才是真正的手工成本，标注"脚本批量替换"
- 风险表只列真正需要人工介入的项（二进制引用不算风险）

### Step 6：仓库文本扫描（补充配置影响面）

用 `Grep` 在整个仓库中搜索目标目录名（`*.ini,*.json,*.csv,*.txt,*.lua,*.yml` 等），补全 §7 的配置文件清单。

## 关键分析逻辑

### 引用分类规则

对每条引用的目标路径，按优先级匹配：

1. 以 `TARGET_ROOT` 开头 → `target_internal`（内部互引用）
2. 以任一保留通用目录开头 → `keep_dir_X`（如 `vfx_material`）
3. 以 `EFFECT_ROOT` 开头 → `effect_other`（Effect 树内其他目录）
4. 以 `/Game/LetsGo/` 开头 → `letsgo_non_effect`
5. 以 `/Game/Feature` 开头 → `feature_content`
6. 以 `/Engine/` 开头 → `engine`
7. 其余 → `other`

### 分包归属判定

比对 `ChunkConfig.csv` 中的 `resPath` 列：命中则取 `chunkName`，未命中标"默认规则"。

### 迁移风险等级

根据"被外部引用次数"：0 = 零风险，1~3 = 低，4~10 = 中，>10 = 高。

### Effect 树内反向引用拆解

被引用方向（`relation=referencer`）中，目标在 `EFFECT_ROOT` 下但不在 `TARGET_ROOT` 下的，**逐个提取 Effect 下第一级子目录名**，按通用库 / 副玩法分别统计。这是最容易被忽略的耦合面。
