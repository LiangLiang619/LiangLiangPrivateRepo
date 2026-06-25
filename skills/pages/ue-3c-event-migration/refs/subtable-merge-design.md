# 子表事件深度合并机制设计

> **定位**：本文档说明 LetsGo3C 事件枚举中"子表型 key"如何透明合并到 `CommonEventEnum`，
> 确保源仓库（LetsGo / Feature/*）的 listener / dispatcher 代码零改动。

## 问题背景

SDK `CommonEventEnum.InitEvents()` 在 `BEFORE_INIT_EVENTS` Hook 收集到所有 `EventsFileName` 后，
按以下逻辑合并：

```lua
-- CommonEventEnum.lua L742-749
for key, value in pairs(EventsFileName) do
    local _, module = xpcall(require, _G.ErrorHandler, value)
    if module then
        CommonEventEnum[key] = module          -- ① 挂到命名空间
        CommonEventEnum.AppendEvents(module)   -- ② 平铺合并
    end
end
```

`AppendEvents` 内部（L715-722）：

```lua
function CommonEventEnum.AppendEvents(newEvents)
    for k, v in pairs(newEvents) do
        -- ... 重复检测 ...
        CommonEventEnum[k] = v    -- ⚠️ 无论 v 是 string 还是 table，直接赋值
    end
end
```

**关键陷阱**：如果 LetsGo3C 和 LetsGo 都声明了 `PlayerInfoEvents = { ... }`，
后加载的会**整表覆盖**先加载的，导致先注入的子 key 丢失。

## SDK 内置解决方案：`POST_INIT_EVENTS` Hook

SDK `CommonEventEnum.lua` L750-777 已提供 `POST_INIT_EVENTS` 钩子，
其合并逻辑**天然支持子表深度合并**：

```lua
-- L757-776（核心逻辑）
for _, postExtendEvents in ipairs(postExtendEventList) do
    for name, event in pairs(postExtendEvents) do
        if type(event) == "table" then
            if CommonEventEnum[name] and type(CommonEventEnum[name]) == "table" then
                SDK.TableUtils.Merge(CommonEventEnum[name], event)    -- ✅ 深度合并
            elseif not CommonEventEnum[name] then
                CommonEventEnum[name] = event                         -- 新 key 直接赋
            else
                SDK.Logger.LogError(...)                              -- 类型冲突报错
            end
        elseif type(name) == "string" then
            -- flat string 类型的去重 + 冲突检测
        end
    end
end
```

**这意味着**：只要把子表型事件通过 `POST_INIT_EVENTS` 注入，SDK 会自动用
`SDK.TableUtils.Merge` 合并到已有的 `CommonEventEnum.PlayerInfoEvents` 上，
不会覆盖 LetsGo 侧已注入的子 key。

## 推荐方案：双 Hook 策略

### Hook 1（已有）：`BeforeInitEvents` — 注入 flat 事件文件

维持现有的 `CommonEventEnumInitEventsHook`，通过 `EventsFileName` 注入
`LetsGo3CEvents.lua`。该文件中**只放 flat key**（string value）。

### Hook 2（新增）：`PostInitEvents` — 注入子表事件

新建 `CommonEventEnumPostInitEventsHook`，在 `POST_INIT_EVENTS` 时机，
把需要深度合并的子表 push 到 `ctx.EventsList`：

```lua
-- LetsGo3C/Script/Hooks/Event/CommonEventEnumPostInitEventsHook.lua
local CommonEventEnumPostInitEventsHook = {}

function CommonEventEnumPostInitEventsHook:Execute(ctx)
    local EventsList = ctx.EventsList
    local subtableEvents = require("LetsGo3C.Script.Core.Event.LetsGo3CSubtableEvents")
    EventsList[#EventsList + 1] = subtableEvents
end

return CommonEventEnumPostInitEventsHook
```

在 `SDK_HookConfig.lua` 追加注册：

```lua
{
    HookName    = "CommonEventEnum.PostInitEvents",
    Source      = "LetsGo3C",
    HandlerPath = "LetsGo3C.Script.Hooks.Event.CommonEventEnumPostInitEventsHook",
    Priority    = 100,
},
```

### `LetsGo3CSubtableEvents.lua` 示例结构

```lua
local LetsGo3CSubtableEvents = {
    PlayerInfoEvents = {
        OnRep_PlayerStatus = "EventOnRep_PlayerStatus",
    },
    InputActionEvents = {
        ExclusiveVehicleInputAction = "InputAction_ExclusiveVehicle",
    },
}
return LetsGo3CSubtableEvents
```

**value string 必须与源仓库声明完全一致**，保证 listener 按 string 匹配不受影响。

## 运行时等价性验证

合并完成后，以下访问路径等价（value string 相同）：

| 访问路径 | 来源 | value |
|----------|------|-------|
| `_MOE.EventEnum.PlayerInfoEvents.OnRep_PlayerStatus` | LetsGo GlobalEvents.lua | `"EventOnRep_PlayerStatus"` |
| `MOE_3C.EventEnum.PlayerInfoEvents.OnRep_PlayerStatus` | LetsGo3CSubtableEvents.lua（经 POST_INIT_EVENTS 合并） | `"EventOnRep_PlayerStatus"` |

两者指向同一张 table（`CommonEventEnum.PlayerInfoEvents`），所以：
- LetsGo 侧 `_MOE.EventManager:DispatchEvent(_MOE.EventEnum.PlayerInfoEvents.OnRep_PlayerStatus, ...)` 正常
- 3C 侧 `MOE_3C.EventManager:RegisterEvent(MOE_3C.EventEnum.PlayerInfoEvents.OnRep_PlayerStatus, ...)` 正常
- **无需修改任何 dispatch / register 调用**

## Fallback 方案（如 POST_INIT_EVENTS 不可用）

如果在某些环境中 `POST_INIT_EVENTS` Hook 未暴露（极端情况），可在 `BeforeInitEvents` 
handler 中手动 require 源仓库 module 做合并。但根据当前 SDK 代码（`CommonEventEnum.lua` L750-777），
`POST_INIT_EVENTS` 已完全就绪，建议优先使用。

## 注意事项

1. **加载顺序无关**：`POST_INIT_EVENTS` 在所有 `EventsFileName` 合并完成后触发，
   此时 LetsGo 的 `PlayerInfoEvents` 已存在于 `CommonEventEnum`，3C 的子 key 通过
   `TableUtils.Merge` 补入，不存在覆盖风险
2. **重复检测**：SDK 的 `POST_INIT_EVENTS` 合并逻辑对 flat string 有冲突检测，
   对 table 用 Merge（后者覆盖同名子 key）——同一子 key 声明两次不会报错但值以后注入为准，
   因此需保证 **value string 完全一致**
3. **新增子表 key 的判断标准**：仅当源仓库使用 `_MOE.EventEnum.SubTable.Key` 二级访问时
   才走 PostInitEvents 路径；如果在 3C 侧可以改为 flat key 访问（如 `ON_HANDHOLD_BLEND_TYPE_CHANGE`
   已被平铺化），优先走 flat 路径
