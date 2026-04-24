---
title: "ProjectT Android 包解包流程"
category: "游戏开发"
tags:
  - "Android"
  - "LetsGo"
  - "UE5"
  - "热更"
source: "工作"
importance: 3
importance_label: "⭐️⭐️⭐️"
summary: "从流水线下载 Android 包并使用 UnrealPakViewerMoe 解包查看 pak 资产的完整流程"
created: 2026-04-24
updated: 2026-04-24
notion_url: "https://www.notion.so/ProjectT-Android-34c5f1d3510d8173813ffd08481dd4e1"
---

# ProjectT Android 包解包流程

> **分类**：游戏开发 | **来源**：工作 | **重要程度**：⭐️⭐️⭐️
>
> 从流水线下载 Android 包并使用 UnrealPakViewerMoe 解包查看 pak 资产的完整流程

## 📌 核心概念

- 目的：从流水线下载的 Android 安装包中，提取并查看 pak 资产内容

- 工具：UnrealPakViewerMoe（编译自游戏项目）

- 密钥路径：LetsGoDevelop\LetsGo\Tools\MoeAssetsToolSet\Config\Crypto.json

## 💻 完整步骤

### Step 1：从流水线下载包

![Crypto.json 位于 LetsGo_Tools 仓库 MoeAssetsToolSet/Config/ 目录下](https://raw.githubusercontent.com/LiangLiang619/LiangLiangPrivateRepo/main/notes/assets/unpack/step1-crypto-json.png)

- 从 CI/CD 流水线下载 Android 安装包（apk/obb 格式）

### Step 2：解压 apk

- 将 apk 文件后缀改为 .zip

- 解压 zip，进入 assets/ 目录

```plain text
ProjectT-Android-CN-Development-0.0.462.1-xiaowo-farmcrazy-6-signed/
└── assets/
    ├── main.obb.zip          ← 重点文件（约 1.7 GB）
    ├── MidasPay.zip
    ├── libwbsafeedit
    ├── MSDKConfig.ini
    └── ...
```

![apk 改为 zip 解压后的 assets/ 目录，main.obb.zip 即为目标文件](https://raw.githubusercontent.com/LiangLiang619/LiangLiangPrivateRepo/main/notes/assets/unpack/step2-assets-dir.png)

### Step 3：解压 main.obb

- 在 assets/ 目录中找到 main.obb 文件（此时已是 main.obb.zip）

- 解压 main.obb.zip，pak 文件存放在以下目录：

```plain text
assets/ProjectT/Content/Paks/
├── p_680010001-Android_ASTCClient.pak          (404,575 KB)
├── p_avatar_effect-Android_ASTCClient.pak      (28,981 KB)
├── p_base_prop-Android_ASTCClient.pak          (3,649 KB)
├── p_cl_baseblueprint-Android_ASTCClient.pak   (324 KB)
├── p_common_effect-Android_ASTCClient.pak      (43,483 KB)
├── p_common_effect_none_ref-Android_ASTCClient.pak (4,813 KB)
├── p_effect_ogc-Android_ASTCClient.pak         (1,790 KB)
├── p_f_sdk_main-Android_ASTCClient.pak         (18,957 KB)
├── p_feature_community_new-Android_ASTCClient.pak (276,534 KB)
├── p_feature_projectt_startup-Android_ASTCClient.pak (2 KB)
├── p_featurebase_placeable_mini-Android_ASTCClient.pak (20,379 KB)
├── p_mainstartup_res-Android_ASTCClient.pak    (11,206 KB)
└── res_base-Android_ASTCClient.pak             (894,129 KB)
```

![main.obb 解压后的 ProjectT/Content/Paks/ 目录，包含所有 pak 文件](https://raw.githubusercontent.com/LiangLiang619/LiangLiangPrivateRepo/main/notes/assets/unpack/step3-paks-dir.png)

### Step 4：打开解包工具

- 在 IDE（CLion/Rider）中打开游戏项目

- 编译参数下拉菜单 → Programs → 选择 UnrealPakViewerMoe

- 点击编译/运行，即可打开解包查看工具

- 路径：Recent Configurations → UnrealPakViewerMoe（或 All Configurations → Programs → UnrealPakViewerMoe）

![IDE 编译参数下拉菜单，选择 Programs → UnrealPakViewerMoe](https://raw.githubusercontent.com/LiangLiang619/LiangLiangPrivateRepo/main/notes/assets/unpack/step4-ide-config.png)

## ⚠️ 注意事项

- 解压密码（AES Key）保存在：LetsGoDevelop\LetsGo\Tools\MoeAssetsToolSet\Config\Crypto.json

- Crypto.json 位于 LetsGo_Tools 仓库（Git），Config/ 目录下，与 common_project_settings.yaml 等配置文件同级

- pak 命名规则：{包名}-Android_ASTCClient.pak，平台后缀为 ASTCClient（Android 纹理格式）

- 见原截图（共4张：apk 解压目录、main.obb 解压后 Paks 目录、IDE 编译配置、Crypto.json 位置）

