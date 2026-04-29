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
notion_url: "https://app.notion.com/p/ProjectT-LocalDS-34a5f1d3510d81dd965ac78acdd60836"
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

![图片](https://prod-files-secure.s3.us-west-2.amazonaws.com/54c5f1d3-510d-815b-99f0-0003f4ecef71/26dee5ac-e366-4b8d-bbbe-f5a4f83535a0/projectt-localds-step1-v2.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466RLUQ7EKG%2F20260429%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260429T100044Z&X-Amz-Expires=3600&X-Amz-Security-Token=IQoJb3JpZ2luX2VjECoaCXVzLXdlc3QtMiJGMEQCIH81h4%2F7YCI54Sgbf3u7mTZbks80DlDVRO6e5sItpf18AiBk6sSmDrHn22x9qnQUE5LTQIsToFsfjiuLQByxHt90EyqIBAjz%2F%2F%2F%2F%2F%2F%2F%2F%2F%2F8BEAAaDDYzNzQyMzE4MzgwNSIMchiR68WHEXaeji1bKtwDtIHgkfDQd%2FS7ZqwowBxd05cr6W0NjpvYlWXOQsDuU2pMDVznFsn5RQWmRZWww5FixoAUpKVkFQDUa7baT8aZv1Oh4cQre%2BAFbC57%2BmHnm0Zq2LDeEfu%2Fm1unp45GkkUzI38Cux604qPa0ITkwkPgcIwmLD4S7YDwh%2FenBgK7g%2F3ayjoIUecsQt81iZ9ceH7C6%2BDrrVpkym1CHq8kO62TZf3jNqp3E3NiCjyzEVXYTdMZDy1WT%2F14nNNI1YqHGo9eJynpl%2FI5H2l%2BTmyjtOcMWPsIXmFvIOVl2iQNrBXVgofyrQHPo2Kt6XJgSxkYEYhP3AtuFSR6vtzqXZDav35bC3Zmc%2BVqTEjZgfvjfyU5kZef0nxGltxLh4QrwuEK5UgI36oEvTcgD1%2Brn19e1tPzLcChnV%2B2Z91mtsP3g9LymWzLuxKrz%2BVlDuQ478chUVYowyQHDOjzMkfay0nIKpBeck08uVWvFrQQrv%2Fe%2FsqB13oZt6FwhitBwklkmll2nV0cyaGmAMS7uGbV9XaCWYlyRBk43pUVofBw5ggTOJ2A7fF84vb6Qlwk1RJFZu67JeGYIbRB87Pk64pvnRTv%2FT%2BBCYShzG%2Btsv4OwiFFDB1Hqp0GBKgVd4k%2FGq9Bg1Ew0qjHzwY6pgHLqVv%2FhjUtMNfAmkAgm6F%2BKZtjfx7Jet4lYGp1b9S0lsuhanrpDdZojExvZ549O8oMRJRBMhxkWd71i8sjmkuHJ8%2BlPD5enKhNJM%2FH1MzweQD4t0V0UlmaLWIGKIJN3%2FZJ%2Be%2BAmZvhh53tNMKfjH2M6KstE38HfgrjPQTZwPwsnPKE%2FjJR3hvz%2BKnfEj3M1hANvrwsvQgYglJifq25f8Z%2Fg%2Bn%2FQ3Ia&X-Amz-Signature=6de6706fffdbd85545da47f3d96f206ae25b7221ddba1c4390b497509e980606&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)

**截图2：游戏内调试面板 — 设置 LocalDSMapID 并点击连接**

![图片](https://prod-files-secure.s3.us-west-2.amazonaws.com/54c5f1d3-510d-815b-99f0-0003f4ecef71/dfa8ce28-1fd3-42fb-beb2-4b1f36e40062/projectt-localds-step2-v2.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466RLUQ7EKG%2F20260429%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260429T100044Z&X-Amz-Expires=3600&X-Amz-Security-Token=IQoJb3JpZ2luX2VjECoaCXVzLXdlc3QtMiJGMEQCIH81h4%2F7YCI54Sgbf3u7mTZbks80DlDVRO6e5sItpf18AiBk6sSmDrHn22x9qnQUE5LTQIsToFsfjiuLQByxHt90EyqIBAjz%2F%2F%2F%2F%2F%2F%2F%2F%2F%2F8BEAAaDDYzNzQyMzE4MzgwNSIMchiR68WHEXaeji1bKtwDtIHgkfDQd%2FS7ZqwowBxd05cr6W0NjpvYlWXOQsDuU2pMDVznFsn5RQWmRZWww5FixoAUpKVkFQDUa7baT8aZv1Oh4cQre%2BAFbC57%2BmHnm0Zq2LDeEfu%2Fm1unp45GkkUzI38Cux604qPa0ITkwkPgcIwmLD4S7YDwh%2FenBgK7g%2F3ayjoIUecsQt81iZ9ceH7C6%2BDrrVpkym1CHq8kO62TZf3jNqp3E3NiCjyzEVXYTdMZDy1WT%2F14nNNI1YqHGo9eJynpl%2FI5H2l%2BTmyjtOcMWPsIXmFvIOVl2iQNrBXVgofyrQHPo2Kt6XJgSxkYEYhP3AtuFSR6vtzqXZDav35bC3Zmc%2BVqTEjZgfvjfyU5kZef0nxGltxLh4QrwuEK5UgI36oEvTcgD1%2Brn19e1tPzLcChnV%2B2Z91mtsP3g9LymWzLuxKrz%2BVlDuQ478chUVYowyQHDOjzMkfay0nIKpBeck08uVWvFrQQrv%2Fe%2FsqB13oZt6FwhitBwklkmll2nV0cyaGmAMS7uGbV9XaCWYlyRBk43pUVofBw5ggTOJ2A7fF84vb6Qlwk1RJFZu67JeGYIbRB87Pk64pvnRTv%2FT%2BBCYShzG%2Btsv4OwiFFDB1Hqp0GBKgVd4k%2FGq9Bg1Ew0qjHzwY6pgHLqVv%2FhjUtMNfAmkAgm6F%2BKZtjfx7Jet4lYGp1b9S0lsuhanrpDdZojExvZ549O8oMRJRBMhxkWd71i8sjmkuHJ8%2BlPD5enKhNJM%2FH1MzweQD4t0V0UlmaLWIGKIJN3%2FZJ%2Be%2BAmZvhh53tNMKfjH2M6KstE38HfgrjPQTZwPwsnPKE%2FjJR3hvz%2BKnfEj3M1hANvrwsvQgYglJifq25f8Z%2Fg%2Bn%2FQ3Ia&X-Amz-Signature=a3e63cf258ee6963286944cb53c4b76b8f95b4832727dc6521846f9e6a1b56aa&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)

