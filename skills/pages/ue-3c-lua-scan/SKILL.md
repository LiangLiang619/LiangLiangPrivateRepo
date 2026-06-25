---
name: ue-3c-lua-scan
description: >-
  Scan all Lua scripts bound to UE assets in LetsGo3C (or any asset list/root path)
  via THREE binding mechanisms — (1) UnLuaInterface BP self-override of
  GetModuleName, (2) UnLuaInterface inherited from a C++ native parent class that
  overrides GetModuleName_Implementation in source, and (3) UIWndNameToLuaPath
  WBP config map — by directly parsing .uasset binary (FName table + native
  parent class via super_name / Class imports), the project's
  UIWndNameToLuaPath_*.lua config files, and the project's Source/ + Plugins/
  *.cpp for GetModuleName_Implementation literals. For each bound Lua, also
  computes its require BFS closure stats (direct/recursive LetsGo Lua module
  count + business-keyword hits + ProjectT hardcoded refs) and infers a
  suggested 3C target subdirectory (Character/Controller/Camera). Outputs a
  19-column CSV aligned with the ue-recursive-deps-scan schema, ready to feed
  ue-3c-lua-migration. Use when the user asks 3C Lua 扫描 /
  3C 资产对应 Lua / 扫描 LetsGo3C Lua 绑定 / scan 3c lua binding /
  资产 Lua 映射 CSV / 3C 资产Lua关联.
---

# UE 3C Lua Binding Scanner

> 把"LetsGo3C 资产列表 / 资产根目录"扩展为"每条资产绑定的 Lua 文件 + 该 Lua 的迁移成本"19 列 CSV，作为 `ue-3c-lua-migration` 的输入。
>
> **定位**：本 Skill 是 3C Lua 搬迁前的**扫描调研工具**——只产 CSV，不动任何文件。

## 与同生态 Skill 的边界

| 阶段 | Skill | 形态 | 输入 → 输出 |
|------|-------|------|-----------|
| 1. 资产路径分类 | `ue-3c-migration-path-mapper` | Skill | xlsx → 带 3C 目标路径的 CSV |
| 2. 3C 资产搬迁执行 | `ue-3c-asset-migration` | Skill | 路径映射 CSV → 实际迁移 + 记录 |
| 3. 3C 资产→Lua 关联扫描（**本 Skill**） | `ue-3c-lua-scan` | Skill | 资产 CSV/根目录 → Lua 绑定+依赖 CSV |
| 4. 3C Lua 搬迁执行 | `ue-3c-lua-migration` | Skill | 本 Skill 的 CSV → 实际 Lua 搬迁 |

**关键边界**：本 Skill 只读、只扫；**不修改任何资产、Lua、配置**。

## 触发关键词

- `3C Lua 扫描` / `3C 资产对应 Lua` / `扫描 LetsGo3C Lua 绑定`
- `scan 3c lua binding` / `资产 Lua 映射 CSV` / `3C 资产Lua关联`

## 前置条件

1. `uasset_mcp` 已安装（与 `ue-recursive-deps-scan` 共用同一探测逻辑）：
   - `F:\F4\LetsGoEditor\Editor\LetsGo\Tools\Python311\Lib\site-packages`
   - 当前 Python 解释器自带
   - 环境变量 `UASSET_MCP_SITE_PACKAGES`

   若都未找到：

   ```bash
   pip install --index-url https://mirrors.tencent.com/pypi/simple/ uasset_mcp
   ```

2. **输入二选一**：
   - 资产 CSV（含列 `外部资产完整路径`，兼容 `ue-recursive-deps-scan` 输出）
   - 资产根目录（绝对路径 或 `/Game/LetsGo3C/...` 形式）

3. （可选）`Content/LetsGo3C/Intermediate/user.json` 提供负责人字段 `user`，缺失则负责人列留空。

## Lua 绑定来源（**四种途径 + 动态绑定的多重解析**）

