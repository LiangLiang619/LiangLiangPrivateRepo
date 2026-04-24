# letsgo-quick-pak

> 给非 cook 资产做临时 pak + Lua 强制 mount，用来**本地排障 / 线上热修验证**。不走 HotPatcher、不走 ChunkGroup，**写一个 txt，跑一个脚本，生成 pak + mount 代码**。

---

## 能做什么

- 把任意文件（`.fb / .json / .txt / .csv / .mp4 / .bin / .lua …`）打成一个加密 UE pak
- 同时打印一段 Lua 挂载代码片段到控制台，供你拷贝到 `AppEntry.lua`
- 所有配置都是**一个简单 txt**，改哪里、打什么、挂哪儿，一看就懂

## 不做什么

- 不打 uasset / cook 资源
- 不管 IoStore、ChunkGroup、HotPatcher
- 不是正式热更发布链路 —— 仅供**QA/研发验证**

> 线上正式热更请走：`HotPatcher → ChunkConfig → MoeChunkGroupManager → MoeMultiDownload → MoePakManager`。本 skill 是这条链路之外的"旁路快速通道"。

---

## 3 步使用

### 1) 复制一份 config

```
configs/_template.txt  →  configs/<你的名字>.txt
```

编辑它，填：pak 名字 + 源文件列表 + pak 内挂载路径。模板里都有注释。

最小示例（打一个 AssetNameMapping 覆盖包）：

```
pak: res_base-Android_ASTCClient_2_P

D:/AssetNameMapping_8000/AssetNameMapping.fb   -> ../../../{project}/Content/LetsGo/Data/AssetData/AssetNameMapping/AssetNameMapping.fb
D:/AssetNameMapping_8000/AssetNameMapping.json -> ../../../{project}/Content/LetsGo/Data/AssetData/AssetNameMapping/AssetNameMapping.json
D:/AssetNameMapping_8000/AssetNameMapping.txt  -> ../../../{project}/Content/LetsGo/Data/AssetData/AssetNameMapping/AssetNameMapping.txt
```

> `{project}` 是占位符。`Build.ps1` 从 skill 目录往上找 `.uproject`，把 `{project}` 替换成对应工程名：**LetsGo 仓里就是 `LetsGo`，TMR 仓里就是 `ProjectT`**。同一份 config 两个仓通用。想强制覆盖可以带参数：`./scripts/Build.ps1 -Project MyProject`。

### 2) 跑脚本

```powershell
# 在 LetsGoSDK/Skill/letsgo-quick-pak/ 下
./scripts/Build.ps1
```

脚本会：

- 扫描 `configs/*.txt`
- 每个 txt 生成一个 pak 到 `generated/pak/<pakName>.pak`
- **不会**生成 lua 文件 —— 而是把**配套的 lua 挂载片段直接打印到控制台**，由你自己拷贝
- 最后会列出每个 pak 的**绝对路径 + 大小**，以及你需要粘贴到 `AppEntry.lua` 的 lua 代码块

参数（都有默认值）：

```powershell
./scripts/Build.ps1                             # 全量构建
./scripts/Build.ps1 -Config example.txt         # 只构建某一个
./scripts/Build.ps1 -OutDir D:/temp/pak         # 换输出目录
```

### 3) 下发 + 挂载

把 `generated/pak/` 里的 pak **放到设备的固定位置**（两种都行）：

- **Android**：`/sdcard/Android/data/<包名>/files/UE4Game/<Project>/<Project>/Saved/PersistentDownloadDir/`
- **iOS**：`<App Container>/Documents/<Project>/Saved/PersistentDownloadDir/`
- **Win/Editor**：`<Project>/Saved/PersistentDownloadDir/`

对应 Lua 里的 `FPaths::ProjectPersistentDownloadDir()`，**不用改路径**。

然后把 `Build.ps1` 打印出来的 lua 片段**拷贝到 `LetsGoSDK/Script/Boot/AppEntry.lua`** 的合适位置（或任何在资源首次加载前会跑到的启动钩子）。片段长这样：

