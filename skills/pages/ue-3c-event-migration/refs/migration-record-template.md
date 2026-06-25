# 事件迁移记录模板

> 实际使用时复制本模板到
> `Content/LetsGo3C/Migration/Records/EventMigration_<batch_name>_<YYYYMMDD>.md`，
> 替换所有 `<placeholder>` 内容。

---

# EventMigration — <batch_name>

- **迁移日期**：<YYYY-MM-DD>
- **操作人**：<@handle>
- **触发来源**：<会话描述 / CSV 文件路径>

## 本批迁入事件

### Flat Key（通过 BeforeInitEvents → AppendEvents 合并）

| # | event_key | value string | 原声明文件:行 | 已有/新增 |
|---|-----------|-------------|--------------|----------|
| 1 | `<KEY>` | `"<VALUE>"` | `<file>:<line>` | 新增 |

### Subtable Key（通过 PostInitEvents → TableUtils.Merge 合并）

| # | subtable.key | value string | 原声明文件:行 | 已有/新增 |
|---|-------------|-------------|--------------|----------|
| 1 | `<SubTable>.<Key>` | `"<VALUE>"` | `<file>:<line>` | 新增 |

### 已在 3C 的事件（仅校对）

| # | event_key | value 一致? | 备注 |
|---|-----------|------------|------|
| 1 | `<KEY>` | 是/否 | <如不一致说明差异> |

## 子表合并机制

- [ ] 本批是否首次引入 `PostInitEvents` Hook？（是/否）
- [ ] `LetsGo3CSubtableEvents.lua` 是否为新文件？（是/否）
- [ ] `SDK_HookConfig.lua` 是否有新增条目？（是/否）

## 文件变更清单

| 文件 | 变更类型 | 描述 |
|------|---------|------|
| `LetsGo3C/Script/Core/Event/LetsGo3CEvents.lua` | 修改 | 追加 N 个 flat key |
| `LetsGo3C/Script/Core/Event/LetsGo3CSubtableEvents.lua` | 新增/修改 | 追加 N 个子表 key |
| `LetsGo3C/Script/Hooks/Event/CommonEventEnumPostInitEventsHook.lua` | 新增 | PostInitEvents handler |
| `LetsGo3C/Script/HookConfig/OverrideSDK/SDK_HookConfig.lua` | 修改 | 注册 PostInitEvents hook |
| `<源仓库 EventEnum 文件>` | 修改（可选） | 删除已迁移的 KV |

## 源仓库删除状态

| 原文件 | key | 是否已删除 | 备注 |
|--------|-----|----------|------|
| `<file>` | `<KEY>` | 是/否/保留 | <保守策略说明> |

## 冒烟检查清单

- [ ] PIE 启动无 `attempt to index a nil value (field 'EventEnum')` 报错
- [ ] 抽样 flat key：`_MOE.EventEnum.<KEY>` 与 `MOE_3C.EventEnum.<KEY>` 取值一致
- [ ] 抽样 subtable key：`_MOE.EventEnum.<SubTable>.<Key>` 与 `MOE_3C.EventEnum.<SubTable>.<Key>` 取值一致
- [ ] listener 仍能收到 dispatch（抽样验证高频事件）
- [ ] `LetsGo3CEvents.lua` 内无重复 key（非 Shipping 模式下 SDK 会 LogWarning）
- [ ] `LetsGo3CSubtableEvents.lua` 中 value string 与源声明完全一致
- [ ] 3C 代码内不再有 `_MOE.EventEnum.<已迁移 KEY>`，统一使用 `MOE_3C.EventEnum.<KEY>`

## 遗留问题

| 问题 | 状态 | 跟进人 |
|------|------|--------|
| <描述> | 待处理/已解决 | <@handle> |