> **关键认知**：BP→Lua 绑定有四种典型形态。前三种能完全静态扫到；第四种"动态绑定"
> 又分三条解析路径（MCP > 文件名启发式 > 占位）。**任何实现了 IUnLuaInterface 的 BP
> 都不会被静默漏扫，至少会有一行结果（哪怕只是占位）**。
>
> | 类别 | BP 实现 IUnLuaInterface | GetModuleName 来源 | 静态可解析 |
> |------|----------------------|-------------------|----------|
> | A. UnLua 自重载 | ✓ | BP graph 返回字面量 | ✓（FName 表命中） |
> | B. UnLua C++ 继承 | ✓（继承自 C++ 类） | C++ 父类 `GetModuleName_Implementation` 返回 `TEXT("...")` | ✓（扫 .cpp） |
> | C. WBP 配置表 | ✗（不走 UnLua） | `UIWndNameToLuaPath` 配置项 | ✓（扫 Lua 配置） |
> | **D. UnLua 动态** | ✓ | BP graph 函数拼接 / UnLua C++ `Class->GetName()` 兜底 / 无静态字面量 | ⚠ 看 D1/D2/D3 |
>
> **D 类的三层解析**（按优先级）：
>
> | 子策略 | 名称 | 工作方式 | 标签 |
> |--------|------|---------|------|
> | D1 | MCP-resolved | 用 `user-ue-editor-mcp` 调 `graph.describe(BP, "GetModuleName")` 读 Return Node 字面量 | `UnLuaInterface(动态-MCP)` |
> | D2 | 文件名匹配 | 用全工程 `.lua` 索引，按 `BP_Foo` ↔ `Foo.lua`/`BP_Foo.lua`/`Foo_C.lua` 多 candidate 搜，唯一/最优命中即采用；多 candidate 命中时优先 `LetsGo3C.Script.*` > `LetsGo.Script.*` > `LetsGoSDK.Script.*` > `Feature.*` | `UnLuaInterface(动态-文件名匹配)` |
> | D3 | 占位 | D1/D2 都失败，留 `[动态计算: 调用 FullLuaModuleName]` 待人工 / 后续 MCP 跑一遍补回 | `UnLuaInterface(动态)` |

### A. UnLuaInterface — BP 自重载 `GetModuleName`

UnLua 把 BP 重载的 `GetModuleName()` 返回字符串以 **FName** 形式落到 `.uasset` 的 Names 表。扫描时用正则匹配：

```
^(LetsGo|LetsGo3C|LetsGoSDK)\.Script\.[\w.]+$
^Feature\.\w+\.Script\.[\w.]+$
```

一个资产最多输出一条 UnLua(self) 命中（取第一个匹配项；若有多个，写入 `备注` 字段提示人工 review）。
**引用类型** 列写 `UnLuaInterface`。

### B. UnLuaInterface — 继承自 C++ 父类的 `GetModuleName_Implementation`

C++ 实现模式（项目实际存在的例子）：

```cpp
// f:\F3\LetsGoDevelop\LetsGo\Plugins\MOE\GameCommon-Obsolete\...\HomeGame.cpp:21
FString AHomeGame::GetModuleName_Implementation() const
{
    return TEXT("LetsGo.Script.Modplay.Core.GameMode.Games.Home.HomeGame");
}
```

```cpp
// f:\F3\LetsGoDevelop\LetsGo\Plugins\MOE\GameCommon-Obsolete\...\DDPGame.cpp:52
FString ADDPGame::GetModuleName_Implementation() const
{
    return TEXT("Feature.DDP.Script.Modplay.Core.GameMode.Games.DDP.DDPGame");
}
```

扫描流程：

1. glob `<project_root>/Source/**/*.cpp` 和 `<project_root>/Plugins/**/*.cpp`（排除 `Intermediate/` / `*.gen.cpp`）
2. 用一次性多行正则抓 `类名::GetModuleName_Implementation` + `return TEXT("xxx")`
3. 建立 `{ A/U/F前缀的类名, 去前缀的类名 } -> Lua 路径` 双向映射
4. 文件级 mtime 缓存到 `cache/cpp_module_map.json`，二次跑秒级

每个 BP 资产的"native parent" 由以下两步获取（优先级 1 > 2）：

1. 找 .uasset 的 `BlueprintGeneratedClass` export，读 `super_name`
2. 兜底：遍历 imports，取 `class_name == "Class"` 且 `class_package` 以 `/Script/` 开头的所有 native 类，按顺序逐个查 cpp_map

**仅当 BP 自己未重载（情况 A 未命中）时**才会进入情况 B 查询——避免重复输出。

**引用类型** 列写 `UnLuaInterface(C++继承)`，`外部资产完整路径` 末尾追加 `[native_parent=AHomeGame]` 用于审查。

### D. UnLuaInterface — 动态拼接路径（关键漏洞修复点）

**真实案例**：`BP_MoeCharAbleAbilityComponent.uasset`
- imports 命中 `UnLuaInterface` ✓
- FName 表中存在 `GetModuleName` + `CallFunc_FullLuaModuleName_FullModuleName` ✓
- **但完整 Lua 路径字符串**在 .uasset 二进制中**不存在**——`FullLuaModuleName` 是 `BP_SharedLibrary` 中的 BP 函数，运行时通过类反射拼接出最终路径

