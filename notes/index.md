---
title: "📚 亮亮的学习笔记"
tags:
  - index
---

# 📚 亮亮的学习笔记

> Notion 为主数据源 · Obsidian 为镜像


## 📋 全部笔记

| 标题 | 分类 | ⭐ | 标签 | 来源 | 创建 |
|---|---|---|---|---|---|
| [ProjectT Android 包解包流程](pages/ProjectT-Android-包解包流程.md) | 游戏开发 | ⭐️⭐️⭐️ | `- "Android` `LetsGo` `UE5` `热更` | 工作 | 2026-04-24 |
| [Android手机包塞文件测试路径](pages/Android手机包塞文件测试路径.md) | 游戏开发 | ⭐️⭐️ | `- "Android` `LetsGo` | 工作 | 2026-04-24 |
| [ProjectT 启动 LocalDS 的方式](pages/ProjectT-启动-LocalDS-的方式.md) | 游戏开发 | ⭐️⭐️⭐️ 必掌握 | `- "UE5` | 工作 | 2026-04-22 |
| [UE5 网络同步原理与实践（以 IdleShow 为例）](pages/UE5-网络同步原理与实践（以-IdleShow-为例）.md) | 游戏开发 | ⭐️⭐️⭐️ 必掌握 | `- "UE5` `Lua` `网络` | 工作 | 2026-04-22 |
| [手机端强制Mount Pak文件](pages/手机端强制Mount-Pak文件.md) | 游戏开发 | ⭐️⭐️ 重要 | `- "Lua` `UE5` `热更` | 工作 | 2026-04-24 |
| [【示例】C++ 虚函数表（vtable）原理](pages/示例-C++-虚函数表（vtable）原理.md) | 编程 | ⭐️⭐️⭐️ 必掌握 | `- "C++` `设计模式` | 学习 | 2026-04-22 |
| [闭包（Closure）原理详解](pages/闭包（Closure）原理详解.md) | 语言 | ⭐️⭐️⭐️ 必掌握 | `- "Lua` `C++` | 学习 | 2026-04-22 |
| [面试技巧：项目深挖 + 隐性指标](pages/面试技巧：项目深挖-+-隐性指标.md) | 其他 | ⭐️⭐️⭐️ 必掌握 | `- "面试` | 工作 | 2026-04-22 |

## 📂 按分类

### 📝 其他（1 条）

- ⭐️⭐️⭐️ 必掌握 [面试技巧：项目深挖 + 隐性指标](pages/面试技巧：项目深挖-+-隐性指标.md)
  > 面试官视角：项目深挖技巧 + 品格/人际/概念能力三类隐性指标评估方法
  `- "面试`

### 🎮 游戏开发（5 条）

- ⭐️⭐️⭐️ [ProjectT Android 包解包流程](pages/ProjectT-Android-包解包流程.md)
  > 从流水线下载 Android 包并使用 UnrealPakViewerMoe 解包查看 pak 资产的完整流程
  `- "Android` · `LetsGo` · `UE5` · `热更`

- ⭐️⭐️ [Android手机包塞文件测试路径](pages/Android手机包塞文件测试路径.md)
  > Android Pixel 5 塞文件路径：内部共享存储空间/Android/data/com.tencent.letsgo/files/
  `- "Android` · `LetsGo`

- ⭐️⭐️⭐️ 必掌握 [ProjectT 启动 LocalDS 的方式](pages/ProjectT-启动-LocalDS-的方式.md)
  > 启动器资产名：FarmLocalDSTool。分两步：①FarmLocalDSTool 选 ProjectT 填私服配置 Start；② 游戏内调试面板设 LocalDSMapID 后点连接。
  `- "UE5`

- ⭐️⭐️⭐️ 必掌握 [UE5 网络同步原理与实践（以 IdleShow 为例）](pages/UE5-网络同步原理与实践（以-IdleShow-为例）.md)
  > UE5 网络同步核心概念：主控端/模拟端、需要同步的数据类型、FMoeActionStateDataProxy 结构体、OnRep 机制、组件复制前提，以及 IdleShow 随机数同步完整流程。
  `- "UE5` · `Lua` · `网络`

- ⭐️⭐️ 重要 [手机端强制Mount Pak文件](pages/手机端强制Mount-Pak文件.md)
  > 通过Lua在iOS手机端强制挂载pak文件，使用GetPhysicalFullPathVer获取持久化下载目录并调用UPakMountManager.Mount
  `- "Lua` · `UE5` · `热更`

### 💻 编程（1 条）

- ⭐️⭐️⭐️ 必掌握 [【示例】C++ 虚函数表（vtable）原理](pages/示例-C++-虚函数表（vtable）原理.md)
  > 每个含虚函数的类有一张 vtable，对象头部存 vptr 指针，虚函数调用通过 vptr 间接跳转，实现运行时多态。
  `- "C++` · `设计模式`

### 📖 语言（1 条）

- ⭐️⭐️⭐️ 必掌握 [闭包（Closure）原理详解](pages/闭包（Closure）原理详解.md)
  > 闭包 = 函数 + 捕获的 upvalue。外部函数局部变量因被内部函数引用而迁移到堆上，生命周期超越作用域。
  `- "Lua` · `C++`

---

## 🔍 动态索引（需要 Dataview 插件）

```dataview
TABLE
  category AS "分类",
  importance_label AS "⭐",
  tags AS "标签",
  source AS "来源",
  summary AS "摘要",
  created AS "创建"
FROM "notes/pages"
SORT importance DESC, created DESC
```
