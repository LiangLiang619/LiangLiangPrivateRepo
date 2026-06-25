# -*- coding: utf-8 -*-
# 深度切片分析模板：读取英文 detail/summary CSV，输出 JSON 供报告写入。
# 系统 Python 运行，无需 UE 环境。

from __future__ import annotations

import csv
import json
import os
from collections import Counter, defaultdict

# ===CONFIG===
TARGET_ROOT = "/Game/LetsGo/Assets/Effect/VFX_Community"
EFFECT_ROOT = "/Game/LetsGo/Assets/Effect"
HERE = os.path.dirname(os.path.abspath(__file__))
DETAIL = os.path.join(HERE, "VFX_Community_reference_detail.csv")
SUMMARY = os.path.join(HERE, "VFX_Community_reference_summary.csv")
# ===CONFIG END===


def subroot(path):
    prefix = TARGET_ROOT + "/"
    if not path.startswith(prefix):
        return None
    tail = path[len(prefix):]
    parts = tail.split("/")
    return parts[0] if len(parts) > 1 else "<root>"


def top_ns(path):
    if not path.startswith("/Game/"):
        return "/other"
    segs = path.split("/")
    if len(segs) >= 4 and segs[2] == "LetsGo" and segs[3] == "Assets" and len(segs) >= 5:
        if segs[4] == "Effect" and len(segs) >= 6:
            return "/".join(segs[:6])
        return "/".join(segs[:5])
    if len(segs) >= 4 and segs[2] == "Feature":
        return "/".join(segs[:4])
    return "/".join(segs[:3]) if len(segs) >= 3 else path


def sub_ns(path):
    segs = path.split("/")
    if len(segs) >= 4 and segs[2] == "LetsGo" and segs[3] == "Assets" and len(segs) >= 6:
        if segs[4] == "Effect" and len(segs) >= 7:
            return "/".join(segs[:7])
        return "/".join(segs[:6])
    if len(segs) >= 5 and segs[2] == "Feature":
        return "/".join(segs[:5])
    return top_ns(path)


def effect_subfolder(path):
    prefix = EFFECT_ROOT + "/"
    if not path.startswith(prefix):
        return None
    return path[len(prefix):].split("/")[0]


def main():
    dep_cat = Counter()
    ref_ext_ns = Counter()
    effect_rev_sub = Counter()
    sub_assets = Counter()
    sub_zero = Counter()
    per_asset_ext = {}

    with open(DETAIL, "r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rel = row["relation"]
            tgt = row["target"]
            cat = row["target_category"]
            pkg = row["source_package"]
            sub = subroot(pkg) or "<unknown>"
            if rel == "dependency":
                dep_cat[cat] += 1
            else:
                if not tgt.startswith(TARGET_ROOT):
                    ref_ext_ns[top_ns(tgt)] += 1
                    if tgt.startswith(EFFECT_ROOT) and not tgt.startswith(TARGET_ROOT):
                        sf = effect_subfolder(tgt)
                        if sf:
                            effect_rev_sub[sf] += 1

    with open(SUMMARY, "r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            pkg = row["source_package"]
            sub = subroot(pkg) or "<unknown>"
            sub_assets[sub] += 1
            ext = int(row.get("referencer_external_count", 0))
            per_asset_ext[pkg] = ext
            if ext == 0:
                sub_zero[sub] += 1

    top_ref = sorted(((p, c) for p, c in per_asset_ext.items() if c > 0),
                     key=lambda x: x[1], reverse=True)[:30]

    report = {
        "dep_by_category": dep_cat.most_common(),
        "ref_external_by_namespace": ref_ext_ns.most_common(),
        "effect_reverse_by_subfolder": effect_rev_sub.most_common(),
        "subroot_zero_ref": [
            {"sub": s, "total": sub_assets[s], "zero": sub_zero.get(s, 0),
             "pct": round(100.0 * sub_zero.get(s, 0) / sub_assets[s], 1)}
            for s in sorted(sub_assets, key=lambda k: sub_assets[k], reverse=True)
        ],
        "top_referenced_assets": top_ref,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
