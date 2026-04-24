---
title: "✅ 亮亮的待办"
tags:
  - index
  - todo
---

# ✅ 亮亮的待办

> Notion 为主数据源 · 以 Notion 为准 · 最后同步：2026-04-24 18:34
> 安装 Dataview 插件后索引变为动态表格

---

## 📋 未完成（7 项）

| 标题 | 优先级 | 状态 | 类型 | 工作量 | 截止日期 |
|---|---|---|---|---|---|
| [[元梦之星-LiteProject-推进-Service-化，减少-LiteProject-对-System-仓库的全量依赖|【元梦之星】【LiteProject】推进 Service …]] | 🔴 High | ⬜ Not started | 💬 Feature request | Large | 2026-04-27 |
| [[元梦之星-LiteProject-解除-System-仓库对大厅仓库的依赖|【元梦之星】【LiteProject】解除 System 仓…]] | 🔴 High | ⬜ Not started | 💬 Feature request | Large | 2026-04-27 |
| [[savedata相关代码合入-dev-和-projectt-分支，并安排QA进行专项测试|savedata相关代码合入 dev 和 projectt …]] | 🔴 High | ⬜ Not started | - | - | - |
| [[ini配置隔离方案|ini配置隔离方案]] | 🟢 Low | ⬜ Not started | - | - | - |
| [[Fonts字体仓挪回到LetsGo仓库，并变成一个独立仓|Fonts字体仓挪回到LetsGo仓库，并变成一个独立仓]] | 🟢 Low | ⬜ Not started | - | - | - |
| [[分析连带迁入的SDK仓库-BP资产|分析连带迁入的SDK仓库 BP资产]] | 🟢 Low | ⬜ Not started | - | - | - |
| [[分析外部资产依赖-—-针对不同类型的资产找对应同学分析出方案|分析外部资产依赖 — 针对不同类型的资产找对应同学分析出方案]] | 🟢 Low | ⬜ Not started | - | - | - |

---

## ✅ 已完成（1 项）

| 标题 | 优先级 | 截止日期 |
|---|---|---|
| [[和孙傲、王艺瑾打羽毛球|和孙傲、王艺瑾打羽毛球]] | 🔴 High | 2026-04-22 |

---

## 🔍 动态索引（需要 Dataview 插件）

```dataview
TABLE
  status AS "状态",
  priority AS "优先级",
  task_type AS "类型",
  effort AS "工作量",
  due AS "截止",
  summary AS "摘要"
FROM "todos"
WHERE file.name != "index" AND status != "Done"
SORT priority_num DESC, due ASC
```
