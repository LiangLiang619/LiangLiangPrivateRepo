---
title: "手机端强制Mount Pak文件"
category: "游戏开发"
tags:
  - "Lua"
  - "UE5"
  - "热更"
source: "工作"
importance: 1
importance_label: "⭐️⭐️ 重要"
summary: "通过Lua在iOS手机端强制挂载pak文件，使用GetPhysicalFullPathVer获取持久化下载目录并调用UPakMountManager.Mount"
created: 2026-04-24
updated: 2026-04-24
notion_url: "https://www.notion.so/Mount-Pak-34c5f1d3510d81f38153cf46a91e8691"
---

# 手机端强制Mount Pak文件

> **分类**：游戏开发 | **来源**：工作 | **重要程度**：⭐️⭐️ 重要
>
> 通过Lua在iOS手机端强制挂载pak文件，使用GetPhysicalFullPathVer获取持久化下载目录并调用UPakMountManager.Mount

在手机包上强行 mount pak 文件的方法。以下示例为 pak 位于 iOS 手机塞文件的根目录（PersistentDownloadDir）。

核心流程：

- 通过 FMoeDolphinManager:GetPhysicalFullPathVer() 获取实际物理路径

- UBlueprintPathsLibrary.ProjectPersistentDownloadDir() 获取持久化下载目录

- 拼接 pak 文件名得到完整路径

- 调用 UPakMountManager.Mount(pak_path, mount_order) 挂载

示例代码：

`local function mount_pak(pak_file_name, mount_order)
    local download_dir = UE4.FMoeDolphinManager.GetInstance():GetPhysicalFullPathVer(
        UE4.UBlueprintPathsLibrary.ProjectPersistentDownloadDir()
    )
    local pak_path = string.format("%s/%s", download_dir, pak_file_name)
    UE4.UPakMountManager.Mount(pak_path, mount_order)
end

mount_pak("YourAsset.pak", 0)`

注意事项：

- mount_order 决定 pak 的优先级，值越小优先级越高

- GetPhysicalFullPathVer 是项目自定义的路径解析方法，将虚拟路径转为真实物理路径

- 确保 pak 文件已存在于设备的 PersistentDownloadDir 目录下





