---
name: sdk-savedata-migration
description: >-
  扫描分析 LetsGoSDK 下 SaveData 缓存数据的使用情况，识别与外部仓库共享的存档字段，
  生成字段级迁移方案并执行迁移。将 SDK 使用的字段从共享 slot 迁移到 SDK 专属 slot，
  防止与业务玩法数据冲突。Use when the user asks to migrate SaveData, 缓存数据迁移,
  SaveData 解耦, 存档迁移, SDK 存档隔离, or wants to decouple SDK save data from
  shared slots.
---

# SDK SaveData 字段级迁移

扫描 LetsGoSDK 下 SaveData 使用情况，将 SDK 字段从共享 slot 迁移到 SDK 专属 slot，生成分析文档和迁移报告。

## 关键概念

- **slot**: 存档槽位，对应一个本地 JSON 文件（如 `LetsGo_SG_CustomConfig0.json`），由 `SaveDataModel` 管理
- **字段级迁移**: 只提取 SDK 需要的特定字段写入新 slot，不全量复制旧 slot 数据
- **SaveDataName.lua**: slot 名称常量表，位于 `LetsGoSDK/Script/Data/SaveDataName.lua`
- **SaveDataModel.lua**: 存档读写引擎，位于 `LetsGoSDK/Script/Data/SaveDataModel.lua`
- **fallbackSlotName**: `GetSaveData` 的第 4 个参数，新 slot 无数据时自动从旧 slot 加载（注意：返回整个旧 table）
- 参考文档: [iwiki/4008081964](https://iwiki.woa.com/p/4008081964)

## Phase 1: 扫描分析

### 1.1 识别 SDK 使用的 slot

扫描 `LetsGoSDK/Script` 下所有 `.lua` 文件中对 `SaveDataName.*` 的引用：

```
Grep pattern: SaveDataName\.\w+
Path: LetsGoSDK/Script
Glob: *.lua
```

汇总 SDK 实际使用了哪些 slot 常量（如 `CustomConfig`、`LoginData`、`LoginExtraData`、`PushData`）。

### 1.2 逐字段分析

对每个 SDK 使用的 slot，识别 SDK 读写了哪些**字段**。对每个字段判断：

1. **SDK 写入位置** — 哪个 SDK 文件的哪个函数写入该字段
2. **SDK 读取位置** — 哪个 SDK 文件的哪个函数读取该字段
3. **外部是否有活跃代码直接操作** — 扫描外部仓库（`LetsGo/Script`），检查是否有活跃代码直接读写该字段

### 1.3 判断外部代码是否为死代码

对每个外部引用，必须验证：

- 文件是否已迁移到 SDK（检查文件头是否有 `⚠️ 此文件已迁移到 LetsGoSDK` 标记，或 `do return require(...)` 留桩）
- 代码是否在 `--[[ ]]--` 注释块内
- 函数是否已改为转发 SDK 接口（如 `return LoginUtils.xxx()`）
- 检查 `LetsGoSDK/Script/Core/Guard/MigratedFiles.lua` 中是否有对应迁移记录

### 1.4 分类判定

| 分类 | 条件 | 处理 |
|------|------|------|
| 可迁移 | SDK 自闭环，外部无活跃直接操作（或外部已通过 SDK 接口调用） | 迁移到 SDK 专属 slot |
| 需同步修复 | 外部有活跃代码直接读取 SDK 写入的字段 | 迁移 + 修改外部代码改为调用 SDK 接口 |
| 不迁移 | SDK 和外部通过同一接口操作不同 key（天然隔离）；或 slot 完全无外部使用 | 保持现状 |

### 1.5 生成分析文档

在 `LetsGoSDK/Script/Migration/Data/Analysis/` 下生成 `SaveData_SDK独立存档迁移分析.md`，包含：

- 所有字段的读写来源、外部操作状态、迁移结论
- 需修改的文件清单
- 验证清单（逐项列出每个字段的外部活跃状态和验证依据）

## Phase 2: 用户确认

切换到 Plan 模式，向用户展示分析结论和迁移方案，等待确认后再执行。

## Phase 3: 执行迁移

### 3.1 新增 SDK 专属 slot 常量

在 `SaveDataName.lua` 中新增：

```lua
SDKConfig = "LetsGoSDK_SG_Config",
```

### 3.2 创建一次性迁移函数

在合适的 SDK 工具模块中（如 `LoginUtils.lua`）新增迁移函数。核心逻辑：

```lua
local SDK_CONFIG_FIELDS = { "field1", "field2", ... }

function MigrateSDKConfigFromCustomConfig()
    -- 新 slot 已有数据 → 跳过（幂等）
    local newData = SDK.Models.SaveDataModel:GetSaveData(SDK.SaveDataName.SDKConfig, true)
    if newData then return end

    -- 旧 slot 无数据 → 跳过（全新用户）
    local oldData = SDK.Models.SaveDataModel:GetSaveData(SDK.SaveDataName.CustomConfig, true)
    if not oldData then return end

    -- 只提取 SDK 需要的字段，写入新 slot
    newData = SDK.Models.SaveDataModel:GetSaveData(SDK.SaveDataName.SDKConfig)
    for _, field in ipairs(SDK_CONFIG_FIELDS) do
        if oldData[field] ~= nil then
            newData[field] = oldData[field]
        end
    end
    SDK.Models.SaveDataModel:SetSaveData(newData, SDK.SaveDataName.SDKConfig)
end
```

不要用 `fallbackSlotName` 做迁移写入——它会把旧 slot 的整个 table（含业务字段）写入新 slot。

### 3.3 修改 SDK 读写代码

所有原来操作旧 slot 的地方改为：

1. 调用迁移函数（确保数据已迁移）
2. 直接操作新 slot（不再带 fallback）

```lua
function XXX:GetFieldFromSave()
    MigrateSDKConfigFromCustomConfig()
    local saveData = SDK.Models.SaveDataModel:GetSaveData(SDK.SaveDataName.SDKConfig, true)
    return saveData and saveData.myField or defaultValue
end

function XXX:SetFieldToSave(value)
    MigrateSDKConfigFromCustomConfig()
    local saveData = SDK.Models.SaveDataModel:GetSaveData(SDK.SaveDataName.SDKConfig)
    if saveData then
        saveData.myField = value
        SDK.Models.SaveDataModel:SetSaveData(saveData, SDK.SaveDataName.SDKConfig)
    end
end
```

### 3.4 修复外部仓库引用

如果分析阶段发现外部有活跃代码直接读取 SDK 迁移的字段：

1. 在 SDK 中暴露查询接口
2. 修改外部代码改为调用 SDK 接口

### 3.5 处理硬编码 slot name

搜索 SDK 中直接使用字符串字面量的地方（如 `GetSaveData("LetsGo_SG_CustomConfig")`），改为先读新 slot 再 fallback 旧 slot。

## Phase 4: 生成迁移报告

在 `LetsGoSDK/Script/Migration/Data/Result/` 下生成 `SaveData_字段级迁移记录.md`，包含：

- 迁移日期、负责人
- 迁移字段表（字段名、用途、迁移前后位置）
- 现网兼容方案（迁移函数代码）
- 逐文件修改明细
- 未迁移项及原因
- 测试验证要点

## 注意事项

- 存档文件是运行时本地文件（`Saved/SaveGames/`），不是仓库资产，不涉及 AssetNameMapping
- 不要用 `fallbackSlotName` 做迁移写入，只用于 Editor 模式等无法调用迁移函数的场景
- 迁移函数必须**幂等**（新 slot 已有数据则跳过）
- 旧 slot 文件保留不删除，外部业务数据不受影响
- 如果字段通过 `LocalDataSaveModel`（CustomStr key-value 容器）操作，且 SDK 和外部共用同一接口只是 key 不同，则天然隔离不需要迁移
