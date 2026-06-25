# -*- coding: utf-8 -*-
"""
Read the JSON produced by scan_redirector_refs.py and emit UE Python
snippets (load_asset + save_loaded_asset) split into batches of <= 50.

Each printed batch is meant to be passed verbatim to a UE Editor MCP
python-exec action (e.g. ue_actions_run with a python-execution action).
The snippet itself prints `[redirector-fix] <pkg>: OK|FAIL|LOADFAIL` lines
so ue_logs_tail can be used to reconcile results.

Usage:
  python fix_redirector_refs.py --json <scan_output.json>
                                [--batch-size 50]
                                [--out-dir <dir>]
                                [--dry-run]
"""

import argparse
import json
import os
import sys
from pathlib import Path


SNIPPET_TEMPLATE = """\
import unreal
eal = unreal.EditorAssetLibrary
targets = {targets!r}
ok_n = 0
fail_n = 0
for pkg in targets:
    asset = eal.load_asset(pkg)
    if asset is None:
        unreal.log_warning("[redirector-fix] LOADFAIL " + pkg)
        fail_n += 1
        continue
    try:
        ok = eal.save_loaded_asset(asset, only_if_is_dirty=False)
    except Exception as e:
        unreal.log_warning("[redirector-fix] SAVEEXC " + pkg + " :: " + str(e))
        fail_n += 1
        continue
    if ok:
        unreal.log("[redirector-fix] OK " + pkg)
        ok_n += 1
    else:
        unreal.log_warning("[redirector-fix] FAIL " + pkg)
        fail_n += 1
unreal.log("[redirector-fix] BATCH_DONE ok={{0}} fail={{1}} total={{2}}".format(ok_n, fail_n, len(targets)))
"""


def chunks(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", required=True, help="scan output JSON")
    ap.add_argument("--batch-size", type=int, default=50)
    ap.add_argument("--out-dir", default=None, help="if set, write per-batch .py files there")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    with open(args.json, encoding="utf-8") as fh:
        payload = json.load(fh)

    referencers = payload.get("referencers") or sorted({r["referencer"] for r in payload.get("records", [])})
    referencers = [p for p in referencers if p and p.startswith("/Game/")]

    if not referencers:
        print("[fix] no in-directory referencers found; nothing to do.")
        return 0

    batches = list(chunks(referencers, max(1, args.batch_size)))
    print(f"[fix] referencers: {len(referencers)}; batches: {len(batches)} (size={args.batch_size})")

    out_dir = Path(args.out_dir) if args.out_dir else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    manifest = []
    for idx, batch in enumerate(batches, 1):
        snippet = SNIPPET_TEMPLATE.format(targets=batch)
        entry = {"batch_index": idx, "size": len(batch), "targets": batch}
        if out_dir:
            fpath = out_dir / f"fix_batch_{idx:03d}.py"
            with open(fpath, "w", encoding="utf-8") as fh:
                fh.write(snippet)
            entry["file"] = str(fpath)
        manifest.append(entry)
        if args.dry_run:
            print(f"  -- batch {idx} ({len(batch)}) --")
            print(snippet)
            print(f"  -- end batch {idx} --")

    print(json.dumps({
        "json_input": args.json,
        "batches": manifest if not args.dry_run else [
            {k: v for k, v in e.items() if k != "targets"} for e in manifest
        ],
        "snippet_for_each_batch": "see SNIPPET_TEMPLATE; runs unreal.EditorAssetLibrary.load_asset + save_loaded_asset",
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