检测策略（只识别"有动态绑定"，不解析具体路径）：

1. 资产 imports 表存在 `UnLuaInterface` → BP 意图绑 Lua（强信号）
2. 前面 A/B 两条路都没命中 → 必然是动态拼接
3. 扫 FName 表的 `CallFunc_<X>_<Y>` 节点名，过滤 `<X>` 含 `module`/`lua`/`path`/`script`/`luamod`/`fullname` 的，作为 resolver 函数候选

**引用类型** 列写 `UnLuaInterface(动态)`，`外部资产完整路径` 列写 `[动态计算: 调用 FullLuaModuleName]`，`3C仓库目标路径` 列写 `[待编辑器查询]`。

**MCP 介入流程**（半离线模式，按需打开）：

1. 主脚本第一次跑 → 静态扫 + 文件名启发式（D2）已经能解出 80%+ 的动态绑定
2. 仍剩下的标 `UnLuaInterface(动态)`，自动写到 `cache/pending_mcp_resolution.json`
3. AI / 人工触发 `user-ue-editor-mcp.graph.describe(BP, "GetModuleName")` 跑这一批
4. 用 `utils.mcp_resolver.parse_describe_response()` 解析每个 BP 的 Return Node 字面量
5. 整理成 `[{"asset_short_name": "BP_Foo", "resolved_module": "LetsGo.Script..."}, ...]` 喂回：
   ```bash
   python scan_3c_lua_bindings.py --root-dir ... --output-csv ... --apply-mcp-result <result.json>
   ```
6. 现在 D 类全部解析到真路径，CSV 完整

> ⚠️ **重要注意**：在本项目实测，**所有 D 类动态 BP 实际上都没有静态 GetModuleName 函数图**（UnLua 走 C++ 兜底 `Class->GetName()` 路径）。所以 MCP 的 `graph.describe` 大概率拿不到字面量，**D2 文件名匹配才是这个项目的主力解析手段**。MCP 路径作为通用兜底保留，给那些真有静态字面量的 BP 用。

### C. UIWndNameToLuaPath（WBP 配置表）

参考 [`Content/LetsGoSDK/Script/Core/Class/BaseViewClass.lua`](Content/LetsGoSDK/Script/Core/Class/BaseViewClass.lua) §1024：

```lua
function BaseViewClass.GetLuaViewPathByWndNameOrWidget(WndName, Widget)
    local LuaView = SDK.UIWndNameToLuaPath[WndName]
    ...
end
```

数据源 glob：

- `Content/LetsGo/Script/Config/UIWndNameToLuaPath*.lua`
- `Content/LetsGoSDK/Script/Config/UIWndNameToLuaPath*.lua`
- `Content/Feature/**/Script/Config/UIWndNameToLuaPath_*.lua`

文本正则抽取 `["widgetName"] = "lua.path"` 项，构建全局 `widget_map`。每个 .uasset 用文件 stem 查表，命中即输出一条 WBP 绑定。
**引用类型** 列写 `UIWndNameToLuaPath`。

### 四种来源的优先级与互斥

| 优先级 | 来源 | 触发条件 |
|--------|------|---------|
| 1 | `UnLuaInterface`（情况 A） | BP 自身 FName 表里有 Lua 路径字符串 |
| 2 | `UnLuaInterface(C++继承)`（情况 B） | 情况 A 未命中 且 BP 的 native parent 在 cpp_map 中命中 |
| 3 | `UnLuaInterface(动态)`（情况 D） | 情况 1/2 均未命中 且 imports 含 `UnLuaInterface`（**兜底防漏**） |
| 4 | `UIWndNameToLuaPath`（情况 C） | 资产是 WBP（文件名以 `WBP_`/`UWBP_`/`W_` 起手）且 widget_map 命中 |

情况 1 / 2 / 3 **互斥**：BP 命中任一即不再查后两类。情况 4 (WBP) 可与 1/2/3 共存。

**铁律**：**只要 .uasset imports 里出现 `UnLuaInterface`，就一定会输出至少一行绑定记录**，要么是 A 真路径、要么是 B C++ 推断、要么是 D 动态占位。不再有"实现了 UnLuaInterface 但被静默漏扫"的情况。

