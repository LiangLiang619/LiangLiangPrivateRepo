# 事件归属分类准则

> **定位**：判断一个外部事件 key 是否应迁入 LetsGo3C 的标准参考。
> 本规则由 @yuliangjing 在 2026-06-23 的迁移决策会话中确认。

## 核心原则

**3C 仓库承载 Character / Controller / Camera 三个 C 的基础能力层**，
凡是与角色操控直接相关的事件——无论载具、道具、还是玩家属性——都应归入 3C。

## 归属规则

### 归 3C（enter_3c = 是）

| 领域 | 关键词 / 匹配模式 | 示例 |
|------|-------------------|------|
| **载具** | `Vehicle` / `ExclusiveVehicle` / `Ride` / `GetOn` / `GetOff` / `Seat` | `ON_SET_DATA_WITH_EXCLUSIVE_VEHICLE`、`ON_VEHICLE_SEAT_CHANGE` |
| **道具** | `Prop` / `HandHold` / `ItemChange` / `Energy` / `ForbiddenPick` | `ON_PROP_ENERGY_CHANGE`、`ON_HANDHOLD_BLEND_TYPE_CHANGE` |
| **玩家** | `Player` / `PlayerInfo` / `PlayerStatus` / `OnRep_Player*` | `PlayerInfoEvents.OnRep_PlayerStatus` |
| **角色 Buff / 状态** | `Buff` / `Stealth` / `CharState` | `ON_CHAR_STEALTH_BUFF_STATE_CHANGED` |
| **Avatar 外观** | `SkeletonMesh` / `AnimInstance` / `AvatarInfo` / `Skin` | `OnRefreshAnimInstance`、`ON_CHARACTER_EXTERNAL_SKELETONMESH_CHANGED` |
| **Controller ↔ Camera** | `ControllerBind` / `Camera` / `FPS` | `NOTIFY_POST_CONTROLLER_BIND_CAMERA_SUCCESS` |
| **手持物基础组件** | `HandHold` / `BlendType` / `ForceExit_HandHold` | `OnForceExit_HandHoldLight_UseState` |
| **输入行为** | `InputAction` + 归属 3C 的领域（如载具输入） | `InputActionEvents.ExclusiveVehicleInputAction` |

### 不归 3C（enter_3c = 否）

| 领域 | 关键词 / 匹配模式 | 示例 | 理由 |
|------|-------------------|------|------|
| **社区业务** | `CommunityClient.*` / `Lobby*` | `CommunityClient.OnCharacterDisturbStateChanged` | 社区场景专属 |
| **UGC 平台** | `UGC_*` / `ON_UGC_*` | `ON_UGC_ANIM_STATE_COMPONENT_POST_REFRESH_ANIM_CLASS` | UGC 扩展点 |
| **资源下载** | `GROUP_START_DOWNLOAD` | `ON_GROUP_START_DOWNLOAD` | 资产管理层而非 3C 角色能力 |
| **排行榜 UI** | `BILLBOARD_RANK*` | `ONUPDATE_BILLBOARD_RANKINFO` | 业务 UI 展示层 |
| **强耦合具体道具** | 特定道具名（如 `Umbrella`） | `Interaction.ExitUmbrella` | 过于具体，不是通用道具能力 |

### 边缘案例判断

| 情况 | 判断方法 |
|------|---------|
| 事件名同时含"载具 + UGC" | 看 **dispatch 端**所在文件：若在 3C 组件内 dispatch → 归 3C |
| 事件名含"Skill" + "Prop" | 看 **语义重心**：`ON_SKILL_HANDHOLD_CANCEL_USE_PROP` 重心在"取消使用道具"→ 归 3C |
| 事件名含通用动词（`OnRefresh` / `OnDestroy`） | 看 **参数签名和 dispatch 上下文**：若参数为角色 UID + 3C 组件引用 → 归 3C |
| 事件已在 `LetsGo3CEvents.lua` 中 | **跳过迁移**，仅在 Phase 1 校对 value string 一致性 |

## 维护记录

- 2026-06-23 @yuliangjing 初版确认
