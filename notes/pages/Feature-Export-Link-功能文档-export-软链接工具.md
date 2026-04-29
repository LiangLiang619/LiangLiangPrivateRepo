---
title: "Feature Export Link 功能文档 - export 软链接工具"
category: "工具"
tags:
  - "UE5"
  - "Python"
  - "工具链"
source: "工作"
importance: 2
importance_label: "⭐️⭐️"
summary: "将 mod_protos 下玩法的 excel/Export 目录通过软链接方式链接到独立壳仓库 {FeatureName}_Shell 的 Feature/{FeatureName}/Script/Export 目录。运行 MakeFeatureExportLink.bat 即可（需管理员权限）。两个版本：原版(FeatureExportLink.py)适配 LetsGo 壳，Shell版(FeatureExportLink_shell.py)适配独立 *_Shell 壳仓库。"
created: 2026-04-29
updated: 2026-04-29
notion_url: "https://app.notion.com/p/Feature-Export-Link-export-3515f1d3510d8180a01ad2958323a297"
---

# Feature Export Link 功能文档 - export 软链接工具

> **分类**：工具 | **来源**：工作 | **重要程度**：⭐️⭐️
>
> 将 mod_protos 下玩法的 excel/Export 目录通过软链接方式链接到独立壳仓库 {FeatureName}_Shell 的 Feature/{FeatureName}/Script/Export 目录。运行 MakeFeatureExportLink.bat 即可（需管理员权限）。两个版本：原版(FeatureExportLink.py)适配 LetsGo 壳，Shell版(FeatureExportLink_shell.py)适配独立 *_Shell 壳仓库。

## 📌 核心概念

- 功能：将 mod_protos/{feature}/excel/Export 通过软链接映射到对应壳仓库的 Script/Export 目录

- 入口脚本：CommonLiteCore/clientTools/MakeFeatureExportLink.bat（双击运行，自动 UAC 提权）

- 核心脚本：CommonLiteCore/excel/FeatureExportLink_shell.py（Shell版，适配独立壳仓库）

- 路径推算逻辑：TMR_ProjectTCommon → 替换 Common 为 Develop → 在 Develop 仓库找 *_Shell 目录

- 优势：软链接方式实时同步，节省空间，导表后自动生效无需手动复制

## 📂 两个版本区别

- 原版 FeatureExportLink.py：目标 → LetsGo/Content/Feature/{Feature}/Script/Export（所有玩法在 LetsGo 壳）

- Shell版 FeatureExportLink_shell.py：目标 → {Feature}_Shell/Content/Feature/{Feature}/Script/Export（独立壳仓库）

## ⚠️ 注意事项

- 创建软链接需要管理员权限（脚本自动请求 UAC 提权）

- 依赖 CommonLiteCore/tools/python-3.8.2-64/python.exe，缺失则报错

- Develop 仓库下须存在 *_Shell 目录，且目录结构 {Feature}_Shell/Content/Feature/ 正确

## 🔗 参考链接

- iWiki 原文档：https://iwiki.woa.com/p/4018273660