> **未命中行为**：若资产文件名以 `WBP_` / `UWBP_` 开头但未在 widget_map 中命中，输出一行占位记录，列 `引用类型 = [未绑定]`，方便人工核查是否漏配。

## ObjectRedirector 跟随（关键鲁棒性）

**问题场景**：资产 CSV 里给的是 `/Game/LetsGo/...` 旧路径，但这些 BP 已经被搬迁到
`/Game/LetsGo3C/...`，旧位置只剩 `ObjectRedirector` 桩文件——FName 表 / Class imports
/ super_name 都没有任何 UnLua 信息。

**解决方案**：每次解析 `.uasset` 时自动检测重定向器（"所有非 MetaData 的 export 类型都是
`ObjectRedirector`"）并跟随到目标资产（imports 里第一个 `/Game/...` Package），最多 5 跳。
跟随完成后 `extract_unlua_paths` / `extract_native_parents` 在**真实资产**上工作，绑定信息齐全。

控制台会在简报中报告"已跟随 ObjectRedirector: N 个原路径资产实际是重定向桩"——典型场景下
（用旧版资产 CSV 扫已搬入 3C 的 BP）这个数会很大，N=23/47 都属正常。

## 工作流（6 Phase + 可选预过滤）

> Phase 0 包含资产 CSV 模式下的合并 + 过滤；根目录模式下 Phase 0 只校验路径存在。

### Phase 0 — 输入归一

```bash
# 资产 CSV 模式（支持多 CSV 合并 + 可选预过滤）
python scripts/scan_3c_lua_bindings.py \
    --asset-csv "<path1>" "<path2>" ... \
    [--filter-exclude-method 无需搬迁 ...]  \
    [--filter-bp-only] \
    --output-csv "<output.csv>"

# 根目录模式（不过滤；目录已是清理后的资产集）
python scripts/scan_3c_lua_bindings.py \
    --root-dir "<abs_path | /Game/LetsGo3C/Assets/Base/Character/>" \
    --output-csv "<output.csv>"
```

**资产 CSV 模式专属：预过滤**

| 参数 | 默认 | 说明 |
|------|------|------|
| `--asset-csv` | / | 支持 1 个或多个 CSV，自动合并去重（按 `外部资产完整路径` 列）|
| `--filter-exclude-method <值...>` | `["无需搬迁"]` | 排除 `搬迁方式` 列值在此列表中的资产；传 `--filter-exclude-method` 不带参数则关闭过滤 |
| `--filter-bp-only` | `false` | 启用后只保留资产名以 `BP_` / `WBP_` / `UWBP_` / `ABP_` / `W_` 起手的 BP 系资产 |

**通用可选参数**：

| 参数 | 默认 | 说明 |
|------|------|------|
| `--content-root` | `F:\F3\LetsGoDevelop\LetsGo\Content` | UE 项目 Content 目录 |
| `--project-root` | `F:\F3\LetsGoDevelop\LetsGo` | UE 项目根目录（含 Source/ Plugins/），用于扫 C++ |
| `--cpp-cache` | `<skill>/cache/cpp_module_map.json` | C++ 映射文件级 mtime 缓存 |
| `--skip-cpp-scan` | `false` | 跳过 C++ 父类扫描（提速；BP 继承 native 类的绑定将漏扫） |
| `--lua-index-cache` | `<skill>/cache/lua_index.json` | 全工程 Lua 文件索引缓存 |
| `--skip-lua-index` | `false` | 跳过 Lua 索引（动态绑定 D2 文件名匹配将关闭） |
| `--mcp-pending-out` | `<skill>/cache/pending_mcp_resolution.json` | 仍未解析的动态 BP 列表写到该路径，给 MCP 续跑 |
| `--apply-mcp-result` | `""` | 读取 MCP 解析回填 JSON，覆盖对应行 Lua 路径 |
| `--user-json` | `Content/LetsGo3C/Intermediate/user.json` | 负责人字段来源 |
| `--max-depth` | `0` (无限) | require BFS 最大深度，调试时可设小 |
| `--include-sdk-deps` | `false` | 默认排除 `LetsGoSDK.*` 不计入依赖；加该 flag 则计入 |
| `--widget-map-dump` | `""` | 可选: 把 widget_map 转储到该 JSON 路径用于复查 |

### Phase 1a — 构建 Widget 映射表

启动时 glob 所有 `UIWndNameToLuaPath*.lua`，正则解析；中间结果写入 `Content/.cursor/skills/ue-3c-lua-scan/cache/widget_map_<timestamp>.json` 便于复查。

### Phase 1b — 构建 C++ 父类→Lua 映射表

