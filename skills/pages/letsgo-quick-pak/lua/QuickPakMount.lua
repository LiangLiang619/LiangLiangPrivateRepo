--[[
  QuickPakMount — letsgo-quick-pak 运行时 mount 助手（手写，提交）
  ----------------------------------------------------------------
  上层 generated/lua/Mount_<pak>.lua 通过 MountFromInfo(info) 调本模块。

  约定的 info 结构：
    {
      pakName  = "res_base-Android_ASTCClient_2_P.pak",
      priority = 100,
      reload   = true/false,     -- mount 后是否重载 AssetNameMapping
      mounts   = { "../../../ProjectT/Content/...", ... },  -- 仅用于日志
    }

  Pak 假定放在 FPaths::ProjectPersistentDownloadDir() 根下。
]]

local M = {}

local function log(fmt, ...)
    print(string.format("[QuickPak] " .. fmt, ...))
end

--- 获取 pak 绝对路径
local function ResolvePakPath(pakName)
    local dir = ""
    if UE and UE.FPaths and UE.FPaths.ProjectPersistentDownloadDir then
        dir = UE.FPaths.ProjectPersistentDownloadDir()
    end
    if dir == "" then
        log("Warning: ProjectPersistentDownloadDir empty, using relative path")
    end
    if dir ~= "" and not dir:match("[/\\]$") then dir = dir .. "/" end
    return dir .. pakName
end

--- 逐个尝试已知的 mount API，哪路能跑哪路上
local function DoMount(pakPath, priority)
    -- 路 1：项目自带 MoePakManager（推荐；如存在，会把 pak 注册到业务体系）
    local ok, MoePakManager = pcall(require, "Model.ResourceDownload.MoePakManager")
    if ok and MoePakManager then
        if type(MoePakManager.ForceMount) == "function" then
            local r = MoePakManager:ForceMount(pakPath, priority)
            return r ~= false, "MoePakManager.ForceMount"
        end
        if type(MoePakManager.Mount) == "function" then
            local r = MoePakManager:Mount(pakPath, priority)
            return r ~= false, "MoePakManager.Mount"
        end
    end

    -- 路 2：UE FCoreDelegates.OnMountPak（UnLua 暴露时可用）
    if UE and UE.FCoreDelegates and UE.FCoreDelegates.OnMountPak then
        local r = UE.FCoreDelegates.OnMountPak:Broadcast(pakPath, priority or 100, nil)
        return r ~= false, "FCoreDelegates.OnMountPak"
    end

    -- 路 3：兜底走 exec 控制台命令（需要 C++ 侧已注册 Exec MountPak 处理）
    if UE and UE.UKismetSystemLibrary and UE.UKismetSystemLibrary.ExecuteConsoleCommand then
        UE.UKismetSystemLibrary.ExecuteConsoleCommand(nil, string.format('MountPak "%s" %d', pakPath, priority or 100), nil)
        return true, "ExecuteConsoleCommand"
    end

    return false, "no mount api available"
end

--- mount 成功后的可选重载
local function ReloadAssetNameMapping()
    if UMoeAssetManager and UMoeAssetManager.ReloadAssetNameMapping then
        UMoeAssetManager:ReloadAssetNameMapping()
        log("AssetNameMapping reloaded")
    end
end

function M.MountFromInfo(info)
    assert(info and info.pakName, "QuickPakMount: invalid info")

    local pakPath = ResolvePakPath(info.pakName)
    log("mount %s (priority=%d)", pakPath, info.priority or 100)

    local ok, via = DoMount(pakPath, info.priority or 100)
    log("  via=%s result=%s", tostring(via), tostring(ok))

    if ok and info.reload then
        ReloadAssetNameMapping()
    end
    return ok
end

return M
