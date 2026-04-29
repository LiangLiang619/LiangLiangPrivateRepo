---
title: "📚 亮亮的学习笔记"
tags:
  - index
---

# 📚 亮亮的学习笔记

> 数据来源：Notion | 格式：Obsidian Dataview
> 以 Notion 为主数据源，此处为镜像。

---

## 🔍 全部笔记（按重要程度排序）

```dataview
TABLE
  category AS "分类",
  importance_label AS "⭐️",
  tags AS "标签",
  source AS "来源",
  summary AS "摘要",
  created AS "创建时间"
FROM "notes"
WHERE file.name != "index"
SORT importance DESC, created DESC
```

---

## 📂 按分类浏览

```dataview
TABLE
  importance_label AS "⭐️",
  tags AS "标签",
  summary AS "摘要"
FROM "notes"
WHERE file.name != "index" AND category = "游戏开发"
SORT importance DESC
```

> 修改上方 `category = "游戏开发"` 可切换分类：编程 / 架构 / 工具 / 语言 / 算法 / 游戏开发 / AI·Agent / 其他

---

## 🏷️ 按标签浏览

```dataview
TABLE
  category AS "分类",
  importance_label AS "⭐️",
  summary AS "摘要"
FROM "notes"
WHERE file.name != "index"
FLATTEN tags AS tag
WHERE tag = "UE5"
SORT importance DESC
```

> 修改上方 `tag = "UE5"` 可切换标签

---

## 📊 统计

```dataview
TABLE rows.file.link AS "笔记", length(rows) AS "数量"
FROM "notes"
WHERE file.name != "index"
GROUP BY category
SORT length(rows) DESC
```
