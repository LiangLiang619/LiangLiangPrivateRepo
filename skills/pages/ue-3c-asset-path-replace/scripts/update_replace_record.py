#!/usr/bin/env python3
"""Idempotent merge of path-replace batch results into 3CAssetsPathReplaceRecords.md.

Primary key: (file_rel_path, old_path).
Existing rows accumulate occurrences and update status/timestamps.
New rows are inserted. Entire file is rewritten sorted by first_time ascending.
"""

import argparse
import json
import os
import shutil
import sys
from datetime import datetime

TABLE_HEADER = "| # | 文件相对路径 | 原路径 | 新路径 | 变体 | 累计替换次数 | 最近状态 | 首次替换时间 | 最近更新时间 | 备注 |"
TABLE_SEP =    "|---|------------|--------|--------|------|--------------|----------|-------------|-------------|------|"

COL_NAMES = [
    "num", "file_rel_path", "old_path", "new_path", "variant",
    "total_count", "status", "first_time", "latest_time", "note"
]


def parse_existing(md_path):
    """Parse existing record table into dict keyed by (file_rel_path, old_path)."""
    records = {}
    if not os.path.isfile(md_path):
        return records

    try:
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"WARNING: Could not read {md_path}: {e}", file=sys.stderr)
        return records

    in_table = False
    for line in content.split('\n'):
        stripped = line.strip()
        if stripped.startswith('| # |'):
            in_table = True
            continue
        if in_table and stripped.startswith('|---'):
            continue
        if in_table:
            if not (stripped.startswith('|') and stripped.endswith('|')):
                in_table = False
                continue

            cells = [c.strip() for c in stripped.split('|')[1:-1]]
            if len(cells) < len(COL_NAMES):
                continue

            row = dict(zip(COL_NAMES, cells))
            key = (row.get("file_rel_path", ""), row.get("old_path", ""))
            records[key] = row

    return records


def severity(status):
    """Higher means worse. Used for picking worst status when aggregating."""
    if status.startswith("失败"):
        return 3
    if status.startswith("跳过"):
        return 2
    if status == "成功":
        return 1
    return 0


def aggregate_batch(batch_items):
    """Aggregate batch entries by (file_rel_path, old_path).

    Sums occurrences, takes worst status, merges variants.
    Returns dict[key] -> aggregated entry.
    """
    aggregated = {}
    for item in batch_items:
        key = (item.get("file_rel_path", ""), item.get("old_path", ""))
        if key not in aggregated:
            aggregated[key] = {
                "file_rel_path": item.get("file_rel_path", ""),
                "old_path": item.get("old_path", ""),
                "new_path": item.get("new_path", ""),
                "variants": set(),
                "total_count": 0,
                "status": "成功",
            }

        agg = aggregated[key]
        variant = item.get("variant", "")
        if variant:
            agg["variants"].add(variant)
        agg["total_count"] += int(item.get("occurrences_this_run", 0) or 0)

        new_status = item.get("status", "成功")
        if severity(new_status) > severity(agg["status"]):
            agg["status"] = new_status

        if item.get("new_path"):
            agg["new_path"] = item["new_path"]

    for agg in aggregated.values():
        agg["variant_str"] = "+".join(sorted(agg["variants"])) if agg["variants"] else ""

    return aggregated


