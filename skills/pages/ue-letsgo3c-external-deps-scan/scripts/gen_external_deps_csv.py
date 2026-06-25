"""
gen_external_deps_csv.py
------------------------
Parse ue_batch JSON result files, filter external dependencies (outside the
repo's /Game prefix), and output two CSVs:

1. Detail CSV   — one row per in-repo asset with its external deps listed
2. Aggregate CSV — one row per external asset with reverse in-repo referencers,
                   including asset_class and broad category columns

Usage:
  python gen_external_deps_csv.py \
    --batch-files batch_001.json batch_002.json \
    --game-prefix "/Game/LetsGo3C/" \
    --out-dir "./output"

  # Or via a list file:
  python gen_external_deps_csv.py \
    --batch-list batch_files.txt \
    --game-prefix "/Game/LetsGo3C/" \
    --out-dir "./output"
"""

import argparse
import collections
import csv
import json
import os
import sys


# Broad category mapping by UE asset_class
_ART_ANIM = {
    "Skeleton", "AnimSequence", "AnimMontage", "AnimBlueprint",
    "AnimBlueprintGeneratedClass", "BlendSpace", "BlendSpace1D",
    "AimOffsetBlendSpace", "AimOffsetBlendSpace1D", "AnimComposite",
    "AnimNotify", "AnimNotifyState", "PoseAsset", "AnimSyncMarker",
    "LevelSequence", "MovieSceneTrack",
}
_ART_FX = {
    "ParticleSystem", "NiagaraSystem", "NiagaraEmitter",
    "NiagaraParameterCollection", "NiagaraParameterCollectionInstance",
}
_ART_MATERIAL = {
    "Material", "MaterialInstance", "MaterialInstanceConstant",
    "MaterialInstanceDynamic", "MaterialFunction",
    "MaterialParameterCollection", "MaterialParameterCollectionInstance",
    "SubsurfaceProfile",
}
_ART_TEXTURE = {
    "Texture2D", "TextureCube", "TextureRenderTarget2D",
    "TextureRenderTargetCube", "VolumeTexture",
    "PaperSprite", "PaperTileSet", "PaperFlipbook",
    "PaperSpriteAtlas",
}
_ART_MESH = {
    "StaticMesh", "SkeletalMesh", "DestructibleMesh",
    "PhysicsAsset", "PhysicalMaterial", "GroomAsset",
}
_ART_AUDIO = {
    "SoundCue", "SoundWave", "SoundMix", "SoundClass",
    "SoundAttenuation", "SoundConcurrency", "ReverbEffect",
    "MetaSound", "MetaSoundSource", "AudioBus",
}
_ART_FONT = {"Font", "FontFace"}

_UI = {"WidgetBlueprint", "UserWidget", "Slate"}

_DATA = {
    "DataTable", "DataAsset", "PrimaryDataAsset",
    "CurveFloat", "CurveVector", "CurveLinearColor",
    "CurveTable", "StringTable",
}

_BLUEPRINT = {
    "Blueprint", "BlueprintGeneratedClass", "ActorComponent",
    "GameplayAbility", "GameplayEffect", "GameplayCue",
    "GameplayAbilityTargetActor",
}

_ENUM_STRUCT = {"UserDefinedEnum", "UserDefinedStruct"}


def classify_asset(asset_class):
    """Return (细分类型, 资产大类) for the given UE asset_class string."""
    if asset_class in _ART_ANIM:
        return asset_class, "美术-动画"
    if asset_class in _ART_FX:
        return asset_class, "美术-特效"
    if asset_class in _ART_MATERIAL:
        return asset_class, "美术-材质"
    if asset_class in _ART_TEXTURE:
        return asset_class, "美术-贴图"
    if asset_class in _ART_MESH:
        return asset_class, "美术-网格"
    if asset_class in _ART_AUDIO:
        return asset_class, "美术-音效"
    if asset_class in _ART_FONT:
        return asset_class, "美术-字体"
    if asset_class in _UI:
        return asset_class, "UI蓝图"
    if asset_class in _DATA:
        return asset_class, "数据资产"
    if asset_class in _BLUEPRINT:
        return asset_class, "蓝图"
    if asset_class in _ENUM_STRUCT:
        return asset_class, "枚举/结构"
    if asset_class == "ObjectRedirector":
        return asset_class, "重定向器"
    return asset_class, "其他"


