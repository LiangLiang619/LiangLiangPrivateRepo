# -*- coding: utf-8 -*-
"""
Offline scan: find every asset under a given directory that still references
an ObjectRedirector, by parsing .uasset binaries via uasset_mcp.UAssetParser.

Input:
  --dir         OS absolute path (e.g. F:\\F3\\LetsGoDevelop\\LetsGo\\Content\\LetsGo\\Foo)
                or UE virtual path (e.g. /Game/LetsGo/Foo)
  --content-root  UE project Content root (default F:\\F3\\LetsGoDevelop\\LetsGo\\Content)
  --output-dir  Where to write the JSON/CSV/MD report
                (default: <skill_dir>/reports)

Output (filenames stamped with directory tail + timestamp):
  redirector_refs_<tag>.json   — full machine-readable record (consumed by fix_redirector_refs.py)
  redirector_refs_<tag>.csv    — same content, CSV form
  redirector_refs_<tag>.md     — short markdown table for user preview

Detection rules (mirror ue-recursive-deps-scan):
  - Hard refs:  imports table entries whose class_name == "Package"
  - Soft refs:  FName table entries starting with "/Game/"
  - A target package is a redirector when its .uasset exports are all
    ObjectRedirector (ignoring MetaData).
"""

import argparse
import csv
import importlib
import json
import os
import sys
import time
from pathlib import Path

csv.field_size_limit(2**31 - 1)


def _import_uasset_parser():
    candidates = [
        r"F:\F4\LetsGoEditor\Editor\LetsGo\Tools\Python311\Lib\site-packages",
        os.path.join(os.environ.get("USERPROFILE", ""), r".cache\uv\archive-v0\uasset_mcp"),
    ]
    env_override = os.environ.get("UASSET_MCP_SITE_PACKAGES")
    if env_override:
        candidates.insert(0, env_override)
    for path in candidates:
        if path and os.path.isdir(path):
            if path not in sys.path:
                sys.path.insert(0, path)
            try:
                module = importlib.import_module("src.uasset_parser")
                return module.UAssetParser
            except ImportError:
                continue
    try:
        module = importlib.import_module("src.uasset_parser")
        return module.UAssetParser
    except ImportError as e:
        raise SystemExit(
            "[fatal] uasset_mcp not found. Either:\n"
            "  - pip install uasset_mcp into the current Python; or\n"
            "  - set UASSET_MCP_SITE_PACKAGES to its site-packages dir.\n"
            f"original error: {e}"
        )


UAssetParser = _import_uasset_parser()


def normalize_input_dir(raw, content_root):
    """Accept either an OS abs path or a /Game/... virtual path; return (os_dir, game_dir)."""
    if not raw:
        raise SystemExit("[fatal] --dir is required")
    s = raw.strip().strip('"').strip("'")
    s = s.replace("\\", "/")
    content_root_norm = content_root.replace("\\", "/").rstrip("/")

    if s.startswith("/Game/"):
        rel = s[len("/Game/"):]
        os_dir = os.path.join(content_root, rel.replace("/", os.sep))
        game_dir = "/Game/" + rel.rstrip("/")
        return os.path.normpath(os_dir), game_dir.rstrip("/")

    abs_s = os.path.normpath(s).replace("\\", "/")
    if not abs_s.lower().startswith(content_root_norm.lower()):
        raise SystemExit(
            f"[fatal] directory not under content root.\n"
            f"  dir         = {abs_s}\n"
            f"  content_root= {content_root_norm}"
        )
    rel = abs_s[len(content_root_norm):].lstrip("/")
    game_dir = "/Game/" + rel.rstrip("/") if rel else "/Game"
    return os.path.normpath(abs_s.replace("/", os.sep)), game_dir


def os_to_package(os_path, content_root):
    rel = os.path.relpath(os_path, content_root).replace(os.sep, "/")
    if rel.lower().endswith(".uasset"):
        rel = rel[: -len(".uasset")]
    return "/Game/" + rel


def package_to_os(pkg, content_root):
    if not pkg.startswith("/Game/"):
        return None
    rel = pkg[len("/Game/"):]
    return os.path.join(content_root, rel.replace("/", os.sep) + ".uasset")


def iter_uassets(os_dir):
    for root, _dirs, files in os.walk(os_dir):
        for name in files:
            if name.lower().endswith(".uasset"):
                yield os.path.join(root, name)


def parse_safe(ufile):
    try:
        return UAssetParser(ufile)
    except Exception as e:
        print(f"  [warn] parse failed: {ufile} ({e})")
        return None


def extract_package_refs(parser):
    """Return (hard_pkgs, soft_pkgs) as deduped lists keeping discovery order."""
    hard = []
    seen_h = set()
    for imp in parser.imports:
        if (imp.class_name or "") != "Package":
            continue
        name = (imp.object_name or "")
        if not name.startswith("/Game/"):
            continue
        if name not in seen_h:
            seen_h.add(name)
            hard.append(name)

    soft = []
    seen_s = set()
    for n in parser.names:
        s = (n.name or "").rstrip("\x00")
        if not s.startswith("/Game/"):
            continue
        pkg = s.split(".", 1)[0]
        if pkg in seen_s or pkg in seen_h:
            continue
        seen_s.add(pkg)
        soft.append(pkg)
    return hard, soft


def is_redirector(parser):
    classes = [(e.class_name or "") for e in parser.exports]
    non_meta = [c for c in classes if c and c != "MetaData"]
    return bool(non_meta) and all(c == "ObjectRedirector" for c in non_meta)


