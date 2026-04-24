# letsgo-quick-pak

> 针对 **LetsGo / ProjectT (TMR)** 项目，把任意"非 cook 资产"（AssetNameMapping、mp4、json、csv、文本配置、FlatBuffers 二进制…）快速打成一个带加密 index 的 UE Pak，输出到桌面，供移动端通过 Lua 热更强制 mount 来复现 / 验证 / 修复线上问题。**不走 HotPatcher、不走 Cook 流水线，全程秒级完成。**

## When to use

触发词（中英文都覆盖）：
- "快速打个 pak"、"打一个 pak"、"打一个热更包"、"res_base 补丁"、"打 _N_P 包"
- "挂载测试 / 强制 mount / Lua mount pak / 热更 mount"
- "验证 AssetNameMapping"、"替换 loading 视频"、"塞一个 json/csv 进去试试"
- "quick pak / adhoc pak / patch pak / override pak"

适用场景（强制匹配这些才用本 skill）：
- 目标资产是 **非 uasset 的普通文件**（.fb / .json / .txt / .csv / .mp4 / .bin / .lua…）。
- 目标是 **临时验证 / 排障 / A-B 比对**，不需要进正式流水线。
- 只需要覆盖 / 追加少量文件，走的是 pak **优先级覆盖**（`_N_P` 后缀越大优先级越高）。

**不适用**：需要 cook 的 uasset、需要生成 IoStore、需要进包审核/正式热更包（请走 HotPatcher + `packConfig.json`）。

---

## Core facts（本项目实测值，固定填进命令里即可）

| 项 | 值 |
|---|---|
| UnrealPak 路径 | `E:\UGit\LetsGoDevelop\ue4_tracking_rdcsp\Engine\Binaries\Win64\UnrealPak.exe` |
| 加密 Key（AES-256 base64） | `JhNKU8vZqmXLRu0VDYpX9RP7k5dT253MJVqYge2WUy0=` |
| Key 来源 | `LetsGo\Config\DefaultCrypto.ini` → `EncryptionKey=` |
| 是否加密 index | **必须**（`-encryptindex`，对应 `bEncryptPakIniFiles=True`） |
| 默认不压缩 | 与 base pak 对齐，不加 `-compress` |
| 命名模板 | `res_base-Android_ASTCClient_<N>_P.pak`（N 越大越高优先级，`_P/_p` 表示 patch） |
| 常用 mount 前缀 | `../../../<ProjectName>/Content/...` 或 短路径 `Content/...`（视 Lua 侧 mount 调用方式） |
| 项目名候选 | `LetsGo`（老项目路径）、`ProjectT`（新项目路径）、`ProjectT_Shell`（启动壳工程） |

> **关于密钥敏感性**：这是本项目仓内已经明文写死的开发测试密钥（非商业发行密钥），用户授权记录在此 skill 里使用，不算泄密。正式发行包如果换了 key，重新抓一次 `DefaultCrypto.ini` 即可。

---

## Workflow（每次按这个顺序做）

### Step 1 — 清点源文件

用 `Get-ChildItem -Recurse -File` 列出源目录，确认：
- 目标文件列表（全路径）
- 每个文件应落到 pak 内的哪个虚拟路径（mount path）

### Step 2 — 写 Crypto.json（只需要一次，可复用）

固定写到 `E:\UGit\LetsGoDevelop\Saved\Crypto.json`：

```json
{
  "EncryptionKey": {
    "Name": "embeddedPakSigningKey",
    "Guid": "00000000000000000000000000000000",
    "Key": "JhNKU8vZqmXLRu0VDYpX9RP7k5dT253MJVqYge2WUy0="
  },
  "SecondaryEncryptionKeys": []
}
```

> **坑**：不要保留空的 `SigningKey` 字段，UnrealPak 会触发 `RSA functionality was used but no modular feature was registered` 断言。

### Step 3 — 写 Response 文件

每行一条：`"<源绝对路径>" "<pak 内虚拟路径>"`。UTF-8 无 BOM，路径用正斜杠。

**项目级资产模板**（LetsGo）：
```
"E:\src\AssetNameMapping.fb" "../../../LetsGo/Content/LetsGo/Data/AssetData/AssetNameMapping/AssetNameMapping.fb"
```

