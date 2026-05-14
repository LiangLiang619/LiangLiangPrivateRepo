# Reference: UE 3C Asset Migration

## AssetRenameManager.cpp — Correct Patched Version

The `FixReferencesAndRename` function in `Engine/Source/Developer/AssetTools/Private/AssetRenameManager.cpp` must contain the UGit redirector block. Below is the complete function body from the reference engine (`ue4_tracking_rdcsp`), lines 317–410:

```cpp
bool FAssetRenameManager::FixReferencesAndRename(const TArray<FAssetRenameData>& AssetsAndNames, bool bAutoCheckout, bool bWithDialog) const
{
	bool bSoftReferencesOnly = true;
	// Prep a list of assets to rename with an extra boolean to determine if they should leave a redirector or not
	TArray<FAssetRenameDataWithReferencers> AssetsToRename;
	AssetsToRename.Reset(AssetsAndNames.Num());
	// Avoid duplicates when adding MapBuildData to list
	TSet<UObject*> AssetsToRenameLookup;
	for (const FAssetRenameData& AssetRenameData : AssetsAndNames)
	{
		AssetsToRenameLookup.Add(AssetRenameData.Asset.Get());
	}
	for (const FAssetRenameData& AssetRenameData : AssetsAndNames)
	{
		if (!AssetRenameData.OldObjectPath.IsValid() && !AssetRenameData.NewObjectPath.IsValid())
		{
			// Rename MapBuildData when renaming world
			UWorld* World = Cast<UWorld>(AssetRenameData.Asset.Get());
			if (World && World->PersistentLevel && World->PersistentLevel->MapBuildData && !AssetsToRenameLookup.Contains(World->PersistentLevel->MapBuildData))
			{
				// Leave MapBuildData inside the map's package
				if (World->PersistentLevel->MapBuildData->GetOutermost() != World->GetOutermost())
				{
					FString NewMapBuildDataName = AssetRenameData.NewName + TEXT("_BuiltData");
					// Perform rename of MapBuildData before world otherwise original files left behind
					AssetsToRename.EmplaceAt(0, FAssetRenameDataWithReferencers(FAssetRenameData(World->PersistentLevel->MapBuildData, AssetRenameData.NewPackagePath, NewMapBuildDataName)));
					AssetsToRename[0].bOnlyFixSoftReferences = AssetRenameData.bOnlyFixSoftReferences;
					AssetsToRenameLookup.Add(World->PersistentLevel->MapBuildData);
				}
			}
		}

		// Perform rename of MapBuildData before world otherwise original files left behind
		UMapBuildDataRegistry* MapBuildData = Cast<UMapBuildDataRegistry>(AssetRenameData.Asset.Get());
		if (MapBuildData)
		{
			AssetsToRename.EmplaceAt(0, FAssetRenameDataWithReferencers(AssetRenameData));
		}
		else
		{
			AssetsToRename.Emplace(FAssetRenameDataWithReferencers(AssetRenameData));
		}

		if (!AssetRenameData.bOnlyFixSoftReferences)
		{
			bSoftReferencesOnly = false;
		}
	}

	// Warn the user if they are about to rename an asset that is referenced by a CDO
	TArray<TWeakObjectPtr<UObject>> CDOAssets = FindCDOReferencedAssets(AssetsToRename);

	// Warn the user if there were any references
	if (CDOAssets.Num())
	{
		FString AssetNames;
		for (auto AssetIt = CDOAssets.CreateConstIterator(); AssetIt; ++AssetIt)
		{
			UObject* Asset = (*AssetIt).Get();
			if (Asset)
			{
				AssetNames += FString("\n") + Asset->GetName();
			}
		}

		const FText MessageText = FText::Format(LOCTEXT("RenameCDOReferences", "The following assets are referenced by one or more Class Default Objects: \n{0}\n\nContinuing with the rename may require code changes to fix these references. Do you wish to continue?"), FText::FromString(AssetNames));
		if (FMessageDialog::Open(EAppMsgType::YesNo, EAppReturnType::No, MessageText) == EAppReturnType::No)
		{
			return false;
		}
	}

	// UGit: Skip reference scanning entirely. Always leave a redirector at the old location and
	// never load, checkout, or save any referencing packages. This is required for large projects
	// under version control (UGit) where touching referencing files is prohibitively expensive
	// and causes merge conflicts across branches. The redirector handles all reference resolution
	// at runtime regardless of whether the reference is hard or soft.
	for (FAssetRenameDataWithReferencers& RenameData : AssetsToRename)
	{
		RenameData.bCreateRedirector = true;
		RenameData.ReferencingPackageNames.Empty();
	}

	// Only check out the packages being renamed (not any referencing packages)
	UpdatePackageStatus(AssetsToRename);

	PerformAssetRename(AssetsToRename);

	// Issue post rename event
	AssetPostRenameEvent.Broadcast(AssetsAndNames);

	// Finally, report any failures that happened during the rename
	return ReportFailures(AssetsToRename, bWithDialog) == 0;
}
```

