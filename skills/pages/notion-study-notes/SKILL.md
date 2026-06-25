---
name: notion-study-notes
description: >-
  Write study notes to Notion "笔记索引" database and sync to GitHub Obsidian mirror.
  Use when the user asks to take notes, record learnings, save study content,
  记笔记, 写笔记, 学习笔记, or mentions "笔记索引".
---

# Notion 学习笔记 Skill

当用户要求记笔记时，将内容写入 Notion "亮亮的学习笔记" 中的 **笔记索引** 数据库，并可选同步到 GitHub Obsidian 镜像。

## 核心配置

| 项目 | 值 |
|------|-----|
| Notion Database ID | `34a5f1d3-510d-8147-be95-cac7d8037c54` |
| Data Source ID | `34a5f1d3-510d-814c-bfab-000b4398341b` |
| MCP Server | `user-notionApi` |
| GitHub 镜像仓库 | `LiangLiangPrivateRepo/notes/{分类}.md` |

## 数据库字段 Schema

| 字段 | 类型 | 可选值 |
|------|------|--------|
| 标题 | title | 自由填写 |
| 分类 | select | 编程 / 架构 / 工具 / 语言 / 算法 / 游戏开发 / AI/Agent / 其他 |
| 标签 | multi_select | C++ / Lua / Python / UE5 / 设计模式 / 网络 / 性能优化 / OpenClaw / Notion / Git / 面试 / Android / LetsGo / 热更 （可新增） |
| 来源 | select | 工作 / 学习 / 阅读 / 面试 |
| 重要程度 | select | ⭐️⭐️⭐️ 必掌握 / ⭐️⭐️ 重要 / ⭐️ 了解 |
| 摘要 | rich_text | 一句话概括笔记内容 |
| 创建时间 | created_time | 自动生成 |

## 工作流程

### Step 1: 从用户输入中提取笔记元数据

从用户的描述中智能推断以下字段（未明确的主动询问）：

- **标题**：简洁概括，20 字以内
- **分类**：必须是上表中的值之一
- **标签**：从已有标签中匹配，或根据内容新建
- **来源**：默认 "学习"，用户可指定
- **重要程度**：默认 "⭐️⭐️ 重要"，用户可指定
- **摘要**：一句话概括核心内容

### Step 2: 创建 Notion 页面（索引条目）

调用 `API-post-page`，MCP Server 为 `user-notionApi`：

```json
{
  "parent": {
    "type": "database_id",
    "database_id": "34a5f1d3-510d-8147-be95-cac7d8037c54"
  },
  "properties": {
    "标题": {
      "title": [{ "text": { "content": "<标题>" } }]
    },
    "分类": {
      "select": { "name": "<分类>" }
    },
    "标签": {
      "multi_select": [{ "name": "<标签1>" }, { "name": "<标签2>" }]
    },
    "来源": {
      "select": { "name": "<来源>" }
    },
    "重要程度": {
      "select": { "name": "<重要程度>" }
    },
    "摘要": {
      "rich_text": [{ "text": { "content": "<摘要>" } }]
    }
  }
}
```

### Step 3: 追加页面正文内容

用 `API-patch-block-children`，`block_id` 使用 Step 2 返回的 page id。

正文内容组织为 paragraph 和 bulleted_list_item block：

```json
{
  "block_id": "<page_id>",
  "children": [
    {
      "type": "paragraph",
      "paragraph": {
        "rich_text": [{ "text": { "content": "正文段落内容" } }]
      }
    },
    {
      "type": "bulleted_list_item",
      "bulleted_list_item": {
        "rich_text": [{ "text": { "content": "要点" } }]
      }
    }
  ]
}
```

### Step 4: 图片处理（如有）

Notion API 不支持直传本地图片，按以下流程处理：

1. 将图片文件放入 Obsidian vault 对应目录
2. `git add` + `git commit` + `git push` 到 GitHub
3. 构造 URL：`https://raw.githubusercontent.com/LiangLiangPrivateRepo/notes/main/{path}`
4. 在 Notion 正文中以 external image block 嵌入（通过 `API-patch-block-children`，使用 image block type）

### Step 5: GitHub Obsidian 镜像同步（可选）

将笔记内容以 Markdown 追加到 Obsidian vault 中对应分类文件：

- 路径：`notes/{分类}.md`（如 `notes/编程.md`）
- 格式：标准 Markdown，以 `## <标题>` 作为二级标题
- 执行 `git add && git commit && git push`
- **必须** push 完成后执行 `git pull` 拉取远程最新变更，确保本地仓库始终为最新状态

## 查询已有笔记

用 `API-query-data-source` 查询，data_source_id 为 `34a5f1d3-510d-814c-bfab-000b4398341b`。

按分类筛选示例：

```json
{
  "data_source_id": "34a5f1d3-510d-814c-bfab-000b4398341b",
  "filter": {
    "property": "分类",
    "select": { "equals": "编程" }
  },
  "sorts": [{ "property": "创建时间", "direction": "descending" }],
  "page_size": 10
}
```

## 注意事项

- 所有 Notion API 调用走 MCP Server `user-notionApi`，不要用 Shell 调 curl
- 创建时间字段自动生成，不需要手动设置
- 摘要控制在 200 字以内
- 标签可以新建，但优先复用已有标签
- 如用户只说"记一下"而没给具体内容，先整理当前对话中的知识点再写入
