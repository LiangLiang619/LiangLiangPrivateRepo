# 3C Lua 扫描输出 CSV — 列字段语义说明

> 本文档是 `ue-3c-lua-scan` 输出 **16 列** CSV 的字段权威说明，供人工 review 和下游 `ue-3c-lua-migration` 参考。

## 列结构概览

每行代表 **一个被绑定的 Lua 模块**（不是一个资产）。若同一个 Lua 被多个资产绑定，会合并为一行，资产名 `|` 分隔写入 `引用链路` 列。

## v2 列变更

| 变更 | 原列名 (v1) | 新列名 (v2) | 原因 |
|------|------------|------------|------|
| 改名 | 外部资产名 | **lua文件名** | 行单位是 Lua 模块，叫"外部资产"误导 |
| 改名 | 外部资产完整路径 | **lua模块完整路径** | 同上 |
| 改名 | 直接依赖LetsGo资产数 / 列表 | **直接依赖Lua数 / 列表** | 这里依赖的是 Lua 模块 |
| 改名 | 递归依赖LetsGo资产总数 / 列表 | **递归依赖Lua总数 / 列表** | 同上 |
| 改名 | 资产父目录 / 资产子目录 | **Lua父目录 / Lua子目录** | 列描述的是 Lua 模块路径段 |
| 改名 | ProjectT资产路径（被该资产依赖） | **Lua中ProjectT硬编码引用** | 表达更精确 |
| 删除 | 引用层级 | — | 恒为 `直接绑定`，常量无信息量 |
| 删除 | 是否需要 | — | 与 `进度` 列功能重复 |
| 值调整 | 3C仓库目标路径的 lua leaf | 不再追加 `Base` 后缀 | 保持原名 |

## 完整字段表（v2 - 16 列）

| # | 列名 | 类型 | 是否空 | 含义 | 取值示例 |
|---|------|------|------|------|---------|
| 1 | lua文件名 | string | 永不空 | Lua 文件名（点号路径末段，不含 `.lua`） | `CharRPCComponent` |
| 2 | lua模块完整路径 | string | 永不空 | Lua 模块完整点号路径。同一资产命中多个 UnLua 候选时，主路径 + `[候选: A \| B]` 后缀；C++ 继承命中追加 `[native_parent=AHomeGame]`；动态绑定追加 `[resolver_hint=...]` | `LetsGo.Script.Community.Components.CharRPCComponent` |
| 3 | 3C仓库目标路径 | string | 可填占位 | 见下方"目标路径推断规则"；推断结果如 `LetsGo3C.Script.Base.{C}.{资产类型}.{LuaLeaf}`（**leaf 保留原名，不加 Base 后缀**）；无法推断 `[待确认]`，已在 SDK `[已在SDK]`，已在 3C 保持原值；动态绑定未解析时 `[待编辑器查询]` | `LetsGo3C.Script.Base.Character.Components.CharRPCComponent` |
| 4 | 引用链路（被谁依赖了） | string | 可空 | 触发该 Lua 的资产名集合（多源 ` \| ` 分隔，按资产名升序） | `BP_CommunityCharRPCComponent \| BP_LobbyCharRPCComponent` |
| 5 | 负责人 | string | 可空 | 从 `Content/LetsGo3C/Intermediate/user.json` 的 `user` 字段读 | `yuliangjing` |
| 6 | 进度 | string | 占位 | 固定 `□`，供人工填 `进行中 / 完成` | `□` |
| 7 | 搬迁方式 | string | 留空 | 留空给人工填，对齐 `ue-3c-asset-migration` 的 `搬迁方式` 列允许值（`直接搬迁` / `资产已调整，可以搬迁` / `不搬迁` 等） |  |
| 8 | Lua中ProjectT硬编码引用 | string | 可空 | 该 Lua 及其 require 闭包中出现的 `"/Game/Feature/ProjectT/..."` 字面量集合 | `/Game/Feature/ProjectT/UI/Foo` |
| 9 | 直接依赖Lua数 | int | `0` 表示无 | 该 Lua **直接 `require(...)`** 的 LetsGo 仓库 Lua 模块数（`Feature.*` 也计入；`LetsGoSDK.*` 默认排除，可用 `--include-sdk-deps` 开启） | `4` |
| 10 | 直接依赖Lua列表 | string | 可空 | 同上的点号路径列表，` \| ` 分隔 | `LetsGo.Script.A \| LetsGo.Script.B` |
| 11 | 递归依赖Lua总数 | int | `0` 表示无 | BFS 闭包内 LetsGo 仓库 Lua 模块总数（去重） | `27` |
| 12 | 递归依赖Lua列表 | string | 可空 | 上述模块的完整列表，按字典序 ` \| ` 分隔 |  |
| 13 | 玩法依赖数量 | int | `0` 表示无 | 递归闭包中"模块路径含业务关键词"的 Lua 数 | `5` |
| 14 | 全部引用玩法列表 | string | 可空 | 命中的关键词集合（去重，` \| ` 分隔） | `UGC \| Community` |
| 15 | Lua父目录 | string | 可空 | Lua 模块点号路径第 3 段（典型 = 业务分类，如 `Community`） | `Community` |
| 16 | Lua子目录 | string | 可空 | 第 4 段（典型 = 文件类型，如 `Components`） | `Components` |
| 17 | 引用类型 | enum | 必填 | `UnLuaInterface` / `UnLuaInterface(C++继承)` / `UnLuaInterface(动态-MCP)` / `UnLuaInterface(动态-文件名匹配)` / `UnLuaInterface(动态)` / `UIWndNameToLuaPath` / `[未绑定]` / `[文件缺失]` | `UnLuaInterface(动态-文件名匹配)` |