def extract_dep_list(items):
    """Normalize dependency items to a list of (package_name, asset_class) tuples."""
    result = []
    if not items:
        return result
    for item in items:
        if isinstance(item, dict):
            pkg = item.get("package_name", "")
            cls = item.get("asset_class", "")
            if pkg:
                result.append((pkg, cls))
        elif isinstance(item, str):
            result.append((item, ""))
    return result


def is_external_dep(pkg, game_prefix):
    """Return True if pkg is a /Game/ path outside the repo prefix."""
    if not pkg.startswith("/Game/"):
        return False
    if pkg.startswith(game_prefix):
        return False
    return True


def get_root_dir(pkg):
    """Extract the first directory segment under /Game/. e.g. /Game/LetsGo/Foo -> LetsGo"""
    parts = pkg.split("/")
    if len(parts) >= 3:
        return parts[2]
    return ""


def load_batch_results(batch_files):
    """Load all batch JSON files and return:
      asset_deps: {asset_path: [(dep_pkg, asset_class), ...]}
      class_map:  {dep_pkg: asset_class}   (best known class per package)
    """
    asset_deps = {}
    class_map = {}

    for bf in batch_files:
        bf = bf.strip()
        if not bf or not os.path.isfile(bf):
            print(f"  [warn] Batch file not found, skipping: {bf}", file=sys.stderr)
            continue

        with open(bf, "r", encoding="utf-8") as f:
            data = json.load(f)

        results = data if isinstance(data, list) else data.get("results", [])

        for r in results:
            if not isinstance(r, dict):
                continue
            if not r.get("success", True):
                continue

            query_path = r.get("query_path", "") or r.get("asset_path", "")
            if not query_path:
                params = r.get("params", {})
                if isinstance(params, dict):
                    query_path = params.get("asset_path", "")
            if not query_path:
                continue

            deps = extract_dep_list(r.get("dependencies", []))

            # Update class_map
            for pkg, cls in deps:
                if cls and pkg not in class_map:
                    class_map[pkg] = cls

            # Merge into asset_deps
            if query_path in asset_deps:
                existing_pkgs = {p for p, _ in asset_deps[query_path]}
                for dep in deps:
                    if dep[0] not in existing_pkgs:
                        asset_deps[query_path].append(dep)
                        existing_pkgs.add(dep[0])
            else:
                asset_deps[query_path] = deps

    return asset_deps, class_map


