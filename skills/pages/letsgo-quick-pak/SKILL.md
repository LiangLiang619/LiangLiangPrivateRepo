---
name: letsgo-quick-pak
description: >-
  Build encrypted UE pak files from arbitrary non-cook assets (fb, json, txt, csv, mp4, lua, etc.)
  and generate Lua mount snippets for local QA/hotfix verification in LetsGo / ProjectT (TMR) projects.
  Use when the user mentions quick pak, hot-patch pak, _N_P pak, AssetNameMapping override,
  pak mount, QuickPakMount, or wants to verify asset replacements without a full cook/HotPatcher pipeline.
---

# letsgo-quick-pak (in-repo skill)

> 给非 cook 资产做临时 pak + Lua 强制 mount，用来**本地排障 / 线上热修验证**。不走 HotPatcher、不走 ChunkGroup，**写一个 txt，跑一个脚本，生成 pak + mount 代码**。
>
> Developer usage: see [README.md](README.md) · 完整文档: https://iwiki.woa.com/p/4020010290

---

## 能做什么 / 不做什么

**能做：**
- 把任意文件（`.fb / .json / .txt / .csv / .mp4 / .bin / .lua …`）打成一个加密 UE pak
- 同时输出 Lua 挂载代码片段，供拷贝到 `AppEntry.lua`

**不做：**
- 不打 uasset / cook 资源；不管 IoStore、ChunkGroup、HotPatcher
- 不是正式热更链路，仅供 QA/研发验证

> 线上正式热更请走：`HotPatcher → ChunkConfig → MoeChunkGroupManager → MoeMultiDownload → MoePakManager`

---

## When to trigger

User is in a LetsGo / ProjectT (TMR) project and mentions any of:

- "打个 pak / 打一个热更包 / 快速 pak / 补丁 pak / _N_P 包"
- "验证 AssetNameMapping / 替换 Loading 视频 / 塞个 json 进去试"
- "配置 configs 下的 txt / 改 quickpak 的 config"
- "热更 mount / 强制 mount / lua mount pak"

---

## Action

1. **Locate the in-repo skill directory**. Priority search (first hit wins):
   - `<any LetsGoSDK sub-repo>/Skill/letsgo-quick-pak/`
     (known paths: `E:\UGit\LetsGoDevelop\LetsGo\Content\LetsGoSDK\Skill\letsgo-quick-pak\`,
      `F:\UGit\TMR_ProjectTDevelop\LetsGo\Content\LetsGoSDK\Skill\letsgo-quick-pak\`)
   - Detection: subdirectory contains `.git` and name starts with `LetsGoSDK`
   - If not found, **ask the user** to copy from an existing LetsGoSDK install (do NOT auto-bootstrap).
2. **Read `configs/*.txt`**. If the user specified a particular config, process only that one.
3. **Config parsing rules** (see `configs/_template.txt`):
   - `pak: <name>` — required (no `.pak` suffix; must end with `_<N>_P` / `_<N>_p`)
   - `priority: <int>` — optional, default 100
   - `reloadAssetNameMapping: true/false` — optional, default false
   - Lines starting with `#` are comments
   - Other non-empty lines: `<absolute source path> -> <virtual path in pak>`
   - **`{project}` placeholder**: auto-replaced with project name from `.uproject`. Always use `{project}`, never hard-code `ProjectT` or `LetsGo`.
4. **Invoke `scripts/Build.ps1`** — never hand-roll UnrealPak commands.
5. **Report to user**: pak absolute path + size + mount point + deploy location (`FPaths::ProjectPersistentDownloadDir()`).

---

## Output rules (mandatory every time)

1. **Show absolute pak path prominently**
2. **Never generate `.lua` files** — output Lua snippets only, user pastes manually
3. **Re-print the Lua snippet in chat** in a ` ```lua ` fenced block
4. **Recommend call site**: default `LetsGoSDK/Script/Boot/AppEntry.lua`

---

## Deploy locations

| Platform | Path |
|---|---|
| Android | `/sdcard/Android/data/<包名>/files/UE4Game/<Project>/<Project>/Saved/PersistentDownloadDir/` |
| iOS | `<App Container>/Documents/<Project>/Saved/PersistentDownloadDir/` |
| Win/Editor | `<Project>/Saved/PersistentDownloadDir/` |

对应 Lua 的 `FPaths::ProjectPersistentDownloadDir()`，不用改路径。

---

## Lua mount 片段示例

```lua
local QuickPakMount = require("LetsGoSDK.Skill.letsgo-quick-pak.lua.QuickPakMount")

-- pak: res_base-Android_ASTCClient_2_P.pak
QuickPakMount.MountFromInfo({
    pakName  = "res_base-Android_ASTCClient_2_P.pak",
    priority = 100,
    reload   = true,
})
```

---

## Config 格式速查

```
pak: res_base-Android_ASTCClient_<N>_P   # 必填，N 越大优先级越高
priority: 100                             # 可选，默认 100
reloadAssetNameMapping: true              # 可选，默认 false

# 源路径 -> pak 内虚拟路径
D:/xxx/AssetNameMapping.fb -> ../../../{project}/Content/LetsGo/Data/AssetData/AssetNameMapping/AssetNameMapping.fb
```

mount 路径两种写法：
- **完整路径**：`../../../{project}/Content/...` — 与引擎加载路径对齐，覆盖 base
- **短路径**：`Content/Movies/Loading_V4.mp4` — 配合 Lua 手动 mount

---

## Forbidden actions

- Do NOT modify `scripts/Crypto.json` keys unless explicitly requested
- Do NOT add `generated/` to git (already in `.gitignore`)
- Do NOT generate uasset-based paks; do NOT invoke cook / IoStore workflows
- Do NOT auto-generate lua files (`Mount_*.lua` / `QuickPakMountAll.lua`)
  - Exception: `lua/QuickPakMount.lua` is a hand-written runtime helper, fine to commit

---

## 常见问题

**Q：mount 了但游戏还是读老文件？**
- pak 优先级（`_N_P` 的 N）不够大 → 加大 N 重打
- 资产已被内存缓存 → `reloadAssetNameMapping: true`

**Q：`Failed to find requested encryption key`**
- 手动调 UnrealPak 时忘带 `-cryptokeys`，`Build.ps1` 已自动带

**Q：安卓上 pak 放进去没生效？**
- 用 `adb shell ls` 核对 `PersistentDownloadDir` 下有没有你的 pak
- Android 11+ 需要用 `/sdcard/Android/data/<包名>/` 路径

**Q：Lua 里找不到 `MoePakManager`？**
- 看 `lua/QuickPakMount.lua`，里面有多路兜底（`MoePakManager` → `FCoreDelegates.OnMountPak` → exec 命令）

---

## Available context (quick reuse)

- UnrealPak: `E:\UGit\LetsGoDevelop\ue4_tracking_rdcsp\Engine\Binaries\Win64\UnrealPak.exe`
- Encryption key source: `LetsGo/Config/DefaultCrypto.ini`
- Runtime mount helper: `lua/QuickPakMount.lua` (multi-path fallback)
- User-level skill (more background): `~/.cursor/skills-cursor/letsgo-quick-pak/SKILL.md`

## Reference docs

- 完整使用文档（iWiki）：https://iwiki.woa.com/p/4020010290