glob `<project_root>/Source/**/*.cpp` 和 `<project_root>/Plugins/**/*.cpp`，正则抓 `Class::GetModuleName_Implementation` + `return TEXT("...")`，建立 `{ class_name -> lua_path }` 双向映射（含 A/U/F 前缀与去前缀双 key），文件级 mtime 缓存到 `cache/cpp_module_map.json`。

控制台输出：

```
[Phase 1a] widget_map built: 312 entries from 6 config files
[Phase 1b] cpp_map: scanning 4520 cpp files under ['Source', 'Plugins']
  [cpp_map] done in 18.7s (scanned=4520, cache_hit=0); 187 class keys, 94 unique lua paths
```

加了 `--skip-cpp-scan` 则跳过 Phase 1b。

### Phase 2 — 抽取 Lua 绑定

逐资产解析 `.uasset`：

```
[Phase 2] scanning 47 assets...
[1/47] BP_FollowerSurroundingsActor   UnLua(self): LetsGo.Script.Community.Components.FollowerSurroundingsActor
[2/47] BP_HomeGameInstance            UnLua(C++ parent: AHomeGame): LetsGo.Script.Modplay.Core.GameMode.Games.Home.HomeGame
[3/47] WBP_HomePanel                  Widget: LetsGo.Script.UI.Home.HomePanelView
...
```

未命中任何来源的 BP 资产，跳过（不输出空记录）；WBP 但未命中 widget_map 输出占位行 `[未绑定]`。

### Phase 3 — Lua require 链 BFS

对每条命中的 Lua 模块路径：

1. 点号路径→物理 .lua 文件
   - `LetsGo.Script.X.Y` → `Content/LetsGo/Script/X/Y.lua`
   - `LetsGo3C.Script.Base.Character.X` → `Content/LetsGo3C/Script/Base/Character/X.lua`
   - `Feature.Farm.Script.X` → `Content/Feature/Farm/Script/X.lua`
2. 抓 `require('xxx.yyy')` / `require("xxx.yyy")`（含 `string.format` 拼接的不抓，做不到静态分析）
3. BFS 到底，缓存命中模块，避免环
4. 业务关键词命中（复用 `ue-3c-lua-migration` 清单）：

```
Farm | Arena | UGC | Chase | Chest | Home | StarP | Community | Lobby | Commercial
```

匹配规则：模块路径或文件路径中作为单词出现（前缀/后缀/中缀）即命中；`StarP` 前缀匹配（覆盖 `StarParty` 等）。

### Phase 4 — 写出 CSV

19 列结构详见 [`refs/column-schema.md`](refs/column-schema.md)。末尾打印简报：

```
============== 扫描简报 ==============
输入资产: 47
UnLua(self) 命中: 26
UnLua(C++继承) 命中: 6
Widget 命中: 8
WBP 未命中: 1
文件缺失/解析失败: 0
输出行数: 41
平均递归依赖: 27.1
输出: F:\F3\LetsGoDevelop\LetsGo\Content\...\3C_Lua扫描_20260518_215345.csv
耗时: 32.5s
=====================================
```

## 输出 CSV — 16 列

| # | 列名 | 含义 | 空值 |
|---|------|------|------|
| 1 | **lua文件名** | Lua 文件名（不含 `.lua`） | 永不空 |
| 2 | **lua模块完整路径** | Lua 模块点号路径 | 永不空 |
| 3 | 3C仓库目标路径 | **优先**用 BP 在 `LetsGo3C/Assets/Base/{C}/{资产类型}/` 的真实物理位置反推为 `LetsGo3C.Script.Base.{C}.{资产类型}.{LuaLeaf}`（**leaf 保留原名，不加 Base 后缀**），否则关键词兜底（`{资产类型}` 默认 `Components`） | 无法推断 `[待确认]` |
| 4 | 引用链路（被谁依赖了） | 触发该 Lua 的资产名（多源 `\|` 分隔） | / |
| 5 | 负责人 | `user.json` 的 `user` 字段 | 缺失时空 |
| 6 | 进度 | 占位 `□`，供人工填 `进行中`/`完成` | / |
| 7 | 搬迁方式 | 留空给人工填 | 空 |
| 8 | **Lua中ProjectT硬编码引用** | Lua 中字面量 `/Game/Feature/ProjectT/...` 引用 | 无则空 |
| 9 | **直接依赖Lua数** | 直接 require 的 **LetsGo 仓库 Lua 模块** 数 | 无则 `0` |
| 10 | **直接依赖Lua列表** | 列表 `\|` 分隔 | / |
| 11 | **递归依赖Lua总数** | BFS 闭包内 LetsGo 仓库 Lua 模块数 | `0` |
| 12 | **递归依赖Lua列表** | 列表 | / |
| 13 | 玩法依赖数量 | 命中业务关键词的依赖 Lua 数 | `0` |
| 14 | 全部引用玩法列表 | 命中关键词集合（去重后 `\|` 分隔） | / |
| 15 | **Lua父目录** | 模块路径第 3 段（如 `Community`） | / |
| 16 | **Lua子目录** | 第 4 段（如 `Components`） | / |
| 17 | 引用类型 | `UnLuaInterface` / `UnLuaInterface(C++继承)` / `UnLuaInterface(动态-MCP)` / `UnLuaInterface(动态-文件名匹配)` / `UnLuaInterface(动态)` / `UIWndNameToLuaPath` / `[未绑定]` / `[文件缺失]` | / |

