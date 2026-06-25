---
name: ue-redirector-reference-fix
description: >-
  Recursively scan a given UE Content directory for assets that still reference
  ObjectRedirectors (created by keep-redirector migrations), present the list
  to the user, and after explicit confirmation re-save only those in-directory
  referencers via UE Editor MCP so their imports point to the real target.
  Redirectors themselves are preserved. Use when the user asks 扫描重定向器引用,
  修复重定向器引用, 资产迁移后清理目录引用, fix redirector references in folder,
  resave referencers in folder, or provides an absolute directory path after a
  keep-redirector asset migration.
---

# UE Redirector Reference Scan & Fix

清理某个目录下「仍指向 ObjectRedirector」的资产引用。**修复范围**：仅对目录内的引用方做 `load_asset` + `save_loaded_asset`，让其 import 表直接指向真实目标；**重定向器本体保留不动**，与 keep-redirector 迁移策略一致。

## 何时使用

- 完成 `ue-3c-asset-migration` / `ue-asset-migration` 之后，需要在某个目录内清理引用
- 用户提供一个目录绝对路径（OS 或 `/Game/...`），说要扫/修「重定向器引用」
- 资产搬迁后 IDE/编辑器报「Asset references a redirector」

## 前置条件

1. `uasset_mcp` 已就绪（脚本按下列顺序自动定位 site-packages）：
   - `F:\F4\LetsGoEditor\Editor\LetsGo\Tools\Python311\Lib\site-packages`
   - 当前 Python 解释器自带
   - 环境变量 `UASSET_MCP_SITE_PACKAGES`

   若都没找到：
   ```bash
   pip install --index-url https://mirrors.tencent.com/pypi/simple/ uasset_mcp
   ```

2. **修复阶段**需要 UE 编辑器开着并启用 MCP 插件；**扫描阶段**不需要。

## 工作流

复制如下勾选表跟踪进度：

```
- [ ] Phase 0: 路径归一与校验
- [ ] Phase 1: 离线扫描
- [ ] Phase 2: 渲染表格 / 等用户 confirm
- [ ] Phase 3: ue_ping → load+save 分批执行
- [ ] Phase 4: 写 RedirectorRefFixRecords.md
- [ ] Phase 5: 汇总
```

### Phase 0 — 路径归一与校验

接收用户输入（一行）。可能形式：

| 输入形态 | 处理 |
|----------|------|
| `F:\F3\LetsGoDevelop\LetsGo\Content\LetsGo\Foo` | 直接作为 `--dir` |
| `F:/F3/.../Content/LetsGo/Foo` | 替换斜杠后同上 |
| `/Game/LetsGo/Foo` | 由扫描脚本自动转 OS 路径 |
| `Content/LetsGo/Foo` | 拼上 content-root 后作为 `--dir` |
| 末尾或两端带引号 / 空格 | trim 处理 |

若路径不在 `Content/` 之下，或目录不存在 → 提示用户重输，给出最近一次正确格式作为示例；不要自作主张拼接。

### Phase 1 — 离线扫描

```bash
python scripts/scan_redirector_refs.py --dir "<目录>"
```

可选参数：
- `--content-root`：默认 `F:\F3\LetsGoDevelop\LetsGo\Content`
- `--output-dir`：默认 skill 同级 `reports/` 目录

脚本动作：
1. 递归遍历目录下所有 `.uasset`
2. 用 `UAssetParser` 解析：
   - 硬引用：imports 表中 `class_name == "Package"` 且以 `/Game/` 开头
   - 软引用：FName 表中以 `/Game/` 开头的字符串（取 `.` 之前的 package 段）
3. 对每个被引用 package 做「重定向器探针」：解析其 `.uasset`，若 exports 全为 `ObjectRedirector`（忽略 `MetaData`），跟随 imports.Package 链最多 5 跳取最终目标
4. 输出（带目录尾段 + 时间戳后缀）：
   - `redirector_refs_<tag>.json`：完整数据，Phase 3 消费
   - `redirector_refs_<tag>.csv`：referencer/ref_type/redirector/final_target
   - `redirector_refs_<tag>.md`：渲染给用户用的预览表

读取 `stats` 字段，确认 `uassets_scanned > 0`。若结果为空且目录正确，直接告知用户「未发现重定向器引用，无需修复」，停止流程。

### Phase 2 — 用户确认

把扫描脚本产出的 `.md` 前若干行展示给用户（行数过多时只贴前 30 行 + 「省略 X 条，详见 `<csv 路径>`」）。

末尾汇总：

> 目录内涉及 **M** 个引用方资产，共 **K** 条重定向器引用，涉及 **N** 个不同重定向器。
> 修复将对上述 **M** 个引用方执行 `load_asset` + `save_loaded_asset`（重定向器本体不动）。
> 回复 **confirm** 继续，或指出需要排除的资产。

**未收到显式 `confirm` 前不得进入 Phase 3。**

### Phase 3 — UE Editor MCP 修复