def main():
    parser = argparse.ArgumentParser(
        description="Filter external dependencies and generate Detail + Aggregate CSVs")
    parser.add_argument("--batch-files", nargs="*", default=[],
                        help="Paths to batch result JSON files")
    parser.add_argument("--batch-list", default=None,
                        help="Text file listing batch JSON paths (one per line)")
    parser.add_argument("--game-prefix", required=True,
                        help="The /Game/ prefix for the repo, e.g. /Game/LetsGo3C/")
    parser.add_argument("--out-dir", required=True,
                        help="Output directory for CSV files")
    args = parser.parse_args()

    game_prefix = args.game_prefix
    if not game_prefix.endswith("/"):
        game_prefix += "/"

    batch_files = list(args.batch_files)
    if args.batch_list and os.path.isfile(args.batch_list):
        with open(args.batch_list, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    batch_files.append(line)

    if not batch_files:
        print("[error] No batch files provided. Use --batch-files or --batch-list.",
              file=sys.stderr)
        sys.exit(1)

    print(f"Game prefix:  {game_prefix}")
    print(f"Batch files:  {len(batch_files)}")

    asset_deps, class_map = load_batch_results(batch_files)
    print(f"Total assets loaded: {len(asset_deps)}")

    os.makedirs(args.out_dir, exist_ok=True)

    detail_rows = []
    # ext_to_info: {ext_pkg: {"refs": [in_repo_path, ...], "class": str}}
    ext_to_info = {}

    total_assets = len(asset_deps)
    assets_with_ext_deps = 0

    for asset_path in sorted(asset_deps.keys()):
        all_deps = asset_deps[asset_path]

        ext_deps = []
        seen = set()
        for pkg, cls in all_deps:
            if pkg in seen:
                continue
            seen.add(pkg)
            if is_external_dep(pkg, game_prefix):
                ext_deps.append((pkg, cls))

        if not ext_deps:
            continue

        assets_with_ext_deps += 1
        asset_name = asset_path.rsplit("/", 1)[-1]

        root_counter = collections.Counter()
        for pkg, _ in ext_deps:
            root_counter[get_root_dir(pkg)] += 1
        root_dist = ";".join(f"{k}:{v}" for k, v in root_counter.most_common())

        detail_rows.append({
            "本仓资产名": asset_name,
            "本仓资产路径": asset_path,
            "外部依赖数量": len(ext_deps),
            "外部依赖资产列表": "|".join(p for p, _ in ext_deps),
            "外部依赖根目录分布": root_dist,
        })

        for pkg, cls in ext_deps:
            if pkg not in ext_to_info:
                resolved_cls = cls or class_map.get(pkg, "")
                ext_to_info[pkg] = {"refs": [], "class": resolved_cls}
            ext_to_info[pkg]["refs"].append(asset_path)
            # Update class if we now have a better one
            if not ext_to_info[pkg]["class"] and cls:
                ext_to_info[pkg]["class"] = cls

    detail_path = os.path.join(args.out_dir, "External_Deps_Detail.csv")
    detail_cols = ["本仓资产名", "本仓资产路径", "外部依赖数量",
                   "外部依赖资产列表", "外部依赖根目录分布"]

    with open(detail_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=detail_cols)
        writer.writeheader()
        writer.writerows(detail_rows)

    print(f"\nDetail CSV:    {detail_path}  ({len(detail_rows)} rows)")

    agg_rows = []
    for ext_path, info in ext_to_info.items():
        ext_name = ext_path.rsplit("/", 1)[-1]
        ref_list = info["refs"]
        asset_class = info["class"]
        _cls, broad = classify_asset(asset_class)
        agg_rows.append({
            "外部资产名": ext_name,
            "外部资产路径": ext_path,
            "外部资产根目录": get_root_dir(ext_path),
            "资产类型": asset_class,
            "资产大类": broad,
            "被本仓资产引用次数": len(ref_list),
            "被引用的本仓资产列表": "|".join(sorted(ref_list)),
        })

    # Sort: primarily by 资产大类, secondarily by 被引次数 desc
    agg_rows.sort(key=lambda r: (r["资产大类"], -r["被本仓资产引用次数"]))

    agg_path = os.path.join(args.out_dir, "External_Deps_Aggregate.csv")
    agg_cols = ["外部资产名", "外部资产路径", "外部资产根目录",
                "资产类型", "资产大类",
                "被本仓资产引用次数", "被引用的本仓资产列表"]

    with open(agg_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=agg_cols)
        writer.writeheader()
        writer.writerows(agg_rows)

    print(f"Aggregate CSV: {agg_path}  ({len(agg_rows)} rows)")

    root_total = collections.Counter()
    cat_total = collections.Counter()
    for ext_path, info in ext_to_info.items():
        root_total[get_root_dir(ext_path)] += 1
        _cls, broad = classify_asset(info["class"])
        cat_total[broad] += 1

    # For Top 5 by ref count
    top_by_refs = sorted(agg_rows, key=lambda r: -r["被本仓资产引用次数"])

    print(f"\n{'=' * 45}")
    print(f" 外部依赖扫描简报")
    print(f"{'=' * 45}")
    print(f"本仓资产总数:            {total_assets}")
    print(f"含外部依赖的资产数:      {assets_with_ext_deps}")
    print(f"外部依赖资产 (unique):   {len(ext_to_info)}")
    print()

    print("按资产大类分布:")
    for cat, cnt in cat_total.most_common():
        print(f"  {cat:20s}  {cnt}")
    print()

    print("Top 5 外部根目录:")
    for root, cnt in root_total.most_common(5):
        print(f"  {root:20s}  {cnt}")
    print()

    print("Top 5 被引最多的外部资产:")
    for row in top_by_refs[:5]:
        print(f"  [{row['资产大类']}] {row['外部资产路径']:50s}  {row['被本仓资产引用次数']} 次")

    print(f"{'=' * 45}")


if __name__ == "__main__":
    main()