## 关键语义澄清

### 目标路径推断规则（列 3）

**3C 仓库标准目录约定**（user 提供）：

```
/Content/LetsGo3C/Script/Base/
├── Character/                  ← 角色蓝图基类
│   ├── 资产类型/  ← 任意子分类（Components / Animation / ConfigData / Blueprint / States ...）
│   ├── Components/
│   ├── Animation/
│   └── ConfigData/
├── Controller/                 ← 角色控制器基类
│   ├── 资产类型/
│   ├── Components/
│   └── ConfigData/
└── Camera/                     ← 相机基类
    ├── 资产类型/
    ├── Components/
    └── ConfigData/
```

`/Content/LetsGo3C/Assets/Base/` 下的 .uasset 资产目录结构与之**严格对齐**（同样三大类 + 同样的子分类名）——所以：

**Strategy 1（首选 / 最准）**：用 BP 资产在 `LetsGo3C/Assets/Base/{C}/{资产类型}/` 的真实位置反推：

```
/Game/LetsGo3C/Assets/Base/Character/Components/BP_Foo
        → LetsGo3C.Script.Base.Character.Components.<LuaLeaf>

/Game/LetsGo3C/Assets/Base/Camera/Blueprint/BP_DefaultCamera
        → LetsGo3C.Script.Base.Camera.Blueprint.<LuaLeaf>
```

资产被多个 BP 引用时：**优先取在 LetsGo3C/Assets/Base/ 标准目录下的那个**作为反推源（避免被混进来的非标准位置 BP 干扰）。

**Strategy 2（兜底）**：BP 物理路径不在 3C 标准目录时，按 Lua 模块路径关键词判 `{C}`：

| 关键词类别 | 命中 → {C} |
|---|---|
| Character / Char / Pawn / Avatar / Anim / ABP / Mesh / Skeletal / IK / Physics / Footprint / Billboard / LerpLocation / Sound / ReceiveHit / Push / RPC | Character |
| Controller / Input / Movement / Locomotion / Move | Controller |
| Camera / View / Spring / Boom / FOV | Camera |

`{资产类型}` 默认填 `Components`（最常见）。需要其他子类型时人工修正。

**Strategy 3（终极兜底）**：两条都不命中 → `[待确认]`。

**Lua leaf 命名**：**保留原模块名，不加 Base 后缀**。`MoeCharStateRebirth` → `MoeCharStateRebirth`（v1 曾追加 Base，v2 已撤销）。

