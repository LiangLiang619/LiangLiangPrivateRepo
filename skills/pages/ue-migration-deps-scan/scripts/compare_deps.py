"""
compare_deps.py
---------------
Compare pre-migration and post-migration dependency CSVs.

Usage:
  python compare_deps.py \
    --pre  LetsGo3C_PreMigration_Deps_Refs.csv \
    --post LetsGo3C_Asset_Deps_Refs_new.csv \
    --out  LetsGo3C_Migration_Comparison.csv

Normalization: paths are compared by their last segment (asset_name).
Same asset_name = same logical asset, even if the path changed during migration.
"""

import argparse
import csv
import sys

csv.field_size_limit(10 * 1024 * 1024)  # 10 MB


def parse_list(cell):
    if not cell or not cell.strip():
        return []
    return [p.strip() for p in cell.split("|") if p.strip()]


def asset_name(path):
    return path.rsplit("/", 1)[-1]


def compare_sets(pre_list, post_list):
    """Returns (lost_full_paths, gained_full_paths) using name-based matching."""
    pre_map  = {}
    post_map = {}
    for p in pre_list:
        n = asset_name(p)
        if n not in pre_map:
            pre_map[n] = p
    for p in post_list:
        n = asset_name(p)
        if n not in post_map:
            post_map[n] = p

    lost   = [pre_map[n]  for n in pre_map  if n not in post_map]
    gained = [post_map[n] for n in post_map if n not in pre_map]
    return lost, gained


def severity(dep_lost, ref_lost):
    if dep_lost and ref_lost:
        return "⚠ 正向+反向均有丢失"
    if dep_lost:
        return "⚠ 正向依赖丢失"
    if ref_lost:
        return "⚠ 反向依赖丢失"
    return "✓ 无丢失"


COLS = [
    "资产名",
    "迁移前路径", "迁移后路径",
    "迁移前正向依赖数量", "迁移后正向依赖数量", "正向依赖变化",
    "正向依赖丢失数量", "正向依赖丢失列表",
    "正向依赖新增数量", "正向依赖新增列表",
    "迁移前反向依赖数量", "迁移后反向依赖数量", "反向依赖变化",
    "反向依赖丢失数量", "反向依赖丢失列表",
    "反向依赖新增数量", "反向依赖新增列表",
    "综合评估",
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pre",  required=True, help="Pre-migration CSV")
    parser.add_argument("--post", required=True, help="Post-migration CSV")
    parser.add_argument("--out",  required=True, help="Output comparison CSV")
    args = parser.parse_args()

    # Read pre CSV — key col may be "资产名（迁移后）" or "资产名"
    pre_data = {}
    with open(args.pre, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = row.get("资产名（迁移后）") or row.get("资产名", "")
            pre_data[key] = row

    # Read post CSV
    post_data = {}
    with open(args.post, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            post_data[row["资产名"]] = row

    rows = []
    for name, post_row in post_data.items():
        pre_row   = pre_data.get(name, {})
        post_path = post_row["资产路径"]
        pre_path  = (pre_row.get("迁移前资产路径") or pre_row.get("资产路径") or "") if pre_row else ""
        no_record = pre_path in ("", "无迁移记录") or not pre_row

        if no_record:
            row = {c: "" for c in COLS}
            row.update({
                "资产名":         name,
                "迁移前路径":     "（无迁移记录/新建资产）",
                "迁移后路径":     post_path,
                "迁移后正向依赖数量": len(parse_list(post_row.get("一级正向依赖资产列表", ""))),
                "迁移后反向依赖数量": len(parse_list(post_row.get("一级反向依赖资产列表", ""))),
                "综合评估":       "新建资产",
            })
        else:
            pre_deps  = parse_list(pre_row.get("一级正向依赖资产列表", ""))
            pre_refs  = parse_list(pre_row.get("一级反向依赖资产列表", ""))
            post_deps = parse_list(post_row.get("一级正向依赖资产列表", ""))
            post_refs = parse_list(post_row.get("一级反向依赖资产列表", ""))

            dep_lost, dep_gained = compare_sets(pre_deps, post_deps)
            ref_lost, ref_gained = compare_sets(pre_refs, post_refs)

            row = {
                "资产名":          name,
                "迁移前路径":      pre_path,
                "迁移后路径":      post_path,
                "迁移前正向依赖数量": len(pre_deps),
                "迁移后正向依赖数量": len(post_deps),
                "正向依赖变化":    f"{len(post_deps) - len(pre_deps):+d}",
                "正向依赖丢失数量":  len(dep_lost),
                "正向依赖丢失列表":  "|".join(dep_lost),
                "正向依赖新增数量":  len(dep_gained),
                "正向依赖新增列表":  "|".join(dep_gained),
                "迁移前反向依赖数量": len(pre_refs),
                "迁移后反向依赖数量": len(post_refs),
                "反向依赖变化":    f"{len(post_refs) - len(pre_refs):+d}",
                "反向依赖丢失数量":  len(ref_lost),
                "反向依赖丢失列表":  "|".join(ref_lost),
                "反向依赖新增数量":  len(ref_gained),
                "反向依赖新增列表":  "|".join(ref_gained),
                "综合评估":        severity(dep_lost, ref_lost),
            }

        rows.append(row)

    # Sort: issues first
    order = {"⚠ 正向+反向均有丢失": 0, "⚠ 正向依赖丢失": 1,
             "⚠ 反向依赖丢失": 2, "✓ 无丢失": 3, "新建资产": 4}
    rows.sort(key=lambda r: (order.get(r["综合评估"], 9), r["资产名"]))

    with open(args.out, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=COLS)
        writer.writeheader()
        writer.writerows(rows)

    issues = sum(1 for r in rows if r["综合评估"].startswith("⚠"))
    clean  = sum(1 for r in rows if r["综合评估"] == "✓ 无丢失")
    new_a  = sum(1 for r in rows if r["综合评估"] == "新建资产")
    print(f"Done. Written {len(rows)} rows to {args.out}")
    print(f"  有丢失: {issues}  无丢失: {clean}  新建资产: {new_a}")


if __name__ == "__main__":
    main()
