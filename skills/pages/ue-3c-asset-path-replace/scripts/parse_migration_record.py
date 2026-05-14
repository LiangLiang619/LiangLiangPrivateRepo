#!/usr/bin/env python3
"""Parse 3CAssetsMigrationRecords.md and output successful migration pairs as JSON.

Filter: 迁移状态 ∈ {成功, 已重定向（再次搬迁）}
Output (stdout): JSON list of { "asset_name", "old_path", "new_path" }
"""

import json
import os
import sys

SUCCESS_STATUSES = {"成功", "已重定向（再次搬迁）"}
COL_NAMES = [
    "num", "asset_name", "source_path", "dest_path", "migration_method",
    "owner", "ref_type", "status", "first_time", "latest_time", "note"
]


def parse_record(md_path):
    if not os.path.isfile(md_path):
        print(f"ERROR: Record file not found: {md_path}", file=sys.stderr)
        sys.exit(1)

    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    pairs = []
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
            if row.get("status", "") not in SUCCESS_STATUSES:
                continue

            old_path = row.get("source_path", "")
            new_path = row.get("dest_path", "")
            if not old_path or not new_path:
                continue
            if not old_path.startswith("/Game/") or not new_path.startswith("/Game/LetsGo3C/"):
                continue

            pairs.append({
                "asset_name": row.get("asset_name", ""),
                "old_path": old_path,
                "new_path": new_path,
            })

    print(json.dumps(pairs, ensure_ascii=False, indent=2))
    print(f"\n[INFO] Parsed {len(pairs)} eligible migration pairs from {md_path}", file=sys.stderr)
    return pairs


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python parse_migration_record.py <3CAssetsMigrationRecords.md>", file=sys.stderr)
        sys.exit(1)
    parse_record(sys.argv[1])
