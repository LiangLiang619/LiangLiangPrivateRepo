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
notion_url: "https://app.notion.com/p/UE5-IdleShow-34a5f1d3510d8100829bf32b670b613a"
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

![图片](https://prod-files-secure.s3.us-west-2.amazonaws.com/54c5f1d3-510d-815b-99f0-0003f4ecef71/4344ed5a-2b22-4293-b299-12da8c5ea3ee/net-sync-04-FMoeActionStateDataProxy.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466YNMXGGJX%2F20260429%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260429T100040Z&X-Amz-Expires=3600&X-Amz-Security-Token=IQoJb3JpZ2luX2VjECoaCXVzLXdlc3QtMiJIMEYCIQDptF1VTnwNkQLq17QmWouEgsQDcHahIbxlHgTNLXc8uAIhAPEmM0lACho%2Fdre0a9Ci8TrXVIcG5NL11pILh5xcwLGrKogECPP%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEQABoMNjM3NDIzMTgzODA1Igyg44UDhjR5aq%2BDU90q3AOq7YU%2FFIxv%2Bjig4e2Fe0St3JrZW4WHZRfOdfBHOAAtF%2FLUlQsSVVQuHmDsbslqK5IK%2F3KrjxF2En%2FFrmQcYFzCiZownv2bPfCqBsJma20kTpeqK3wg9h9c9ZnthHYocR1HQasjZ8Ijp%2FW%2FLoLXWwQsNGFT6hWEdDxvG7ZOkBG7DlRx0XQ5Muz27pHjZbAmsQG62pEcGodoLlgi9JThCFqai595jjG3sO4nLe85V2knyvAQyrNasLYdL1AXk2527Nd9CxmTK4c8KjUrv7Ujl3rDMgZsZPtG2y%2F%2BTEctlyXRXv0XPnrfwAPjkfGi4EUUyQhCqg3sIrys3vsWuQtmqoQuCaT9Llv%2Bfj%2FvgG%2Bp3GLS1QaKVqlPICyLkxzeQTcvyObSg%2BRIJriGpq8Ll2TMz%2BN5x7MKc6URdGHUaapl4LlPwBPrMUpTynja5bqS0ISTrQQ%2F8SZba0ujxlPNk8FN28CBPmYLNOqk8Msw%2BpZq%2BIXM8T2P2slRxbDeDrFttBxiZ%2Fy2IDbL9J2ebXB6uaCWSnDkFoYYwkjArSwlddajTuQ7xleA604ByrG29xkZhE0BF6ybQszhqrXXjtRlffdsYDLQSOjwvFrEIZt2Me9HqXKUZwHamIoNn9MRETVr4zDWqMfPBjqkAWvDFp%2F3tmpD3aW20VRvCl3ldaHyXWi4tEJ%2FTdQks3yyvIvzORcTyDcZCjBTduFJWiqpwW97rSttBIiA97sjTIJ0oN4rL0ucpABLwhxWjaFiqlwuvkQk%2BkwXSef0e%2BBOR0HLY4eH9MiO0OJu1zgb0P7py0Ipxh9c8koRlnJxi7aZV5v%2BXJQhKBDAPDhbkZLVXZCJVNi9fdsh7VSvAFgkI524FW9A&X-Amz-Signature=dc699af03f69bf6791a01aeab1501b46d88cc97242449cb554e40044023735b9&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)

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

![图片](https://prod-files-secure.s3.us-west-2.amazonaws.com/54c5f1d3-510d-815b-99f0-0003f4ecef71/59b1fcd1-5e60-4aaf-a675-aa68f4c84869/net-sync-05-addbool-getbool.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466YNMXGGJX%2F20260429%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260429T100040Z&X-Amz-Expires=3600&X-Amz-Security-Token=IQoJb3JpZ2luX2VjECoaCXVzLXdlc3QtMiJIMEYCIQDptF1VTnwNkQLq17QmWouEgsQDcHahIbxlHgTNLXc8uAIhAPEmM0lACho%2Fdre0a9Ci8TrXVIcG5NL11pILh5xcwLGrKogECPP%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEQABoMNjM3NDIzMTgzODA1Igyg44UDhjR5aq%2BDU90q3AOq7YU%2FFIxv%2Bjig4e2Fe0St3JrZW4WHZRfOdfBHOAAtF%2FLUlQsSVVQuHmDsbslqK5IK%2F3KrjxF2En%2FFrmQcYFzCiZownv2bPfCqBsJma20kTpeqK3wg9h9c9ZnthHYocR1HQasjZ8Ijp%2FW%2FLoLXWwQsNGFT6hWEdDxvG7ZOkBG7DlRx0XQ5Muz27pHjZbAmsQG62pEcGodoLlgi9JThCFqai595jjG3sO4nLe85V2knyvAQyrNasLYdL1AXk2527Nd9CxmTK4c8KjUrv7Ujl3rDMgZsZPtG2y%2F%2BTEctlyXRXv0XPnrfwAPjkfGi4EUUyQhCqg3sIrys3vsWuQtmqoQuCaT9Llv%2Bfj%2FvgG%2Bp3GLS1QaKVqlPICyLkxzeQTcvyObSg%2BRIJriGpq8Ll2TMz%2BN5x7MKc6URdGHUaapl4LlPwBPrMUpTynja5bqS0ISTrQQ%2F8SZba0ujxlPNk8FN28CBPmYLNOqk8Msw%2BpZq%2BIXM8T2P2slRxbDeDrFttBxiZ%2Fy2IDbL9J2ebXB6uaCWSnDkFoYYwkjArSwlddajTuQ7xleA604ByrG29xkZhE0BF6ybQszhqrXXjtRlffdsYDLQSOjwvFrEIZt2Me9HqXKUZwHamIoNn9MRETVr4zDWqMfPBjqkAWvDFp%2F3tmpD3aW20VRvCl3ldaHyXWi4tEJ%2FTdQks3yyvIvzORcTyDcZCjBTduFJWiqpwW97rSttBIiA97sjTIJ0oN4rL0ucpABLwhxWjaFiqlwuvkQk%2BkwXSef0e%2BBOR0HLY4eH9MiO0OJu1zgb0P7py0Ipxh9c8koRlnJxi7aZV5v%2BXJQhKBDAPDhbkZLVXZCJVNi9fdsh7VSvAFgkI524FW9A&X-Amz-Signature=9d859edc77bfb5940f871c25d59deab55184420dfeb5998d52c0c992e9d2b3eb&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)

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

![图片](https://prod-files-secure.s3.us-west-2.amazonaws.com/54c5f1d3-510d-815b-99f0-0003f4ecef71/9da92056-7141-43fa-82ee-66b3745052fe/net-sync-01-onrep.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466YNMXGGJX%2F20260429%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260429T100040Z&X-Amz-Expires=3600&X-Amz-Security-Token=IQoJb3JpZ2luX2VjECoaCXVzLXdlc3QtMiJIMEYCIQDptF1VTnwNkQLq17QmWouEgsQDcHahIbxlHgTNLXc8uAIhAPEmM0lACho%2Fdre0a9Ci8TrXVIcG5NL11pILh5xcwLGrKogECPP%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEQABoMNjM3NDIzMTgzODA1Igyg44UDhjR5aq%2BDU90q3AOq7YU%2FFIxv%2Bjig4e2Fe0St3JrZW4WHZRfOdfBHOAAtF%2FLUlQsSVVQuHmDsbslqK5IK%2F3KrjxF2En%2FFrmQcYFzCiZownv2bPfCqBsJma20kTpeqK3wg9h9c9ZnthHYocR1HQasjZ8Ijp%2FW%2FLoLXWwQsNGFT6hWEdDxvG7ZOkBG7DlRx0XQ5Muz27pHjZbAmsQG62pEcGodoLlgi9JThCFqai595jjG3sO4nLe85V2knyvAQyrNasLYdL1AXk2527Nd9CxmTK4c8KjUrv7Ujl3rDMgZsZPtG2y%2F%2BTEctlyXRXv0XPnrfwAPjkfGi4EUUyQhCqg3sIrys3vsWuQtmqoQuCaT9Llv%2Bfj%2FvgG%2Bp3GLS1QaKVqlPICyLkxzeQTcvyObSg%2BRIJriGpq8Ll2TMz%2BN5x7MKc6URdGHUaapl4LlPwBPrMUpTynja5bqS0ISTrQQ%2F8SZba0ujxlPNk8FN28CBPmYLNOqk8Msw%2BpZq%2BIXM8T2P2slRxbDeDrFttBxiZ%2Fy2IDbL9J2ebXB6uaCWSnDkFoYYwkjArSwlddajTuQ7xleA604ByrG29xkZhE0BF6ybQszhqrXXjtRlffdsYDLQSOjwvFrEIZt2Me9HqXKUZwHamIoNn9MRETVr4zDWqMfPBjqkAWvDFp%2F3tmpD3aW20VRvCl3ldaHyXWi4tEJ%2FTdQks3yyvIvzORcTyDcZCjBTduFJWiqpwW97rSttBIiA97sjTIJ0oN4rL0ucpABLwhxWjaFiqlwuvkQk%2BkwXSef0e%2BBOR0HLY4eH9MiO0OJu1zgb0P7py0Ipxh9c8koRlnJxi7aZV5v%2BXJQhKBDAPDhbkZLVXZCJVNi9fdsh7VSvAFgkI524FW9A&X-Amz-Signature=ce3ed272b729937abb59bf0b4866257f3803db3a28700c78ec65090426214692&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)

---

## 5️⃣ 组件复制是变量复制的前提

> 🚨 组件未调用 SetIsReplicated(true) → 客户端无镜像组件 → 组件内所有变量的 REPLICATED 声明全部失效！

- ✅ 组件已复制 + 变量声明复制 → 完整同步

- ❌ 组件未复制 → 客户端无组件 → 变量复制无效

- ⚠️ 组件已复制 + 变量未声明复制 → 仅同步组件框架（无数据）

截图：组件复制机制说明

![图片](https://prod-files-secure.s3.us-west-2.amazonaws.com/54c5f1d3-510d-815b-99f0-0003f4ecef71/de6ef4b4-219e-4d8b-9f16-064401414420/net-sync-02-component-replication.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466YNMXGGJX%2F20260429%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260429T100040Z&X-Amz-Expires=3600&X-Amz-Security-Token=IQoJb3JpZ2luX2VjECoaCXVzLXdlc3QtMiJIMEYCIQDptF1VTnwNkQLq17QmWouEgsQDcHahIbxlHgTNLXc8uAIhAPEmM0lACho%2Fdre0a9Ci8TrXVIcG5NL11pILh5xcwLGrKogECPP%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEQABoMNjM3NDIzMTgzODA1Igyg44UDhjR5aq%2BDU90q3AOq7YU%2FFIxv%2Bjig4e2Fe0St3JrZW4WHZRfOdfBHOAAtF%2FLUlQsSVVQuHmDsbslqK5IK%2F3KrjxF2En%2FFrmQcYFzCiZownv2bPfCqBsJma20kTpeqK3wg9h9c9ZnthHYocR1HQasjZ8Ijp%2FW%2FLoLXWwQsNGFT6hWEdDxvG7ZOkBG7DlRx0XQ5Muz27pHjZbAmsQG62pEcGodoLlgi9JThCFqai595jjG3sO4nLe85V2knyvAQyrNasLYdL1AXk2527Nd9CxmTK4c8KjUrv7Ujl3rDMgZsZPtG2y%2F%2BTEctlyXRXv0XPnrfwAPjkfGi4EUUyQhCqg3sIrys3vsWuQtmqoQuCaT9Llv%2Bfj%2FvgG%2Bp3GLS1QaKVqlPICyLkxzeQTcvyObSg%2BRIJriGpq8Ll2TMz%2BN5x7MKc6URdGHUaapl4LlPwBPrMUpTynja5bqS0ISTrQQ%2F8SZba0ujxlPNk8FN28CBPmYLNOqk8Msw%2BpZq%2BIXM8T2P2slRxbDeDrFttBxiZ%2Fy2IDbL9J2ebXB6uaCWSnDkFoYYwkjArSwlddajTuQ7xleA604ByrG29xkZhE0BF6ybQszhqrXXjtRlffdsYDLQSOjwvFrEIZt2Me9HqXKUZwHamIoNn9MRETVr4zDWqMfPBjqkAWvDFp%2F3tmpD3aW20VRvCl3ldaHyXWi4tEJ%2FTdQks3yyvIvzORcTyDcZCjBTduFJWiqpwW97rSttBIiA97sjTIJ0oN4rL0ucpABLwhxWjaFiqlwuvkQk%2BkwXSef0e%2BBOR0HLY4eH9MiO0OJu1zgb0P7py0Ipxh9c8koRlnJxi7aZV5v%2BXJQhKBDAPDhbkZLVXZCJVNi9fdsh7VSvAFgkI524FW9A&X-Amz-Signature=9871eef3827fae31b3ea3b68652f9661b411f0875f17f45813efebfca5b2d430&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)

---

## 6️⃣ 时序注意：网络同步 > OnBeginPlay

> ⏱️ 网络同步数据回调的时序通常早于 OnBeginPlay。如果同步回调中使用了 OnBeginPlay 里初始化的字段，此时字段尚未初始化，会导致空引用或逻辑错误。

---

## 7️⃣ 实战示例：IdleShow 随机数同步

> 🎯 问题：进入 IdleShow 或时装 IdleShow 时需要随机选取动作，不同端生成的随机数不同，必须同步主控端结果。

### Step 1：生成 StateData（MoeCharInputComponent）

MoeCharInputComponent:GenerateIdleShowStateData() 设置 IdleShowStateData，包含：CurrentIdleShowIdx / bSurroundingsIdleShowSwitch / bIsHitSurroundingsProbability

截图：GenerateIdleShowStateData 代码

![图片](https://prod-files-secure.s3.us-west-2.amazonaws.com/54c5f1d3-510d-815b-99f0-0003f4ecef71/9f69b755-8864-4488-8648-6b5dcf4ae7b4/net-sync-03-generate-idleshow.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466YNMXGGJX%2F20260429%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260429T100040Z&X-Amz-Expires=3600&X-Amz-Security-Token=IQoJb3JpZ2luX2VjECoaCXVzLXdlc3QtMiJIMEYCIQDptF1VTnwNkQLq17QmWouEgsQDcHahIbxlHgTNLXc8uAIhAPEmM0lACho%2Fdre0a9Ci8TrXVIcG5NL11pILh5xcwLGrKogECPP%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEQABoMNjM3NDIzMTgzODA1Igyg44UDhjR5aq%2BDU90q3AOq7YU%2FFIxv%2Bjig4e2Fe0St3JrZW4WHZRfOdfBHOAAtF%2FLUlQsSVVQuHmDsbslqK5IK%2F3KrjxF2En%2FFrmQcYFzCiZownv2bPfCqBsJma20kTpeqK3wg9h9c9ZnthHYocR1HQasjZ8Ijp%2FW%2FLoLXWwQsNGFT6hWEdDxvG7ZOkBG7DlRx0XQ5Muz27pHjZbAmsQG62pEcGodoLlgi9JThCFqai595jjG3sO4nLe85V2knyvAQyrNasLYdL1AXk2527Nd9CxmTK4c8KjUrv7Ujl3rDMgZsZPtG2y%2F%2BTEctlyXRXv0XPnrfwAPjkfGi4EUUyQhCqg3sIrys3vsWuQtmqoQuCaT9Llv%2Bfj%2FvgG%2Bp3GLS1QaKVqlPICyLkxzeQTcvyObSg%2BRIJriGpq8Ll2TMz%2BN5x7MKc6URdGHUaapl4LlPwBPrMUpTynja5bqS0ISTrQQ%2F8SZba0ujxlPNk8FN28CBPmYLNOqk8Msw%2BpZq%2BIXM8T2P2slRxbDeDrFttBxiZ%2Fy2IDbL9J2ebXB6uaCWSnDkFoYYwkjArSwlddajTuQ7xleA604ByrG29xkZhE0BF6ybQszhqrXXjtRlffdsYDLQSOjwvFrEIZt2Me9HqXKUZwHamIoNn9MRETVr4zDWqMfPBjqkAWvDFp%2F3tmpD3aW20VRvCl3ldaHyXWi4tEJ%2FTdQks3yyvIvzORcTyDcZCjBTduFJWiqpwW97rSttBIiA97sjTIJ0oN4rL0ucpABLwhxWjaFiqlwuvkQk%2BkwXSef0e%2BBOR0HLY4eH9MiO0OJu1zgb0P7py0Ipxh9c8koRlnJxi7aZV5v%2BXJQhKBDAPDhbkZLVXZCJVNi9fdsh7VSvAFgkI524FW9A&X-Amz-Signature=0febb3f5ea4eb39cdd68b7384d95551352444aad754abe93008967eed9cfa5a2&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)

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

![图片](https://prod-files-secure.s3.us-west-2.amazonaws.com/54c5f1d3-510d-815b-99f0-0003f4ecef71/16ce4297-1309-434d-a361-5d6d5f3af297/net-sync-06-setsync-parsesync.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466YNMXGGJX%2F20260429%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260429T100040Z&X-Amz-Expires=3600&X-Amz-Security-Token=IQoJb3JpZ2luX2VjECoaCXVzLXdlc3QtMiJIMEYCIQDptF1VTnwNkQLq17QmWouEgsQDcHahIbxlHgTNLXc8uAIhAPEmM0lACho%2Fdre0a9Ci8TrXVIcG5NL11pILh5xcwLGrKogECPP%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEQABoMNjM3NDIzMTgzODA1Igyg44UDhjR5aq%2BDU90q3AOq7YU%2FFIxv%2Bjig4e2Fe0St3JrZW4WHZRfOdfBHOAAtF%2FLUlQsSVVQuHmDsbslqK5IK%2F3KrjxF2En%2FFrmQcYFzCiZownv2bPfCqBsJma20kTpeqK3wg9h9c9ZnthHYocR1HQasjZ8Ijp%2FW%2FLoLXWwQsNGFT6hWEdDxvG7ZOkBG7DlRx0XQ5Muz27pHjZbAmsQG62pEcGodoLlgi9JThCFqai595jjG3sO4nLe85V2knyvAQyrNasLYdL1AXk2527Nd9CxmTK4c8KjUrv7Ujl3rDMgZsZPtG2y%2F%2BTEctlyXRXv0XPnrfwAPjkfGi4EUUyQhCqg3sIrys3vsWuQtmqoQuCaT9Llv%2Bfj%2FvgG%2Bp3GLS1QaKVqlPICyLkxzeQTcvyObSg%2BRIJriGpq8Ll2TMz%2BN5x7MKc6URdGHUaapl4LlPwBPrMUpTynja5bqS0ISTrQQ%2F8SZba0ujxlPNk8FN28CBPmYLNOqk8Msw%2BpZq%2BIXM8T2P2slRxbDeDrFttBxiZ%2Fy2IDbL9J2ebXB6uaCWSnDkFoYYwkjArSwlddajTuQ7xleA604ByrG29xkZhE0BF6ybQszhqrXXjtRlffdsYDLQSOjwvFrEIZt2Me9HqXKUZwHamIoNn9MRETVr4zDWqMfPBjqkAWvDFp%2F3tmpD3aW20VRvCl3ldaHyXWi4tEJ%2FTdQks3yyvIvzORcTyDcZCjBTduFJWiqpwW97rSttBIiA97sjTIJ0oN4rL0ucpABLwhxWjaFiqlwuvkQk%2BkwXSef0e%2BBOR0HLY4eH9MiO0OJu1zgb0P7py0Ipxh9c8koRlnJxi7aZV5v%2BXJQhKBDAPDhbkZLVXZCJVNi9fdsh7VSvAFgkI524FW9A&X-Amz-Signature=4835faea85d2fb88809a5503b1fb6e4f9f0254ffa23348ed131ad91b2cbe7e71&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)

---

## 8️⃣ 完整调用链流程图

左侧：本地状态切换链路 → 右侧：网络同步链路

- UpdateIdleShow → GenerateIdleShowStateData → TryEnterActionState → TryEnterState → EnterState → CheckStateChange

- CheckStateChange（虚线）→ SetSyncStateData → AddOrSetSyncDataBool → ParseSyncStateData → GetSyncDataFloat

- 最终执行：ExecutiveSyncMotionState / ExecutiveStateChange

![图片](https://prod-files-secure.s3.us-west-2.amazonaws.com/54c5f1d3-510d-815b-99f0-0003f4ecef71/1858ca10-38db-457d-988c-574b3360181f/net-sync-07-flowchart.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466YNMXGGJX%2F20260429%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260429T100040Z&X-Amz-Expires=3600&X-Amz-Security-Token=IQoJb3JpZ2luX2VjECoaCXVzLXdlc3QtMiJIMEYCIQDptF1VTnwNkQLq17QmWouEgsQDcHahIbxlHgTNLXc8uAIhAPEmM0lACho%2Fdre0a9Ci8TrXVIcG5NL11pILh5xcwLGrKogECPP%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEQABoMNjM3NDIzMTgzODA1Igyg44UDhjR5aq%2BDU90q3AOq7YU%2FFIxv%2Bjig4e2Fe0St3JrZW4WHZRfOdfBHOAAtF%2FLUlQsSVVQuHmDsbslqK5IK%2F3KrjxF2En%2FFrmQcYFzCiZownv2bPfCqBsJma20kTpeqK3wg9h9c9ZnthHYocR1HQasjZ8Ijp%2FW%2FLoLXWwQsNGFT6hWEdDxvG7ZOkBG7DlRx0XQ5Muz27pHjZbAmsQG62pEcGodoLlgi9JThCFqai595jjG3sO4nLe85V2knyvAQyrNasLYdL1AXk2527Nd9CxmTK4c8KjUrv7Ujl3rDMgZsZPtG2y%2F%2BTEctlyXRXv0XPnrfwAPjkfGi4EUUyQhCqg3sIrys3vsWuQtmqoQuCaT9Llv%2Bfj%2FvgG%2Bp3GLS1QaKVqlPICyLkxzeQTcvyObSg%2BRIJriGpq8Ll2TMz%2BN5x7MKc6URdGHUaapl4LlPwBPrMUpTynja5bqS0ISTrQQ%2F8SZba0ujxlPNk8FN28CBPmYLNOqk8Msw%2BpZq%2BIXM8T2P2slRxbDeDrFttBxiZ%2Fy2IDbL9J2ebXB6uaCWSnDkFoYYwkjArSwlddajTuQ7xleA604ByrG29xkZhE0BF6ybQszhqrXXjtRlffdsYDLQSOjwvFrEIZt2Me9HqXKUZwHamIoNn9MRETVr4zDWqMfPBjqkAWvDFp%2F3tmpD3aW20VRvCl3ldaHyXWi4tEJ%2FTdQks3yyvIvzORcTyDcZCjBTduFJWiqpwW97rSttBIiA97sjTIJ0oN4rL0ucpABLwhxWjaFiqlwuvkQk%2BkwXSef0e%2BBOR0HLY4eH9MiO0OJu1zgb0P7py0Ipxh9c8koRlnJxi7aZV5v%2BXJQhKBDAPDhbkZLVXZCJVNi9fdsh7VSvAFgkI524FW9A&X-Amz-Signature=9ba623c8e49f005b983fb808fda769e7cfdf55390d3ec9894ed749a7771f570b&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)

---

## 📚 参考文档

iWiki 网络同步文档：https://iwiki.woa.com/p/4009438969

iWiki 相关参考：https://iwiki.woa.com/p/4009201134

