---
name: replace-shortpath-to-longpath
description: >-
  两阶段长路径迁移：① Python 扫描脚本扫全量 wiki 接口调用，输出带 arg_expression / resolve_hint
  的 CSV；② 大模型据 CSV + 读代码补判并执行替换。最终生成长 path_migration_report.md 完整状态表。
  当用户说「帮我替换长路径」「短路径改长路径」「长路径迁移」并给出根目录时使用。
---

# 短路径替换为长路径（脚本扫全 + 大模型判准）

在指定根目录递归扫描所有 `.lua`，使用 [scripts/scan_longpath_usage.py](scripts/scan_longpath_usage.py) 匹配 wiki 对齐的框架接口。脚本为**每条命中**记录「资产名参数表达式」和 **resolve_hint**（供你/大模型继续判断），**不**对复杂数据流做最终结论。

## 三阶段工作流

### Phase 1 — 扫描采集

**输入**：扫描根目录；`AssetNameMapping.txt` 路径（默认在 `<项目>/Content/LetsGo/Data/AssetData/AssetNameMapping/AssetNameMapping.txt`）。

**命令**：

```bash
python "<本 skill 目录>/scripts/scan_longpath_usage.py" "<扫描根目录>"
```

**输出**：`<根目录>/Intermediate/LuaCheck/longpath_migration_scan_<timestamp>.csv`

**CSV 列说明**：

| 列 | 含义 |
|----|------|
| `file`, `line`, `interface`, `category`, `risk` | 位置与接口元数据 |
| `first_string_arg` | 行内**第一个**字符串字面量（兼容旧逻辑，可能非资产参数） |
| `is_long_path` | 由 **资产名参数**（见 `arg_expression`）上的字面量是否以 `/Game/` 开头推导；变量参数多为 `no` |
| `arg_expression` | 按接口类型选取的**资产名相关参数**的完整表达式（如 `OpenWindow` 第 0 个、`OpenWindowWithWidget` 第 1 个、`ImgSetImage` 第 2 个/索引 1） |
| `resolve_hint` | 脚本侧线索，见下表 |
| `wiki_longpath` | 对应 iWiki 行为：`yes` 支持长路径；`no` 走 `GetAssetObjectPath` 不支持；`N/A` 不涉及或分支相关 |
| `call_style` | `method` / `function` / `bp_method` / `cpp_static` |
| `code` | 原始行 |

**resolve_hint 常见取值**（前缀即可区分）：

- `literal:...` — 字面量或可还原为字面量
- `local_var:名=值` — 同函数内 `local 名 = "短名"` 回溯
- `config_ref:...` — `SaveDataName.xxx` 等
- `window_name:UI_...` — `WindowName` 上字段
- `or_fallback:...` — `a or "短名"` 中的回退短名
- `func_param:名` — 实参为当前函数形参，多为框架透传
- `likely_member_or_state:...` — 可能是 `self.xxx` 等，需大模型读上下文
- `cpp_unsupported:...` — `wiki_longpath=no` 的接口
- `CDN_N/A` / `needs_moe_flag_or_branch` / `N/A:widget_ref` — 不迁移或需分支判断
- `unknown:...` — 脚本无法判断，**必须由大模型读代码**追溯来源

脚本的局限（有意留给大模型）：

- 跨文件、`require` 的配置表、`_MOE` 代理、多行调用、复杂表达式可能标为 `unknown`。
- `first_string_arg` 可能与 `arg_expression` 不一致（例如行内另有字符串）— **以 `arg_expression` 为主**。

### Phase 2 — 大模型判准

对 **CSV 每一行**（尤其 `resolve_hint` 为 `window_name`、`config_ref`、`local_var`、`unknown`）执行以下**强制判定链**：

1. 打开 `file` 对应行附近，根据 `arg_expression` 追溯：局部变量、表字段、上游入参、蓝图 `GetImgName()` 等。
2. 对 `resolve_hint=window_name:UI_Xxx`：**必须**先查 `AssetNameMapping.txt`（`Select-String "^ui_xxx:"`）拿到长路径。
   - 若 `interface=OpenWindow`：改为 `OpenWindowWithWidget(原第1参数, "长路径", 原第2+参数...)`。
   - 若 `interface=LoadAssetObject` 或其他资产加载接口：将 `WindowName` 参数直接替换为 `"长路径"` 字面量。
   - 仅当接口本身不涉及资产加载（例如关闭窗口查询类）才标记无需修改。
