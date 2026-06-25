# -*- coding: utf-8 -*-
# UE AssetRegistry 双向引用扫描模板
# 在 UE 编辑器 Python 环境中运行。
# 使用前替换下方 ===CONFIG=== 区块中的变量。

import csv
import os
import unreal

# ===CONFIG=== 按实际目录修改 ================================================
TARGET_ROOT = "/Game/LetsGo/Assets/Effect/VFX_Community"
EFFECT_ROOT = "/Game/LetsGo/Assets/Effect"
KEEP_DIRS = {
    "vfx_material": "/Game/LetsGo/Assets/Effect/VFX_Material",
    "vfx_mesh": "/Game/LetsGo/Assets/Effect/VFX_Mesh",
    "vfx_texture": "/Game/LetsGo/Assets/Effect/VFX_Texture",
}
OUTPUT_PREFIX = "VFX_Community"
# ===CONFIG END===============================================================

DETAIL_CSV = OUTPUT_PREFIX + "_reference_detail.csv"
SUMMARY_CSV = OUTPUT_PREFIX + "_reference_summary.csv"


def _s(v):
    return "" if v is None else str(v)


def classify(target_str):
    if not target_str:
        return "empty"
    if target_str.startswith(TARGET_ROOT):
        return "target_internal"
    for key, prefix in KEEP_DIRS.items():
        if target_str.startswith(prefix):
            return key
    if target_str.startswith(EFFECT_ROOT):
        return "effect_other"
    if target_str.startswith("/Game/LetsGo/"):
        return "letsgo_non_effect"
    if target_str.startswith("/Game/Feature"):
        return "feature_content"
    if target_str.startswith("/Engine/"):
        return "engine"
    return "other"


def make_dep_opts():
    opts = unreal.AssetRegistryDependencyOptions()
    for attr, val in (
        ("include_soft_package_references", True),
        ("include_hard_package_references", True),
        ("include_hard_management_references", True),
        ("include_editor_only_dependencies", False),
    ):
        if hasattr(opts, attr):
            setattr(opts, attr, val)
    return opts


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    detail_path = os.path.join(script_dir, DETAIL_CSV)
    summary_path = os.path.join(script_dir, SUMMARY_CSV)

    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    try:
        ar.wait_for_completion()
    except Exception:
        pass

    dep_opts = make_dep_opts()
    assets = ar.get_assets_by_path(TARGET_ROOT, recursive=True)
    unreal.log("{0} scan: found {1} assets under {2}".format(OUTPUT_PREFIX, len(assets), TARGET_ROOT))

    counts = {}
    detail = []

    keep_keys = sorted(KEEP_DIRS.keys())
    dep_keep_fields = ["dep_" + k for k in keep_keys]

    for idx, ad in enumerate(assets):
        if idx > 0 and idx % 100 == 0:
            unreal.log("{0} scan: processed {1}/{2}".format(OUTPUT_PREFIX, idx, len(assets)))

        pkg = _s(ad.package_name)
        obj = _s(ad.object_path)
        cls = _s(ad.asset_class)

        c = {
            "object_path": obj,
            "asset_class": cls,
            "dep_target_internal": 0,
            "dep_effect_other": 0,
            "dep_outside": 0,
            "ref_external": 0,
            "ref_internal": 0,
        }
        for k in keep_keys:
            c["dep_" + k] = 0
        counts[pkg] = c

        try:
            deps = ar.get_dependencies(ad.package_name, dep_opts)
        except Exception:
            deps = []
        for d in deps:
            ds = _s(d)
            cat = classify(ds)
            detail.append({
                "source_package": pkg,
                "source_object_path": obj,
                "source_asset_class": cls,
                "relation": "dependency",
                "target": ds,
                "target_category": cat,
            })
            if cat == "target_internal":
                c["dep_target_internal"] += 1
            elif cat in KEEP_DIRS:
                c["dep_" + cat] += 1
            elif cat == "effect_other":
                c["dep_effect_other"] += 1
            else:
                c["dep_outside"] += 1

        try:
            refs = ar.get_referencers(ad.package_name, dep_opts)
        except Exception:
            refs = []
        for r in refs:
            rs = _s(r)
            cat = classify(rs)
            detail.append({
                "source_package": pkg,
                "source_object_path": obj,
                "source_asset_class": cls,
                "relation": "referencer",
                "target": rs,
                "target_category": cat,
            })
            if rs.startswith(TARGET_ROOT):
                c["ref_internal"] += 1
            else:
                c["ref_external"] += 1

    det_fields = ["source_package", "source_object_path", "source_asset_class",
                  "relation", "target", "target_category"]
    with open(detail_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=det_fields)
        w.writeheader()
        w.writerows(detail)

    sum_fields = (["source_package", "source_object_path", "source_asset_class",
                   "dep_target_internal"] + dep_keep_fields +
                  ["dep_effect_other", "dep_outside",
                   "referencer_external_count", "referencer_internal_count"])
    with open(summary_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=sum_fields)
        w.writeheader()
        for pkg in sorted(counts):
            c = counts[pkg]
            row = {
                "source_package": pkg,
                "source_object_path": c["object_path"],
                "source_asset_class": c["asset_class"],
                "dep_target_internal": c["dep_target_internal"],
                "dep_effect_other": c["dep_effect_other"],
                "dep_outside": c["dep_outside"],
                "referencer_external_count": c["ref_external"],
                "referencer_internal_count": c["ref_internal"],
            }
            for k in keep_keys:
                row["dep_" + k] = c["dep_" + k]
            w.writerow(row)

    unreal.log("{0} scan: wrote {1} detail rows -> {2}".format(OUTPUT_PREFIX, len(detail), detail_path))
    unreal.log("{0} scan: wrote summary -> {1}".format(OUTPUT_PREFIX, summary_path))


if __name__ == "__main__":
    main()
