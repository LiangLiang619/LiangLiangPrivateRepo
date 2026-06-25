# 白名单与外部模式定义

## Lua require 白名单前缀

以下前缀开头的 `require` 目标**不算外部依赖**：

| 前缀 | 含义 |
|------|------|
| `LetsGo3C.` | 本仓库模块 |
| `LetsGoSDK.` | SDK 共享底座（用户确认允许） |
| `UE4.` | UnLua 引擎绑定 |
| `UnLua.` | UnLua 框架 |

以下**单段**模块名（无点号）属于 Lua 标准库，白名单放行：

```
string, table, math, io, os, coroutine, package, debug, utf8, bit, bit32, ffi, jit
```

UE4.Class 继承使用相同白名单逻辑：`UE4.Class("LetsGo3C.xxx")` = OK，`UE4.Class("LetsGo.xxx")` = 外部。

## Lua require 外部分类

不在白名单内的 require 目标按首段前缀分类：

| 首段前缀 | category 标签 |
|---------|--------------|
| `LetsGo.` | `LetsGo` |
| `Feature.` | `Feature` |
| `ProjectT.` | `ProjectT` |
| 其他 | `Other` |

## 硬编码资产路径白名单

字符串中 `/Game/...` 路径，以下前缀**不算外部**：

| 前缀 | 含义 |
|------|------|
| `/Game/LetsGo3C/` | 本仓库 |
| `/Game/LetsGoSDK/` | SDK |
| `/Game/Engine/` | 引擎 |

以下路径模式直接忽略（非 Content 资产）：

- `/Script/` 开头
- `/Engine/` 开头（非 `/Game/Engine/`）

## 硬编码资产路径外部分类

| 路径前缀 | category |
|---------|----------|
| `/Game/LetsGo/` | `LetsGo` |
| `/Game/Feature/` | `Feature` |
| `/Game/ProjectT/` 或 `/Game/Feature/ProjectT/` | `ProjectT` |
| 其他 `/Game/...` | `Other` |

## 全局变量白名单

| 模式 | 含义 |
|------|------|
| `MOE_3C.*` | 本仓库专属命名空间，不报告 |
| `_G.LetsGoSDK*` | SDK 全局，白名单 |

**例外**：以下 `MOE_3C.<field>` 虽在命名空间内，但运行时回退到 `_MOE`，仍报告为外部依赖：

## MOE_3C 外部回退字段（metatable __index fallback）

| 字段名 | 来源 | 说明 |
|--------|------|------|
| `DsInstance` | `_MOE.DsInstance` | DS 服务端实例 |
| `LobbyUtils` | `_MOE.LobbyUtils` | 大厅工具 |
| `ItemEffectUtil` | `_MOE.ItemEffectUtil` | 道具效果工具 |
| `HomeGame` | `_MOE.HomeGame` | 家园玩法 |
| `UGC` | `_MOE.UGC` | UGC 模块 |
| `WindowName` | `_MOE.WindowName` | 窗口名枚举（proxy） |
| `SocketNameEnum` | `_MOE.SocketNameEnum` | Socket 名枚举 |
| `UGCGameStatic` | `_MOE.UGCGameStatic` | UGC 静态工具 |
| `GasAbilityManager` | `_MOE.GasAbilityManager` | GAS 能力管理器 |

可通过 `--moe3c-fallback-fields` CLI 参数覆盖此列表。

## 全局变量外部模式

| 正则 | 说明 |
|------|------|
| `_MOE\.\w+` | LetsGo 仓库注入的全局表访问 |
| `_G\.(LetsGo\|Feature\|ProjectT)\w*` | 显式跨仓库全局 |

## 业务关键词（3C 不应包含的业务逻辑标识）

来源：`ue-3c-lua-migration` skill 业务逻辑识别规则

| 关键词 | 说明 |
|--------|------|
| `Farm` | 农场玩法 |
| `Arena` | 竞技场 |
| `UGC` | 用户创作 |
| `Chase` | 追逐模式 |
| `Chest` | 宝箱 |
| `Home` | 家园 |
| `StarP` | 星派对（含 StarParty 等派生词） |
| `Community` | 社区模块 |
| `Lobby` | 大厅 |
| `Commercial` | 商业化 |

匹配方式：大小写不敏感，允许作为前缀/后缀/中缀出现。
可通过 `--biz-keywords` CLI 参数覆盖此列表。

## UE 资产 imports 白名单

`.uasset` imports / FName 表中的路径，以下前缀**白名单**：

| 前缀 | 含义 |
|------|------|
| `/Game/LetsGo3C/` | 本仓库 |
| `/Game/LetsGoSDK/` | SDK |
| `/Game/Engine/` | 引擎资产 |
| `/Script/` | C++ 模块（非 Content） |
| `/Engine/` | 引擎内建 |
| `/Game/Developers/` | 开发者临时（忽略） |

外部分类规则同硬编码资产路径。