### "LetsGo 资产" = Lua 模块（不是 .uasset）

列 10-13 中"LetsGo 资产"沿用了 `ue-recursive-deps-scan` 的列名以保持 CSV 兼容，但在本 Skill 上下文中含义是 **LetsGo 仓库下的 Lua 模块**——回答 "搬这个 Lua，会拖出多少其它 Lua"。

判定规则：

| 模块前缀 | 是否计入"LetsGo 资产" |
|---------|--------------------|
| `LetsGo.Script.*` | ✅ 计入 |
| `Feature.<X>.Script.*` | ✅ 计入（业务 Feature Lua） |
| `LetsGo3C.Script.*` | ❌ 不计入（已经在 3C 仓库） |
| `LetsGoSDK.Script.*` | ❌ 默认不计入（已迁 SDK，加 `--include-sdk-deps` 开启） |

### "玩法关键词"匹配规则

清单（大小写不敏感、子串匹配；`StarP` 前缀匹配覆盖 `StarParty` 等派生词）：

```
Farm  Arena  UGC  Chase  Chest  Home  StarP  Community  Lobby  Commercial
```

模块点号路径中任一段命中即视为玩法 Lua。例如：

- `LetsGo.Script.UGC.Components.X` → 命中 `UGC`
- `LetsGo.Script.Community.Lobby.Y` → 命中 `Community` + `Lobby`
- `Feature.Farm.Script.Z` → 命中 `Farm`

### "引用类型"取值

| 取值 | 来源 | 备注 |
|------|------|------|
| `UnLuaInterface` | BP 重载 `GetModuleName()`，FName 表命中 | 多匹配时取第一个，候选写入列 2 末尾 `[候选: ...]` |
| `UnLuaInterface(C++继承)` | BP 没自重载，但 native 父类的 `GetModuleName_Implementation` 在 C++ 源码中命中 | 列 2 末尾追加 `[native_parent=AHomeGame]` 用于审查；如有多个 native 类候选写入列 2 末尾 |
| `UnLuaInterface(动态-MCP)` | imports 含 `UnLuaInterface`、前两类未命中、用 MCP 的 `graph.describe` 在 BP 的 GetModuleName 图里读到字面量返回值 | 列 2 写真路径；列 3 用真路径反推 3C 目标 |
| `UnLuaInterface(动态-文件名匹配)` | imports 含 `UnLuaInterface`、MCP 未命中（或没开），用 Lua 文件名启发式（去/留 BP_ 前缀候选）从全工程 `.lua` 索引中命中唯一文件 | 列 2 写真路径；列 11/13 含完整 require 依赖统计；列 2 末尾若有同名候选会标注 |
| `UnLuaInterface(动态)` | imports 含 `UnLuaInterface` 但**三层解析全失败**（无 MCP 结果、无文件名匹配） | 列 2 写 `[动态计算: 调用 <resolver_func>]`，列 3 写 `[待编辑器查询]`；自动加入 `pending_mcp_resolution.json` 等下次 MCP 跑 |
| `UIWndNameToLuaPath` | WBP 在 `UIWndNameToLuaPath*.lua` 配置表中有项 | 已合并主表 + Feature 表 + SDK 表 |
| `[未绑定]` | WBP 命名前缀但未在 widget_map 命中 | 占位行供人工核查是否漏配 |
| `[文件缺失]` | 输入资产的 .uasset 在 Content 下找不到 | 占位行 |

**优先级**：`UnLuaInterface(self)` > `UnLuaInterface(C++继承)` > `UnLuaInterface(动态)` —— 前三种互斥兜底，每个绑 Lua 的 BP 必出至少一行；`UIWndNameToLuaPath` 与前三种可并存（WBP 同时有 BP 重载 + 配置表项 → 输出两行）。

**铁律**：**.uasset imports 含 `UnLuaInterface` → 必输出至少一行**。若一个 BP 实现了 UnLuaInterface 但在 CSV 中完全找不到对应行，说明 skill 有 bug，请反馈。

### "C++继承" 路径的可靠性边界