```lua
local QuickPakMount = require("LetsGoSDK.Skill.letsgo-quick-pak.lua.QuickPakMount")

-- pak: res_base-Android_ASTCClient_2_P.pak
QuickPakMount.MountFromInfo({
    pakName  = "res_base-Android_ASTCClient_2_P.pak",
    priority = 100,
    reload   = true,
})
```

完事。**刻意不帮你生成 lua 文件**，免得哪天你忘了清理导致真实工程被污染；手工粘贴，位置你自己心里有数。

---

## Config 格式速查

```
# 以 # 开头是注释
# 头部：key: value
pak: res_base-Android_ASTCClient_<N>_P      # 必填，越大优先级越高
priority: 100                                # 可选，mount 优先级，默认 100
reloadAssetNameMapping: true                 # 可选，mount 后自动重载 AssetNameMapping

# 文件列表：每行一条  <源绝对路径> -> <pak 内挂载路径>
# 也可以省略 ->，让脚本按源文件名自动挂到某个默认前缀下（见 _template.txt）
# 路径里可用 {project} 占位符 —— 自动替换为当前仓 .uproject 的名字
```

### 命名规则（`_N_P`）

UE pak 加载优先级：`_N_p / _N_P` 的 N 越大越先查。所以补丁包想覆盖 base 里的同路径文件，N 必须大于线上最大的 `_p`。**当前桌面已用到的 N**：请自行在配置里递增。

### mount 路径两种写法

| 形式 | 举例 | 用在什么时候 |
|---|---|---|
| 完整 | `../../../{project}/Content/LetsGo/Data/AssetData/AssetNameMapping/xx.fb` | 和引擎真实加载路径严格对齐，覆盖 base |
| 短 | `Content/Movies/Loading_V4.mp4` | 配合 Lua 手动 mount 到 `Content/` 根 |

写错了看 `Build.ps1` 输出里的 `Mount point` 那一行回对。

---

## 产物目录结构

```
letsgo-quick-pak/
├── README.md                     ← 你现在看的文档
├── SKILL.md                      ← 给 AI 看的触发规则（你可以不看）
├── configs/                      ← 提交到仓库，每个 txt = 一个 pak 任务
│   ├── _template.txt
│   └── example_AssetNameMapping.txt
├── lua/
│   └── QuickPakMount.lua         ← 运行时共用 helper（手写，提交）
├── scripts/
│   ├── Build.ps1                 ← 构建脚本
│   └── Crypto.json               ← 加密 key 缓存（项目 dev key，非发行）
└── generated/                    ← 脚本产物（默认 .gitignore，不提交）
    └── pak/*.pak                 ← 只放 pak，lua 不写文件，只打印在控制台
```

---

## 常见问题

**Q：mount 了但游戏还是读老文件？**
- pak 优先级（`_N_P` 的 N）不够大 → 加大 N 重打
- 资产已经被内存缓存 → `reloadAssetNameMapping: true`，或手动 reset 对应 manager

**Q：`Failed to find requested encryption key`**
- 读 pak 没带 `-cryptokeys`，`Build.ps1` 已自动带，手动调 UnrealPak 时记得加

**Q：安卓上 pak 放进去没生效？**
- 路径不对：用 `adb shell ls` 核对 `PersistentDownloadDir` 下有没有你的 pak
- 权限/沙箱：Android 11+ 需要用 `/sdcard/Android/data/<包名>/` 路径

**Q：我要换加密 key 怎么办？**
- 改 `scripts/Crypto.json` 里那串 base64。默认用的是项目 dev key（来自 `LetsGo/Config/DefaultCrypto.ini`）。

**Q：Lua 里找不到 `OnMountPak` / `MoePakManager`？**
- 看 `lua/QuickPakMount.lua`，里面有多路兜底（`MoePakManager` → `FCoreDelegates.OnMountPak` → exec 命令）。哪一路能跑就用哪路。

---

## 能力边界（不用往里深挖）

- 底层就是 `UnrealPak.exe -Create -cryptokeys -encryptindex`
- Lua mount 底层就是 `FCoreDelegates::OnMountPak` 或 `FPakPlatformFile::Mount`
- 多看一眼日志比读文档省事。出了怪事，把 pak 用 `UnrealPak -List -cryptokeys=...` 打一遍对着看。