> **v2 变更**（vs 原 19 列）：
> - 删除了 `引用层级`（恒为 `直接绑定`，无信息量）和 `是否需要`（与 `进度` 列重复）
> - `外部资产名/完整路径` 改名为 `lua文件名/lua模块完整路径`（语义更明确）
> - `直接/递归依赖LetsGo资产` 改名为 `直接/递归依赖Lua`（行单位本来就是 Lua 模块）
> - `资产父/子目录` 改名为 `Lua父/子目录`
> - `ProjectT资产路径...` 改名为 `Lua中ProjectT硬编码引用`（更准确）
> - **3C 目标路径不再追加 Base 后缀**，保持 lua 原名

## 默认输出路径

- 输入 CSV 模式：`<input_csv_dir>/3C_Lua扫描_<timestamp>.csv`
- 输入根目录模式：`Content/LetsGo3C/Migration/LuaMigration/Manifest/3C_Lua扫描_<timestamp>.csv`
- 用户传 `--output-csv` 时一律以用户值为准

## 错误处理

| 场景 | 行为 |
|------|------|
| `uasset_mcp` 未安装 | 立即报错并给出 pip 命令 |
| 资产 CSV 缺列 `外部资产完整路径` | 报错并提示需走 `ue-3c-migration-path-mapper` 或对齐列名 |
| 资产 .uasset 文件不存在 | 输出占位行 `引用类型=[文件缺失]` 并继续 |
| 资产是 ObjectRedirector 桩 | 自动跟随到真实资产（最多 5 跳），按真实资产解析；控制台累计跟随次数（"已跟随 ObjectRedirector: N"）|
| Lua 模块路径无法解析到物理文件 | 当作叶子节点，依赖统计填 `0` 并在控制台告警 |
| `user.json` 缺失或无 `user` 字段 | 负责人列留空，控制台 warning 一次 |
| BP 资产命中多条 UnLua 路径 | 取第一个，候选写入 `外部资产完整路径` 列尾 `[候选: A \| B]` |
| BP 既未命中 self UnLua、native parent 也未在 cpp_map 中 | imports 含 `UnLuaInterface` → 输出 `UnLuaInterface(动态)` 占位（兜底）；imports 不含 → 非 WBP 跳过，WBP 走 `[未绑定]` |
| BP 的 native parent 找不到（super_name 空 且无 native Class import） | 跳过 C++ 查询；不阻断扫描 |
| C++ 扫描某个 .cpp 不可读 | 单文件 silently 跳过；用 `--skip-cpp-scan` 完全跳过该 phase |
| WBP 命名前缀但未命中 widget_map | 输出占位行 `引用类型=[未绑定]` |
| Lua 内出现 `require(string.format(...))` 动态路径 | 静态分析跳过，控制台 warning 列出文件名 + 行号 |

## 相关文件

- 列字段语义详表：[`refs/column-schema.md`](refs/column-schema.md)
- 上游：[`ue-3c-asset-migration`](../ue-3c-asset-migration/SKILL.md)、[`ue-3c-migration-path-mapper`](../ue-3c-migration-path-mapper/SKILL.md)
- 下游：[`ue-3c-lua-migration`](../ue-3c-lua-migration/SKILL.md)
- 复用基础：[`ue-recursive-deps-scan`](../ue-recursive-deps-scan/SKILL.md) 的 `UAssetParser` 引导
- 业务关键词清单母版：[`ue-3c-lua-migration/SKILL.md`](../ue-3c-lua-migration/SKILL.md) §业务逻辑识别规则
