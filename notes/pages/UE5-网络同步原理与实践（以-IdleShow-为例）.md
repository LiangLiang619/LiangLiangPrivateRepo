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

![图片](https://prod-files-secure.s3.us-west-2.amazonaws.com/54c5f1d3-510d-815b-99f0-0003f4ecef71/4344ed5a-2b22-4293-b299-12da8c5ea3ee/net-sync-04-FMoeActionStateDataProxy.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466VX35X3CF%2F20260507%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260507T080306Z&X-Amz-Expires=3600&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEOj%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIQCulK5AFcTfGWuzgcrlJOGhtqV6TImKOI99tU5eXzNV%2BgIgLN%2BDHGiC%2BJTixMV8iyqIbNpCFYtftWEpI6VTKUwVlJYqiAQIsf%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FARAAGgw2Mzc0MjMxODM4MDUiDPfWqWm0hghk%2BTKitSrcA4k2uJSYrvps3V%2FkWYTxYgEXlUwPZOSo5PKrFq%2FlwAMv6rtdB97f1t99vuALD5hxBm6N%2FVHUlXyw31WUU09qi0vIfnKDw5tgw80axrA9XQI79VAkHbTkAgjFlcg8sG0UT9zSzwegtWK5c%2BtShYRIVEldGyi4pRgXHryI%2B21n7Rvk7LmPUyBwEl30ldzWDkSXfpWkE9ERnDEyGt%2Bd30NZEOa4wFZc43juC7G03meuV5Oo2nm%2Fz2lat6U1U%2FC8GC9Pvt%2BdVTXW3o9yX7kUUJPfn1%2BTMkXV7F7T8w5asi0FWKKadqHqRqVftFkeFGHd1pOor95sDy20Gg9eiyx56%2BY25%2F4Gk4Bjv8nzJ%2FrTBuHl3IgLP7osRoKlb9pd3KNPaIOKuIQZpO1hgHjMVXXVdiiyw4xImq1FWr79eNjU4IFDwOBH8qFoZJk4XoXznxuOJEl68i25pvtXDoKK3K%2BBofexcnc9lKYK1K3UYY6JzjyLB1YsHmsOdMaeimQkn%2FaxfmPgUgAbtJE%2BvZeqwl%2B7ia6jWb8mcszmeUUHspM5smPrhRFTvgmvtTqFMCs7PM%2FvUDJfPl8lETWJSQvtgpf8JYvkhXtuyZikeAWqWkyUHLzXwGWcZHQqW9E9Tgi5IomhMP%2F%2F8M8GOqUBIvZkY9Up7vExKE8%2F2CS8JlHDb9XHTyJ5oM45n6An%2FqXsULSqBjcsg2cSRr52qTayYBAsDW1eWRU1tTdfkf%2BKBK5Mb0DYMiQkFxfKEHT7y%2Fc2geKioYxRYmySfK1eLbXoWrUlXw9X%2FYm0YCURRqRV8VlFtglDRJlbUbJLU4NIkwVVrAI86Nhel8WsTxBZZ2AkbDU8%2BDkhAfaLKirmvDRyxI5NdHDB&X-Amz-Signature=fadde09796fb48f7607e8ace1d9a6f23f467e475630a1d2e74e5203e4ed4ba81&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)

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

![图片](https://prod-files-secure.s3.us-west-2.amazonaws.com/54c5f1d3-510d-815b-99f0-0003f4ecef71/59b1fcd1-5e60-4aaf-a675-aa68f4c84869/net-sync-05-addbool-getbool.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466VX35X3CF%2F20260507%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260507T080306Z&X-Amz-Expires=3600&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEOj%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIQCulK5AFcTfGWuzgcrlJOGhtqV6TImKOI99tU5eXzNV%2BgIgLN%2BDHGiC%2BJTixMV8iyqIbNpCFYtftWEpI6VTKUwVlJYqiAQIsf%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FARAAGgw2Mzc0MjMxODM4MDUiDPfWqWm0hghk%2BTKitSrcA4k2uJSYrvps3V%2FkWYTxYgEXlUwPZOSo5PKrFq%2FlwAMv6rtdB97f1t99vuALD5hxBm6N%2FVHUlXyw31WUU09qi0vIfnKDw5tgw80axrA9XQI79VAkHbTkAgjFlcg8sG0UT9zSzwegtWK5c%2BtShYRIVEldGyi4pRgXHryI%2B21n7Rvk7LmPUyBwEl30ldzWDkSXfpWkE9ERnDEyGt%2Bd30NZEOa4wFZc43juC7G03meuV5Oo2nm%2Fz2lat6U1U%2FC8GC9Pvt%2BdVTXW3o9yX7kUUJPfn1%2BTMkXV7F7T8w5asi0FWKKadqHqRqVftFkeFGHd1pOor95sDy20Gg9eiyx56%2BY25%2F4Gk4Bjv8nzJ%2FrTBuHl3IgLP7osRoKlb9pd3KNPaIOKuIQZpO1hgHjMVXXVdiiyw4xImq1FWr79eNjU4IFDwOBH8qFoZJk4XoXznxuOJEl68i25pvtXDoKK3K%2BBofexcnc9lKYK1K3UYY6JzjyLB1YsHmsOdMaeimQkn%2FaxfmPgUgAbtJE%2BvZeqwl%2B7ia6jWb8mcszmeUUHspM5smPrhRFTvgmvtTqFMCs7PM%2FvUDJfPl8lETWJSQvtgpf8JYvkhXtuyZikeAWqWkyUHLzXwGWcZHQqW9E9Tgi5IomhMP%2F%2F8M8GOqUBIvZkY9Up7vExKE8%2F2CS8JlHDb9XHTyJ5oM45n6An%2FqXsULSqBjcsg2cSRr52qTayYBAsDW1eWRU1tTdfkf%2BKBK5Mb0DYMiQkFxfKEHT7y%2Fc2geKioYxRYmySfK1eLbXoWrUlXw9X%2FYm0YCURRqRV8VlFtglDRJlbUbJLU4NIkwVVrAI86Nhel8WsTxBZZ2AkbDU8%2BDkhAfaLKirmvDRyxI5NdHDB&X-Amz-Signature=b384719dd2fb4e40e1bad8526d673af2494a60d6a2ce7ae0d919f3ae96ed9515&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)

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

![图片](https://prod-files-secure.s3.us-west-2.amazonaws.com/54c5f1d3-510d-815b-99f0-0003f4ecef71/9da92056-7141-43fa-82ee-66b3745052fe/net-sync-01-onrep.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466VX35X3CF%2F20260507%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260507T080307Z&X-Amz-Expires=3600&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEOj%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIQCulK5AFcTfGWuzgcrlJOGhtqV6TImKOI99tU5eXzNV%2BgIgLN%2BDHGiC%2BJTixMV8iyqIbNpCFYtftWEpI6VTKUwVlJYqiAQIsf%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FARAAGgw2Mzc0MjMxODM4MDUiDPfWqWm0hghk%2BTKitSrcA4k2uJSYrvps3V%2FkWYTxYgEXlUwPZOSo5PKrFq%2FlwAMv6rtdB97f1t99vuALD5hxBm6N%2FVHUlXyw31WUU09qi0vIfnKDw5tgw80axrA9XQI79VAkHbTkAgjFlcg8sG0UT9zSzwegtWK5c%2BtShYRIVEldGyi4pRgXHryI%2B21n7Rvk7LmPUyBwEl30ldzWDkSXfpWkE9ERnDEyGt%2Bd30NZEOa4wFZc43juC7G03meuV5Oo2nm%2Fz2lat6U1U%2FC8GC9Pvt%2BdVTXW3o9yX7kUUJPfn1%2BTMkXV7F7T8w5asi0FWKKadqHqRqVftFkeFGHd1pOor95sDy20Gg9eiyx56%2BY25%2F4Gk4Bjv8nzJ%2FrTBuHl3IgLP7osRoKlb9pd3KNPaIOKuIQZpO1hgHjMVXXVdiiyw4xImq1FWr79eNjU4IFDwOBH8qFoZJk4XoXznxuOJEl68i25pvtXDoKK3K%2BBofexcnc9lKYK1K3UYY6JzjyLB1YsHmsOdMaeimQkn%2FaxfmPgUgAbtJE%2BvZeqwl%2B7ia6jWb8mcszmeUUHspM5smPrhRFTvgmvtTqFMCs7PM%2FvUDJfPl8lETWJSQvtgpf8JYvkhXtuyZikeAWqWkyUHLzXwGWcZHQqW9E9Tgi5IomhMP%2F%2F8M8GOqUBIvZkY9Up7vExKE8%2F2CS8JlHDb9XHTyJ5oM45n6An%2FqXsULSqBjcsg2cSRr52qTayYBAsDW1eWRU1tTdfkf%2BKBK5Mb0DYMiQkFxfKEHT7y%2Fc2geKioYxRYmySfK1eLbXoWrUlXw9X%2FYm0YCURRqRV8VlFtglDRJlbUbJLU4NIkwVVrAI86Nhel8WsTxBZZ2AkbDU8%2BDkhAfaLKirmvDRyxI5NdHDB&X-Amz-Signature=3ba0b56dcea5139bdce3d432eec027175c920abb1e0825b24d149e139af89007&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)

---

## 5️⃣ 组件复制是变量复制的前提

> 🚨 组件未调用 SetIsReplicated(true) → 客户端无镜像组件 → 组件内所有变量的 REPLICATED 声明全部失效！

- ✅ 组件已复制 + 变量声明复制 → 完整同步

- ❌ 组件未复制 → 客户端无组件 → 变量复制无效

- ⚠️ 组件已复制 + 变量未声明复制 → 仅同步组件框架（无数据）

截图：组件复制机制说明

![图片](https://prod-files-secure.s3.us-west-2.amazonaws.com/54c5f1d3-510d-815b-99f0-0003f4ecef71/de6ef4b4-219e-4d8b-9f16-064401414420/net-sync-02-component-replication.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466VX35X3CF%2F20260507%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260507T080307Z&X-Amz-Expires=3600&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEOj%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIQCulK5AFcTfGWuzgcrlJOGhtqV6TImKOI99tU5eXzNV%2BgIgLN%2BDHGiC%2BJTixMV8iyqIbNpCFYtftWEpI6VTKUwVlJYqiAQIsf%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FARAAGgw2Mzc0MjMxODM4MDUiDPfWqWm0hghk%2BTKitSrcA4k2uJSYrvps3V%2FkWYTxYgEXlUwPZOSo5PKrFq%2FlwAMv6rtdB97f1t99vuALD5hxBm6N%2FVHUlXyw31WUU09qi0vIfnKDw5tgw80axrA9XQI79VAkHbTkAgjFlcg8sG0UT9zSzwegtWK5c%2BtShYRIVEldGyi4pRgXHryI%2B21n7Rvk7LmPUyBwEl30ldzWDkSXfpWkE9ERnDEyGt%2Bd30NZEOa4wFZc43juC7G03meuV5Oo2nm%2Fz2lat6U1U%2FC8GC9Pvt%2BdVTXW3o9yX7kUUJPfn1%2BTMkXV7F7T8w5asi0FWKKadqHqRqVftFkeFGHd1pOor95sDy20Gg9eiyx56%2BY25%2F4Gk4Bjv8nzJ%2FrTBuHl3IgLP7osRoKlb9pd3KNPaIOKuIQZpO1hgHjMVXXVdiiyw4xImq1FWr79eNjU4IFDwOBH8qFoZJk4XoXznxuOJEl68i25pvtXDoKK3K%2BBofexcnc9lKYK1K3UYY6JzjyLB1YsHmsOdMaeimQkn%2FaxfmPgUgAbtJE%2BvZeqwl%2B7ia6jWb8mcszmeUUHspM5smPrhRFTvgmvtTqFMCs7PM%2FvUDJfPl8lETWJSQvtgpf8JYvkhXtuyZikeAWqWkyUHLzXwGWcZHQqW9E9Tgi5IomhMP%2F%2F8M8GOqUBIvZkY9Up7vExKE8%2F2CS8JlHDb9XHTyJ5oM45n6An%2FqXsULSqBjcsg2cSRr52qTayYBAsDW1eWRU1tTdfkf%2BKBK5Mb0DYMiQkFxfKEHT7y%2Fc2geKioYxRYmySfK1eLbXoWrUlXw9X%2FYm0YCURRqRV8VlFtglDRJlbUbJLU4NIkwVVrAI86Nhel8WsTxBZZ2AkbDU8%2BDkhAfaLKirmvDRyxI5NdHDB&X-Amz-Signature=9525609f8cd08b236e29c24b1778cc3417a3f0939aa9d7c0e06aff39a082c762&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)

---

## 6️⃣ 时序注意：网络同步 > OnBeginPlay

> ⏱️ 网络同步数据回调的时序通常早于 OnBeginPlay。如果同步回调中使用了 OnBeginPlay 里初始化的字段，此时字段尚未初始化，会导致空引用或逻辑错误。

---

## 7️⃣ 实战示例：IdleShow 随机数同步

> 🎯 问题：进入 IdleShow 或时装 IdleShow 时需要随机选取动作，不同端生成的随机数不同，必须同步主控端结果。

### Step 1：生成 StateData（MoeCharInputComponent）

MoeCharInputComponent:GenerateIdleShowStateData() 设置 IdleShowStateData，包含：CurrentIdleShowIdx / bSurroundingsIdleShowSwitch / bIsHitSurroundingsProbability

截图：GenerateIdleShowStateData 代码

![图片](https://prod-files-secure.s3.us-west-2.amazonaws.com/54c5f1d3-510d-815b-99f0-0003f4ecef71/9f69b755-8864-4488-8648-6b5dcf4ae7b4/net-sync-03-generate-idleshow.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466VX35X3CF%2F20260507%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260507T080307Z&X-Amz-Expires=3600&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEOj%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIQCulK5AFcTfGWuzgcrlJOGhtqV6TImKOI99tU5eXzNV%2BgIgLN%2BDHGiC%2BJTixMV8iyqIbNpCFYtftWEpI6VTKUwVlJYqiAQIsf%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FARAAGgw2Mzc0MjMxODM4MDUiDPfWqWm0hghk%2BTKitSrcA4k2uJSYrvps3V%2FkWYTxYgEXlUwPZOSo5PKrFq%2FlwAMv6rtdB97f1t99vuALD5hxBm6N%2FVHUlXyw31WUU09qi0vIfnKDw5tgw80axrA9XQI79VAkHbTkAgjFlcg8sG0UT9zSzwegtWK5c%2BtShYRIVEldGyi4pRgXHryI%2B21n7Rvk7LmPUyBwEl30ldzWDkSXfpWkE9ERnDEyGt%2Bd30NZEOa4wFZc43juC7G03meuV5Oo2nm%2Fz2lat6U1U%2FC8GC9Pvt%2BdVTXW3o9yX7kUUJPfn1%2BTMkXV7F7T8w5asi0FWKKadqHqRqVftFkeFGHd1pOor95sDy20Gg9eiyx56%2BY25%2F4Gk4Bjv8nzJ%2FrTBuHl3IgLP7osRoKlb9pd3KNPaIOKuIQZpO1hgHjMVXXVdiiyw4xImq1FWr79eNjU4IFDwOBH8qFoZJk4XoXznxuOJEl68i25pvtXDoKK3K%2BBofexcnc9lKYK1K3UYY6JzjyLB1YsHmsOdMaeimQkn%2FaxfmPgUgAbtJE%2BvZeqwl%2B7ia6jWb8mcszmeUUHspM5smPrhRFTvgmvtTqFMCs7PM%2FvUDJfPl8lETWJSQvtgpf8JYvkhXtuyZikeAWqWkyUHLzXwGWcZHQqW9E9Tgi5IomhMP%2F%2F8M8GOqUBIvZkY9Up7vExKE8%2F2CS8JlHDb9XHTyJ5oM45n6An%2FqXsULSqBjcsg2cSRr52qTayYBAsDW1eWRU1tTdfkf%2BKBK5Mb0DYMiQkFxfKEHT7y%2Fc2geKioYxRYmySfK1eLbXoWrUlXw9X%2FYm0YCURRqRV8VlFtglDRJlbUbJLU4NIkwVVrAI86Nhel8WsTxBZZ2AkbDU8%2BDkhAfaLKirmvDRyxI5NdHDB&X-Amz-Signature=9bf52f9c06d7e5aea1292d412b1e5aed2ae4e695e2de4a01bfe5d1dda93ad0c2&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)

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

![图片](https://prod-files-secure.s3.us-west-2.amazonaws.com/54c5f1d3-510d-815b-99f0-0003f4ecef71/16ce4297-1309-434d-a361-5d6d5f3af297/net-sync-06-setsync-parsesync.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466VX35X3CF%2F20260507%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260507T080307Z&X-Amz-Expires=3600&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEOj%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIQCulK5AFcTfGWuzgcrlJOGhtqV6TImKOI99tU5eXzNV%2BgIgLN%2BDHGiC%2BJTixMV8iyqIbNpCFYtftWEpI6VTKUwVlJYqiAQIsf%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FARAAGgw2Mzc0MjMxODM4MDUiDPfWqWm0hghk%2BTKitSrcA4k2uJSYrvps3V%2FkWYTxYgEXlUwPZOSo5PKrFq%2FlwAMv6rtdB97f1t99vuALD5hxBm6N%2FVHUlXyw31WUU09qi0vIfnKDw5tgw80axrA9XQI79VAkHbTkAgjFlcg8sG0UT9zSzwegtWK5c%2BtShYRIVEldGyi4pRgXHryI%2B21n7Rvk7LmPUyBwEl30ldzWDkSXfpWkE9ERnDEyGt%2Bd30NZEOa4wFZc43juC7G03meuV5Oo2nm%2Fz2lat6U1U%2FC8GC9Pvt%2BdVTXW3o9yX7kUUJPfn1%2BTMkXV7F7T8w5asi0FWKKadqHqRqVftFkeFGHd1pOor95sDy20Gg9eiyx56%2BY25%2F4Gk4Bjv8nzJ%2FrTBuHl3IgLP7osRoKlb9pd3KNPaIOKuIQZpO1hgHjMVXXVdiiyw4xImq1FWr79eNjU4IFDwOBH8qFoZJk4XoXznxuOJEl68i25pvtXDoKK3K%2BBofexcnc9lKYK1K3UYY6JzjyLB1YsHmsOdMaeimQkn%2FaxfmPgUgAbtJE%2BvZeqwl%2B7ia6jWb8mcszmeUUHspM5smPrhRFTvgmvtTqFMCs7PM%2FvUDJfPl8lETWJSQvtgpf8JYvkhXtuyZikeAWqWkyUHLzXwGWcZHQqW9E9Tgi5IomhMP%2F%2F8M8GOqUBIvZkY9Up7vExKE8%2F2CS8JlHDb9XHTyJ5oM45n6An%2FqXsULSqBjcsg2cSRr52qTayYBAsDW1eWRU1tTdfkf%2BKBK5Mb0DYMiQkFxfKEHT7y%2Fc2geKioYxRYmySfK1eLbXoWrUlXw9X%2FYm0YCURRqRV8VlFtglDRJlbUbJLU4NIkwVVrAI86Nhel8WsTxBZZ2AkbDU8%2BDkhAfaLKirmvDRyxI5NdHDB&X-Amz-Signature=ea6b6d79b0ef6761e636003c2bc13b1f7f1815e05e9d666f706ceef2e0b65da0&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)

---

## 8️⃣ 完整调用链流程图

左侧：本地状态切换链路 → 右侧：网络同步链路

- UpdateIdleShow → GenerateIdleShowStateData → TryEnterActionState → TryEnterState → EnterState → CheckStateChange

- CheckStateChange（虚线）→ SetSyncStateData → AddOrSetSyncDataBool → ParseSyncStateData → GetSyncDataFloat

- 最终执行：ExecutiveSyncMotionState / ExecutiveStateChange

![图片](https://prod-files-secure.s3.us-west-2.amazonaws.com/54c5f1d3-510d-815b-99f0-0003f4ecef71/1858ca10-38db-457d-988c-574b3360181f/net-sync-07-flowchart.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466VX35X3CF%2F20260507%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260507T080307Z&X-Amz-Expires=3600&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEOj%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIQCulK5AFcTfGWuzgcrlJOGhtqV6TImKOI99tU5eXzNV%2BgIgLN%2BDHGiC%2BJTixMV8iyqIbNpCFYtftWEpI6VTKUwVlJYqiAQIsf%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FARAAGgw2Mzc0MjMxODM4MDUiDPfWqWm0hghk%2BTKitSrcA4k2uJSYrvps3V%2FkWYTxYgEXlUwPZOSo5PKrFq%2FlwAMv6rtdB97f1t99vuALD5hxBm6N%2FVHUlXyw31WUU09qi0vIfnKDw5tgw80axrA9XQI79VAkHbTkAgjFlcg8sG0UT9zSzwegtWK5c%2BtShYRIVEldGyi4pRgXHryI%2B21n7Rvk7LmPUyBwEl30ldzWDkSXfpWkE9ERnDEyGt%2Bd30NZEOa4wFZc43juC7G03meuV5Oo2nm%2Fz2lat6U1U%2FC8GC9Pvt%2BdVTXW3o9yX7kUUJPfn1%2BTMkXV7F7T8w5asi0FWKKadqHqRqVftFkeFGHd1pOor95sDy20Gg9eiyx56%2BY25%2F4Gk4Bjv8nzJ%2FrTBuHl3IgLP7osRoKlb9pd3KNPaIOKuIQZpO1hgHjMVXXVdiiyw4xImq1FWr79eNjU4IFDwOBH8qFoZJk4XoXznxuOJEl68i25pvtXDoKK3K%2BBofexcnc9lKYK1K3UYY6JzjyLB1YsHmsOdMaeimQkn%2FaxfmPgUgAbtJE%2BvZeqwl%2B7ia6jWb8mcszmeUUHspM5smPrhRFTvgmvtTqFMCs7PM%2FvUDJfPl8lETWJSQvtgpf8JYvkhXtuyZikeAWqWkyUHLzXwGWcZHQqW9E9Tgi5IomhMP%2F%2F8M8GOqUBIvZkY9Up7vExKE8%2F2CS8JlHDb9XHTyJ5oM45n6An%2FqXsULSqBjcsg2cSRr52qTayYBAsDW1eWRU1tTdfkf%2BKBK5Mb0DYMiQkFxfKEHT7y%2Fc2geKioYxRYmySfK1eLbXoWrUlXw9X%2FYm0YCURRqRV8VlFtglDRJlbUbJLU4NIkwVVrAI86Nhel8WsTxBZZ2AkbDU8%2BDkhAfaLKirmvDRyxI5NdHDB&X-Amz-Signature=55390fcf7f22d2cf5b1c86a75ecc978ce1edf66341e3e39fe1d9df826f62d64b&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)

---

## 📚 参考文档

iWiki 网络同步文档：https://iwiki.woa.com/p/4009438969

iWiki 相关参考：https://iwiki.woa.com/p/4009201134

