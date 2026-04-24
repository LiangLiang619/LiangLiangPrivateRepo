---
title: "ProjectT 启动 LocalDS 的方式"
category: "游戏开发"
tags:
  - "UE5"
source: "工作"
importance: 1
importance_label: "⭐️⭐️⭐️ 必掌握"
summary: "启动器资产名：FarmLocalDSTool。分两步：①FarmLocalDSTool 选 ProjectT 填私服配置 Start；② 游戏内调试面板设 LocalDSMapID 后点连接。"
created: 2026-04-22
updated: 2026-04-22
notion_url: "https://www.notion.so/ProjectT-LocalDS-34a5f1d3510d81dd965ac78acdd60836"
---

# ProjectT 启动 LocalDS 的方式

> **分类**：游戏开发 | **来源**：工作 | **重要程度**：⭐️⭐️⭐️ 必掌握
>
> 启动器资产名：FarmLocalDSTool。分两步：①FarmLocalDSTool 选 ProjectT 填私服配置 Start；② 游戏内调试面板设 LocalDSMapID 后点连接。

## 📌 核心信息

- 启动器资产名：FarmLocalDSTool

- 用于本地启动 ProjectT 专属 DS（Dedicated Server）

## 🚀 步骤一：FarmLocalDSTool 配置界面

1. 打开 FarmLocalDSTool 启动器

1. 「选择玩法」勾选 ☑ ProjectT

1. 填写私服 IP（示例：9.134.130.41），右侧下拉选 sk_projectt

1. 填写 Token ID 和 Token Name（示例：141 / junrongyu）

1. 点击「Start」按钮启动 LocalDS

## 🎮 步骤二：游戏内调试面板连接

1. 进入游戏后打开内部调试面板

1. Category 选 Feature，Server 选对应服（示例：vmiaochen）

1. 设置 LocalDSMapID（示例：1）

1. 勾选「大厅单机」（如需单机模式）

1. 点击「连接」按钮

## ⚠️ 注意事项

- 必须先 Start LocalDS，再在游戏内点连接，顺序不能颠倒

- 私服 IP / Token / Server 根据当前测试环境填写，不固定

- 调试面板中版本号前的复选框需勾选才会生效

## 📸 参考截图

**截图1：FarmLocalDSTool 启动器 — 选择 ProjectT 玩法并填写私服配置**

