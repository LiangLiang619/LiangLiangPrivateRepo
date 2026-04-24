# 📚 游戏开发

> 共 3 条笔记 · 最后同步：2026-04-24

---

## ⭐️⭐️ Android手机包塞文件测试路径

**来源**：工作 · **创建**：2026-04-24 · #Android #LetsGo

> Android Pixel 5 塞文件路径：内部共享存储空间/Android/data/com.tencent.letsgo/files/

## 📌 核心概念
- 设备：Android Pixel 5
- 包名：com.tencent.letsgo
- 完整路径：此电脑 > Pixel 5 > 内部共享存储空间 > Android > data > com.tencent.letsgo > files
- files 目录下共 18 个项目，包含：LuaPatch、Content、System、UE4Game、StartUp 等
## 💻 目录结构
```plain text
com.tencent.letsgo/files/
├── Content/
├── FrameWorkCache/
├── LuaPatch/
├── MultiDownload/
├── NativeShader/
├── pixui/
├── RHICache/
├── StartUp/
├── System/
├── TGPA/
├── UE4Game/
├── 0.0.458.1/
├── 200006/
├── Puffet/ (%50%75%66%66%65%74)
├── _CacheDolphinInfo
├── _CheckUpdateInfo
├── CacheCleanIsAppVersionUpdateConfV2.json
└── CacheCleanMangerConfig.json (71B)
```
## ⚠️ 注意事项
- USB 连接设备后，通过 Windows 资源管理器可直接访问该路径
- 版本号：Development-0.0.458.1
- 见原截图（企业微信截图）

---

## ⭐️⭐️⭐️ 必掌握 UE5 网络同步原理与实践（以 IdleShow 为例）

**来源**：工作 · **创建**：2026-04-22 · #UE5 #Lua #网络

> UE5 网络同步核心概念：主控端/模拟端、需要同步的数据类型、FMoeActionStateDataProxy 结构体、OnRep 机制、组件复制前提，以及 IdleShow 随机数同步完整流程。

## 1️⃣ 核心概念：主控端 vs 模拟端
- 主控端：玩家当前操控的角色，拥有第一手数据
- 模拟端：其他玩家角色，通过网络同步数据模拟行为
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
---
## 5️⃣ 组件复制是变量复制的前提
- ✅ 组件已复制 + 变量声明复制 → 完整同步
- ❌ 组件未复制 → 客户端无组件 → 变量复制无效
- ⚠️ 组件已复制 + 变量未声明复制 → 仅同步组件框架（无数据）
截图：组件复制机制说明
---
## 6️⃣ 时序注意：网络同步 > OnBeginPlay
---
## 7️⃣ 实战示例：IdleShow 随机数同步
### Step 1：生成 StateData（MoeCharInputComponent）
MoeCharInputComponent:GenerateIdleShowStateData() 设置 IdleShowStateData，包含：CurrentIdleShowIdx / bSurroundingsIdleShowSwitch / bIsHitSurroundingsProbability
截图：GenerateIdleShowStateData 代码
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
---
## 8️⃣ 完整调用链流程图
左侧：本地状态切换链路 → 右侧：网络同步链路
- UpdateIdleShow → GenerateIdleShowStateData → TryEnterActionState → TryEnterState → EnterState → CheckStateChange
- CheckStateChange（虚线）→ SetSyncStateData → AddOrSetSyncDataBool → ParseSyncStateData → GetSyncDataFloat
- 最终执行：ExecutiveSyncMotionState / ExecutiveStateChange
---
## 📚 参考文档
iWiki 网络同步文档：https://iwiki.woa.com/p/4009438969
iWiki 相关参考：https://iwiki.woa.com/p/4009201134

---

## ⭐️⭐️⭐️ 必掌握 ProjectT 启动 LocalDS 的方式

**来源**：工作 · **创建**：2026-04-22 · #UE5

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
**截图2：游戏内调试面板 — 设置 LocalDSMapID 并点击连接**

---
