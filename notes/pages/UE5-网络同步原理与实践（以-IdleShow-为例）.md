---
title: "UE5 网络同步原理与实践（以 IdleShow 为例）"
category: "游戏开发"
tags:
  - "UE5"
  - "Lua"
  - "网络"
source: "工作"
importance: 1
importance_label: "⭐️⭐️⭐️ 必掌握"
summary: "UE5 网络同步核心概念：主控端/模拟端、需要同步的数据类型、FMoeActionStateDataProxy 结构体、OnRep 机制、组件复制前提，以及 IdleShow 随机数同步完整流程。"
created: 2026-04-22
updated: 2026-04-22
notion_url: "https://www.notion.so/UE5-IdleShow-34a5f1d3510d8100829bf32b670b613a"
---

# UE5 网络同步原理与实践（以 IdleShow 为例）

> **分类**：游戏开发 | **来源**：工作 | **重要程度**：⭐️⭐️⭐️ 必掌握
>
> UE5 网络同步核心概念：主控端/模拟端、需要同步的数据类型、FMoeActionStateDataProxy 结构体、OnRep 机制、组件复制前提，以及 IdleShow 随机数同步完整流程。

## 1️⃣ 核心概念：主控端 vs 模拟端

- 主控端：玩家当前操控的角色，拥有第一手数据

- 模拟端：其他玩家角色，通过网络同步数据模拟行为

> 💡 主控端和模拟端逻辑完全相同时，无需额外同步。只有主控端独有的数据（随机数、开关状态等）才需要上传 DS 同步。

---

## 2️⃣ 哪些数据需要同步？

### ✅ 自动同步（无需处理）

- Avatar Info 等角色相关信息 — 框架层已处理

### ⚠️ 需要手动同步

- 随机数：各端独立生成结果不同，必须将主控端结果上传 DS 广播

- 角色自控开关：如「开关自己的环绕物」，只有主控端有此数据，其他端无法感知

---

## 3️⃣ 同步机制：数据结构体

### FMoeActionStateDataProxy（MoeStateBase.h）

- SyncDataFactory：类型 FMoeStateSyncDataProxy，Transient（不序列化）— 存储和管理状态同步数据

- SyncActor：类型 AActor*，初始化为 nullptr — 指向需要同步的 Actor

截图：结构体定义

