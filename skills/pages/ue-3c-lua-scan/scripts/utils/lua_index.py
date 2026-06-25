# -*- coding: utf-8 -*-
"""
lua_index.py — 全工程 Lua 文件索引

一次性 glob Content/ 下所有 .lua，建：
    by_stem  : { 文件名(不含 .lua) -> [list of {module_path, fs_path}] }
    by_basename: { 文件名(含 .lua)   -> [list of ...]  }

module_path：把 fs_path 转换为 UnLua 风格的点号路径，例如：
    Content/LetsGo/Script/Modplay/Character/Component/BillboardDataComponent.lua
      -> LetsGo.Script.Modplay.Character.Component.BillboardDataComponent

文件级 mtime 缓存到 JSON，二次扫秒级。
"""

import json
import os
import sys
import time
from pathlib import Path


# 排除目录关键词（按子串匹配，命中即跳过）
SKIP_DIR_TOKENS = [
    os.sep + "Intermediate" + os.sep,
    os.sep + "Saved" + os.sep,
    os.sep + "DerivedDataCache" + os.sep,
    os.sep + ".codebuddy" + os.sep,
    os.sep + ".codesync_messages" + os.sep,
    os.sep + ".vs" + os.sep,
    os.sep + ".vscode" + os.sep,
    os.sep + ".cursor" + os.sep,    # skill 自身、各种缓存
    os.sep + ".idea" + os.sep,
]


def _is_skip_path(p):
    s = str(p)
    return any(tok in s for tok in SKIP_DIR_TOKENS)


def fs_to_module(fs_path, content_root):
    """`Content/LetsGo/Script/X/Y.lua` -> `LetsGo.Script.X.Y`."""
    fs_path = os.path.normpath(fs_path)
    content_root = os.path.normpath(content_root)
    try:
        rel = os.path.relpath(fs_path, content_root)
    except ValueError:
        return ""
    if rel.lower().endswith(".lua"):
        rel = rel[: -len(".lua")]
    return rel.replace(os.sep, ".")


def build_lua_index(content_root, cache_file="", verbose=True):
    """Walk content_root for *.lua, build index.

    Returns dict:
        {
          "by_stem": {stem: [{"module_path","fs_path"}, ...]},
          "by_basename": {basename: [...]},
          "total": int,
        }
    """
    content_root = os.path.abspath(content_root)

    cache_payload = None
    if cache_file and os.path.isfile(cache_file):
        try:
            with open(cache_file, encoding="utf-8") as fh:
                cache_payload = json.load(fh)
        except Exception:
            cache_payload = None

    t0 = time.time()
    by_stem = {}
    by_basename = {}
    total = 0
    scanned = 0
    skipped = 0

    for root, dirs, files in os.walk(content_root):
        # in-place pruning
        if _is_skip_path(root + os.sep):
            skipped += len(files)
            dirs[:] = []
            continue
        # prune subdirs by name early
        dirs[:] = [d for d in dirs if not _is_skip_path(os.path.join(root, d) + os.sep)]

        for fn in files:
            if not fn.lower().endswith(".lua"):
                continue
            fp = os.path.join(root, fn)
            scanned += 1
            stem = fn[: -len(".lua")]
            mod = fs_to_module(fp, content_root)
            if not mod:
                continue
            entry = {"module_path": mod, "fs_path": fp}
            by_stem.setdefault(stem, []).append(entry)
            by_basename.setdefault(fn, []).append(entry)
            total += 1

    elapsed = time.time() - t0
    if verbose:
        print(
            f"  [lua_index] scanned {scanned} lua files, indexed {total} entries"
            f", unique stems={len(by_stem)}, elapsed={elapsed:.1f}s"
        )

    index = {
        "by_stem": by_stem,
        "by_basename": by_basename,
        "total": total,
    }

    if cache_file:
        try:
            Path(cache_file).parent.mkdir(parents=True, exist_ok=True)
            with open(cache_file, "w", encoding="utf-8") as fh:
                json.dump(index, fh, ensure_ascii=False, indent=0)
        except Exception as e:
            print(f"  [lua_index] warn: cache write failed: {e}", file=sys.stderr)

    return index


# 排序优先级：当一个候选文件名命中多个 module_path 时，按以下顺序优先选择
_PREFERRED_ROOTS = [
    "LetsGo3C.Script.",   # 已搬到 3C 的优先
    "LetsGo.Script.",
    "LetsGoSDK.Script.",
    "Feature.",
]


def _rank(module_path):
    for i, p in enumerate(_PREFERRED_ROOTS):
        if module_path.startswith(p):
            return i
    return len(_PREFERRED_ROOTS)


def lookup_by_candidates(index, candidates):
    """Try each candidate stem in order. Return (resolved_module, all_matches) on first stem with hits.

    resolved_module: best single pick (highest preference)
    all_matches: full list of {module_path, fs_path} for human review
    Returns (None, []) if all candidates miss.
    """
    by_stem = index.get("by_stem", {})
    for stem in candidates:
        hits = by_stem.get(stem)
        if not hits:
            continue
        sorted_hits = sorted(hits, key=lambda h: (_rank(h["module_path"]), h["module_path"]))
        return sorted_hits[0]["module_path"], sorted_hits
    return None, []


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Build & query the Lua file index")
    ap.add_argument("--content-root", default=r"F:\F3\LetsGoDevelop\LetsGo\Content")
    ap.add_argument("--cache-file", default=r"F:\F3\LetsGoDevelop\LetsGo\Content\.cursor\skills\ue-3c-lua-scan\cache\lua_index.json")
    ap.add_argument("--lookup", default="", help="Comma-separated candidate stems to look up")
    args = ap.parse_args()
    idx = build_lua_index(args.content_root, cache_file=args.cache_file)
    if args.lookup:
        cands = [c.strip() for c in args.lookup.split(",") if c.strip()]
        resolved, matches = lookup_by_candidates(idx, cands)
        print(f"candidates={cands} -> resolved={resolved!r}")
        for m in matches[:10]:
            print(f"  - {m['module_path']}")
