---
name: ue-3c-migration-path-mapper
description: >-
  分析3C迁移待办 Excel/CSV 中的外部资产路径，自动判断每个资产属于 Character/Controller/Camera
  哪一个C，再根据 asset_class 决定子目录，生成 LetsGo3C 仓库目标路径并回填到新列。
  Use when the user asks 3C迁移路径, 3C目标路径, 3C仓库分类, LetsGo3C路径生成, 外部3C资产分析,
  3C path mapping, or provides an asset CSV/Excel for 3C migration path planning.
---

# UE 3C 迁移路径映射

根据资产 CSV/Excel 文件中的 `外部资产完整路径` 列，自动分析每个资产属于 3C 中的哪一个 C（Character / Controller / Camera），再根据 asset_class 决定子目录，生成 `/Game/LetsGo3C/Assets/Base/<C>/<subdir>/<asset_name>` 目标路径。

## 输入

- `.xlsx`（多 Sheet）或 `.csv`
- CSV 至少包含 `外部资产完整路径` 列（UE 路径，如 `/Game/LetsGo/Assets/Animation/...`）

## 输出

- 在输入文件同级新建 `<原文件名>_3C_mapped_YYYYMMDD_HHMMSS/` 文件夹
- 输出新 CSV：保留全部原始列，在 `外部资产完整路径` 列之后插入新列 `3C仓库目标路径`
- 编码 UTF-8 with BOM

## 执行流程

### Phase 0: Excel 拆分（仅 .xlsx）

运行 `split_xlsx.py`：

```bash
python scripts/split_xlsx.py "<input.xlsx>"
```

在同目录生成 `<文件名>_sheets/Sheet名.csv`。列出所有 CSV 让用户选择要分析的文件。

如果用户直接提供 `.csv` 则跳过此步。

### Phase 1: 路径关键字批量分类

运行 `classify_assets.py`：

```bash
python scripts/classify_assets.py "<input.csv>"
```

脚本逐行读取 `外部资产完整路径`，按路径关键字规则快速判断 3C 分类和子目录。详细规则见 [rules.md](rules.md)。

**输出**：
- 新 CSV 到 `<原文件名>_3C_mapped_<timestamp>/` 目录（含 `3C仓库目标路径` 列）
- 控制台打印 `[PENDING]` 行列表——这些行路径关键字未命中，需要 uasset-analyzer 补全

### Phase 2: uasset-analyzer 补全（agent 主动执行）

对每个 `[PENDING]` 行：

1. 将 UE 路径转换为磁盘路径：`/Game/X` → `Content/X.uasset`
2. 调用 `user-uasset-analyzer` 的 `uasset_exports` 获取主导出对象的 class_name 和父类：

```
CallMcpTool(server="user-uasset-analyzer", toolName="uasset_exports",
            arguments={"file_path": "<磁盘绝对路径>"})
```

3. 从 exports 结果中找到主对象（通常是与文件同名的 export），读取其 `class_name` 作为 asset_class
4. 如需确认父类继承链，补充调用 `uasset_imports`：

```
CallMcpTool(server="user-uasset-analyzer", toolName="uasset_imports",
            arguments={"file_path": "<磁盘绝对路径>"})
```

5. 根据 class_name / 父类判定 3C 分类（见 [rules.md](rules.md) Phase 2 规则）
6. 仍无法判定的标记为 `[待确认]`

### Phase 3: 回填与输出

将 Phase 2 的判定结果更新到输出 CSV 的 `3C仓库目标路径` 列。

最终向用户报告：
- 输出 CSV 路径
- 成功映射数 / 待确认数
- `[待确认]` 行明细表（资产名、路径、原因）

## 目标路径模板

```
/Game/LetsGo3C/Assets/Base/<C>/<subdir>/<asset_name>
```

- `<C>`：`Character` / `Controller` / `Camera`
- `<subdir>`：`Components/` / `Animation/<AnimClass>/` / `Config/` / `<asset_class>/`
- `<asset_name>`：原资产文件名（不含路径前缀）

## 路径生成规则速查

### 3C 分类优先级

| 优先级 | 方法 | Camera 关键字 | Controller 关键字 | Character 关键字 |
|---|---|---|---|---|
| 1 | 路径关键字 | `/Camera/`, `CineCamera`, `_Camera`, `Camera_`, `CCM_`, `Camera[A-Z]`(文件名) | `/Controller/`, `/PlayerController/`, `/AIController/`, `PC_`, `AIC_`, `BP_Controller` | `/Character/`, `/Characters/`, `/Anim`, `/Skeleton/`, `BP_CH_`, `ABP_CH_`, `AS_CH_`, `SK_`, `BU_`, `OG_`, `PL_`, `BP_*Char*Component`, `BP_MoeChar`, `BP_MainChar` |
| 2 | uasset 父类 | `CameraActor`, `CineCamera`, `CameraComponent` | `PlayerController`, `AIController`, `Controller` | `Character`, `Pawn`, `AnimInstance` |
| 3 | 兜底 | — | — | — → `[待确认]` |

### 子目录规则

| 优先级 | 条件 | 子目录 |
|---|---|---|
| 1 | 父类继承 ActorComponent/SceneComponent/PrimitiveComponent | `Components/` |
| 2 | asset_class ∈ 动画类（AnimBlueprint/AnimNotify/AnimSequence/AnimMontage/BlendSpace 等）且 3C=Character | `Animation/<AnimClass>/`（按精确 class 细分二级目录） |
| 3 | asset_class ∈ 配置类（DataTable, DataAsset, CurveFloat, CurveVector 等） | `Config/` |
| 4 | 其他 | `<asset_class>/` |

完整规则见 [rules.md](rules.md)。

## 注意事项

- 忽略原 CSV 中 `资产父目录`/`资产子目录` 列的人工预分析，纯依赖路径 + uasset 重新分析
- 所有行均尝试生成目标路径（含"无需搬迁"行），便于用户审阅
- Python 脚本依赖：`openpyxl`（仅 xlsx 拆分）、`csv`/`re`/`os`（标准库）