### Key Patch Block (to be inserted)

This is the **minimum code block** that must exist between the CDO warning `if` block and `UpdatePackageStatus`. If the file does not contain this block, `apply_engine_patch.py` inserts it:

```cpp
	// UGit: Skip reference scanning entirely. Always leave a redirector at the old location and
	// never load, checkout, or save any referencing packages. This is required for large projects
	// under version control (UGit) where touching referencing files is prohibitively expensive
	// and causes merge conflicts across branches. The redirector handles all reference resolution
	// at runtime regardless of whether the reference is hard or soft.
	for (FAssetRenameDataWithReferencers& RenameData : AssetsToRename)
	{
		RenameData.bCreateRedirector = true;
		RenameData.ReferencingPackageNames.Empty();
	}

	// Only check out the packages being renamed (not any referencing packages)
	UpdatePackageStatus(AssetsToRename);
```

### What the patch replaces

In an unpatched engine, the section between the CDO warning block and `PerformAssetRename` typically contains:
- `PopulateAssetReferencers(AssetsToRename);`
- `DetectReadOnlyPackages(AssetsToRename);` or `GatherReferencingObjects(...)`
- Reference fix-up logic and package checkout of referencing packages

The patch **removes** all of that and replaces it with the simple redirector-only loop above.

### Backup & Restore

`apply_engine_patch.py` creates `AssetRenameManager.cpp.bak` before modifying. To restore:

```bash
copy AssetRenameManager.cpp.bak AssetRenameManager.cpp
```

---

## Migration Record Table Schema

File: `LetsGo3C/Migration/AssetsMigration/3CAssetsMigrationRecords.md`

### Header

```markdown
# 3C 资产迁移记录

> 本文件由 `ue-3c-asset-migration` skill 自动维护，请勿手动编辑表格数据。

## 统计

- **累计资产数**: N
- **最近批次时间**: YYYY-MM-DD HH:MM:SS
- **最近批次成功**: X
- **最近批次失败**: Y

## 迁移明细
```

### Table columns

| Column | Key | Description |
|--------|-----|-------------|
| `#` | — | Auto-increment row number |
| `外部资产名` | — | Asset name (from CSV `外部资产名`) |
| `源路径` | **Primary Key** | `/Game/...` source path (from CSV `外部资产完整路径`) |
| `目标路径` | — | `/Game/LetsGo3C/...` destination (from CSV `3C仓库目标路径`) |
| `搬迁方式` | — | Migration method from CSV |
| `负责人` | — | Owner from CSV `负责人(人员)` |
| `引用类型` | — | Reference type from CSV `引用类型` |
| `迁移状态` | — | `成功` / `失败: <reason>` / `已重定向（再次搬迁）` |
| `首次迁移时间` | — | First migration attempt timestamp (never overwritten) |
| `最近更新时间` | — | Latest update timestamp |
| `备注` | — | Free-form notes |

### Merge rules

- **Key**: `源路径` (source_path)
- **On existing row**: update `目标路径`, `搬迁方式`, `负责人`, `引用类型`, `迁移状态`, `最近更新时间`, `备注`; preserve `首次迁移时间`; if previously `成功` and now migrated again → set status to `已重定向（再次搬迁）`
- **On new row**: set `首次迁移时间 = 最近更新时间 = now`
- **Sort order**: ascending by `首次迁移时间`

### Example row

```
| 1 | BP_MoeCharBase | /Game/LetsGo/Assets/Character/BP_MoeCharBase | /Game/LetsGo3C/Assets/Base/Character/Blueprint/BP_MoeCharBase | 直接搬迁 | chrisguo | hard+serialized | 成功 | 2026-05-14 17:00:00 | 2026-05-14 17:00:00 | |
```
