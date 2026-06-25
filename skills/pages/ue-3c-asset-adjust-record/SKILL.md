---
name: ue-3c-asset-adjust-record
description: 为 UE 3C 迁移过程中的资产修改建立调整记录档案。每当用户告知修改了某资产 A，自动在 Content/LetsGo3C/Migration/AssetsMigration/A/ 下新建文件夹并生成 AdjustRecord_A.md 记录文件，按"决策锁定 / 路径决策 / Phase 执行明细 / 变更日志"模板组织内容；后续修改追加到同一文件的变更日志区。Use when the user says 我修改了资产 / 落档资产修改 / 记录资产调整 / 新建调整记录 / AdjustRecord / 资产改动落档 / 3C 资产修改记录, or provides an asset name with modification details for 3C migration.
---

# UE 3C Asset Adjust Record

为 `Content/LetsGo3C/Migration/AssetsMigration/` 下的每个被修改资产维护一份独立的 `AdjustRecord_<AssetName>.md` 落档文件。

## 何时使用

用户表达以下意图时触发：
- "我修改了资产 X，帮我落档"
- "新建 X 的调整记录"
- "把这次对 X 的改动追加进调整记录"
- 提供资产名 + 修改说明，要求归档

## 工作流

### Step 1: 解析输入

从用户消息中提取：
- **AssetName**：资产名（不含扩展名，如 `BP_CommunityCharRPCComponent`）
- **改动内容**：本次修改的操作 / 工具 / 参数 / 结果 / 备注
- **可选元数据**：关联 wiki / plan 路径、Phase 标号、决策选项等

若 AssetName 缺失或歧义，先用 AskQuestion 确认。

### Step 2: 路径决策

基础目录：`F:/F3/LetsGoDevelop/LetsGo/Content/LetsGo3C/Migration/AssetsMigration/`

- 资产文件夹：`<基础目录>/<AssetName>/`
- 记录文件：`<基础目录>/<AssetName>/AdjustRecord_<AssetName>.md`

### Step 3: 判断新建 or 追加

用 Glob 或 Read 检查 `AdjustRecord_<AssetName>.md` 是否存在：

- **不存在** → Step 4a 新建完整文件
- **已存在** → Step 4b 仅向"四、变更日志"区追加一条新记录

### Step 4a: 新建文件

按下方模板填充。未知字段保留 `(待补)`，不要编造。

#### 模板

```markdown
# <AssetName> 3C 迁移调整记录

> 关联 wiki: <wiki 链接 或 (待补)>
>
> 关联 plan: <plan 路径 或 (待补)>
>
> 执行人: AI agent (Cursor)
>
> 开始时间: <YYYY-MM-DD HH:MM> (UTC+8)

---

## 一、决策锁定

- (按用户给出的范围 / 选项 / 不做项分条列出，未给出则写 `(待补)`)

## 二、路径决策（执行采用值）

| 维度 | 旧 | 新 |
|---|---|---|
| (按需补行：UE 路径 / Lua require / Lua 磁盘 / 其它) | | |

## 三、Phase 执行明细

### Phase A 预检
- [ ] (按需列子项)

### Phase B …
- [ ] …

(按本次资产实际涉及的 Phase 列出，无则省略对应 Phase)

---

## 四、变更日志（按时间倒序追加）

<!-- 每条变更格式：
### YYYY-MM-DD HH:MM:SS - <Phase 标号> - <短标题>
- 操作：...
- 命令/工具：...
- 输入参数：...
- 结果：成功/失败
- 备注：...
-->

### <YYYY-MM-DD HH:MM> - <Phase 或 -> - <短标题>
- 操作：…
- 命令/工具：…
- 输入参数：…
- 结果：…
- 备注：…
```

### Step 4b: 追加变更日志

读取现有文件，定位 `## 四、变更日志（按时间倒序追加）` 标题，**在该标题下、紧邻其后的位置插入新条目**（保持时间倒序：最新在最上）。

新条目格式：

```markdown
### <YYYY-MM-DD HH:MM> - <Phase 标号 或 -> - <短标题>
- 操作：…
- 命令/工具：…
- 输入参数：…
- 结果：成功 / 失败 / 部分完成
- 备注：…
```

不要修改"一、决策锁定"、"二、路径决策"、"三、Phase 执行明细"等历史区块，除非用户显式要求更新（例如"把 Phase B1 标为完成"）。此类更新用 StrReplace 精确改对应 checkbox。

### Step 5: 反馈用户

简短回复：
- 文件路径
- 是新建还是追加
- 本次写入的关键字段摘要

## 约束

- 编码：UTF-8、LF 换行
- 时间：用本地时间（UTC+8），从系统 timestamp 取
- 不调用 git 提交，仅落档文件
- 不污染其它资产的记录文件，每个资产各自独立目录
- 路径一律使用正斜杠 `/`

## 参考实例

`Content/LetsGo3C/Migration/AssetsMigration/BP_CommunityCharRPCComponent/AdjustRecord_BP_CommunityCharRPCComponent .md` 是首份样例，可作为格式对齐基准。