![图片](https://prod-files-secure.s3.us-west-2.amazonaws.com/54c5f1d3-510d-815b-99f0-0003f4ecef71/26dee5ac-e366-4b8d-bbbe-f5a4f83535a0/projectt-localds-step1-v2.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466TW4EKIKD%2F20260424%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260424T105522Z&X-Amz-Expires=3600&X-Amz-Security-Token=IQoJb3JpZ2luX2VjELP%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIQC5ZY1DsmnzYii4MdX1ogiJwwTbY%2F5LENcKZ8wxkhXAKAIgNA72SAa2T1lY7z%2BsLKzfAXNWbPp68xRy9w5Tm584gJUq%2FwMIfBAAGgw2Mzc0MjMxODM4MDUiDGuRn4PCKRNcMQPlMyrcA9k8MCilHkeEVQJCuSDEGPcG9oWCOIH1R0dS8NCOtTOkVqEJyfWXaKMsfJia1EUhX7r7QWswWTEtt6%2F2w5TVzH5O1DdIFU0gsNK9TaJCKK43UzwRCIFt8E9lgw3P8RbhxmYaKzb78HdtK9cnaUAGRH5gTqINmgc7snNYVsykoMS2pHJAC40B2RbMAJpMs30VhGL8tJjpUBPNQurjt29s6RgSpjKptxbkDROFKQZBZOSBEHhH8J2V2X2vMKF9niUYrSUjWaUKj81HtswK0xuPaU6%2FPj2fcylZzfHyORO3ofTsfX%2Fyx8VYZvjVTVvH%2F0ofZastQP8yy8BgB0OW1gojDIPulXPDNcEGSwWyOwS83R0zo3RBY38w8cdJwby8D3b0w%2F6E2wC6dOQKuKnWpS1gxqdm7xIv9wYYKGeojxWWsq4Pdz2wQjG%2FsB%2Fm5%2BjqeypB9ndToo7ibODHJc14KilbAWwTCy4Ov70n6V%2FrcjE%2BiY2GY47UP6u83bKm3k3jTopOKpdkoAGjF3zYQ%2Bf0qYYyA64%2FEUURssj2KFXSPRUUhO%2F1wSH8OUFSImK0%2BQ3TOeHR6VSQ%2FmaIDWDFBdzmixUdJOLRKzU1oV8tUtnBOVUKP8oyby9Nu%2Ftwuc85EZMXMJqPrc8GOqUBmV4pGX5ScEk6vWMMMMn7dVfSqaPGer8aeQPn%2Fcjr2l%2F0uvlEmSe42tMLgRU599U591A1VQYTCFwxTZ41chrf8mTXoH9BBK7V76vO%2BfxnrzCyDxdVEgRD11z%2FilTskKyv1fploNONR4Q7HqcrE%2BLJX5LreBsZ6LOF1US%2F5HXYIlceU31fjPfSmGY3knPKXP4jRi2BgXTSW0w6GvK1GKvrYcW85Iq0&X-Amz-Signature=26516c55ee793faa06e91078b276df90cf95444472902c7d6515b061a151978f&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)

**截图2：游戏内调试面板 — 设置 LocalDSMapID 并点击连接**

![图片](https://prod-files-secure.s3.us-west-2.amazonaws.com/54c5f1d3-510d-815b-99f0-0003f4ecef71/dfa8ce28-1fd3-42fb-beb2-4b1f36e40062/projectt-localds-step2-v2.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466TW4EKIKD%2F20260424%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260424T105522Z&X-Amz-Expires=3600&X-Amz-Security-Token=IQoJb3JpZ2luX2VjELP%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIQC5ZY1DsmnzYii4MdX1ogiJwwTbY%2F5LENcKZ8wxkhXAKAIgNA72SAa2T1lY7z%2BsLKzfAXNWbPp68xRy9w5Tm584gJUq%2FwMIfBAAGgw2Mzc0MjMxODM4MDUiDGuRn4PCKRNcMQPlMyrcA9k8MCilHkeEVQJCuSDEGPcG9oWCOIH1R0dS8NCOtTOkVqEJyfWXaKMsfJia1EUhX7r7QWswWTEtt6%2F2w5TVzH5O1DdIFU0gsNK9TaJCKK43UzwRCIFt8E9lgw3P8RbhxmYaKzb78HdtK9cnaUAGRH5gTqINmgc7snNYVsykoMS2pHJAC40B2RbMAJpMs30VhGL8tJjpUBPNQurjt29s6RgSpjKptxbkDROFKQZBZOSBEHhH8J2V2X2vMKF9niUYrSUjWaUKj81HtswK0xuPaU6%2FPj2fcylZzfHyORO3ofTsfX%2Fyx8VYZvjVTVvH%2F0ofZastQP8yy8BgB0OW1gojDIPulXPDNcEGSwWyOwS83R0zo3RBY38w8cdJwby8D3b0w%2F6E2wC6dOQKuKnWpS1gxqdm7xIv9wYYKGeojxWWsq4Pdz2wQjG%2FsB%2Fm5%2BjqeypB9ndToo7ibODHJc14KilbAWwTCy4Ov70n6V%2FrcjE%2BiY2GY47UP6u83bKm3k3jTopOKpdkoAGjF3zYQ%2Bf0qYYyA64%2FEUURssj2KFXSPRUUhO%2F1wSH8OUFSImK0%2BQ3TOeHR6VSQ%2FmaIDWDFBdzmixUdJOLRKzU1oV8tUtnBOVUKP8oyby9Nu%2Ftwuc85EZMXMJqPrc8GOqUBmV4pGX5ScEk6vWMMMMn7dVfSqaPGer8aeQPn%2Fcjr2l%2F0uvlEmSe42tMLgRU599U591A1VQYTCFwxTZ41chrf8mTXoH9BBK7V76vO%2BfxnrzCyDxdVEgRD11z%2FilTskKyv1fploNONR4Q7HqcrE%2BLJX5LreBsZ6LOF1US%2F5HXYIlceU31fjPfSmGY3knPKXP4jRi2BgXTSW0w6GvK1GKvrYcW85Iq0&X-Amz-Signature=028e8c28285fb86f35044a8ef5d1065d4a9da1b66457bbcc0398f891e77a2ce4&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)

