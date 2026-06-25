"""
gen_deps_csv.py
---------------
Merge ObjectRedirector referencers into each asset's reverse deps and write CSV.

Usage (post-migration, with redirector merging):
  python gen_deps_csv.py \
    --state _scan_state.json \
    --redirector-batches RFILE1.txt RFILE2.txt \
    --asset-order assets.txt \
    --out output_Deps_Refs.csv

Usage (pre-migration, no redirector merging):
  python gen_deps_csv.py \
    --state _prescan_state.json \
    --asset-order assets_pre.txt \
    --out output_PreMigration_Deps_Refs.csv \
    --name-col "资产名（迁移后）" \
    --path-col "迁移前资产路径"

assets.txt: one asset_path per line (defines row order in output CSV).
"""

import argparse
import csv
import json
import os


def extract_pkg_list(items):
    result = []
    for item in items:
        if isinstance(item, dict):
            result.append(item)
        elif isinstance(item, str):
            result.append({"package_name": item,
                            "asset_name": item.rsplit("/", 1)[-1],
                            "asset_class": ""})
    return result


def merge_refs(asset_path, direct_refs, redirector_map, redirector_refs):
    """
    merged = (direct_refs - ObjectRedirectors) UNION (refs of each ObjectRedirector)
    Dedup by package_name.
    """
    redirector_pkgs = {ref["package_name"]
                       for ref in direct_refs
                       if ref.get("asset_class") == "ObjectRedirector"}
    seen = {}

    def add(item):
        pkg = item.get("package_name", "")
        if pkg and pkg not in seen:
            seen[pkg] = item

    for ref in direct_refs:
        if ref.get("asset_class") != "ObjectRedirector":
            add(ref)

    for rdir_pkg in redirector_pkgs:
        for ref in redirector_refs.get(rdir_pkg, []):
            if ref.get("package_name") != asset_path:
                add(ref)

    return list(seen.values())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--state",             required=True)
    parser.add_argument("--redirector-batches", nargs="*", default=[])
    parser.add_argument("--asset-order",        required=True,
                        help="Text file with one asset_path per line")
    parser.add_argument("--out",               required=True)
    parser.add_argument("--name-col",  default="资产名",
                        help="Header for the asset name column")
    parser.add_argument("--path-col",  default="资产路径",
                        help="Header for the asset path column")
    args = parser.parse_args()

    with open(args.state, "r", encoding="utf-8") as f:
        state = json.load(f)

    asset_data    = state["asset_data"]
    redirector_map = state.get("redirector_map", {})

    # Load redirector referencers
    redirector_refs = {}  # redirector_pkg -> [ref_dict, ...]
    for bf in args.redirector_batches:
        with open(bf, "r", encoding="utf-8") as f:
            data = json.load(f)
        for r in data.get("results", []):
            if not r.get("success"):
                continue
            qpath = r.get("query_path", "")
            if r.get("type") == "get_asset_referencers" and qpath in redirector_map:
                redirector_refs[qpath] = extract_pkg_list(r.get("referencers", []))

    # Load asset order
    with open(args.asset_order, "r", encoding="utf-8") as f:
        asset_order = [line.strip() for line in f if line.strip()]

    COLS = [args.name_col, args.path_col,
            "一级正向依赖数量", "一级正向依赖资产列表",
            "一级反向依赖数量", "一级反向依赖资产列表"]

    rows = []
    for asset_path in asset_order:
        asset_name = asset_path.rsplit("/", 1)[-1]
        info = asset_data.get(asset_path, {"deps": [], "refs": []})

        deps = info.get("deps", [])
        direct_refs = info.get("refs", [])

        dep_pkgs = [d.get("package_name", "") for d in deps if isinstance(d, dict) if d.get("package_name")]

        if args.redirector_batches:
            merged = merge_refs(asset_path, direct_refs, redirector_map, redirector_refs)
        else:
            merged = [r for r in direct_refs if isinstance(r, dict)]

        ref_pkgs = [r.get("package_name", "") for r in merged if r.get("package_name")]

        rows.append({
            args.name_col: asset_name,
            args.path_col: asset_path,
            "一级正向依赖数量":    len(dep_pkgs),
            "一级正向依赖资产列表": "|".join(dep_pkgs),
            "一级反向依赖数量":    len(ref_pkgs),
            "一级反向依赖资产列表": "|".join(ref_pkgs),
        })
        print(f"  {asset_name}: deps={len(dep_pkgs)}, refs={len(ref_pkgs)}")

    with open(args.out, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=COLS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nDone. Written {len(rows)} rows to {args.out}")

    # Cleanup state file
    os.remove(args.state)


if __name__ == "__main__":
    main()