3. 对 `resolve_hint=config_ref:SaveDataName.Xxx`：读取 `SaveDataName.lua` 获取实际 slotName，并确保 `SaveDataName.AssetPath[slotName]` + `CreateSaveData` 查表逻辑完整。
4. 对 `resolve_hint=local_var:变量=短名`：查 `AssetNameMapping.txt` 后直接替换变量值为长路径。
5. 对 `wiki_longpath=no` 的接口：**不要**强行改为长路径，标为 `C++层不支持，需修复后处理`。
6. 对 `unknown`：必须读代码上下文再定性，禁止直接按“待上游”跳过。

### Phase 3 — 执行替换 + 报告

- 仅对判为「需替换」的项改仓库代码。
- 在 `<根目录>/Migration/LongPath/` 生成 **`longpath_migration_report.md`**。

**状态**枚举（对每条命中**必选其一**）：

| 状态 | 含义 |
|------|------|
| `已替换为长路径` | 已改代码：字面量替换、OpenWindow→OpenWindowWithWidget、局部变量改值 |
| `已通过配置/映射表解决` | SaveDataName.AssetPath + CreateSaveData 查表等间接机制 |
| `C++层不支持，需修复后处理` | `wiki_longpath=no`，依赖 C++ GetAssetObjectPath 修复 |
| `待人工确认` | 大模型与映射表均无法定论，需人工审查 |
| `框架透传，无需修改` | 参数来自函数形参，上游传长路径即自动通路 |
| `框架内部解析，无需修改` | AssetLoadUtils 内部 string.split 后的中间变量处理 |
| `CDN/N/A/非资产，无需修改` | CDN 专用、SetBrush 已加载对象、AddView 传 widget 等 |
| `非资产参数，无需修改` | windowId 等窗口句柄，非资产路径 |
| `扫描误报，无需修改` | Logger.Log 中误采的字符串等 |

**报告格式要求**（按状态分表，重要信息优先）：

```markdown
# 长路径迁移完整报告

## 状态总览                    ← 最顶部：一眼看到全局数据
| 状态 | 数量 | 说明 |
|------|-----:|------|
| 已替换为长路径 | 42 | ... |
| ... | ... | ... |

## 已修改文件（N 个）          ← 其次：哪些文件被改了

## 已替换为长路径（N 处）       ← 每种状态一个独立表格
| # | 文件 | 行 | 接口 | arg_expression | 说明 |

## 已通过配置/映射表解决（N 处）
...

## C++层不支持（N 处）          ← 需要关注的排在前面
...

## 待人工确认（N 处）             ← 额外两列：处理人 + 确认结果
| # | 文件 | 行 | 接口 | arg_expression | 说明 | 处理人 | 确认结果 |
...

## 框架透传，无需修改（N 处）    ← 不需要关注的排在后面
...

## 验证建议                    ← 最底部
```

**状态分表排序**（从需要关注到无需关注）：

1. 已替换为长路径
2. 已通过配置/映射表解决
3. C++层不支持，需修复后处理
4. 待人工确认
5. 框架透传，无需修改
6. 框架内部解析，无需修改
7. CDN/N/A/非资产，无需修改
8. 非资产参数，无需修改
9. 扫描误报，无需修改

## 注意

- `OpenWindowWithWidget` 与 `OpenWindow` 行为差异见 iWiki（预加载、横竖屏等）。
- 长路径格式：UI 蓝图用 `/Game/路径/资产名.资产名_C`，贴图用 `.资产名`（无 `_C`）。
- `window_name` 类必须改：`OpenWindow` 的调用在本仓库，即使 WindowName 值定义在上游，**替换 OpenWindow→OpenWindowWithWidget 是调用侧职责**。
- `LoadAssetObject(WindowName.xxx)` 也必须替换为长路径字面量，不限于 OpenWindow 接口。
