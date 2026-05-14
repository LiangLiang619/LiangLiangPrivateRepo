#!/usr/bin/env python3
"""Filter a 3C migration CSV by 搬迁方式 whitelist and validate target paths.

Output: JSON with { "to_migrate": [...], "skipped": [...] } to stdout.
"""

import csv
import json
import os
import sys

ALLOW_VALUES = {"资产已调整，可以搬迁", "直接搬迁"}
REQUIRED_COLUMNS = ["外部资产名", "外部资产完整路径", "3C仓库目标路径", "搬迁方式"]
TARGET_PREFIX = "/Game/LetsGo3C/"
INVALID_TARGETS = {"[待确认]", ""}


def filter_csv(csv_path):
    if not os.path.isfile(csv_path):
        print(f"ERROR: File not found: {csv_path}", file=sys.stderr)
        sys.exit(1)

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []

        missing = [c for c in REQUIRED_COLUMNS if c not in headers]
        if missing:
            print(f"ERROR: Missing required columns: {missing}", file=sys.stderr)
            print("Please run ue-3c-migration-path-mapper first.", file=sys.stderr)
            sys.exit(1)

        to_migrate = []
        skipped = []

        for row in reader:
            method = row.get("搬迁方式", "").strip()
            if method not in ALLOW_VALUES:
                continue

            asset_name = row.get("外部资产名", "").strip()
            source = row.get("外部资产完整路径", "").strip()
            target = row.get("3C仓库目标路径", "").strip()
            owner = row.get("负责人(人员)", row.get("负责人", "")).strip()
            ref_type = row.get("引用类型", "").strip()

            entry = {
                "asset_name": asset_name,
                "source_path": source,
                "dest_path": target,
                "migration_method": method,
                "owner": owner,
                "ref_type": ref_type,
            }

            if target in INVALID_TARGETS or not target.startswith(TARGET_PREFIX):
                entry["skip_reason"] = f"目标路径无效: '{target}'"
                skipped.append(entry)
            else:
                to_migrate.append(entry)

    to_migrate.sort(key=lambda x: x["asset_name"])
    skipped.sort(key=lambda x: x["asset_name"])

    result = {"to_migrate": to_migrate, "skipped": skipped}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python filter_csv.py <input.csv>", file=sys.stderr)
        sys.exit(1)
    filter_csv(sys.argv[1])
