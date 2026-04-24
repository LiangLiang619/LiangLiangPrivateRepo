# SKILL: notion-obsidian-sync（笔记与待办双端同步）

> 本 Skill 管理「Notion 主数据源 + Obsidian/GitHub 镜像」的完整工作流。
> 参考仓内 `letsgo-quick-pak` skill 风格编写。

---

## When to trigger

用户说到以下意图之一就激活本 skill：

- "记一条笔记 / 保存笔记 / 新增笔记"
- "记一个待办 / 新增任务 / 加一条 todo"
- "同步 Obsidian / 更新笔记镜像 / push 笔记"
- "更新待办 / 同步待办 / 生成待办索引"
- "笔记索引乱了 / 重新生成 index"
- "查看我的笔记 / 查看我的待办"

---

## 架构概览

```
Notion（主数据源）
    ↓ gen_obsidian_v2.py / gen_todos.py
LiangLiangPrivateRepo（GitHub Public）
├── .obsidian/              ← Obsidian 插件配置（Working Copy 同步到手机）
├── notes/
│   ├── index.md            ← 静态索引（标准 Markdown 链接）
│   ├── pages/              ← 每条笔记独立 .md 文件
│   │   └── {笔记标题}.md
│   └── assets/{笔记名}/    ← 配套截图（本地相对路径 `../assets/...`）
├── todos/
│   ├── index.md            ← 静态索引（未完成/已完成分区）
│   └── pages/              ← 每条待办独立 .md 文件
│       └── {待办标题}.md
└── skills/ rules/ ...
```

---

## 关键配置

| 项目 | 值 |
|---|---|
| Notion 笔记 DB | `34a5f1d3-510d-8147-be95-cac7d8037c54` |
| Notion 待办 DB | `34a5f1d3-510d-804b-854e-f050b2a4a4bb` |
| Notion API | Maton 网关 `https://gateway.maton.ai/notion/v1` |
| Maton 连接 ID | `a925e154-93a3-4dd6-80d1-1a4fb3dfffc8` |
| MATON_API_KEY | Windows User 环境变量（已配置） |
| GitHub 仓库 | `https://github.com/LiangLiang619/LiangLiangPrivateRepo`（Public） |
| 本地仓库路径 | `C:\Users\Administrator\.openclaw\workspace\LiangLiangPrivateRepo` |
| Obsidian Vault | 即本仓库根目录，通过 Working Copy 同步到 iOS |

---

## Action：记笔记

### 完整流程（5 步）

**Step 1 — 写入 Notion**

```python
# POST /pages  到笔记 Database
# 必填字段：标题(title) / 分类(category) / 重要程度(importance) / 来源(source) / 摘要(summary) / 标签(tags)
# 用 Maton 网关，不直连 api.notion.com（内网 502）
```

分类枚举：`游戏开发 / 编程 / 语言 / 架构 / 工具 / 算法 / AI·Agent / 其他`  
重要程度枚举：`⭐️ / ⭐️⭐️ / ⭐️⭐️⭐️`（对应 1/2/3）  
来源枚举：`工作 / 学习 / 阅读 / 面试`

**Step 2 — 截图处理（有截图时）**

1. 复制截图到 `notes/assets/{笔记slug}/` 目录
2. `git add notes/assets/ && git push`（先 push 图片）
3. 在 Notion 页面正文插入 external image block，URL 用 `raw.githubusercontent.com/LiangLiang619/LiangLiangPrivateRepo/main/notes/assets/{slug}/{filename}`
   > ⚠️ 仓库为 Public，raw URL 可公开访问

**Step 3 — 同步到 Obsidian**

```powershell
cd C:\Users\Administrator\.openclaw\workspace
python gen_obsidian_v2.py
```

生成结果：
- `notes/pages/{笔记标题}.md`（含 YAML frontmatter + 正文 + 本地图片链接）
- `notes/index.md`（自动更新）

图片在笔记文件中以 `![[../assets/{slug}/{filename}]]` 形式引用（本地路径）

**Step 4 — 更新索引**

```powershell
python gen_index.py
```

**Step 5 — Git Push**

```powershell
cd C:\Users\Administrator\.openclaw\workspace\LiangLiangPrivateRepo
git add notes/
git commit -m "feat: add note - {笔记标题}"
git push origin main
```

---

## Action：记待办

### 完整流程（3 步）

**Step 1 — 写入 Notion**

```python
# POST /pages 到待办 Database
# 必填字段：Task name(title) / Status / Priority / Due date
# 可选：Task type(multi_select) / Effort level / Description / Summary
```

Status 枚举：`Not started / In progress / Done`  
Priority 枚举：`High / Medium / Low`  
Task type 枚举：`🐞 Bug / 💬 Feature request / 💅 Polish`  
Effort level 枚举：`Small / Medium / Large`

