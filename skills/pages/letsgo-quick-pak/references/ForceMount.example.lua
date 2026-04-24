--[[
  LetsGo / ProjectT 热更 pak 强制 mount 示例
  ------------------------------------------
  前提：
    1) 已用 letsgo-quick-pak skill 打出 res_base-Android_ASTCClient_<N>_P.pak
    2) 已通过 MoeMultiDownload / adb push 把 pak 放到设备的
       FPaths::ProjectPersistentDownloadDir()
       常见位置：
         /sdcard/Android/data/<package>/files/UE4Game/<Project>/<Project>/Saved/PersistentDownloadDir/
  使用：
    - 只为验证问题是否被修复，不走 ChunkGroup 流程
    - 触发时机建议：登录前 / 进入玩法前 / GM 指令
]]

local M = {}

--- 强制 mount 本地 pak
-- @param fileName string     pak 文件名，例如 "res_base-Android_ASTCClient_6_P.pak"
-- @param priority number     数字越大越先查，通常给 100+
-- @return boolean, string
function M.ForceMountLocal(fileName, priority)
    priority = priority or 100
    local UEPaths = UE.FPaths
    local pakPath = UEPaths.ProjectPersistentDownloadDir() .. "/" .. fileName

    -- 方式 1：项目自带的 MoePakManager（推荐，会同步更新内部状态）
    local MoePakManager = _G.MoePakManager or require("Model.ResourceDownload.MoePakManager")
    if MoePakManager and MoePakManager.Mount then
        local ok = MoePakManager:Mount(pakPath, priority)
        return ok, pakPath
    end

    -- 方式 2：兜底走 FCoreDelegates.OnMountPak
    if UE.FCoreDelegates and UE.FCoreDelegates.OnMountPak then
        local ok = UE.FCoreDelegates.OnMountPak:Broadcast(pakPath, priority, nil)
        return ok, pakPath
    end

    return false, "No mount API available"
end

--- Mount 完之后，典型的重载动作
function M.ReloadAfterMount()
    -- AssetNameMapping 变了要重新读 mapping（UMoeAssetManager 负责）
    if UMoeAssetManager and UMoeAssetManager.ReloadAssetNameMapping then
        UMoeAssetManager:ReloadAssetNameMapping()
    end

    -- 配置表 / Lua 模块按需重置缓存
    -- package.loaded["SomeConfig"] = nil
end

--- 一键验证流程
function M.QuickVerify(fileName)
    local ok, info = M.ForceMountLocal(fileName, 999)
    print(string.format("[QuickPak] Mount %s => %s (%s)", fileName, tostring(ok), tostring(info)))
    if ok then
        M.ReloadAfterMount()
    end
    return ok
end

return M

--[[
用法：
  local QuickPak = require("Dev.QuickPakMount")
  QuickPak.QuickVerify("res_base-Android_ASTCClient_6_P.pak")
]]