**切换项目名**（同一资产要挂到 ProjectT 而不是 LetsGo，改前缀即可）：
```
"E:\src\AssetNameMapping.fb" "../../../ProjectT/Content/LetsGo/Data/AssetData/AssetNameMapping/AssetNameMapping.fb"
```

**短 mount 路径**（Lua 里用相对 Content 路径强制 mount 时常用）：
```
"F:\...\Loading_V4.mp4" "Content/Movies/Loading_V4.mp4"
```

### Step 4 — 调 UnrealPak

```powershell
& "E:\UGit\LetsGoDevelop\ue4_tracking_rdcsp\Engine\Binaries\Win64\UnrealPak.exe" `
  "C:\Users\tsuyu\Desktop\res_base-Android_ASTCClient_<N>_P.pak" `
  "-Create=<ResponseFile>.txt" `
  "-cryptokeys=E:\UGit\LetsGoDevelop\Saved\Crypto.json" `
  "-encryptindex"
```

看到 `Encryption - ENABLED` 和 `Added N files` 就算成功。

### Step 5 — 自检（可选但强烈建议）

```powershell
& "<UnrealPak>" "<pak>" -List "-cryptokeys=<Crypto.json>"
```

确认：
- `Mount point` 是否是你想要的（`../../../ProjectT/...` 还是 `Content/Movies/`）
- 文件清单 & 大小对得上源文件

---

## Lua 侧热更强制 mount 模板

项目已有 `MoePakManager / MoeChunkGroupManager` 体系。**紧急验证场景**下，可以绕开 ChunkGroup，直接把 pak 下发到终端 `PersistentDownloadDir`，然后用 Lua 触发 mount：

```lua
-- 伪代码，真实调用请按 MoePakManager 实际 API 对齐
local MoePakManager = require("Model.ResourceDownload.MoePakManager")

-- 1) pak 已经通过 MoeMultiDownload 或 adb push 到 PersistentDownloadDir
local pakAbsPath = UE.FPaths.ProjectPersistentDownloadDir()
                   .. "/res_base-Android_ASTCClient_6_P.pak"

-- 2) 强制 mount，优先级比 base pak 高即可（N 越大越先查）
--    具体 API 名参考 MoePakManager.cpp / .lua 实现
MoePakManager:ForceMount(pakAbsPath, 100 --[[priority]])

-- 3) 触发资产重载，例如 AssetNameMapping 变了要 reload mapping
UMoeAssetManager:ReloadAssetNameMapping()
```

> 如果项目没有暴露 `ForceMount`，可以 C++ 侧临时加个 exec 命令调 `FCoreDelegates::MountPak.Broadcast(PakPath, 100)`，或者封装 `FPakPlatformFile::Mount`。

---

## Naming / priority 速查

UE pak 加载优先级（高 → 低）：
1. `<Project>_N_p.pak`（N 越大越先）—— 本 skill 生成的就是这一类
2. `<Project>_p.pak`
3. `<Project>.pak` / `pakchunk*.pak`（base）

所以热更覆盖验证：
- `_1_P` 已占用（之前打过）→ 新包从 `_2_P` 开始递增。
- 想强覆盖 base 的某个文件 → 把要覆盖的文件打进 `_N_P`，路径完全一致，N 比线上最大的 `_p` 大即可。

---

## 常见踩坑

| 现象 | 原因 | 解法 |
|---|---|---|
| `Failed to find requested encryption key` | 读 pak 时没传 `-cryptokeys` | 任何 `-List / -Info / 解压` 都必须带 cryptokeys |
| `RSA functionality ... Assertion failed` | Crypto.json 里带了空 `SigningKey` | 只保留 `EncryptionKey`，删掉 SigningKey |
| `Files: 0 / Total: 2xx bytes` 看起来很小 | 正常 — 这里的 "Files 0" 指被加密的单文件数（只加密了 index）；内容其实加进去了 | 用 `-List` 看真实文件清单 |
| mount 后游戏还是读老文件 | pak 优先级不够 / 没真正 mount / 资产被内存缓存 | 加大 `_N_P` 的 N；确认 Lua mount 返回 true；必要时重载对应 manager |
| 安卓上 pak 没生效 | 没放到 `ProjectPersistentDownloadDir`，或路径拼错 | `adb shell ls /sdcard/Android/data/<pkg>/files/UE4Game/<Project>/<Project>/Saved/PersistentDownloadDir/` 验证 |
| Mount point 不对 | response file 里虚拟路径前缀和项目实际加载路径不一致 | 看引擎 log `Mount` 段，和 base pak `-Info` 对齐 |