![图片](https://prod-files-secure.s3.us-west-2.amazonaws.com/54c5f1d3-510d-815b-99f0-0003f4ecef71/4344ed5a-2b22-4293-b299-12da8c5ea3ee/net-sync-04-FMoeActionStateDataProxy.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466R2ABIWL6%2F20260424%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260424T101353Z&X-Amz-Expires=3600&X-Amz-Security-Token=IQoJb3JpZ2luX2VjELL%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJIMEYCIQC4wYyhwP6tSW9jGiJPOxe511nCAqO9pWQej9JuHUxR5QIhAKWeyUlEw%2BlUNW%2BP2zTS%2FVio2aHbcVZYC5mI5mKdLoFOKv8DCHsQABoMNjM3NDIzMTgzODA1IgwvKwX%2FlImACsHkhLMq3AP34ui%2FJ%2BvZy4GFNeQ9GVbY0Pj%2Fb6wSIp2eC%2BrheJXyCva5WdlMTjbssdhl%2FYue8%2BSTL8eW8GTYXY8hpWUwGMH7B%2FD2o257NnZyhUV6wml4q5ghN25syUVEEQkb%2FOGKYW37n0VmNy4PQWXrH76Cqbdx8rDrSQDc98HkNV4x%2Fzbb5hF8L86rmf3ESpVi1hfqjwQuZrOUJjDJXRpnPdwahADOCQ3E3avc8i%2BAsjXHbXvXUECt4iWGC1CNR7FaXJClA3KkgIUxeMt6gvENdlVp0FMRbqgSFBT3c0DwJY%2FEVKrsJLmkfsdT8gAmTeSiyra9Y%2Bo2QzpqmBgbBymRek3JxUPlxJ0bbqVJbgylrIZ%2Fgv6hwDmIGGvKER0K%2BLijbH9oPNX9kPkdGqF%2BCvyfgtwfY77UB%2FGoDLsuWKaYOQD4vRJyl0Gi2Dcn70iXSTHqSu4OM6cn4%2B6I%2Br6rQT%2BAQkIGYEqPGQmezSTm3Up7id47RvkLZSTYK7niZN%2BnVpV0osMByJIa5FXflLe3oyjIPea61w8xCMwj3%2FmQO8Huqp%2FKdK5JFMvS6kWe8E4VOy32rpIIeieAyNp2ZoRkGq4Wt1HR8iQqmk8ETB6hSK49PQYlUYt2YZIcHuDhQI4XHIDS4TDC7azPBjqkAWY%2BpZg%2FmKnUKgV1FZ2%2FtKFz6udrCzDKff1fIfVwDvA7kzodiefG%2F3qG6UKwLjrmQZLjPR7Cq6dy45LnGAaHuAFPgpoOasCEjdFdW7JRdzRIPTjGznU%2BKeiBMkm3rMxWFPItZ%2B7SYhbm2%2BmPghvbjgTvXfYG7tKTyfKt1JukXlKoB%2BpSilPw3ihXgxj9jXOxjJjpqY%2B6aaFQNgjJbQ%2FGYvLgjrYQ&X-Amz-Signature=3e75a1585d3bb9c34e221cd04ad5659b64935ffba0e9284c5b0316234a975e79&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)

### 读写 API（以 Bool 为例）

```c++
// 写入
void AddOrSetSyncDataBool(FString& keyName, bool& value, FMoeStateSyncDataProxy& SyncDataProxy)
{
    SyncDataProxy.AddOrSetSyncDataItem<bool>(keyName, value);
}

// 读取
bool GetSyncDataBool(FString& keyName, const FMoeStateSyncDataProxy& SyncDataProxy)
{
    return SyncDataProxy.GetValue<bool>(keyName);
}
```

截图：AddOrSetSyncDataBool / GetSyncDataBool

![图片](https://prod-files-secure.s3.us-west-2.amazonaws.com/54c5f1d3-510d-815b-99f0-0003f4ecef71/59b1fcd1-5e60-4aaf-a675-aa68f4c84869/net-sync-05-addbool-getbool.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466R2ABIWL6%2F20260424%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260424T101353Z&X-Amz-Expires=3600&X-Amz-Security-Token=IQoJb3JpZ2luX2VjELL%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJIMEYCIQC4wYyhwP6tSW9jGiJPOxe511nCAqO9pWQej9JuHUxR5QIhAKWeyUlEw%2BlUNW%2BP2zTS%2FVio2aHbcVZYC5mI5mKdLoFOKv8DCHsQABoMNjM3NDIzMTgzODA1IgwvKwX%2FlImACsHkhLMq3AP34ui%2FJ%2BvZy4GFNeQ9GVbY0Pj%2Fb6wSIp2eC%2BrheJXyCva5WdlMTjbssdhl%2FYue8%2BSTL8eW8GTYXY8hpWUwGMH7B%2FD2o257NnZyhUV6wml4q5ghN25syUVEEQkb%2FOGKYW37n0VmNy4PQWXrH76Cqbdx8rDrSQDc98HkNV4x%2Fzbb5hF8L86rmf3ESpVi1hfqjwQuZrOUJjDJXRpnPdwahADOCQ3E3avc8i%2BAsjXHbXvXUECt4iWGC1CNR7FaXJClA3KkgIUxeMt6gvENdlVp0FMRbqgSFBT3c0DwJY%2FEVKrsJLmkfsdT8gAmTeSiyra9Y%2Bo2QzpqmBgbBymRek3JxUPlxJ0bbqVJbgylrIZ%2Fgv6hwDmIGGvKER0K%2BLijbH9oPNX9kPkdGqF%2BCvyfgtwfY77UB%2FGoDLsuWKaYOQD4vRJyl0Gi2Dcn70iXSTHqSu4OM6cn4%2B6I%2Br6rQT%2BAQkIGYEqPGQmezSTm3Up7id47RvkLZSTYK7niZN%2BnVpV0osMByJIa5FXflLe3oyjIPea61w8xCMwj3%2FmQO8Huqp%2FKdK5JFMvS6kWe8E4VOy32rpIIeieAyNp2ZoRkGq4Wt1HR8iQqmk8ETB6hSK49PQYlUYt2YZIcHuDhQI4XHIDS4TDC7azPBjqkAWY%2BpZg%2FmKnUKgV1FZ2%2FtKFz6udrCzDKff1fIfVwDvA7kzodiefG%2F3qG6UKwLjrmQZLjPR7Cq6dy45LnGAaHuAFPgpoOasCEjdFdW7JRdzRIPTjGznU%2BKeiBMkm3rMxWFPItZ%2B7SYhbm2%2BmPghvbjgTvXfYG7tKTyfKt1JukXlKoB%2BpSilPw3ihXgxj9jXOxjJjpqY%2B6aaFQNgjJbQ%2FGYvLgjrYQ&X-Amz-Signature=5364cf2bf7e0b6124eb39cc7c8dd68e529ef53bc88fbd0b49e722c7a152a7835&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)

---

## 4️⃣ OnRep 函数（复制通知）

属性从服务器复制到客户端时自动触发，用于响应数值变化（更新 UI、播放特效、同步动画等）。

```c++
// 声明复制属性
UPROPERTY(ReplicatedUsing=OnRep_Health)
int32 Health;

// 定义 OnRep 函数
void AMyCharacter::OnRep_Health() {
    UpdateHUD(); // 更新UI
}
```

截图：OnRep 原理文档

![图片](https://prod-files-secure.s3.us-west-2.amazonaws.com/54c5f1d3-510d-815b-99f0-0003f4ecef71/9da92056-7141-43fa-82ee-66b3745052fe/net-sync-01-onrep.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466R2ABIWL6%2F20260424%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260424T101353Z&X-Amz-Expires=3600&X-Amz-Security-Token=IQoJb3JpZ2luX2VjELL%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJIMEYCIQC4wYyhwP6tSW9jGiJPOxe511nCAqO9pWQej9JuHUxR5QIhAKWeyUlEw%2BlUNW%2BP2zTS%2FVio2aHbcVZYC5mI5mKdLoFOKv8DCHsQABoMNjM3NDIzMTgzODA1IgwvKwX%2FlImACsHkhLMq3AP34ui%2FJ%2BvZy4GFNeQ9GVbY0Pj%2Fb6wSIp2eC%2BrheJXyCva5WdlMTjbssdhl%2FYue8%2BSTL8eW8GTYXY8hpWUwGMH7B%2FD2o257NnZyhUV6wml4q5ghN25syUVEEQkb%2FOGKYW37n0VmNy4PQWXrH76Cqbdx8rDrSQDc98HkNV4x%2Fzbb5hF8L86rmf3ESpVi1hfqjwQuZrOUJjDJXRpnPdwahADOCQ3E3avc8i%2BAsjXHbXvXUECt4iWGC1CNR7FaXJClA3KkgIUxeMt6gvENdlVp0FMRbqgSFBT3c0DwJY%2FEVKrsJLmkfsdT8gAmTeSiyra9Y%2Bo2QzpqmBgbBymRek3JxUPlxJ0bbqVJbgylrIZ%2Fgv6hwDmIGGvKER0K%2BLijbH9oPNX9kPkdGqF%2BCvyfgtwfY77UB%2FGoDLsuWKaYOQD4vRJyl0Gi2Dcn70iXSTHqSu4OM6cn4%2B6I%2Br6rQT%2BAQkIGYEqPGQmezSTm3Up7id47RvkLZSTYK7niZN%2BnVpV0osMByJIa5FXflLe3oyjIPea61w8xCMwj3%2FmQO8Huqp%2FKdK5JFMvS6kWe8E4VOy32rpIIeieAyNp2ZoRkGq4Wt1HR8iQqmk8ETB6hSK49PQYlUYt2YZIcHuDhQI4XHIDS4TDC7azPBjqkAWY%2BpZg%2FmKnUKgV1FZ2%2FtKFz6udrCzDKff1fIfVwDvA7kzodiefG%2F3qG6UKwLjrmQZLjPR7Cq6dy45LnGAaHuAFPgpoOasCEjdFdW7JRdzRIPTjGznU%2BKeiBMkm3rMxWFPItZ%2B7SYhbm2%2BmPghvbjgTvXfYG7tKTyfKt1JukXlKoB%2BpSilPw3ihXgxj9jXOxjJjpqY%2B6aaFQNgjJbQ%2FGYvLgjrYQ&X-Amz-Signature=aeb132f9189f7b697782bff665024c47cd97ac883eb0d73b2c4ca22d76e0f678&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)

---

## 5️⃣ 组件复制是变量复制的前提

> 🚨 组件未调用 SetIsReplicated(true) → 客户端无镜像组件 → 组件内所有变量的 REPLICATED 声明全部失效！

- ✅ 组件已复制 + 变量声明复制 → 完整同步

- ❌ 组件未复制 → 客户端无组件 → 变量复制无效

- ⚠️ 组件已复制 + 变量未声明复制 → 仅同步组件框架（无数据）

截图：组件复制机制说明

![图片](https://prod-files-secure.s3.us-west-2.amazonaws.com/54c5f1d3-510d-815b-99f0-0003f4ecef71/de6ef4b4-219e-4d8b-9f16-064401414420/net-sync-02-component-replication.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466R2ABIWL6%2F20260424%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260424T101353Z&X-Amz-Expires=3600&X-Amz-Security-Token=IQoJb3JpZ2luX2VjELL%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJIMEYCIQC4wYyhwP6tSW9jGiJPOxe511nCAqO9pWQej9JuHUxR5QIhAKWeyUlEw%2BlUNW%2BP2zTS%2FVio2aHbcVZYC5mI5mKdLoFOKv8DCHsQABoMNjM3NDIzMTgzODA1IgwvKwX%2FlImACsHkhLMq3AP34ui%2FJ%2BvZy4GFNeQ9GVbY0Pj%2Fb6wSIp2eC%2BrheJXyCva5WdlMTjbssdhl%2FYue8%2BSTL8eW8GTYXY8hpWUwGMH7B%2FD2o257NnZyhUV6wml4q5ghN25syUVEEQkb%2FOGKYW37n0VmNy4PQWXrH76Cqbdx8rDrSQDc98HkNV4x%2Fzbb5hF8L86rmf3ESpVi1hfqjwQuZrOUJjDJXRpnPdwahADOCQ3E3avc8i%2BAsjXHbXvXUECt4iWGC1CNR7FaXJClA3KkgIUxeMt6gvENdlVp0FMRbqgSFBT3c0DwJY%2FEVKrsJLmkfsdT8gAmTeSiyra9Y%2Bo2QzpqmBgbBymRek3JxUPlxJ0bbqVJbgylrIZ%2Fgv6hwDmIGGvKER0K%2BLijbH9oPNX9kPkdGqF%2BCvyfgtwfY77UB%2FGoDLsuWKaYOQD4vRJyl0Gi2Dcn70iXSTHqSu4OM6cn4%2B6I%2Br6rQT%2BAQkIGYEqPGQmezSTm3Up7id47RvkLZSTYK7niZN%2BnVpV0osMByJIa5FXflLe3oyjIPea61w8xCMwj3%2FmQO8Huqp%2FKdK5JFMvS6kWe8E4VOy32rpIIeieAyNp2ZoRkGq4Wt1HR8iQqmk8ETB6hSK49PQYlUYt2YZIcHuDhQI4XHIDS4TDC7azPBjqkAWY%2BpZg%2FmKnUKgV1FZ2%2FtKFz6udrCzDKff1fIfVwDvA7kzodiefG%2F3qG6UKwLjrmQZLjPR7Cq6dy45LnGAaHuAFPgpoOasCEjdFdW7JRdzRIPTjGznU%2BKeiBMkm3rMxWFPItZ%2B7SYhbm2%2BmPghvbjgTvXfYG7tKTyfKt1JukXlKoB%2BpSilPw3ihXgxj9jXOxjJjpqY%2B6aaFQNgjJbQ%2FGYvLgjrYQ&X-Amz-Signature=adb6b63d572196e13d85452df2db5ca6e38bed20ba359e6c26c3b4bce9047fe4&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)

---

## 6️⃣ 时序注意：网络同步 > OnBeginPlay

> ⏱️ 网络同步数据回调的时序通常早于 OnBeginPlay。如果同步回调中使用了 OnBeginPlay 里初始化的字段，此时字段尚未初始化，会导致空引用或逻辑错误。

---

## 7️⃣ 实战示例：IdleShow 随机数同步

> 🎯 问题：进入 IdleShow 或时装 IdleShow 时需要随机选取动作，不同端生成的随机数不同，必须同步主控端结果。

### Step 1：生成 StateData（MoeCharInputComponent）

MoeCharInputComponent:GenerateIdleShowStateData() 设置 IdleShowStateData，包含：CurrentIdleShowIdx / bSurroundingsIdleShowSwitch / bIsHitSurroundingsProbability

截图：GenerateIdleShowStateData 代码

![图片](https://prod-files-secure.s3.us-west-2.amazonaws.com/54c5f1d3-510d-815b-99f0-0003f4ecef71/9f69b755-8864-4488-8648-6b5dcf4ae7b4/net-sync-03-generate-idleshow.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466R2ABIWL6%2F20260424%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260424T101353Z&X-Amz-Expires=3600&X-Amz-Security-Token=IQoJb3JpZ2luX2VjELL%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJIMEYCIQC4wYyhwP6tSW9jGiJPOxe511nCAqO9pWQej9JuHUxR5QIhAKWeyUlEw%2BlUNW%2BP2zTS%2FVio2aHbcVZYC5mI5mKdLoFOKv8DCHsQABoMNjM3NDIzMTgzODA1IgwvKwX%2FlImACsHkhLMq3AP34ui%2FJ%2BvZy4GFNeQ9GVbY0Pj%2Fb6wSIp2eC%2BrheJXyCva5WdlMTjbssdhl%2FYue8%2BSTL8eW8GTYXY8hpWUwGMH7B%2FD2o257NnZyhUV6wml4q5ghN25syUVEEQkb%2FOGKYW37n0VmNy4PQWXrH76Cqbdx8rDrSQDc98HkNV4x%2Fzbb5hF8L86rmf3ESpVi1hfqjwQuZrOUJjDJXRpnPdwahADOCQ3E3avc8i%2BAsjXHbXvXUECt4iWGC1CNR7FaXJClA3KkgIUxeMt6gvENdlVp0FMRbqgSFBT3c0DwJY%2FEVKrsJLmkfsdT8gAmTeSiyra9Y%2Bo2QzpqmBgbBymRek3JxUPlxJ0bbqVJbgylrIZ%2Fgv6hwDmIGGvKER0K%2BLijbH9oPNX9kPkdGqF%2BCvyfgtwfY77UB%2FGoDLsuWKaYOQD4vRJyl0Gi2Dcn70iXSTHqSu4OM6cn4%2B6I%2Br6rQT%2BAQkIGYEqPGQmezSTm3Up7id47RvkLZSTYK7niZN%2BnVpV0osMByJIa5FXflLe3oyjIPea61w8xCMwj3%2FmQO8Huqp%2FKdK5JFMvS6kWe8E4VOy32rpIIeieAyNp2ZoRkGq4Wt1HR8iQqmk8ETB6hSK49PQYlUYt2YZIcHuDhQI4XHIDS4TDC7azPBjqkAWY%2BpZg%2FmKnUKgV1FZ2%2FtKFz6udrCzDKff1fIfVwDvA7kzodiefG%2F3qG6UKwLjrmQZLjPR7Cq6dy45LnGAaHuAFPgpoOasCEjdFdW7JRdzRIPTjGznU%2BKeiBMkm3rMxWFPItZ%2B7SYhbm2%2BmPghvbjgTvXfYG7tKTyfKt1JukXlKoB%2BpSilPw3ihXgxj9jXOxjJjpqY%2B6aaFQNgjJbQ%2FGYvLgjrYQ&X-Amz-Signature=e54839661ce0f146d55600dc31c0a3c5a418d3e51c52ddb105e2a29108bed878&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)

### Step 2：写入同步结构体（SetSyncStateData）

```lua
function MoeCharActionStateIdleShow:SetSyncStateData(SyncStateDataProxy)
    local IdleShowIdx = self.CurrentStateData.CurrentIdleShowIdx
    local bSurroundingsSwitch = self.CurrentStateData.bSurroundingsIdleShowSwitch
    local bIsHitProbability = self.CurrentStateData.bIsHitSurroundingsProbability
    self:AddOrSetSyncDataInt32('CurrentIdleShowIdx', IdleShowIdx, SyncStateDataProxy.SyncDataFactory)
    self:AddOrSetSyncDataBool('bSurroundingsIdleShowSwitch', bSurroundingsSwitch, SyncStateDataProxy.SyncDataFactory)
    self:AddOrSetSyncDataBool('bIsHitSurroundingsProbability', bIsHitProbability, SyncStateDataProxy.SyncDataFactory)
end
```

### Step 3：其他端解析同步数据（ParseSyncStateData）

```lua
function MoeCharActionStateIdleShow:ParseSyncStateData(SyncStateDataProxy)
    local StateData = UE4.NewObject(StateDataClass)
    local _, IdleShowIdx = self:GetSyncDataInt32('CurrentIdleShowIdx', SyncStateDataProxy.SyncDataFactory)
    local _, bSurroundingsSwitch = self:GetSyncDataBool('bSurroundingsIdleShowSwitch', SyncStateDataProxy.SyncDataFactory)
    -- 注意：本地玩家不需要解析同步数据，直接使用本地数据
    return StateData
end
```

截图：SetSyncStateData / ParseSyncStateData 完整代码

![图片](https://prod-files-secure.s3.us-west-2.amazonaws.com/54c5f1d3-510d-815b-99f0-0003f4ecef71/16ce4297-1309-434d-a361-5d6d5f3af297/net-sync-06-setsync-parsesync.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466R2ABIWL6%2F20260424%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260424T101354Z&X-Amz-Expires=3600&X-Amz-Security-Token=IQoJb3JpZ2luX2VjELL%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJIMEYCIQC4wYyhwP6tSW9jGiJPOxe511nCAqO9pWQej9JuHUxR5QIhAKWeyUlEw%2BlUNW%2BP2zTS%2FVio2aHbcVZYC5mI5mKdLoFOKv8DCHsQABoMNjM3NDIzMTgzODA1IgwvKwX%2FlImACsHkhLMq3AP34ui%2FJ%2BvZy4GFNeQ9GVbY0Pj%2Fb6wSIp2eC%2BrheJXyCva5WdlMTjbssdhl%2FYue8%2BSTL8eW8GTYXY8hpWUwGMH7B%2FD2o257NnZyhUV6wml4q5ghN25syUVEEQkb%2FOGKYW37n0VmNy4PQWXrH76Cqbdx8rDrSQDc98HkNV4x%2Fzbb5hF8L86rmf3ESpVi1hfqjwQuZrOUJjDJXRpnPdwahADOCQ3E3avc8i%2BAsjXHbXvXUECt4iWGC1CNR7FaXJClA3KkgIUxeMt6gvENdlVp0FMRbqgSFBT3c0DwJY%2FEVKrsJLmkfsdT8gAmTeSiyra9Y%2Bo2QzpqmBgbBymRek3JxUPlxJ0bbqVJbgylrIZ%2Fgv6hwDmIGGvKER0K%2BLijbH9oPNX9kPkdGqF%2BCvyfgtwfY77UB%2FGoDLsuWKaYOQD4vRJyl0Gi2Dcn70iXSTHqSu4OM6cn4%2B6I%2Br6rQT%2BAQkIGYEqPGQmezSTm3Up7id47RvkLZSTYK7niZN%2BnVpV0osMByJIa5FXflLe3oyjIPea61w8xCMwj3%2FmQO8Huqp%2FKdK5JFMvS6kWe8E4VOy32rpIIeieAyNp2ZoRkGq4Wt1HR8iQqmk8ETB6hSK49PQYlUYt2YZIcHuDhQI4XHIDS4TDC7azPBjqkAWY%2BpZg%2FmKnUKgV1FZ2%2FtKFz6udrCzDKff1fIfVwDvA7kzodiefG%2F3qG6UKwLjrmQZLjPR7Cq6dy45LnGAaHuAFPgpoOasCEjdFdW7JRdzRIPTjGznU%2BKeiBMkm3rMxWFPItZ%2B7SYhbm2%2BmPghvbjgTvXfYG7tKTyfKt1JukXlKoB%2BpSilPw3ihXgxj9jXOxjJjpqY%2B6aaFQNgjJbQ%2FGYvLgjrYQ&X-Amz-Signature=d920a9f831c7614a7b3662952d273d9d22a23045c0b40a2c9733e02b985233e4&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)

---

## 8️⃣ 完整调用链流程图

左侧：本地状态切换链路 → 右侧：网络同步链路

- UpdateIdleShow → GenerateIdleShowStateData → TryEnterActionState → TryEnterState → EnterState → CheckStateChange

- CheckStateChange（虚线）→ SetSyncStateData → AddOrSetSyncDataBool → ParseSyncStateData → GetSyncDataFloat

- 最终执行：ExecutiveSyncMotionState / ExecutiveStateChange

![图片](https://prod-files-secure.s3.us-west-2.amazonaws.com/54c5f1d3-510d-815b-99f0-0003f4ecef71/1858ca10-38db-457d-988c-574b3360181f/net-sync-07-flowchart.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466R2ABIWL6%2F20260424%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260424T101354Z&X-Amz-Expires=3600&X-Amz-Security-Token=IQoJb3JpZ2luX2VjELL%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJIMEYCIQC4wYyhwP6tSW9jGiJPOxe511nCAqO9pWQej9JuHUxR5QIhAKWeyUlEw%2BlUNW%2BP2zTS%2FVio2aHbcVZYC5mI5mKdLoFOKv8DCHsQABoMNjM3NDIzMTgzODA1IgwvKwX%2FlImACsHkhLMq3AP34ui%2FJ%2BvZy4GFNeQ9GVbY0Pj%2Fb6wSIp2eC%2BrheJXyCva5WdlMTjbssdhl%2FYue8%2BSTL8eW8GTYXY8hpWUwGMH7B%2FD2o257NnZyhUV6wml4q5ghN25syUVEEQkb%2FOGKYW37n0VmNy4PQWXrH76Cqbdx8rDrSQDc98HkNV4x%2Fzbb5hF8L86rmf3ESpVi1hfqjwQuZrOUJjDJXRpnPdwahADOCQ3E3avc8i%2BAsjXHbXvXUECt4iWGC1CNR7FaXJClA3KkgIUxeMt6gvENdlVp0FMRbqgSFBT3c0DwJY%2FEVKrsJLmkfsdT8gAmTeSiyra9Y%2Bo2QzpqmBgbBymRek3JxUPlxJ0bbqVJbgylrIZ%2Fgv6hwDmIGGvKER0K%2BLijbH9oPNX9kPkdGqF%2BCvyfgtwfY77UB%2FGoDLsuWKaYOQD4vRJyl0Gi2Dcn70iXSTHqSu4OM6cn4%2B6I%2Br6rQT%2BAQkIGYEqPGQmezSTm3Up7id47RvkLZSTYK7niZN%2BnVpV0osMByJIa5FXflLe3oyjIPea61w8xCMwj3%2FmQO8Huqp%2FKdK5JFMvS6kWe8E4VOy32rpIIeieAyNp2ZoRkGq4Wt1HR8iQqmk8ETB6hSK49PQYlUYt2YZIcHuDhQI4XHIDS4TDC7azPBjqkAWY%2BpZg%2FmKnUKgV1FZ2%2FtKFz6udrCzDKff1fIfVwDvA7kzodiefG%2F3qG6UKwLjrmQZLjPR7Cq6dy45LnGAaHuAFPgpoOasCEjdFdW7JRdzRIPTjGznU%2BKeiBMkm3rMxWFPItZ%2B7SYhbm2%2BmPghvbjgTvXfYG7tKTyfKt1JukXlKoB%2BpSilPw3ihXgxj9jXOxjJjpqY%2B6aaFQNgjJbQ%2FGYvLgjrYQ&X-Amz-Signature=7716a9d52f4204cce57b40fe98d354c6f1cbdae502ec1e123aa69ddbfe02a2dd&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)

---

## 📚 参考文档

iWiki 网络同步文档：https://iwiki.woa.com/p/4009438969

iWiki 相关参考：https://iwiki.woa.com/p/4009201134