**Step 2 — 同步到 Obsidian**

```powershell
python gen_todos.py
```

生成结果：
- `todos/pages/{待办标题}.md`（含 YAML frontmatter + 属性表格 + 描述 + Notion 链接）
- `todos/index.md`（未完成/已完成分区，标题列为可点击链接）

**Step 3 — Git Push**

```powershell
cd C:\Users\Administrator\.openclaw\workspace\LiangLiangPrivateRepo
git add todos/
git commit -m "feat: add todo - {待办标题}"
git push origin main
```

---

## Action：仅同步（不新增内容）

当用户只想刷新镜像时：

```powershell
cd C:\Users\Administrator\.openclaw\workspace
$env:MATON_API_KEY = [System.Environment]::GetEnvironmentVariable("MATON_API_KEY","User")
python gen_obsidian_v2.py   # 同步笔记
python gen_todos.py          # 同步待办
python gen_index.py          # 重建笔记索引（可选，gen_obsidian_v2.py 已包含）

cd LiangLiangPrivateRepo
git add notes/ todos/
git commit -m "chore: sync from Notion"
git push origin main
```

---

## Obsidian 文件格式规范

### 笔记 YAML frontmatter

```yaml
---
title: "笔记标题"
category: "游戏开发"          # 分类
tags:
  - "UE5"
  - "热更"
source: "工作"                # 来源
importance: 3                 # 1-3
importance_label: "⭐️⭐️⭐️ 必掌握"
summary: "一句话摘要"
created: 2026-04-24
updated: 2026-04-24
notion_url: "https://www.notion.so/..."
---
```

### 待办 YAML frontmatter

```yaml
---
title: "待办标题"
status: "Not started"         # Not started / In progress / Done
priority: "High"              # High / Medium / Low
priority_num: 3               # 用于 Dataview 排序
task_type:
  - "💬 Feature request"
effort: "Large"
due: 2026-04-27
summary: "一句话描述"
created: 2026-04-24
updated: 2026-04-24
notion_url: "https://www.notion.so/..."
---
```

---

## 不允许做什么

- **不能直连 `api.notion.com`**（内网 502，统一走 Maton 网关）
- **不能新建第二个笔记 Database 或待办 Database**（只操作上方两个固定 DB ID）
- **不能把敏感信息存入仓库**（仓库为 Public）
- **不能把待办以 Notion 之外为准**（Obsidian 是只读镜像）
- **不能在 Notion 中用文字描述代替图片**（有截图必须上传到 GitHub assets/ 后嵌入）

---

## 脚本路径速查

| 脚本 | 作用 |
|---|---|
| `gen_obsidian_v2.py` | Notion 笔记 → `notes/pages/*.md` + `notes/index.md` |
| `gen_todos.py` | Notion 待办 → `todos/pages/*.md` + `todos/index.md` |
| `gen_index.py` | 单独重建 `notes/index.md` 静态索引 |

所有脚本在 `C:\Users\Administrator\.openclaw\workspace\` 下，运行前确保 `MATON_API_KEY` 环境变量可读。

---

## Obsidian 插件（已配置）

`.obsidian/community-plugins.json` 中已写入以下插件，首次使用需在 Obsidian 手动安装一次，之后通过 Working Copy 同步到 iOS：

| 插件 ID | 功能 |
|---|---|
| `dataview` | 动态查询索引 |
| `obsidian-shiki-plugin` | 代码高亮（github-dark 主题） |
| `cm-editor-syntax-highlight-obsidian` | 编辑模式高亮 |
| `editing-toolbar` | 富文本工具栏（移动端友好） |
| `recent-files-obsidian` | 最近文件 |
| `obsidian-minimal-settings` | 配合 Minimal 主题 |
| `obsidian-style-settings` | 细粒度样式 |
| `obsidian-checklist-plugin` | 待办清单汇总 |
| `obsidian-file-color` | 文件夹着色 |

> 新增插件时，同步更新 `.obsidian/community-plugins.json` 并 push。

---

## 常见问题

**Q：Notion 图片显示 404？**  
A：确认 `LiangLiangPrivateRepo` 仍为 Public，且图片已 push 到 `notes/assets/` 目录。

**Q：Obsidian 中点击索引链接跳不过去？**  
A：链接格式应为标准 Markdown `[标题](pages/文件名.md)`，不要用 `[[wiki链接]]`（跨目录不稳定）。

**Q：图片在 Obsidian 中不显示？**  
A：检查 `notes/pages/` 中的笔记，图片应为 `![[../assets/{slug}/{filename}]]` 格式（本地 wiki 链接）。

**Q：Maton API 报 401？**  
A：检查 `MATON_API_KEY` 环境变量，或从 `openclaw.json` 中 `skills.entries.notion.apiKey` 读取。
