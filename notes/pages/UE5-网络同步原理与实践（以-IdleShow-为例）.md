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

![图片](https://prod-files-secure.s3.us-west-2.amazonaws.com/54c5f1d3-510d-815b-99f0-0003f4ecef71/4344ed5a-2b22-4293-b299-12da8c5ea3ee/net-sync-04-FMoeActionStateDataProxy.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB4667EO57WNT%2F20260424%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260424T105517Z&X-Amz-Expires=3600&X-Amz-Security-Token=IQoJb3JpZ2luX2VjELP%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJGMEQCIApR1oBAbxQ5AvQHV%2FQuMm%2FV1b7cF%2Bmb37Qu3fb%2Bgp36AiBd3GwKcdo9gLJFhrdL2rpO%2F3rjv1qF3PUY2kPvyAikWir%2FAwh8EAAaDDYzNzQyMzE4MzgwNSIMxXvyIM%2BoXluxnwtqKtwD06GKodWK9K1Q4Lmczew1mV9iRxPUlSpSEROjSUhv3wqllmXjgT6jhX1H9LOS8sCVk%2F1wsBnk9V8jRRFKnJCVaImr5%2B1wzDhSzmxZ0Qnm4kgrp34fg8k%2Fdim5CPD2%2BYxtcqtJSBb0OakxcPLGvRnExmCeY12feumyvx1r571yoHM0%2Fnh9H%2FRlRB%2BJkqWosID9mmMIQHfo9gjGkA%2FxmHnBSx13JWYwuMcZuFuwyvZCT59FQPSl9ux4EwLWQsW3BlqTcVP9rmarZ2glrGt4fTbfbues09mNIJjmHf%2BxgGLUPSRDmZbyuDNxK35XcmlE0N9VUHvvk1qa9m91FB2fYR47s2oPDAT5a842X3pP%2BIl9LQIieBajABYfHVbca5MYSdJJgaod%2BagSHUW4xVtPxN4n%2FB0rwtk1ssdy8fo8q1fTVjXyJvJ90dDINbXi4HC1WkjXZd1fedLZVG7kuXhxVuL9xCbJvXSZghXM4ng7MQHL42yIwJXXtaoQkw7O2TmpivJkaQ3dH%2Bn42Msw2v8XskN2Rx4g9YzCsORxnTqbj12rI8AJfbUXOlm34SWr6BHW0NPOPKIJ7XZsJon0KeePdHM90CVd4Df7aQQ9Cb2WJ4BRZNOhl8%2Fn1dbGNc1b6K8wkY%2BtzwY6pgEo%2Ffr8A43wUIgweCXDADA5dsCl5Glq9WM%2FyI8CgcNElR9iBwgo4JrVJYuSKCWjJL85v7GlhaqQVc4ELTt1%2B4B4S4HaaH8dJwljLa4CnorS3A2OqBDGc34939M%2F6uwNLCFLEuQ4BWCJk1b1oFq1VjD6pkVQo%2BAmW%2BtAUQCPu%2FGn0jhLSvzAljc4EbQRpv3GwU%2ByqD4GPVUqDW9pYUP9Uo0Y09PXYpTC&X-Amz-Signature=cab935aaefab4ff34f7954bab2da8a137d2d40859599e2c31edb99e093041b71&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)

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

![图片](https://prod-files-secure.s3.us-west-2.amazonaws.com/54c5f1d3-510d-815b-99f0-0003f4ecef71/59b1fcd1-5e60-4aaf-a675-aa68f4c84869/net-sync-05-addbool-getbool.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB4667EO57WNT%2F20260424%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260424T105517Z&X-Amz-Expires=3600&X-Amz-Security-Token=IQoJb3JpZ2luX2VjELP%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJGMEQCIApR1oBAbxQ5AvQHV%2FQuMm%2FV1b7cF%2Bmb37Qu3fb%2Bgp36AiBd3GwKcdo9gLJFhrdL2rpO%2F3rjv1qF3PUY2kPvyAikWir%2FAwh8EAAaDDYzNzQyMzE4MzgwNSIMxXvyIM%2BoXluxnwtqKtwD06GKodWK9K1Q4Lmczew1mV9iRxPUlSpSEROjSUhv3wqllmXjgT6jhX1H9LOS8sCVk%2F1wsBnk9V8jRRFKnJCVaImr5%2B1wzDhSzmxZ0Qnm4kgrp34fg8k%2Fdim5CPD2%2BYxtcqtJSBb0OakxcPLGvRnExmCeY12feumyvx1r571yoHM0%2Fnh9H%2FRlRB%2BJkqWosID9mmMIQHfo9gjGkA%2FxmHnBSx13JWYwuMcZuFuwyvZCT59FQPSl9ux4EwLWQsW3BlqTcVP9rmarZ2glrGt4fTbfbues09mNIJjmHf%2BxgGLUPSRDmZbyuDNxK35XcmlE0N9VUHvvk1qa9m91FB2fYR47s2oPDAT5a842X3pP%2BIl9LQIieBajABYfHVbca5MYSdJJgaod%2BagSHUW4xVtPxN4n%2FB0rwtk1ssdy8fo8q1fTVjXyJvJ90dDINbXi4HC1WkjXZd1fedLZVG7kuXhxVuL9xCbJvXSZghXM4ng7MQHL42yIwJXXtaoQkw7O2TmpivJkaQ3dH%2Bn42Msw2v8XskN2Rx4g9YzCsORxnTqbj12rI8AJfbUXOlm34SWr6BHW0NPOPKIJ7XZsJon0KeePdHM90CVd4Df7aQQ9Cb2WJ4BRZNOhl8%2Fn1dbGNc1b6K8wkY%2BtzwY6pgEo%2Ffr8A43wUIgweCXDADA5dsCl5Glq9WM%2FyI8CgcNElR9iBwgo4JrVJYuSKCWjJL85v7GlhaqQVc4ELTt1%2B4B4S4HaaH8dJwljLa4CnorS3A2OqBDGc34939M%2F6uwNLCFLEuQ4BWCJk1b1oFq1VjD6pkVQo%2BAmW%2BtAUQCPu%2FGn0jhLSvzAljc4EbQRpv3GwU%2ByqD4GPVUqDW9pYUP9Uo0Y09PXYpTC&X-Amz-Signature=803509afbec0ae895ada13bea22801b6bfba26c399f5fb2b38ce7a89c6a03eec&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)

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

![图片](https://prod-files-secure.s3.us-west-2.amazonaws.com/54c5f1d3-510d-815b-99f0-0003f4ecef71/9da92056-7141-43fa-82ee-66b3745052fe/net-sync-01-onrep.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB4667EO57WNT%2F20260424%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260424T105518Z&X-Amz-Expires=3600&X-Amz-Security-Token=IQoJb3JpZ2luX2VjELP%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJGMEQCIApR1oBAbxQ5AvQHV%2FQuMm%2FV1b7cF%2Bmb37Qu3fb%2Bgp36AiBd3GwKcdo9gLJFhrdL2rpO%2F3rjv1qF3PUY2kPvyAikWir%2FAwh8EAAaDDYzNzQyMzE4MzgwNSIMxXvyIM%2BoXluxnwtqKtwD06GKodWK9K1Q4Lmczew1mV9iRxPUlSpSEROjSUhv3wqllmXjgT6jhX1H9LOS8sCVk%2F1wsBnk9V8jRRFKnJCVaImr5%2B1wzDhSzmxZ0Qnm4kgrp34fg8k%2Fdim5CPD2%2BYxtcqtJSBb0OakxcPLGvRnExmCeY12feumyvx1r571yoHM0%2Fnh9H%2FRlRB%2BJkqWosID9mmMIQHfo9gjGkA%2FxmHnBSx13JWYwuMcZuFuwyvZCT59FQPSl9ux4EwLWQsW3BlqTcVP9rmarZ2glrGt4fTbfbues09mNIJjmHf%2BxgGLUPSRDmZbyuDNxK35XcmlE0N9VUHvvk1qa9m91FB2fYR47s2oPDAT5a842X3pP%2BIl9LQIieBajABYfHVbca5MYSdJJgaod%2BagSHUW4xVtPxN4n%2FB0rwtk1ssdy8fo8q1fTVjXyJvJ90dDINbXi4HC1WkjXZd1fedLZVG7kuXhxVuL9xCbJvXSZghXM4ng7MQHL42yIwJXXtaoQkw7O2TmpivJkaQ3dH%2Bn42Msw2v8XskN2Rx4g9YzCsORxnTqbj12rI8AJfbUXOlm34SWr6BHW0NPOPKIJ7XZsJon0KeePdHM90CVd4Df7aQQ9Cb2WJ4BRZNOhl8%2Fn1dbGNc1b6K8wkY%2BtzwY6pgEo%2Ffr8A43wUIgweCXDADA5dsCl5Glq9WM%2FyI8CgcNElR9iBwgo4JrVJYuSKCWjJL85v7GlhaqQVc4ELTt1%2B4B4S4HaaH8dJwljLa4CnorS3A2OqBDGc34939M%2F6uwNLCFLEuQ4BWCJk1b1oFq1VjD6pkVQo%2BAmW%2BtAUQCPu%2FGn0jhLSvzAljc4EbQRpv3GwU%2ByqD4GPVUqDW9pYUP9Uo0Y09PXYpTC&X-Amz-Signature=f0fb327ca8f784c993a4a554ee29beb7561574a7d9bf5abf32d281e52df5ef73&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)

---

## 5️⃣ 组件复制是变量复制的前提

> 🚨 组件未调用 SetIsReplicated(true) → 客户端无镜像组件 → 组件内所有变量的 REPLICATED 声明全部失效！

- ✅ 组件已复制 + 变量声明复制 → 完整同步

- ❌ 组件未复制 → 客户端无组件 → 变量复制无效

- ⚠️ 组件已复制 + 变量未声明复制 → 仅同步组件框架（无数据）

截图：组件复制机制说明

![图片](https://prod-files-secure.s3.us-west-2.amazonaws.com/54c5f1d3-510d-815b-99f0-0003f4ecef71/de6ef4b4-219e-4d8b-9f16-064401414420/net-sync-02-component-replication.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB4667EO57WNT%2F20260424%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260424T105518Z&X-Amz-Expires=3600&X-Amz-Security-Token=IQoJb3JpZ2luX2VjELP%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJGMEQCIApR1oBAbxQ5AvQHV%2FQuMm%2FV1b7cF%2Bmb37Qu3fb%2Bgp36AiBd3GwKcdo9gLJFhrdL2rpO%2F3rjv1qF3PUY2kPvyAikWir%2FAwh8EAAaDDYzNzQyMzE4MzgwNSIMxXvyIM%2BoXluxnwtqKtwD06GKodWK9K1Q4Lmczew1mV9iRxPUlSpSEROjSUhv3wqllmXjgT6jhX1H9LOS8sCVk%2F1wsBnk9V8jRRFKnJCVaImr5%2B1wzDhSzmxZ0Qnm4kgrp34fg8k%2Fdim5CPD2%2BYxtcqtJSBb0OakxcPLGvRnExmCeY12feumyvx1r571yoHM0%2Fnh9H%2FRlRB%2BJkqWosID9mmMIQHfo9gjGkA%2FxmHnBSx13JWYwuMcZuFuwyvZCT59FQPSl9ux4EwLWQsW3BlqTcVP9rmarZ2glrGt4fTbfbues09mNIJjmHf%2BxgGLUPSRDmZbyuDNxK35XcmlE0N9VUHvvk1qa9m91FB2fYR47s2oPDAT5a842X3pP%2BIl9LQIieBajABYfHVbca5MYSdJJgaod%2BagSHUW4xVtPxN4n%2FB0rwtk1ssdy8fo8q1fTVjXyJvJ90dDINbXi4HC1WkjXZd1fedLZVG7kuXhxVuL9xCbJvXSZghXM4ng7MQHL42yIwJXXtaoQkw7O2TmpivJkaQ3dH%2Bn42Msw2v8XskN2Rx4g9YzCsORxnTqbj12rI8AJfbUXOlm34SWr6BHW0NPOPKIJ7XZsJon0KeePdHM90CVd4Df7aQQ9Cb2WJ4BRZNOhl8%2Fn1dbGNc1b6K8wkY%2BtzwY6pgEo%2Ffr8A43wUIgweCXDADA5dsCl5Glq9WM%2FyI8CgcNElR9iBwgo4JrVJYuSKCWjJL85v7GlhaqQVc4ELTt1%2B4B4S4HaaH8dJwljLa4CnorS3A2OqBDGc34939M%2F6uwNLCFLEuQ4BWCJk1b1oFq1VjD6pkVQo%2BAmW%2BtAUQCPu%2FGn0jhLSvzAljc4EbQRpv3GwU%2ByqD4GPVUqDW9pYUP9Uo0Y09PXYpTC&X-Amz-Signature=f8f6759aa7388a7045b32a8307de9b96ff55483d23c6ef034e2be79922fca656&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)

---

## 6️⃣ 时序注意：网络同步 > OnBeginPlay

> ⏱️ 网络同步数据回调的时序通常早于 OnBeginPlay。如果同步回调中使用了 OnBeginPlay 里初始化的字段，此时字段尚未初始化，会导致空引用或逻辑错误。

---

## 7️⃣ 实战示例：IdleShow 随机数同步

> 🎯 问题：进入 IdleShow 或时装 IdleShow 时需要随机选取动作，不同端生成的随机数不同，必须同步主控端结果。

### Step 1：生成 StateData（MoeCharInputComponent）

MoeCharInputComponent:GenerateIdleShowStateData() 设置 IdleShowStateData，包含：CurrentIdleShowIdx / bSurroundingsIdleShowSwitch / bIsHitSurroundingsProbability

截图：GenerateIdleShowStateData 代码

![图片](https://prod-files-secure.s3.us-west-2.amazonaws.com/54c5f1d3-510d-815b-99f0-0003f4ecef71/9f69b755-8864-4488-8648-6b5dcf4ae7b4/net-sync-03-generate-idleshow.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB4667EO57WNT%2F20260424%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260424T105518Z&X-Amz-Expires=3600&X-Amz-Security-Token=IQoJb3JpZ2luX2VjELP%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJGMEQCIApR1oBAbxQ5AvQHV%2FQuMm%2FV1b7cF%2Bmb37Qu3fb%2Bgp36AiBd3GwKcdo9gLJFhrdL2rpO%2F3rjv1qF3PUY2kPvyAikWir%2FAwh8EAAaDDYzNzQyMzE4MzgwNSIMxXvyIM%2BoXluxnwtqKtwD06GKodWK9K1Q4Lmczew1mV9iRxPUlSpSEROjSUhv3wqllmXjgT6jhX1H9LOS8sCVk%2F1wsBnk9V8jRRFKnJCVaImr5%2B1wzDhSzmxZ0Qnm4kgrp34fg8k%2Fdim5CPD2%2BYxtcqtJSBb0OakxcPLGvRnExmCeY12feumyvx1r571yoHM0%2Fnh9H%2FRlRB%2BJkqWosID9mmMIQHfo9gjGkA%2FxmHnBSx13JWYwuMcZuFuwyvZCT59FQPSl9ux4EwLWQsW3BlqTcVP9rmarZ2glrGt4fTbfbues09mNIJjmHf%2BxgGLUPSRDmZbyuDNxK35XcmlE0N9VUHvvk1qa9m91FB2fYR47s2oPDAT5a842X3pP%2BIl9LQIieBajABYfHVbca5MYSdJJgaod%2BagSHUW4xVtPxN4n%2FB0rwtk1ssdy8fo8q1fTVjXyJvJ90dDINbXi4HC1WkjXZd1fedLZVG7kuXhxVuL9xCbJvXSZghXM4ng7MQHL42yIwJXXtaoQkw7O2TmpivJkaQ3dH%2Bn42Msw2v8XskN2Rx4g9YzCsORxnTqbj12rI8AJfbUXOlm34SWr6BHW0NPOPKIJ7XZsJon0KeePdHM90CVd4Df7aQQ9Cb2WJ4BRZNOhl8%2Fn1dbGNc1b6K8wkY%2BtzwY6pgEo%2Ffr8A43wUIgweCXDADA5dsCl5Glq9WM%2FyI8CgcNElR9iBwgo4JrVJYuSKCWjJL85v7GlhaqQVc4ELTt1%2B4B4S4HaaH8dJwljLa4CnorS3A2OqBDGc34939M%2F6uwNLCFLEuQ4BWCJk1b1oFq1VjD6pkVQo%2BAmW%2BtAUQCPu%2FGn0jhLSvzAljc4EbQRpv3GwU%2ByqD4GPVUqDW9pYUP9Uo0Y09PXYpTC&X-Amz-Signature=7e52b034293e33d9fea7253e141d84dfda9a543ceb9748255a4df56fc91b8307&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)

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

![图片](https://prod-files-secure.s3.us-west-2.amazonaws.com/54c5f1d3-510d-815b-99f0-0003f4ecef71/16ce4297-1309-434d-a361-5d6d5f3af297/net-sync-06-setsync-parsesync.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB4667EO57WNT%2F20260424%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260424T105518Z&X-Amz-Expires=3600&X-Amz-Security-Token=IQoJb3JpZ2luX2VjELP%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJGMEQCIApR1oBAbxQ5AvQHV%2FQuMm%2FV1b7cF%2Bmb37Qu3fb%2Bgp36AiBd3GwKcdo9gLJFhrdL2rpO%2F3rjv1qF3PUY2kPvyAikWir%2FAwh8EAAaDDYzNzQyMzE4MzgwNSIMxXvyIM%2BoXluxnwtqKtwD06GKodWK9K1Q4Lmczew1mV9iRxPUlSpSEROjSUhv3wqllmXjgT6jhX1H9LOS8sCVk%2F1wsBnk9V8jRRFKnJCVaImr5%2B1wzDhSzmxZ0Qnm4kgrp34fg8k%2Fdim5CPD2%2BYxtcqtJSBb0OakxcPLGvRnExmCeY12feumyvx1r571yoHM0%2Fnh9H%2FRlRB%2BJkqWosID9mmMIQHfo9gjGkA%2FxmHnBSx13JWYwuMcZuFuwyvZCT59FQPSl9ux4EwLWQsW3BlqTcVP9rmarZ2glrGt4fTbfbues09mNIJjmHf%2BxgGLUPSRDmZbyuDNxK35XcmlE0N9VUHvvk1qa9m91FB2fYR47s2oPDAT5a842X3pP%2BIl9LQIieBajABYfHVbca5MYSdJJgaod%2BagSHUW4xVtPxN4n%2FB0rwtk1ssdy8fo8q1fTVjXyJvJ90dDINbXi4HC1WkjXZd1fedLZVG7kuXhxVuL9xCbJvXSZghXM4ng7MQHL42yIwJXXtaoQkw7O2TmpivJkaQ3dH%2Bn42Msw2v8XskN2Rx4g9YzCsORxnTqbj12rI8AJfbUXOlm34SWr6BHW0NPOPKIJ7XZsJon0KeePdHM90CVd4Df7aQQ9Cb2WJ4BRZNOhl8%2Fn1dbGNc1b6K8wkY%2BtzwY6pgEo%2Ffr8A43wUIgweCXDADA5dsCl5Glq9WM%2FyI8CgcNElR9iBwgo4JrVJYuSKCWjJL85v7GlhaqQVc4ELTt1%2B4B4S4HaaH8dJwljLa4CnorS3A2OqBDGc34939M%2F6uwNLCFLEuQ4BWCJk1b1oFq1VjD6pkVQo%2BAmW%2BtAUQCPu%2FGn0jhLSvzAljc4EbQRpv3GwU%2ByqD4GPVUqDW9pYUP9Uo0Y09PXYpTC&X-Amz-Signature=258fd639d15a33e9e4007d86c677f2786b6bfb655e18e8c2a9f183b59dc0e446&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)

---

## 8️⃣ 完整调用链流程图

左侧：本地状态切换链路 → 右侧：网络同步链路

- UpdateIdleShow → GenerateIdleShowStateData → TryEnterActionState → TryEnterState → EnterState → CheckStateChange

- CheckStateChange（虚线）→ SetSyncStateData → AddOrSetSyncDataBool → ParseSyncStateData → GetSyncDataFloat

- 最终执行：ExecutiveSyncMotionState / ExecutiveStateChange

![图片](https://prod-files-secure.s3.us-west-2.amazonaws.com/54c5f1d3-510d-815b-99f0-0003f4ecef71/1858ca10-38db-457d-988c-574b3360181f/net-sync-07-flowchart.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB4667EO57WNT%2F20260424%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260424T105518Z&X-Amz-Expires=3600&X-Amz-Security-Token=IQoJb3JpZ2luX2VjELP%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJGMEQCIApR1oBAbxQ5AvQHV%2FQuMm%2FV1b7cF%2Bmb37Qu3fb%2Bgp36AiBd3GwKcdo9gLJFhrdL2rpO%2F3rjv1qF3PUY2kPvyAikWir%2FAwh8EAAaDDYzNzQyMzE4MzgwNSIMxXvyIM%2BoXluxnwtqKtwD06GKodWK9K1Q4Lmczew1mV9iRxPUlSpSEROjSUhv3wqllmXjgT6jhX1H9LOS8sCVk%2F1wsBnk9V8jRRFKnJCVaImr5%2B1wzDhSzmxZ0Qnm4kgrp34fg8k%2Fdim5CPD2%2BYxtcqtJSBb0OakxcPLGvRnExmCeY12feumyvx1r571yoHM0%2Fnh9H%2FRlRB%2BJkqWosID9mmMIQHfo9gjGkA%2FxmHnBSx13JWYwuMcZuFuwyvZCT59FQPSl9ux4EwLWQsW3BlqTcVP9rmarZ2glrGt4fTbfbues09mNIJjmHf%2BxgGLUPSRDmZbyuDNxK35XcmlE0N9VUHvvk1qa9m91FB2fYR47s2oPDAT5a842X3pP%2BIl9LQIieBajABYfHVbca5MYSdJJgaod%2BagSHUW4xVtPxN4n%2FB0rwtk1ssdy8fo8q1fTVjXyJvJ90dDINbXi4HC1WkjXZd1fedLZVG7kuXhxVuL9xCbJvXSZghXM4ng7MQHL42yIwJXXtaoQkw7O2TmpivJkaQ3dH%2Bn42Msw2v8XskN2Rx4g9YzCsORxnTqbj12rI8AJfbUXOlm34SWr6BHW0NPOPKIJ7XZsJon0KeePdHM90CVd4Df7aQQ9Cb2WJ4BRZNOhl8%2Fn1dbGNc1b6K8wkY%2BtzwY6pgEo%2Ffr8A43wUIgweCXDADA5dsCl5Glq9WM%2FyI8CgcNElR9iBwgo4JrVJYuSKCWjJL85v7GlhaqQVc4ELTt1%2B4B4S4HaaH8dJwljLa4CnorS3A2OqBDGc34939M%2F6uwNLCFLEuQ4BWCJk1b1oFq1VjD6pkVQo%2BAmW%2BtAUQCPu%2FGn0jhLSvzAljc4EbQRpv3GwU%2ByqD4GPVUqDW9pYUP9Uo0Y09PXYpTC&X-Amz-Signature=e1f6078e68d1921eda3445ce669bbed2c037bb000988a28ffa7d393f3e607a55&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)

---

## 📚 参考文档

iWiki 网络同步文档：https://iwiki.woa.com/p/4009438969

iWiki 相关参考：https://iwiki.woa.com/p/4009201134