def redirector_target(parser):
    """Best-effort: first Package import in the redirector's imports table."""
    for imp in parser.imports:
        if (imp.class_name or "") == "Package":
            name = (imp.object_name or "")
            if name.startswith("/Game/"):
                return name
    return None


class RedirectorProbe:
    """Cache lookups: package path -> (is_redirector, final_target_or_None)."""

    def __init__(self, content_root, max_hops=5):
        self.content_root = content_root
        self.max_hops = max_hops
        self.cache = {}

    def probe(self, pkg):
        if pkg in self.cache:
            return self.cache[pkg]
        result = self._resolve(pkg)
        self.cache[pkg] = result
        return result

    def _resolve(self, pkg):
        cur = pkg
        seen = set()
        first_is_redirector = None
        for _ in range(self.max_hops):
            if cur in seen:
                return (first_is_redirector or False, None)
            seen.add(cur)
            ufile = package_to_os(cur, self.content_root)
            if not ufile or not os.path.isfile(ufile):
                return (first_is_redirector or False, None)
            parser = parse_safe(ufile)
            if parser is None:
                return (first_is_redirector or False, None)
            if is_redirector(parser):
                if first_is_redirector is None:
                    first_is_redirector = True
                nxt = redirector_target(parser)
                if not nxt:
                    return (True, None)
                cur = nxt
                continue
            return (bool(first_is_redirector), cur if first_is_redirector else None)
        return (bool(first_is_redirector), None)


def short_name(pkg):
    return pkg.rsplit("/", 1)[-1] if "/" in pkg else pkg


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", required=True, help="OS abs path or /Game/... virtual path")
    ap.add_argument("--content-root", default=r"F:\F3\LetsGoDevelop\LetsGo\Content")
    ap.add_argument(
        "--output-dir",
        default=os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "reports",
        ),
    )
    args = ap.parse_args()

    os_dir, game_dir = normalize_input_dir(args.dir, args.content_root)
    if not os.path.isdir(os_dir):
        raise SystemExit(f"[fatal] directory does not exist: {os_dir}")

    print(f"[1/4] target directory:")
    print(f"      OS path  : {os_dir}")
    print(f"      Game path: {game_dir}")

    uassets = list(iter_uassets(os_dir))
    print(f"[2/4] found {len(uassets)} .uasset files")

    probe = RedirectorProbe(args.content_root)
    records = []
    t0 = time.time()
    for idx, ufile in enumerate(uassets, 1):
        if idx % 200 == 0:
            print(f"      scanning {idx}/{len(uassets)} ... elapsed={time.time()-t0:.1f}s")
        parser = parse_safe(ufile)
        if parser is None:
            continue
        if is_redirector(parser):
            continue
        referencer_pkg = os_to_package(ufile, args.content_root)
        hard, soft = extract_package_refs(parser)
        for ref_type, pkgs in (("hard", hard), ("soft", soft)):
            for dep in pkgs:
                if dep == referencer_pkg:
                    continue
                hit, target = probe.probe(dep)
                if not hit:
                    continue
                records.append({
                    "referencer": referencer_pkg,
                    "referencer_short": short_name(referencer_pkg),
                    "ref_type": ref_type,
                    "redirector": dep,
                    "redirector_short": short_name(dep),
                    "final_target": target or "",
                    "final_target_short": short_name(target) if target else "",
                })
    print(f"      done in {time.time()-t0:.1f}s; raw refs found: {len(records)}")

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    tag = (game_dir.strip("/").replace("/", "_") or "Game") + "_" + time.strftime("%Y%m%d_%H%M%S")
    json_path = out_dir / f"redirector_refs_{tag}.json"
    csv_path = out_dir / f"redirector_refs_{tag}.csv"
    md_path = out_dir / f"redirector_refs_{tag}.md"

    referencers = sorted({r["referencer"] for r in records})
    redirectors = sorted({r["redirector"] for r in records})
    payload = {
        "scanned_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "content_root": args.content_root,
        "os_dir": os_dir,
        "game_dir": game_dir,
        "stats": {
            "uassets_scanned": len(uassets),
            "raw_references": len(records),
            "unique_referencers": len(referencers),
            "unique_redirectors": len(redirectors),
        },
        "referencers": referencers,
        "redirectors": redirectors,
        "records": records,
    }
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    print(f"[3/4] JSON written: {json_path}")

    with open(csv_path, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["referencer", "ref_type", "redirector", "final_target"],
            quoting=csv.QUOTE_MINIMAL,
        )
        writer.writeheader()
        for r in records:
            writer.writerow({
                "referencer": r["referencer"],
                "ref_type": r["ref_type"],
                "redirector": r["redirector"],
                "final_target": r["final_target"],
            })

    md_lines = [
        f"# Redirector References under `{game_dir}`",
        "",
        f"- scanned_at: {payload['scanned_at']}",
        f"- uassets scanned: {len(uassets)}",
        f"- raw references: {len(records)}",
        f"- unique referencers: {len(referencers)}",
        f"- unique redirectors: {len(redirectors)}",
        "",
        "| # | referencer | ref_type | redirector | final_target |",
        "|---|------------|----------|------------|--------------|",
    ]
    for i, r in enumerate(records, 1):
        md_lines.append(
            f"| {i} | `{r['referencer']}` | {r['ref_type']} | "
            f"`{r['redirector']}` | `{r['final_target']}` |"
        )
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(md_lines) + "\n")

    print(f"[4/4] CSV written: {csv_path}")
    print(f"      MD  written: {md_path}")
    print(json.dumps({
        "json": str(json_path),
        "csv": str(csv_path),
        "md": str(md_path),
        "stats": payload["stats"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
