#!/usr/bin/env python3
"""Idempotent merge of migration batch results into 3CAssetsMigrationRecords.md.

Keyed by source_path. Existing rows are updated; new rows are appended.
The entire file is rewritten sorted by first_time ascending.
"""

import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime

TABLE_HEADER = "| # | 外部资产名 | 源路径 | 目标路径 | 搬迁方式 | 负责人 | 迁移状态 | 首次迁移时间 | 最近更新时间 | 备注 |"
TABLE_SEP =    "|---|-----------|--------|----------|----------|--------|----------|-------------|-------------|------|"

COL_NAMES = [
    "num", "asset_name", "source_path", "dest_path", "migration_method",
    "owner", "status", "first_time", "latest_time", "note"
]


def parse_existing_table(md_path):
    """Parse the markdown table in the record file into a dict keyed by source_path."""
    records = {}
    if not os.path.isfile(md_path):
        return records

    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
    in_table = False
    header_re = re.compile(r'^\|\s*#\s*\|')
    sep_re = re.compile(r'^\|\s*-+\s*\|')

    for line in lines:
        stripped = line.strip()
        if header_re.match(stripped) or sep_re.match(stripped):
            in_table = True
            continue
        if in_table and stripped.startswith('|') and stripped.endswith('|'):
            cells = [c.strip() for c in stripped.split('|')[1:-1]]
            # Legacy format had 11 columns including 引用类型 between 负责人 and 迁移状态
            if len(cells) == 11:
                legacy = ["num", "asset_name", "source_path", "dest_path",
                          "migration_method", "owner", "ref_type", "status",
                          "first_time", "latest_time", "note"]
                row = dict(zip(legacy, cells))
                row.pop("ref_type", None)
                records[row["source_path"]] = row
            elif len(cells) >= len(COL_NAMES):
                row = dict(zip(COL_NAMES, cells))
                records[row["source_path"]] = row
            elif len(cells) >= 3:
                row = {}
                for i, name in enumerate(COL_NAMES):
                    row[name] = cells[i] if i < len(cells) else ""
                records[row.get("source_path", "")] = row
        elif in_table and not stripped.startswith('|'):
            in_table = False

    return records


def merge_batch(records, batch_items, now_str):
    """Merge batch results into existing records."""
    batch_success = 0
    batch_fail = 0

    for item in batch_items:
        src = item["source_path"]
        status = item.get("status", "成功")

        if status == "成功":
            batch_success += 1
        else:
            batch_fail += 1

        if src in records:
            existing = records[src]
            old_status = existing.get("status", "")
            if old_status == "成功" and status == "成功":
                status = "已重定向（再次搬迁）"

            existing["dest_path"] = item.get("dest_path", existing.get("dest_path", ""))
            existing["migration_method"] = item.get("migration_method", existing.get("migration_method", ""))
            existing["owner"] = item.get("owner", existing.get("owner", ""))
            existing["status"] = status
            existing["latest_time"] = now_str
            existing["note"] = item.get("note", existing.get("note", ""))
            existing["asset_name"] = item.get("asset_name", existing.get("asset_name", ""))
        else:
            records[src] = {
                "asset_name": item.get("asset_name", ""),
                "source_path": src,
                "dest_path": item.get("dest_path", ""),
                "migration_method": item.get("migration_method", ""),
                "owner": item.get("owner", ""),
                "status": status,
                "first_time": now_str,
                "latest_time": now_str,
                "note": item.get("note", ""),
            }

    return batch_success, batch_fail


def write_record(md_path, records, batch_success, batch_fail, now_str):
    """Write the complete record file."""
    os.makedirs(os.path.dirname(md_path), exist_ok=True)

    sorted_rows = sorted(
        records.values(),
        key=lambda r: r.get("first_time", "0000-00-00 00:00:00")
    )

    lines = []
    lines.append("# 3C 资产迁移记录")
    lines.append("")
    lines.append("> 本文件由 `ue-3c-asset-migration` skill 自动维护，请勿手动编辑表格数据。")
    lines.append("")
    lines.append("## 统计")
    lines.append("")
    lines.append(f"- **累计资产数**: {len(sorted_rows)}")
    lines.append(f"- **最近批次时间**: {now_str}")
    lines.append(f"- **最近批次成功**: {batch_success}")
    lines.append(f"- **最近批次失败**: {batch_fail}")
    lines.append("")
    lines.append("## 迁移明细")
    lines.append("")
    lines.append(TABLE_HEADER)
    lines.append(TABLE_SEP)

    for idx, row in enumerate(sorted_rows, 1):
        cells = [
            str(idx),
            row.get("asset_name", ""),
            row.get("source_path", ""),
            row.get("dest_path", ""),
            row.get("migration_method", ""),
            row.get("owner", ""),
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
    print(f"  Total assets: {len(sorted_rows)}")
    print(f"  This batch: {batch_success} success, {batch_fail} failed")


def main():
    parser = argparse.ArgumentParser(description="Update 3C migration record")
    parser.add_argument("--record", required=True, help="Path to 3CAssetsMigrationRecords.md")
    parser.add_argument("--batch", required=True, help="Path to batch result JSON")
    args = parser.parse_args()

    if not os.path.isfile(args.batch):
        print(f"ERROR: Batch file not found: {args.batch}", file=sys.stderr)
        sys.exit(1)

    with open(args.batch, 'r', encoding='utf-8') as f:
        batch_items = json.load(f)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    records = parse_existing_table(args.record)

    # Backup if existing file is non-empty and might be corrupted
    if os.path.isfile(args.record):
        try:
            parse_existing_table(args.record)
        except Exception as e:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            broken_path = args.record.replace(".md", f".broken.{ts}.md")
            shutil.copy2(args.record, broken_path)
            print(f"WARNING: Existing record parse failed, backed up to {broken_path}")
            records = {}

    batch_success, batch_fail = merge_batch(records, batch_items, now_str)
    write_record(args.record, records, batch_success, batch_fail, now_str)


if __name__ == '__main__':
    main()
