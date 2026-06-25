# -*- coding: utf-8 -*-
# 英文 CSV -> 中文 CSV 模板（带分组列）
# 系统 Python 运行，无需 UE 环境。
# 使用前替换下方 ===CONFIG=== 区块。

from __future__ import annotations

import csv
import os

# ===CONFIG=== 按实际情况修改 ================================================
TARGET_ROOT = "/Game/LetsGo/Assets/Effect/VFX_Community"
OUTPUT_PREFIX = "VFX_Community"
KEEP_DIRS = {
    "vfx_material": "VFX_Material（通用材质库）",
    "vfx_mesh": "VFX_Mesh（通用网格库）",
    "vfx_texture": "VFX_Texture（通用纹理库）",
}
DISPLAY_NAME = "大厅"

HERE = os.path.dirname(os.path.abspath(__file__))
DETAIL_EN = os.path.join(HERE, OUTPUT_PREFIX + "_reference_detail.csv")
SUMMARY_EN = os.path.join(HERE, OUTPUT_PREFIX + "_reference_summary.csv")
CHUNK_CSV = ""  # ChunkConfig.csv 绝对路径；留空则跳过分包列
DETAIL_ZH = os.path.join(HERE, OUTPUT_PREFIX + "_引用明细.csv")
SUMMARY_ZH = os.path.join(HERE, OUTPUT_PREFIX + "_引用汇总.csv")
# ===CONFIG END===============================================================

RELATION_MAP = {
    "dependency": "{0} → 外部（对外依赖）".format(DISPLAY_NAME),
    "referencer": "外部 → {0}（被引用）".format(DISPLAY_NAME),
}

CATEGORY_BASE = {
    "target_internal": "{0}内部".format(DISPLAY_NAME),
    "effect_other": "Effect 其他目录",
    "letsgo_non_effect": "LetsGo 非 Effect 目录",
    "feature_content": "Feature 副玩法内容",
    "engine": "引擎内置",
    "other": "其他",
    "empty": "（空）",
}
CATEGORY_MAP = {**CATEGORY_BASE, **KEEP_DIRS}


def subroot(path):
    prefix = TARGET_ROOT + "/"
    if not path.startswith(prefix):
        return "<unknown>"
    tail = path[len(prefix):]
    parts = tail.split("/")
    return parts[0] if len(parts) > 1 else "<root>"


def top_module(path):
    if not path or not path.startswith("/Game/"):
        return path or ""
    segs = path.split("/")
    if len(segs) >= 4 and segs[2] == "LetsGo" and segs[3] == "Assets" and len(segs) >= 5:
        if segs[4] == "Effect" and len(segs) >= 6:
            return "/".join(segs[:6])
        return "/".join(segs[:5])
    if len(segs) >= 4 and segs[2] in ("LetsGo", "FeatureBaseAssets"):
        return "/".join(segs[:4])
    if len(segs) >= 4 and segs[2] == "Feature":
        return "/".join(segs[:4])
    return "/".join(segs[:3]) if len(segs) >= 3 else path


def sub_module(path):
    if not path or not path.startswith("/Game/"):
        return path or ""
    segs = path.split("/")
    if len(segs) >= 4 and segs[2] == "LetsGo" and segs[3] == "Assets" and len(segs) >= 5:
        if segs[4] == "Effect" and len(segs) >= 7:
            return "/".join(segs[:7])
        if len(segs) >= 6:
            return "/".join(segs[:6])
        return "/".join(segs[:5])
    if len(segs) >= 5 and segs[2] == "Feature":
        return "/".join(segs[:5])
    return top_module(path)


def load_chunk_map():
    if not CHUNK_CSV or not os.path.isfile(CHUNK_CSV):
        return {}
    m = {}
    with open(CHUNK_CSV, "r", encoding="utf-8-sig", newline="") as f:
        for row in csv.reader(f):
            if len(row) >= 4 and row[0].strip() and row[3].strip():
                path = row[3].strip()
                if TARGET_ROOT.split("/")[-1] in path:
                    m[path] = row[0].strip()
    print("[信息] 加载 {0} 条分包登记".format(len(m)))
    return m


def get_chunk(pkg, cm):
    return cm.get(pkg, "默认规则") if cm else ""


def risk_level(n):
    if n == 0:
        return "零引用（零风险）"
    if n <= 3:
        return "低（1~3次）"
    if n <= 10:
        return "中（4~10次）"
    return "高（>10次）"


def localize_detail(cm):
    if not os.path.isfile(DETAIL_EN):
        print("[跳过] 未找到 " + DETAIL_EN)
        return
    fields = ["源资产路径", "源资产类型", "源资产所属子目录", "源资产所属分包",
              "关系方向", "目标资产", "目标分类", "目标所属顶层模块", "目标所属细分目录"]
    n = 0
    with open(DETAIL_EN, "r", encoding="utf-8-sig", newline="") as fi, \
         open(DETAIL_ZH, "w", encoding="utf-8-sig", newline="") as fo:
        r = csv.DictReader(fi)
        w = csv.DictWriter(fo, fieldnames=fields)
        w.writeheader()
        for row in r:
            pkg, tgt = row["source_package"], row["target"]
            w.writerow({
                "源资产路径": pkg,
                "源资产类型": row["source_asset_class"],
                "源资产所属子目录": subroot(pkg),
                "源资产所属分包": get_chunk(pkg, cm),
                "关系方向": RELATION_MAP.get(row["relation"], row["relation"]),
                "目标资产": tgt,
                "目标分类": CATEGORY_MAP.get(row["target_category"], row["target_category"]),
                "目标所属顶层模块": top_module(tgt),
                "目标所属细分目录": sub_module(tgt),
            })
            n += 1
    print("[完成] 明细表 {0} 行 -> {1}".format(n, DETAIL_ZH))


def localize_summary(cm):
    if not os.path.isfile(SUMMARY_EN):
        print("[跳过] 未找到 " + SUMMARY_EN)
        return
    fields = ["源资产路径", "源资产类型", "源资产所属子目录", "源资产所属分包",
              "对外依赖总次数", "被外部引用次数", "被内部引用次数", "迁移风险等级"]
    n = 0
    with open(SUMMARY_EN, "r", encoding="utf-8-sig", newline="") as fi, \
         open(SUMMARY_ZH, "w", encoding="utf-8-sig", newline="") as fo:
        r = csv.DictReader(fi)
        w = csv.DictWriter(fo, fieldnames=fields)
        w.writeheader()
        for row in r:
            dep_cols = [v for k, v in row.items() if k.startswith("dep_")]
            dep_total = sum(int(x) for x in dep_cols)
            ext = int(row.get("referencer_external_count", 0))
            internal = int(row.get("referencer_internal_count",
                           row.get("referencer_community_internal_count", 0)))
            w.writerow({
                "源资产路径": row["source_package"],
                "源资产类型": row["source_asset_class"],
                "源资产所属子目录": subroot(row["source_package"]),
                "源资产所属分包": get_chunk(row["source_package"], cm),
                "对外依赖总次数": dep_total,
                "被外部引用次数": ext,
                "被内部引用次数": internal,
                "迁移风险等级": risk_level(ext),
            })
            n += 1
    print("[完成] 汇总表 {0} 行 -> {1}".format(n, SUMMARY_ZH))


def main():
    cm = load_chunk_map()
    localize_detail(cm)
    localize_summary(cm)
    print("\n提示：中文文件含 UTF-8 BOM，Excel / WPS 可直接正确显示。")


if __name__ == "__main__":
    main()