#### 3.1 连通性

```
CallMcpTool(server="user-ue-editor-mcp", toolName="ue_ping", arguments={})
```

不通则停止并提示用户启动 UE 编辑器。扫描结果已落盘，不会丢失。

#### 3.2 生成分批

```bash
python scripts/fix_redirector_refs.py --json "<scan_output.json>" --batch-size 50
```

输出每批的 referencer 列表 + 在 UE 内执行的 Python snippet。

snippet 形如：

```python
import unreal
eal = unreal.EditorAssetLibrary
targets = ["/Game/LetsGo/Foo/A", "/Game/LetsGo/Foo/B", ...]
for pkg in targets:
    asset = eal.load_asset(pkg)
    if asset is None:
        unreal.log_warning("[redirector-fix] LOADFAIL " + pkg)
        continue
    ok = eal.save_loaded_asset(asset, only_if_is_dirty=False)
    unreal.log("[redirector-fix] " + ("OK " if ok else "FAIL ") + pkg)
```

`save_loaded_asset` 会重新序列化 linker import 表，UE 在写入时会把 `ObjectRedirector` 引用透写到其 `DestinationObject`。**重定向器 `.uasset` 不被修改、不被删除。**

#### 3.3 执行

对每个批次：

```
CallMcpTool(server="user-ue-editor-mcp", toolName="ue_actions_search",
            arguments={"query": "python execute editor"})
CallMcpTool(server="user-ue-editor-mcp", toolName="ue_actions_schema",
            arguments={"action_id": "<found>"})
CallMcpTool(server="user-ue-editor-mcp", toolName="ue_actions_run",
            arguments={"action_id": "<found>", "params": {"code": "<snippet>"}})
```

若找不到 python-exec action，按现场 schema 调整；最坏情况把 snippet 写盘后让用户在 UE 内手动 `Tools → Run Python Script` 执行。

#### 3.4 校验

每批结束后：

```
CallMcpTool(server="user-ue-editor-mcp", toolName="ue_logs_tail",
            arguments={"lines": 400})
```

抓 `[redirector-fix]` 行：
- `OK <pkg>` → 成功
- `FAIL <pkg>` / `LOADFAIL <pkg>` / `SAVEEXC <pkg>` → 失败，记入失败列表
- `BATCH_DONE ok=X fail=Y total=Z` → 批次完成标记

### Phase 4 — 落档

文件固定路径：

```
<workspace>/LetsGo3C/Migration/AssetsMigration/RedirectorRefFixRecords.md
```

不存在则新建，含表头：

```markdown
# Redirector Reference Fix Records

| # | 扫描目录 | 引用方数 | 重定向器数 | 引用条数 | 成功 | 失败 | 时间 | JSON 报告 | 备注 |
|---|----------|----------|------------|----------|------|------|------|-----------|------|
```

每次执行**追加一行**：
- 扫描目录：`game_dir`（如 `/Game/LetsGo/Foo`）
- 引用方数 / 重定向器数 / 引用条数：取自 scan JSON 的 `stats`
- 成功 / 失败：从 `[redirector-fix]` 日志统计
- JSON 报告：写相对仓库的相对路径
- 备注：失败资产列表（若有），逗号分隔；无则留空

### Phase 5 — 汇总

回报用户：
- 扫描目录、扫描资产数
- 修复成功 / 失败 计数
- 失败明细（若有）
- 落档文件路径
- 提醒：重定向器 `.uasset` 保留不动；若后续仍要做硬编码路径替换，建议再跑 `ue-3c-asset-path-replace`

## 错误处理

| 场景 | 处理 |
|------|------|
| 路径不在 `Content/` 下 | 停，给出示例格式提示用户重输 |
| `uasset_mcp` 找不到 | 按「前置条件 1」安装；不要回退到不可靠的纯文本扫描 |
| 单个 `.uasset` 解析异常 | 警告并跳过，不阻塞批次 |
| 扫描 0 条结果 | 告知「目录干净」，跳过 Phase 2-4，仍可在 Phase 4 追加一条 0 行记录方便审计（可选） |
| `ue_ping` 不通 | 停在 Phase 3 入口，提示启动 UE 编辑器；扫描结果不重跑 |
| 找不到 python-exec action | 把 snippet 写盘，让用户在 UE 内 `Tools → Run Python Script` 跑 |
| 个别 `save_loaded_asset` 返回 false | 记入 failed，不回滚已成功者；Phase 4 备注里列出 |
| 编辑器中相关资产被打开未保存 | 让用户先关闭未保存编辑器窗口再重跑该批次 |

## 注意事项

- 本 skill **不会**删除重定向器、**不会**触碰目录外引用者
- 修复后无需重启编辑器；但若同会话内已加载过老引用方，建议手动 `Reload` 一次以避免内存里残留旧 import 表
- `save_loaded_asset(only_if_is_dirty=False)` 即使资产未被改动也会重写，确保 import 表必然刷新