---

## 快速脚本（拷下来直接跑）

保存为 `E:\UGit\LetsGoDevelop\Saved\QuickPak.ps1`：

```powershell
param(
  [Parameter(Mandatory=$true)][string]$SourceDir,   # 源目录或单文件
  [Parameter(Mandatory=$true)][int]$Index,          # _N_P 的 N
  [string]$ProjectName = "ProjectT",                # LetsGo / ProjectT / ProjectT_Shell
  [string]$SubPath = "Content/LetsGo/Data/AssetData/AssetNameMapping", # pak 内虚拟子路径
  [string]$OutDir = "$env:USERPROFILE\Desktop",
  [switch]$ShortMount                               # 使用 "Content/..." 这种短路径，不加 ../../../Project/
)

$UnrealPak = "E:\UGit\LetsGoDevelop\ue4_tracking_rdcsp\Engine\Binaries\Win64\UnrealPak.exe"
$Crypto    = "E:\UGit\LetsGoDevelop\Saved\Crypto.json"
$Resp      = "E:\UGit\LetsGoDevelop\Saved\QuickPakResponse_$($Index)_P.txt"
$Pak       = Join-Path $OutDir "res_base-Android_ASTCClient_$($Index)_P.pak"

$files = if (Test-Path $SourceDir -PathType Container) {
  Get-ChildItem $SourceDir -Recurse -File
} else { Get-Item $SourceDir }

$lines = foreach ($f in $files) {
  $mount = if ($ShortMount) { "$SubPath/$($f.Name)" }
           else { "../../../$ProjectName/$SubPath/$($f.Name)" }
  '"{0}" "{1}"' -f $f.FullName, $mount
}
Set-Content -Path $Resp -Value $lines -Encoding utf8

& $UnrealPak $Pak "-Create=$Resp" "-cryptokeys=$Crypto" "-encryptindex"
& $UnrealPak $Pak -List "-cryptokeys=$Crypto" | Select-String -Pattern "Mount|size"

Write-Host "`nOutput: $Pak" -ForegroundColor Green
```

用法示例：

```powershell
# 打 AssetNameMapping（ProjectT）
./QuickPak.ps1 -SourceDir "D:\AssetNameMapping_8000" -Index 7

# 打 Loading 视频，用短 mount
./QuickPak.ps1 -SourceDir "F:\...\Loading_V4.mp4" -Index 8 `
  -SubPath "Content/Movies" -ShortMount
```

---

## 与项目现有热更系统的边界

- **正规链路**（线上用）：`HotPatcher → packConfig.json / pakAndroid_etc2.json → ChunkConfig.csv → MoeChunkGroupManager → MoeMultiDownload → MoePakManager`。
- **本 skill**：绕过 HotPatcher 和 ChunkGroup，**只做 UnrealPak 直出 + 手动 mount**，适合：
  - QA / 程序本地复现
  - 线上紧急 hotfix 前的方案验证
  - AssetNameMapping / 资源替换测试
- **千万别**拿本 skill 生成的包直接进发布渠道。

---

## Checklist（AI 执行本 skill 时逐项过一遍）

- [ ] 确认源目录/文件存在，列出清单
- [ ] 确认 `Crypto.json` 存在且只含 `EncryptionKey`
- [ ] 写好 response 文件（正斜杠、UTF-8、无 BOM）
- [ ] pak 命名用 `_N_P` 且 N 不与已有冲突
- [ ] UnrealPak 带 `-encryptindex` 和 `-cryptokeys`
- [ ] 用 `-List` 回验 mount point + 文件清单
- [ ] 输出路径默认桌面，打完报路径 + 大小
- [ ] 如果用户没指定 ProjectName，默认 `ProjectT`，并提示可切换
