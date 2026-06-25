---
name: notion-study-notes
description: >-
  Write study notes to Notion "笔记索引" database OR upload Cursor agent files
  (skills, rules, prompts, configs) to "Agent 文件索引" database, and sync to GitHub Obsidian mirror.
  Use when the user asks to take notes, record learnings, save study content,
  记笔记, 写笔记, 学习笔记, or mentions "笔记索引".
  Also use when uploading skills/rules/agent files to Notion, mentions "Agent 文件索引",
  上传skill, 上传rule, 新增至Agent文件索引, or wants to register a Cursor agent file.
---

# Notion 笔记 & Agent 文件索引 Skill

## ⚠️ 首要判断：写入哪个数据库？

| 场景 | 目标数据库 |
|------|-----------|
| 用户说"记笔记"、"写笔记"、"学习笔记" | **笔记索引** |
| 用户说"上传 skill/rule"、"新增至 Agent 文件索引"、"注册 agent 文件" | **Agent 文件索引** |

---

## A. 笔记索引（学习笔记）

当用户要求记笔记时，将内容写入 Notion "亮亮的学习笔记" 中的 **笔记索引** 数据库。

### 核心配置

| 项目 | 值 |
|------|-----|
| Notion Database ID | `34a5f1d3-510d-8147-be95-cac7d8037c54` |
| Data Source ID | `34a5f1d3-510d-814c-bfab-000b4398341b` |
| MCP Server | `user-notionApi` |
| GitHub 镜像仓库 | `LiangLiangPrivateRepo/notes/{分类}.md` |

### 数据库字段 Schema

| 字段 | 类型 | 可选值 |
|------|------|--------|
| 标题 | title | 自由填写 |
| 分类 | select | 编程 / 架构 / 工具 / 语言 / 算法 / 游戏开发 / AI/Agent / 其他 |
| 标签 | multi_select | C++ / Lua / Python / UE5 / 设计模式 / 网络 / 性能优化 / OpenClaw / Notion / Git / 面试 / Android / LetsGo / 热更 （可新增） |
| 来源 | select | 工作 / 学习 / 阅读 / 面试 |
| 重要程度 | select | ⭐️⭐️⭐️ 必掌握 / ⭐️⭐️ 重要 / ⭐️ 了解 |
| 摘要 | rich_text | 一句话概括笔记内容 |
| 创建时间 | created_time | 自动生成 |

### 工作流程

#### Step 1: 从用户输入中提取笔记元数据

从用户的描述中智能推断以下字段（未明确的主动询问）：

- **标题**：简洁概括，20 字以内
- **分类**：必须是上表中的值之一
- **标签**：从已有标签中匹配，或根据内容新建
- **来源**：默认 "学习"，用户可指定
- **重要程度**：默认 "⭐️⭐️ 重要"，用户可指定
- **摘要**：一句话概括核心内容

#### Step 2: 创建 Notion 页面（索引条目）

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

#### Step 3: 追加页面正文内容

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

#### Step 4: 图片处理（如有）

Notion API 不支持直传本地图片，按以下流程处理：

1. 将图片文件放入 Obsidian vault 对应目录
2. `git add` + `git commit` + `git push` 到 GitHub
3. 构造 URL：`https://raw.githubusercontent.com/LiangLiangPrivateRepo/notes/main/{path}`
4. 在 Notion 正文中以 external image block 嵌入（通过 `API-patch-block-children`，使用 image block type）

#### Step 5: GitHub Obsidian 镜像同步（可选）

将笔记内容以 Markdown 追加到 Obsidian vault 中对应分类文件：

- 路径：`notes/{分类}.md`（如 `notes/编程.md`）
- 格式：标准 Markdown，以 `## <标题>` 作为二级标题
- 执行 `git add && git commit && git push`
- **必须** push 完成后执行 `git pull` 拉取远程最新变更，确保本地仓库始终为最新状态

### 查询已有笔记

用 `API-query-data-source` 查询，data_source_id 为 `34a5f1d3-510d-814c-bfab-000b4398341b`。

---

## B. Agent 文件索引（Skill / Rule / Prompt 等）

