#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scan git commit history for UE asset files.
Outputs an incrementally-maintained CSV with committer info.
"""

import argparse
import csv
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


CSV_COLUMNS = [
    "资产名称",
    "资产完整路径",
    "分支",
    "Commit Hash",
    "提交人",
    "提交人邮箱",
    "提交时间",
    "提交说明",
    "扫描时间",
]

DEDUP_KEY = ("资产完整路径", "Commit Hash")


def find_git_root(path: str) -> str | None:
    """Walk up from *path* to locate the nearest .git directory."""
    current = Path(path).resolve()
    if current.is_file():
        current = current.parent
    while True:
        if (current / ".git").exists():
            return str(current)
        parent = current.parent
        if parent == current:
            return None
        current = parent


def git_log_asset(repo_root: str, relative_path: str, branch: str, count: int) -> list[dict]:
    """Run git log for a single asset and return parsed records."""
    fmt = "%H|%an|%ae|%ad|%s"
    cmd = [
        "git", "-C", repo_root,
        "log", "--full-history",
        f"--format={fmt}",
        "--date=format:%Y-%m-%d %H:%M:%S",
        f"-{count}",
        branch,
        "--",
        relative_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, encoding="utf-8")
    except subprocess.CalledProcessError as exc:
        print(f"  [warn] git log failed: {exc.stderr.strip()}", file=sys.stderr)
        return []

    records = []
    for line in result.stdout.strip().splitlines():
        parts = line.split("|", 4)
        if len(parts) < 5:
            continue
        records.append({
            "Commit Hash": parts[0],
            "提交人": parts[1],
            "提交人邮箱": parts[2],
            "提交时间": parts[3],
            "提交说明": parts[4],
        })
    return records


def load_existing_csv(csv_path: str) -> list[dict]:
    """Load existing CSV rows if the file exists."""
    if not os.path.isfile(csv_path):
        return []
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def merge_and_dedup(old_rows: list[dict], new_rows: list[dict]) -> list[dict]:
    """Merge new rows into old, dedup by (asset path, commit hash), sort."""
    seen: set[tuple] = set()
    merged: list[dict] = []

    for row in old_rows + new_rows:
        key = tuple(row.get(k, "") for k in DEDUP_KEY)
        if key in seen:
            continue
        seen.add(key)
        merged.append(row)

    merged.sort(key=lambda r: (r.get("资产名称", ""), r.get("提交时间", "")), reverse=False)
    merged.sort(key=lambda r: r.get("资产名称", ""))
    return merged


def write_csv(csv_path: str, rows: list[dict]):
    """Write rows to CSV with UTF-8 BOM for Excel compatibility."""
    os.makedirs(os.path.dirname(csv_path) or ".", exist_ok=True)
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def parse_assets_from_args(args) -> list[str]:
    """Collect asset paths from --assets and/or --input-csv."""
    paths: list[str] = []

    if args.assets:
        for item in args.assets.split(","):
            item = item.strip()
            if item:
                paths.append(item)

    if args.input_csv:
        col = args.path_column
        with open(args.input_csv, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if col not in (reader.fieldnames or []):
                print(f"[error] column '{col}' not found in {args.input_csv}", file=sys.stderr)
                print(f"  available columns: {reader.fieldnames}", file=sys.stderr)
                sys.exit(1)
            for row in reader:
                val = row.get(col, "").strip()
                if val:
                    paths.append(val)

    return paths


def main():
    parser = argparse.ArgumentParser(description="Scan git history for UE assets")
    parser.add_argument("--assets", type=str, default="",
                        help="Comma-separated absolute paths to .uasset files")
    parser.add_argument("--input-csv", type=str, default="",
                        help="CSV file containing asset paths")
    parser.add_argument("--path-column", type=str, default="资产路径",
                        help="Column name in input CSV that contains asset paths")
    parser.add_argument("--branch", type=str, default="origin/develop",
                        help="Git branch to scan")
    parser.add_argument("--count", type=int, default=2,
                        help="Number of recent commits to fetch per asset")
    parser.add_argument("--output", type=str, default="",
                        help="Output CSV path (default: script_dir/../output/asset_git_history.csv)")
    args = parser.parse_args()

    asset_paths = parse_assets_from_args(args)
    if not asset_paths:
        print("[error] no asset paths provided. Use --assets or --input-csv.", file=sys.stderr)
        sys.exit(1)

    script_dir = Path(__file__).resolve().parent
    output_path = args.output or str(script_dir.parent / "output" / "asset_git_history.csv")

    scan_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_rows: list[dict] = []
    repo_cache: dict[str, str] = {}

    print(f"Scanning {len(asset_paths)} assets on branch [{args.branch}], last {args.count} commits each...")

    for asset_path in asset_paths:
        asset_path = os.path.normpath(asset_path)
        asset_name = Path(asset_path).stem

        parent_dir = str(Path(asset_path).parent) if os.path.isfile(asset_path) else asset_path
        if parent_dir not in repo_cache:
            git_root = find_git_root(asset_path)
            if git_root:
                repo_cache[parent_dir] = git_root
            else:
                print(f"  [skip] no git repo found for: {asset_path}", file=sys.stderr)
                continue
        git_root = repo_cache[parent_dir]

        rel_path = os.path.relpath(asset_path, git_root).replace("\\", "/")

        print(f"  [{asset_name}] repo={git_root}  rel={rel_path}")
        records = git_log_asset(git_root, rel_path, args.branch, args.count)

        if not records:
            print(f"    -> no commits found")
            continue

        for rec in records:
            rec["资产名称"] = asset_name
            rec["资产完整路径"] = asset_path
            rec["分支"] = args.branch
            rec["扫描时间"] = scan_time
            new_rows.append(rec)
            print(f"    -> {rec['提交时间']} | {rec['提交人']} | {rec['提交说明'][:60]}")

    old_rows = load_existing_csv(output_path)
    merged = merge_and_dedup(old_rows, new_rows)
    write_csv(output_path, merged)

    new_count = len(merged) - len(old_rows)
    print(f"\nDone. CSV: {output_path}")
    print(f"  total rows: {len(merged)} (existing: {len(old_rows)}, newly added: {max(new_count, 0)})")


if __name__ == "__main__":
    main()
