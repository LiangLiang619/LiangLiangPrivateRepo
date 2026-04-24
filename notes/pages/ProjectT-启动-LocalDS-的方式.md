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

![图片](https://prod-files-secure.s3.us-west-2.amazonaws.com/54c5f1d3-510d-815b-99f0-0003f4ecef71/26dee5ac-e366-4b8d-bbbe-f5a4f83535a0/projectt-localds-step1-v2.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466V5BZFIES%2F20260424%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260424T101358Z&X-Amz-Expires=3600&X-Amz-Security-Token=IQoJb3JpZ2luX2VjELL%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJIMEYCIQCtPKVVQZ%2B%2F5O%2F3li3Hkh6MVOMUZlRZTrRyvVimzIHXWgIhAPsXfsVQQJJ%2BmGjL9626Yo7az9tMmSTG7X2RF1ulswL0Kv8DCHsQABoMNjM3NDIzMTgzODA1Igy4BXzwfXl6CkV01Q0q3AM%2FSdrgpe9NFuPnfTFTcZgbQ1iq7cbKxXX4Me9yYG6yleyAp9Uhbdd1THoTP6bnwq48x5MQqeBpiPac5%2BJ86ENpkNUScg1JcnyzBnXpPFtC1WthWxiz%2B%2Fo1N%2B2z9bDs4SsKrCERLW8E4uaqOIB%2FF69QTerEt3ks6aCYP7SzkGz93AkFSsWargLQZ1JnEPy4JPMW44lmEGqcXTVohmF2240FlAcEEsAlAYa1hfzBJBHeDh%2FGQbuzQcwVa7Xl%2FcqlYEaljjRZ9ZdgEF8anvN03dP1Kjq1VyjFxM3gIq4L%2BifUbJkkPHXkM6aDGUWv03SlrR0SvinyvDpgxtLr%2BCPZsWPBUE4NiUvN30DkWOmDmJkmeux660wshz1gfwXesKEOQudsHs%2Fe7tgeS57Vryb%2BKlqpB3m1qUecy6VwUo4OrALrg9iQVt0g0rJvz39GiBUonizLW82b1uzaPG5zMS0lTItzZs%2BJNxq4foSMKwxG%2F7TRu4d1Oy%2F7t%2Bbt%2B86ldSIBRHsarDHs9GIw6aDWXvNDwk4qfuU2ccX4Pwu5pDhJo7PZszAL33dVeA7bmXOqxPW%2Fltg6Emrm8I0XJXeimGAl8IEzXXwHIQVCcmP5%2FzsXE8XiOvDcP8K7ZUA3WEH7QDDn8qzPBjqkAe%2BwDJ9W0fJqrUgXVb%2BVNaDB6IFg7yBOyxJNDVUN%2Frs2tCbgyJ4c8cc654YyI4wTMw6LPWRGhYbOrk%2FbpFfyO1RPp9XaxLzUM6X28Gj%2F%2Ffol2iU5CwScPzd%2Fw76zbN8s1AS9c2zAwcnGnN0Fe9Uk0RVmACTEiR8%2FGarVH7IL5C9%2F6zoB0Bl0Ki9QxOEYkjxZS1wsv5z5Ubcvfk0ANySKyLHRSq0J&X-Amz-Signature=4ce735ea334d8c1385591ff7c0a6dbd9e60173f1173a55a18a6d26eaaeec06c6&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)

**截图2：游戏内调试面板 — 设置 LocalDSMapID 并点击连接**

![图片](https://prod-files-secure.s3.us-west-2.amazonaws.com/54c5f1d3-510d-815b-99f0-0003f4ecef71/dfa8ce28-1fd3-42fb-beb2-4b1f36e40062/projectt-localds-step2-v2.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466V5BZFIES%2F20260424%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260424T101358Z&X-Amz-Expires=3600&X-Amz-Security-Token=IQoJb3JpZ2luX2VjELL%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJIMEYCIQCtPKVVQZ%2B%2F5O%2F3li3Hkh6MVOMUZlRZTrRyvVimzIHXWgIhAPsXfsVQQJJ%2BmGjL9626Yo7az9tMmSTG7X2RF1ulswL0Kv8DCHsQABoMNjM3NDIzMTgzODA1Igy4BXzwfXl6CkV01Q0q3AM%2FSdrgpe9NFuPnfTFTcZgbQ1iq7cbKxXX4Me9yYG6yleyAp9Uhbdd1THoTP6bnwq48x5MQqeBpiPac5%2BJ86ENpkNUScg1JcnyzBnXpPFtC1WthWxiz%2B%2Fo1N%2B2z9bDs4SsKrCERLW8E4uaqOIB%2FF69QTerEt3ks6aCYP7SzkGz93AkFSsWargLQZ1JnEPy4JPMW44lmEGqcXTVohmF2240FlAcEEsAlAYa1hfzBJBHeDh%2FGQbuzQcwVa7Xl%2FcqlYEaljjRZ9ZdgEF8anvN03dP1Kjq1VyjFxM3gIq4L%2BifUbJkkPHXkM6aDGUWv03SlrR0SvinyvDpgxtLr%2BCPZsWPBUE4NiUvN30DkWOmDmJkmeux660wshz1gfwXesKEOQudsHs%2Fe7tgeS57Vryb%2BKlqpB3m1qUecy6VwUo4OrALrg9iQVt0g0rJvz39GiBUonizLW82b1uzaPG5zMS0lTItzZs%2BJNxq4foSMKwxG%2F7TRu4d1Oy%2F7t%2Bbt%2B86ldSIBRHsarDHs9GIw6aDWXvNDwk4qfuU2ccX4Pwu5pDhJo7PZszAL33dVeA7bmXOqxPW%2Fltg6Emrm8I0XJXeimGAl8IEzXXwHIQVCcmP5%2FzsXE8XiOvDcP8K7ZUA3WEH7QDDn8qzPBjqkAe%2BwDJ9W0fJqrUgXVb%2BVNaDB6IFg7yBOyxJNDVUN%2Frs2tCbgyJ4c8cc654YyI4wTMw6LPWRGhYbOrk%2FbpFfyO1RPp9XaxLzUM6X28Gj%2F%2Ffol2iU5CwScPzd%2Fw76zbN8s1AS9c2zAwcnGnN0Fe9Uk0RVmACTEiR8%2FGarVH7IL5C9%2F6zoB0Bl0Ki9QxOEYkjxZS1wsv5z5Ubcvfk0ANySKyLHRSq0J&X-Amz-Signature=7a2c761f920379fa8ede3d5bafcc7d8c502776e081c9b12f296d34cba6fea17c&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)

