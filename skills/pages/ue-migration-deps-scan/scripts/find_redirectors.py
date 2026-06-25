"""
find_redirectors.py
-------------------
Parse ue_batch JSON result files and identify ObjectRedirectors in referencers.

ObjectRedirector detection: asset_class == "ObjectRedirector" in the referencers list.

Usage:
  python find_redirectors.py --batch-files F1.txt F2.txt ... --out-state _scan_state.json
"""

import argparse
import json
import os


def extract_pkg_list(items):
    result = []
    for item in items:
        if isinstance(item, dict):
            result.append(item)
        elif isinstance(item, str):
            result.append({"package_name": item,
                            "asset_name": item.rsplit("/", 1)[-1],
                            "asset_class": ""})
    return result


def process_results(results, asset_data):
    for r in results:
        if not r.get("success"):
            continue
        qpath = r.get("query_path", "")
        if not qpath:
            continue
        if qpath not in asset_data:
            asset_data[qpath] = {"deps": [], "refs": []}
        rtype = r.get("type", "")
        if rtype == "get_asset_dependencies":
            asset_data[qpath]["deps"] = extract_pkg_list(r.get("dependencies", []))
        elif rtype == "get_asset_referencers":
            asset_data[qpath]["refs"] = extract_pkg_list(r.get("referencers", []))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-files", nargs="+", required=True)
    parser.add_argument("--out-state", required=True)
    args = parser.parse_args()

    asset_data = {}

    for bf in args.batch_files:
        with open(bf, "r", encoding="utf-8") as f:
            data = json.load(f)
        process_results(data.get("results", []), asset_data)

    print(f"Total assets scanned: {len(asset_data)}")

    # Detect ObjectRedirectors
    redirector_map = {}  # redirector_pkg -> owner_asset_path
    for asset_path, info in asset_data.items():
        for ref in info["refs"]:
            if ref.get("asset_class") == "ObjectRedirector":
                rp = ref["package_name"]
                redirector_map[rp] = asset_path
                print(f"  REDIRECTOR: {rp}  (owner: {asset_path})")

    print(f"\nTotal ObjectRedirectors found: {len(redirector_map)}")

    state = {"asset_data": asset_data, "redirector_map": redirector_map}
    with open(args.out_state, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    print(f"Saved state to {args.out_state}")


if __name__ == "__main__":
    main()