当用户要上传 Cursor agent 文件（skill、rule、prompt、config、workflow）时，写入 **Agent 文件索引** 数据库。

### 核心配置

| 项目 | 值 |
|------|-----|
| Notion Database ID | `34a5f1d3-510d-8187-aa14-df519c5e5d06` |
| Data Source ID | `34a5f1d3-510d-813a-ab21-000b613d2f17` |
| MCP Server | `user-notionApi` |

### 数据库字段 Schema

| 字段 | 类型 | 说明 |
|------|------|------|
| 文件名 | title | skill/rule 的目录名，如 `ue-asset-migration` |
| 类型 | select | `skill` / `rule` / `prompt` / `config` / `workflow` |
| 描述 | rich_text | 一句话功能描述 |
| 适用工具 | multi_select | Cursor / Claude / OpenClaw / Copilot / 通用 / AI编程助手 / Python / Notion API / Git / UE Editor MCP |
| 适用场景 | multi_select | 代码审查 / 游戏开发 / 资产迁移 / Lua迁移 / 3C仓库 / 笔记管理 / 知识库同步 / 通用 等 |
| 编程语言 | multi_select | C++ / Python / JS/TS / Lua / 通用 / PowerShell |
| 仓库路径 | rich_text | 相对路径，如 `skills/pages/ue-asset-migration/SKILL.md` |
| 来源 | url | GitHub 文件直链 |
| 创建时间 | created_time | 自动生成 |

### 工作流程

#### Step 1: 提取 agent 文件元数据

从 SKILL.md / RULE.md 的 frontmatter 和文件内容中提取：

- **文件名**：目录名（如 `ue-asset-migration`）
- **类型**：`skill` / `rule` / `prompt` / `config` / `workflow`
- **描述**：frontmatter 的 `description` 字段，或从内容首段提炼
- **适用工具**：从内容判断（调用了 Cursor / UE Editor MCP / Notion API 等）
- **适用场景**：从关键词推断
- **编程语言**：从内容中出现的语言推断
- **仓库路径**：相对于仓库根目录的路径
- **来源 URL**：`https://github.com/LiangLiang619/LiangLiangPrivateRepo/blob/main/{仓库路径}`

#### Step 2: 检查是否已存在（防重复）

调用 `API-query-data-source` 按文件名查询：

```json
{
  "data_source_id": "34a5f1d3-510d-813a-ab21-000b613d2f17",
  "filter": {
    "property": "文件名",
    "title": { "equals": "<文件名>" }
  }
}
```

- 若已存在：询问用户是否覆盖，或跳过
- 若不存在：继续 Step 3

#### Step 3: 创建 Notion 页面

调用 `API-post-page`：

```json
{
  "parent": {
    "type": "database_id",
    "database_id": "34a5f1d3-510d-8187-aa14-df519c5e5d06"
  },
  "properties": {
    "文件名": {
      "title": [{ "text": { "content": "<文件名>" } }]
    },
    "类型": {
      "select": { "name": "skill" }
    },
    "描述": {
      "rich_text": [{ "text": { "content": "<描述>" } }]
    },
    "适用工具": {
      "multi_select": [{ "name": "Cursor" }]
    },
    "适用场景": {
      "multi_select": [{ "name": "<场景1>" }, { "name": "<场景2>" }]
    },
    "编程语言": {
      "multi_select": [{ "name": "Python" }]
    },
    "仓库路径": {
      "rich_text": [{ "text": { "content": "<仓库路径>" } }]
    },
    "来源": {
      "url": "<GitHub直链>"
    }
  }
}
```

### 注意事项

- **文件名** 字段填 skill 目录名，不含路径和扩展名
- **来源** 字段类型是 `url`（非 select），直接赋值字符串
- 适用场景/适用工具 只能使用数据库中已有的 option，不可随意新增（如需新增需先在 Notion 界面创建）

---

## 通用注意事项

- 所有 Notion API 调用走 MCP Server `user-notionApi`，不要用 Shell 调 curl
- 创建时间字段自动生成，不需要手动设置
- 如用户只说"记一下"而没给具体内容，先整理当前对话中的知识点再写入
