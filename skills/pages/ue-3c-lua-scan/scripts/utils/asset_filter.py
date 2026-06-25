# -*- coding: utf-8 -*-
"""
asset_filter.py — 资产 CSV 预过滤

接收多份 CSV（兼容 ue-recursive-deps-scan / ProjectT 依赖表 等），合并去重后按规则筛选：

    1. 搬迁方式过滤：默认排除 `搬迁方式 == "无需搬迁"` 的资产
       （空值视作"未决定"保留；其他值如 `直接搬迁` / `无法直接搬迁` / `复制一份` / `资产已调整，可以搬迁` 等都保留）
    2. BP-only 过滤（可选）：只保留资产名以 `BP_` / `WBP_` / `UWBP_` / `ABP_` / `W_` 起手的 BP 系资产

返回：
    (targets, stats)
    targets = list[(asset_name, asset_pkg_path)]，dedup 后
    stats   = dict 含每一步的命中数 / 丢弃数 / 来源 CSV 等
"""

import csv
import os
from collections import Counter


# 默认排除的搬迁方式值
DEFAULT_EXCLUDE_METHODS = ["无需搬迁"]

# BP 系资产命名前缀（大小写不敏感）
BP_PREFIXES = ("BP_", "WBP_", "UWBP_", "ABP_", "W_")


def is_bp_asset(name):
    """资产名是否为 BP 系（蓝图 / Widget BP / Anim BP 等）。"""
    if not name:
        return False
    low = name.lower()
    return any(low.startswith(p.lower()) for p in BP_PREFIXES)


def _read_csv(path):
    """Yield dict rows from a CSV file. Handles BOM + alternative column names."""
    if not os.path.isfile(path):
        return [], []
    with open(path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        fieldnames = reader.fieldnames or []
        rows = list(reader)
    return rows, fieldnames


def _row_path(row):
    """Try to get the asset pkg path from a row, tolerating column name variations."""
    for key in ("外部资产完整路径", "asset_path", "pkg_path"):
        v = (row.get(key) or "").strip()
        if v:
            return v
    return ""


def _row_name(row, fallback_path=""):
    """Try to get the asset short name; fallback to path's last segment."""
    for key in ("外部资产名", "asset_name", "name"):
        v = (row.get(key) or "").strip()
        if v:
            return v
    if fallback_path:
        return fallback_path.rsplit("/", 1)[-1]
    return ""


def _row_method(row):
    for key in ("搬迁方式", "migration_method"):
        v = (row.get(key) or "").strip()
        if v:
            return v
    return ""


def collect_and_filter(
    csv_paths,
    exclude_methods=None,
    bp_only=False,
    verbose=True,
):
    """Read multiple asset CSVs, dedup, then filter.

    Args:
        csv_paths: list[str]
        exclude_methods: list[str]; rows where `搬迁方式` ∈ this list are dropped.
                         Default = ["无需搬迁"]. Pass [] to disable filter.
        bp_only: if True, keep only assets with BP-prefix names.
        verbose: print per-stage stats

    Returns:
        (targets, stats)
    """
    if exclude_methods is None:
        exclude_methods = list(DEFAULT_EXCLUDE_METHODS)
    exclude_set = set(exclude_methods)

    # ---- Phase A: read & merge ----
    per_csv = []   # list of {path, total_rows, fieldnames}
    merged_by_path = {}   # asset_pkg_path -> {name, method, sources:[csv_path,...]}
    for cp in csv_paths:
        rows, fieldnames = _read_csv(cp)
        per_csv.append({
            "path": cp,
            "total_rows": len(rows),
            "fieldnames": fieldnames,
        })
        if verbose:
            print(f"  [csv] {os.path.basename(cp)}: {len(rows)} rows, "
                  f"cols={len(fieldnames)}")
        for row in rows:
            asset_path = _row_path(row)
            if not asset_path:
                continue
            name = _row_name(row, asset_path)
            method = _row_method(row)
            entry = merged_by_path.setdefault(
                asset_path,
                {"name": name, "method": method, "sources": []}
            )
            entry["sources"].append(os.path.basename(cp))
            # If first entry had empty method but later one has value, prefer non-empty
            if not entry["method"] and method:
                entry["method"] = method

    pre_filter_total = len(merged_by_path)
    if verbose:
        print(f"  [merge] {sum(c['total_rows'] for c in per_csv)} raw rows "
              f"→ {pre_filter_total} unique assets")

    # ---- Phase B: 搬迁方式 filter ----
    method_counts_before = Counter(e["method"] or "(空)" for e in merged_by_path.values())
    after_method = {
        p: e for p, e in merged_by_path.items()
        if e["method"] not in exclude_set
    }
    excluded_by_method = pre_filter_total - len(after_method)
    if verbose:
        print(f"  [filter:搬迁方式] exclude={sorted(exclude_set) or '(none)'}")
        print(f"    搬迁方式分布: {dict(method_counts_before.most_common())}")
        print(f"    保留 {len(after_method)} 行（剔除 {excluded_by_method} 行）")

    # ---- Phase C: BP-only filter ----
    bp_excluded = 0
    if bp_only:
        before_bp = len(after_method)
        after_bp = {p: e for p, e in after_method.items() if is_bp_asset(e["name"])}
        bp_excluded = before_bp - len(after_bp)
        if verbose:
            print(f"  [filter:BP-only] 保留 BP-prefix 资产: {len(after_bp)} 行（剔除 {bp_excluded} 行非 BP）")
    else:
        after_bp = after_method
        if verbose:
            print(f"  [filter:BP-only] (跳过，--filter-bp-only 未启用)")

    # Result tuples
    targets = [
        (e["name"], asset_path)
        for asset_path, e in after_bp.items()
    ]

    stats = {
        "per_csv": per_csv,
        "pre_filter_total": pre_filter_total,
        "method_counts_before": dict(method_counts_before),
        "excluded_by_method": excluded_by_method,
        "after_method": len(after_method),
        "bp_excluded": bp_excluded,
        "final_total": len(after_bp),
        "exclude_methods": list(exclude_methods),
        "bp_only": bp_only,
    }

    if verbose:
        print(f"  [final] {stats['final_total']} 资产进入 Lua 绑定扫描")

    return targets, stats