- **能扫到的情况**：C++ 源码中存在 `Class::GetModuleName_Implementation` 函数 + `return TEXT("LetsGo.Script....")` 字面量。
- **扫不到的情况**：
  - 返回值通过变量拼接（如 `FString::Printf(TEXT("LetsGo.Script.%s"), *Name)`）—— 我们只匹配静态字面量
  - 返回值放在头文件里 `inline` 实现 —— 当前只扫 `*.cpp`，可加 `*.h` 扩展但代价更高
  - C++ 类实现 `IsLuaBindClass` 或其他非标准接口（罕见）
- 当 super_name 为空、所有 native imports 均不在 cpp_map 中时，BP 输出 0 条绑定（非 WBP 直接跳过；WBP 走未绑定占位）。这种行在 review 阶段需要人工查看是否真不绑 Lua、还是 cpp_map 漏扫。

## 示例行（节选，v2 格式 16 列）

```csv
lua文件名,lua模块完整路径,3C仓库目标路径,引用链路（被谁依赖了）,负责人,进度,搬迁方式,Lua中ProjectT硬编码引用,直接依赖Lua数,直接依赖Lua列表,递归依赖Lua总数,递归依赖Lua列表,玩法依赖数量,全部引用玩法列表,Lua父目录,Lua子目录,引用类型
CharRPCComponent,LetsGo.Script.Community.Components.CharRPCComponent,LetsGo3C.Script.Base.Character.Components.CharRPCComponent,BP_CommunityCharRPCComponent,yuliangjing,□,,,4,LetsGo.Script.Community.Utils.RPCUtils | ...,27,...,5,Community,Community,Components,UnLuaInterface
HomeGame,LetsGo.Script.Modplay.Core.GameMode.Games.Home.HomeGame  [native_parent=AHomeGame],LetsGo3C.Script.Base.Character.Modplay.HomeGame,BP_HomeGameInstance,yuliangjing,□,,,3,...,18,...,1,Home,Modplay,Core,UnLuaInterface(C++继承)
HomePanelView,LetsGo.Script.UI.Home.HomePanelView,[待确认],WBP_HomePanel,yuliangjing,□,,,3,...,18,...,3,Home,UI,Home,UIWndNameToLuaPath
(无绑定@WBP_OrphanWidget),,[待确认],WBP_OrphanWidget,yuliangjing,□,,,0,,0,,0,,,,[未绑定]
```

## 二次使用建议

1. **人工 review 重点**：
   - `引用类型 = [未绑定]` 的行 → 检查 widget_map 是否漏配 / Lua 路径是否手写在 BP 内部
   - `引用类型 = UnLuaInterface(C++继承)` 的行 → C++ 父类一并搬迁/重命名会影响一批 BP，`引用链路` 列出受影响的 BP；`lua模块完整路径` 末尾 `[native_parent=...]` 是父类名
   - `引用类型 = UnLuaInterface(动态)` 的行 → **三层解析全失败**的 BP，`lua模块完整路径` 给出 resolver 函数名，需跑 MCP 或人工查 BP graph 拿到真实 Lua 路径（也会自动写到 `cache/pending_mcp_resolution.json`）
   - `玩法依赖数量 > 0` 的行 → 这些 Lua 含业务依赖，需走 3C 业务子类化方案，不能直接整体搬迁
   - `3C仓库目标路径 = [待确认]` / `[待编辑器查询]` 的行 → 需要在 `ue-3c-lua-migration` Phase 2 设计阶段决策
   - 控制台输出里 `输入资产总数 - 输出行数` 较大的情况 → 大量 BP 既没自重载、native parent 又不在 cpp_map 中、imports 也没 UnLuaInterface，可能是那些 BP 确实不绑 Lua（动画/曲线/数据表等）

2. **下游 `ue-3c-lua-migration` 复用**：
   - `lua模块完整路径` → 作为 `源 Lua 路径`
   - `3C仓库目标路径` → 作为 `目标 Lua 路径` 初稿
   - `引用链路（被谁依赖了）` → 作为"哪些资产会依赖该 Lua"的对照
   - `直接依赖Lua列表 / 递归依赖Lua列表` → Phase 1 分析阶段的依赖清单输入
