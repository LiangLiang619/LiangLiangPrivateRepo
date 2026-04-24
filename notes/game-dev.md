# 📚 游戏开发

> 共 5 条笔记 · 最后同步：2026-04-24

---

## ⭐️⭐️⭐️ ProjectT Android 包解包流程

**来源**：工作 · **创建**：2026-04-24 · #Android #LetsGo #UE5 #热更

> 从流水线下载 Android 包并使用 UnrealPakViewerMoe 解包查看 pak 资产的完整流程

## 📌 核心概念

- 目的：从流水线下载的 Android 安装包中，提取并查看 pak 资产内容
- 工具：UnrealPakViewerMoe（编译自游戏项目）
- 密钥路径：`LetsGoDevelop\LetsGo\Tools\MoeAssetsToolSet\Config\Crypto.json`

## 💻 完整步骤

### Step 1：从流水线下载包

- 从 CI/CD 流水线下载 Android 安装包（apk/obb 格式）

### Step 2：解压 apk

- 将 apk 文件后缀改为 `.zip`
- 解压 zip，进入 `assets/` 目录

```plain text
ProjectT-Android-CN-Development-0.0.462.1-xiaowo-farmcrazy-6-signed/
└── assets/
    ├── main.obb.zip          ← 重点文件（约 1.7 GB）
    ├── MidasPay.zip
    ├── libwbsafeedit
    ├── MSDKConfig.ini
    └── ...
```

### Step 3：解压 main.obb

- 在 `assets/` 目录中找到 `main.obb` 文件（此时已是 `main.obb.zip`）
- 解压后，pak 文件存放在以下目录：

```plain text
assets/ProjectT/Content/Paks/
├── p_680010001-Android_ASTCClient.pak          (404,575 KB)
├── p_avatar_effect-Android_ASTCClient.pak      (28,981 KB)
├── p_base_prop-Android_ASTCClient.pak          (3,649 KB)
├── p_cl_baseblueprint-Android_ASTCClient.pak   (324 KB)
├── p_common_effect-Android_ASTCClient.pak      (43,483 KB)
├── p_common_effect_none_ref-Android_ASTCClient.pak (4,813 KB)
├── p_effect_ogc-Android_ASTCClient.pak         (1,790 KB)
├── p_f_sdk_main-Android_ASTCClient.pak         (18,957 KB)
├── p_feature_community_new-Android_ASTCClient.pak (276,534 KB)
├── p_feature_projectt_startup-Android_ASTCClient.pak (2 KB)
├── p_featurebase_placeable_mini-Android_ASTCClient.pak (20,379 KB)
├── p_mainstartup_res-Android_ASTCClient.pak    (11,206 KB)
└── res_base-Android_ASTCClient.pak             (894,129 KB)
```

### Step 4：打开解包工具

- 在 IDE（CLion/Rider）中打开游戏项目
- 编译参数下拉菜单 → **Programs** → 选择 **UnrealPakViewerMoe**
- 点击编译/运行，即可打开解包查看工具

## ⚠️ 注意事项

- 解压密码（AES Key）保存在：`LetsGoDevelop\LetsGo\Tools\MoeAssetsToolSet\Config\Crypto.json`
- Crypto.json 位于 LetsGo_Tools 仓库（Git），`Config/` 目录下，与 `common_project_settings.yaml` 等同级
- pak 命名规则：`{包名}-Android_ASTCClient.pak`，平台后缀为 ASTCClient（Android ASTC 纹理格式）

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

---

## ⭐️⭐️ 手机端强制Mount Pak文件

**来源**：工作 · **创建**：2026-04-24 · #Lua #UE5 #热更

> 通过Lua在iOS手机端强制挂载pak文件，使用GetPhysicalFullPathVer获取持久化下载目录并调用UPakMountManager.Mount

## 📌 核心流程

- 通过 `FMoeDolphinManager:GetPhysicalFullPathVer()` 获取实际物理路径
- `UBlueprintPathsLibrary.ProjectPersistentDownloadDir()` 获取持久化下载目录
- 拼接 pak 文件名得到完整路径
- 调用 `UPakMountManager.Mount(pak_path, mount_order)` 挂载

## 💻 示例代码

以下示例为 pak 位于 iOS 手机塞文件的根目录（PersistentDownloadDir）：

```lua
local function mount_pak(pak_file_name, mount_order)
    local download_dir = UE4.FMoeDolphinManager.GetInstance():GetPhysicalFullPathVer(
        UE4.UBlueprintPathsLibrary.ProjectPersistentDownloadDir()
    )
    local pak_path = string.format("%s/%s", download_dir, pak_file_name)
    UE4.UPakMountManager.Mount(pak_path, mount_order)
end

mount_pak("YourAsset.pak", 0)
```

## ⚠️ 注意事项

- `mount_order` 决定 pak 的优先级，值越小优先级越高
- `GetPhysicalFullPathVer` 是项目自定义的路径解析方法，将虚拟路径转为真实物理路径
- 确保 pak 文件已存在于设备的 PersistentDownloadDir 目录下

---

## ⭐️⭐️ UE5 网络同步原理与实践（以 IdleShow 为例）

**来源**：工作 · **创建**：2026-04-22 · #UE5

> UE5 网络同步核心原理，结合 IdleShow 项目实践

---

## ⭐️⭐️ ProjectT 启动 LocalDS 的方式

**来源**：工作 · **创建**：2026-04-22 · #UE5 #LetsGo

> ProjectT 项目中启动本地 Dedicated Server 的配置与流程

---
