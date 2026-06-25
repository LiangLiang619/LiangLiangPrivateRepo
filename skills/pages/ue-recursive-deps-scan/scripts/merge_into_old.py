# -*- coding: utf-8 -*-
"""
将 ue-recursive-deps-scan 生成的「新【间接依赖】」CSV 中 OLD 文件缺失的行，
按 OLD 列名风格补入 OLD 文件，输出一份「补充版」CSV。

规则：
  - 行唯一键：「外部资产完整路径」
  - 输出表头与 OLD 完全一致（含 `直接依赖LetsGo资产...` / `递归依赖LetsGo资产...` 命名）
  - OLD 全部行保留并置于前面，相对顺序不变
  - NEW 中、OLD 缺失的行追加到末尾，按 (引用层级深度, 路径) 升序排序
  - 4 列名映射：
      直接依赖外部资产数  -> 直接依赖LetsGo资产数
      直接依赖外部资产列表 -> 直接依赖LetsGo资产列表
      递归依赖外部资产总数 -> 递归依赖LetsGo资产总数
      递归依赖外部资产列表 -> 递归依赖LetsGo资产列表
  - 其它字段（当前进度/搬迁方式/负责人/玩法依赖等）原样取自 NEW（多为空）

用法：
  python scripts/merge_into_old.py \
    --old-csv <旧文件路径> \
    --new-csv <新文件路径> \
    --output-csv <补充版输出路径>
"""

import argparse
import csv
import sys
from pathlib import Path

csv.field_size_limit(2**31 - 1)

# NEW -> OLD 列名映射（仅 4 列名不同）
COL_RENAME = {
    "直接依赖外部资产数": "直接依赖LetsGo资产数",
    "直接依赖外部资产列表": "直接依赖LetsGo资产列表",
    "递归依赖外部资产总数": "递归依赖LetsGo资产总数",
    "递归依赖外部资产列表": "递归依赖LetsGo资产列表",
}


def parse_depth(s):
    try:
        return int(s.split("深度")[1].rstrip(")").strip())
    except Exception:
        return 999


def map_new_row_to_old(new_row, old_fieldnames):
    """把一行 NEW 字典按列名映射到 OLD 字段名集合上。"""
    out = {k: "" for k in old_fieldnames}
    for k, v in new_row.items():
        target = COL_RENAME.get(k, k)
        if target in out:
            out[target] = v
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--old-csv", required=True)
    ap.add_argument("--new-csv", required=True)
    ap.add_argument("--output-csv", required=True)
    args = ap.parse_args()

    print(f"[1/3] 读取 OLD: {args.old_csv}")
    with open(args.old_csv, encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        old_fieldnames = list(reader.fieldnames or [])
        old_rows = list(reader)
    old_paths = {r["外部资产完整路径"] for r in old_rows if r.get("外部资产完整路径")}
    print(f"      OLD rows: {len(old_rows)}; unique paths: {len(old_paths)}")
    print(f"      OLD columns: {len(old_fieldnames)}")

    print(f"[2/3] 读取 NEW: {args.new_csv}")
    with open(args.new_csv, encoding="utf-8-sig", newline="") as fh:
        new_rows = list(csv.DictReader(fh))
    print(f"      NEW rows: {len(new_rows)}")

    missing = [r for r in new_rows
               if r.get("外部资产完整路径") and r["外部资产完整路径"] not in old_paths]
    print(f"      NEW rows missing in OLD: {len(missing)}")

    missing.sort(key=lambda r: (parse_depth(r["引用层级"]), r["外部资产完整路径"]))

    print(f"[3/3] 写出补充版: {args.output_csv}")
    out_path = Path(args.output_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=old_fieldnames, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        for r in old_rows:
            writer.writerow(r)
        for r in missing:
            writer.writerow(map_new_row_to_old(r, old_fieldnames))

    total = len(old_rows) + len(missing)
    print(f"完成。OLD {len(old_rows)} 行 + 补入 {len(missing)} 行 = {total} 行 → {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