def merge(records, aggregated, now_str):
    """Merge aggregated batch into existing records. Returns batch stats."""
    success_count = 0
    fail_count = 0
    skip_count = 0

    for key, agg in aggregated.items():
        status = agg["status"]
        if status == "成功":
            success_count += 1
        elif status.startswith("失败"):
            fail_count += 1
        elif status.startswith("跳过"):
            skip_count += 1

        if key in records:
            existing = records[key]
            try:
                old_total = int(existing.get("total_count", "0") or 0)
            except ValueError:
                old_total = 0

            new_total = old_total + agg["total_count"]
            note = existing.get("note", "")

            if agg["total_count"] == 0 and status == "成功":
                note_addition = "重复扫描无新增"
                if note_addition not in note:
                    note = (note + "; " + note_addition).strip("; ") if note else note_addition

            existing["new_path"] = agg["new_path"] or existing.get("new_path", "")
            existing["variant"] = agg["variant_str"] or existing.get("variant", "")
            existing["total_count"] = str(new_total)
            existing["status"] = status
            existing["latest_time"] = now_str
            existing["note"] = note
        else:
            records[key] = {
                "file_rel_path": agg["file_rel_path"],
                "old_path": agg["old_path"],
                "new_path": agg["new_path"],
                "variant": agg["variant_str"],
                "total_count": str(agg["total_count"]),
                "status": status,
                "first_time": now_str,
                "latest_time": now_str,
                "note": "",
            }

    return success_count, fail_count, skip_count


def write_record(md_path, records, success_count, fail_count, skip_count, now_str):
    os.makedirs(os.path.dirname(md_path), exist_ok=True)

    rows = sorted(
        records.values(),
        key=lambda r: r.get("first_time", "0000-00-00 00:00:00")
    )

    file_set = set(r.get("file_rel_path", "") for r in rows if r.get("file_rel_path"))

    lines = []
    lines.append("# 3C 资产硬编码路径替换记录")
    lines.append("")
    lines.append("> 本文件由 `ue-3c-asset-path-replace` skill 自动维护，请勿手动编辑表格数据。")
    lines.append("")
    lines.append("## 统计")
    lines.append("")
    lines.append(f"- **累计条目数**: {len(rows)}")
    lines.append(f"- **涉及文件数**: {len(file_set)}")
    lines.append(f"- **最近批次时间**: {now_str}")
    lines.append(f"- **最近批次成功**: {success_count}")
    lines.append(f"- **最近批次失败**: {fail_count}")
    lines.append(f"- **最近批次跳过**: {skip_count}")
    lines.append("")
    lines.append("## 替换明细")
    lines.append("")
    lines.append(TABLE_HEADER)
    lines.append(TABLE_SEP)

    for idx, row in enumerate(rows, 1):
        cells = [
            str(idx),
            row.get("file_rel_path", ""),
            row.get("old_path", ""),
            row.get("new_path", ""),
            row.get("variant", ""),
            row.get("total_count", "0"),
            row.get("status", ""),
            row.get("first_time", ""),
            row.get("latest_time", ""),
            row.get("note", ""),
        ]
        lines.append("| " + " | ".join(cells) + " |")

    lines.append("")

    with open(md_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f"Record updated: {md_path}")
    print(f"  Total entries: {len(rows)}")
    print(f"  Files involved: {len(file_set)}")
    print(f"  This batch: {success_count} success, {fail_count} failed, {skip_count} skipped")


def main():
    parser = argparse.ArgumentParser(description="Update 3C path replace record")
    parser.add_argument("--record", required=True, help="Path to 3CAssetsPathReplaceRecords.md")
    parser.add_argument("--batch", required=True, help="Path to batch JSON")
    args = parser.parse_args()

    if not os.path.isfile(args.batch):
        print(f"ERROR: Batch file not found: {args.batch}", file=sys.stderr)
        sys.exit(1)

    with open(args.batch, 'r', encoding='utf-8') as f:
        batch_items = json.load(f)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        records = parse_existing(args.record)
    except Exception as e:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        broken_path = args.record.replace(".md", f".broken.{ts}.md")
        shutil.copy2(args.record, broken_path)
        print(f"WARNING: Existing record parse failed ({e}), backed up to {broken_path}", file=sys.stderr)
        records = {}

    aggregated = aggregate_batch(batch_items)
    success_count, fail_count, skip_count = merge(records, aggregated, now_str)
    write_record(args.record, records, success_count, fail_count, skip_count, now_str)


if __name__ == '__main__':
    main()
