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

![图片](https://prod-files-secure.s3.us-west-2.amazonaws.com/54c5f1d3-510d-815b-99f0-0003f4ecef71/26dee5ac-e366-4b8d-bbbe-f5a4f83535a0/projectt-localds-step1-v2.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466UZAS67UH%2F20260507%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260507T080311Z&X-Amz-Expires=3600&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEOf%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJIMEYCIQDYMqYgyYwVX9msfWgWy7eg1mXIkg0VxPQtbbHTp9K0agIhAKm5YJ24g8MuHIXJpM%2FjJjwYTjBZ78GGCqGfJ8sX2xduKogECLD%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEQABoMNjM3NDIzMTgzODA1IgyTpAc%2F%2FtgIBOGgtDMq3ANn7ykYLuWS1PXvR7BJiT8df0hlW2F1vnonJgqN5XVnFUhv4%2BEhnAgWM3RoKku8mqw4hJ2ABr6bGu1OtJYfU%2FQMRdtKUqCCRn7u8Qtb0RIDMnGuUa0ENkmIYakOT9rV%2B8FAhma8Wx%2BDHpUR%2B1ZUvfCMWcJsK7QlVGiYOfzVSKsxmEMRAAn393XHaqEJnqAuHdKzlQy8pbvUb8D6985NS%2FDDHdOHGGnjGO47ffECqEv2JWrRLCp4isZu9cqQk%2BqM%2BKGi5gzFUS4Hiz5tF3ieslsbExrKtbuTiOBJwFWB4Em9V688Bcf7jht7UzYP7S1DnqFuE07UCUk6GdYTj6rSk9KbnSCLXRHpLSdUJkq0ZZpZ3mjE%2BY3a1JPzGmrYzviO8gOhGpwKC61zCHfmIN%2BH6h9d9TCBkH6NBvdcdKC5ERYafVhM9oA9Rm47sau7I9k5cEL8OelAa%2B8q1es%2FlwfKhRkmtX6E3u7gwP3RI3RHiE%2BOWvzuqfmNy0hBcKuqf2hQ%2FQj%2Fnv6xweVcRMrUQMuWdji8eFkyQBmjXYz4%2F1Mt%2B00ls3g1An52gg88fLahW6otXPMBE3gb%2BAx6oNLWa5%2BR9VLN3N%2BnAayu%2FMT%2BrZhg80YJDVCnCkkYA9Hdzd8TZDCW7fDPBjqkARuogmnpiEj%2FMz5FOqq8suozGCnPbHNjH6hyYpLASGwZewzUYCr6oDLIz9ipxQ3yovbGhlDxlaNDb8fVUGkZmV7qf4rnSzwr7Eu1M5kpvKgkaR5Okt1OKHJkKjIPnkZn5jZFSUE0gFtq7J2LYdAEWezZVLVcdQ5n9x1aZHF%2F5%2FKBChpWeigpnALClwI8vy37ASyf2lWv5YkC4Ezc7CiO1pGcBmLc&X-Amz-Signature=00b891e5d2e3e8e460291ce767177840f6adee6cdb675c16ad02f1151580260d&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)

**截图2：游戏内调试面板 — 设置 LocalDSMapID 并点击连接**

![图片](https://prod-files-secure.s3.us-west-2.amazonaws.com/54c5f1d3-510d-815b-99f0-0003f4ecef71/dfa8ce28-1fd3-42fb-beb2-4b1f36e40062/projectt-localds-step2-v2.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466UZAS67UH%2F20260507%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260507T080311Z&X-Amz-Expires=3600&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEOf%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJIMEYCIQDYMqYgyYwVX9msfWgWy7eg1mXIkg0VxPQtbbHTp9K0agIhAKm5YJ24g8MuHIXJpM%2FjJjwYTjBZ78GGCqGfJ8sX2xduKogECLD%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEQABoMNjM3NDIzMTgzODA1IgyTpAc%2F%2FtgIBOGgtDMq3ANn7ykYLuWS1PXvR7BJiT8df0hlW2F1vnonJgqN5XVnFUhv4%2BEhnAgWM3RoKku8mqw4hJ2ABr6bGu1OtJYfU%2FQMRdtKUqCCRn7u8Qtb0RIDMnGuUa0ENkmIYakOT9rV%2B8FAhma8Wx%2BDHpUR%2B1ZUvfCMWcJsK7QlVGiYOfzVSKsxmEMRAAn393XHaqEJnqAuHdKzlQy8pbvUb8D6985NS%2FDDHdOHGGnjGO47ffECqEv2JWrRLCp4isZu9cqQk%2BqM%2BKGi5gzFUS4Hiz5tF3ieslsbExrKtbuTiOBJwFWB4Em9V688Bcf7jht7UzYP7S1DnqFuE07UCUk6GdYTj6rSk9KbnSCLXRHpLSdUJkq0ZZpZ3mjE%2BY3a1JPzGmrYzviO8gOhGpwKC61zCHfmIN%2BH6h9d9TCBkH6NBvdcdKC5ERYafVhM9oA9Rm47sau7I9k5cEL8OelAa%2B8q1es%2FlwfKhRkmtX6E3u7gwP3RI3RHiE%2BOWvzuqfmNy0hBcKuqf2hQ%2FQj%2Fnv6xweVcRMrUQMuWdji8eFkyQBmjXYz4%2F1Mt%2B00ls3g1An52gg88fLahW6otXPMBE3gb%2BAx6oNLWa5%2BR9VLN3N%2BnAayu%2FMT%2BrZhg80YJDVCnCkkYA9Hdzd8TZDCW7fDPBjqkARuogmnpiEj%2FMz5FOqq8suozGCnPbHNjH6hyYpLASGwZewzUYCr6oDLIz9ipxQ3yovbGhlDxlaNDb8fVUGkZmV7qf4rnSzwr7Eu1M5kpvKgkaR5Okt1OKHJkKjIPnkZn5jZFSUE0gFtq7J2LYdAEWezZVLVcdQ5n9x1aZHF%2F5%2FKBChpWeigpnALClwI8vy37ASyf2lWv5YkC4Ezc7CiO1pGcBmLc&X-Amz-Signature=480ed7a0af287077ec7fd75237a5a14e8fa0700f5645179611db1fb45127a9d5&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)

