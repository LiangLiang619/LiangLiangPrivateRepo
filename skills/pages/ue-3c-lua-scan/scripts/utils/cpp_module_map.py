# -*- coding: utf-8 -*-
"""
cpp_module_map.py — 扫描 C++ 源码，建立 "原生类名 -> Lua 模块路径" 映射

针对场景：
    BP 资产继承自 C++ 类，C++ 类在 native 层重载了 IUnLuaInterface::GetModuleName。
    此时 BP 自身的 .uasset FName 表里**不会**出现 Lua 路径，必须从 C++ 源码反推。

C++ 实现模式：

    FString AHomeGame::GetModuleName_Implementation() const
    {
        return TEXT("LetsGo.Script.Modplay.Core.GameMode.Games.Home.HomeGame");
    }

    // 或：
    FString UMyComp::GetModuleName_Implementation() const
    {
        return FString(TEXT("LetsGoSDK.Script.UI.MyView"));
    }

策略：
    1) glob Source/ 和 Plugins/ 下所有 *.cpp（默认排除 Intermediate / *.gen.cpp）
    2) 用 multi-line 正则一次性抓 "类名::GetModuleName_Implementation ... return TEXT(\"...\")"
    3) 输出 dict： { class_name(原样 + 去 A/U 前缀两个 key): { lua_path, source_file } }
    4) 文件级 mtime 缓存到 JSON，二次跑秒级

关键：键同时存原样（`AHomeGame`）和去前缀（`HomeGame`），因为 .uasset 的
`FObjectExport.super_name` 在某些情况下带 A/U 前缀、某些情况不带。
"""

import json
import os
import re
import sys
import time
from pathlib import Path


_GET_MODULE_RE = re.compile(
    r"""
    (?:FString\s+)?                                  # 可选 FString
    (?P<klass>[AUF]?[A-Z][\w]*)                      # 类名 (AHomeGame / UMyComp / FFoo)
    ::GetModuleName_Implementation\s*\(\s*\)         # 函数签名
    \s*const\s*\{                                    # const {
    [^}]*?                                           # 函数体
    return\s*                                        # return
    (?:FString\s*\(\s*)?                             # 可选 FString( 包装
    TEXT\s*\(\s*                                     # TEXT(
    L?"(?P<lua>[A-Za-z_][\w.]*)"                     # 字符串字面量（兼容 L"..."）
    \s*\)                                            # 闭合 TEXT
    """,
    re.VERBOSE | re.DOTALL,
)


# 默认扫描根目录（相对于 project root，即 LetsGo.uproject 同级）
DEFAULT_SCAN_ROOTS = ["Source", "Plugins"]
# 排除关键词（路径包含即跳过）
SKIP_PATH_TOKENS = [
    os.sep + "Intermediate" + os.sep,
    ".gen.cpp",
    ".generated.h",
    "Build" + os.sep + "Receipts" + os.sep,
]


def _iter_cpp_files(scan_roots, project_root):
    for sub in scan_roots:
        base = Path(project_root) / sub
        if not base.is_dir():
            continue
        for p in base.rglob("*.cpp"):
            sp = str(p)
            if any(tok in sp for tok in SKIP_PATH_TOKENS):
                continue
            yield p


def _load_cache(cache_file):
    if not cache_file or not os.path.isfile(cache_file):
        return {}
    try:
        with open(cache_file, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def _save_cache(cache_file, cache):
    if not cache_file:
        return
    Path(cache_file).parent.mkdir(parents=True, exist_ok=True)
    with open(cache_file, "w", encoding="utf-8") as fh:
        json.dump(cache, fh, ensure_ascii=False, indent=0)


def build_cpp_module_map(project_root, scan_roots=None, cache_file=None, verbose=True):
    """Scan all *.cpp under scan_roots and return (module_map, stats).

    module_map: {
        class_name (with prefix, e.g. 'AHomeGame'): {
            'lua_path': str,
            'source_file': str,
        },
        class_name (without prefix, e.g. 'HomeGame'): { ... },   # 同一份内容，方便正反查
    }
    stats: { 'files_scanned': int, 'files_cache_hit': int, 'unique_classes': int }
    """
    scan_roots = scan_roots or DEFAULT_SCAN_ROOTS
    cache = _load_cache(cache_file)
    new_cache = {}
    module_map = {}

    t0 = time.time()
    files = list(_iter_cpp_files(scan_roots, project_root))
    if verbose:
        print(f"  [cpp_map] scanning {len(files)} cpp files under {scan_roots}")
    cache_hit = 0
    scanned = 0
    for fp in files:
        sp = str(fp)
        try:
            mtime = fp.stat().st_mtime_ns
            size = fp.stat().st_size
        except OSError:
            continue
        cache_key = sp
        cached = cache.get(cache_key)
        entries = None
        if cached and cached.get("mtime") == mtime and cached.get("size") == size:
            entries = cached.get("entries", [])
            cache_hit += 1
        else:
            try:
                text = fp.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            entries = []
            if "GetModuleName_Implementation" not in text:
                # quick skip
                pass
            else:
                for m in _GET_MODULE_RE.finditer(text):
                    klass = m.group("klass")
                    lua = m.group("lua")
                    if "." not in lua:
                        # ignore non-namespaced strings (probably not a Lua path)
                        continue
                    entries.append({"class": klass, "lua_path": lua})
            scanned += 1
        new_cache[cache_key] = {
            "mtime": mtime,
            "size": size,
            "entries": entries,
        }
        for ent in entries:
            klass = ent["class"]
            lua = ent["lua_path"]
            payload = {"lua_path": lua, "source_file": sp}
            module_map.setdefault(klass, payload)
            # also register without A/U/F prefix
            if klass[0] in "AUF" and len(klass) > 1 and klass[1].isupper():
                stripped = klass[1:]
                module_map.setdefault(stripped, payload)

    _save_cache(cache_file, new_cache)
    if verbose:
        print(
            f"  [cpp_map] done in {time.time()-t0:.1f}s "
            f"(scanned={scanned}, cache_hit={cache_hit}); "
            f"{len(module_map)} class keys, "
            f"{len({v['lua_path'] for v in module_map.values()})} unique lua paths"
        )
    stats = {
        "files_total": len(files),
        "files_scanned": scanned,
        "files_cache_hit": cache_hit,
        "unique_classes": len({v["lua_path"] for v in module_map.values()}),
    }
    return module_map, stats


def lookup_native_parent(module_map, parent_class_name):
    """Return lua_path dict for a BP's native parent class name, or None.

    Tries both:
      - exact match (e.g. 'AHomeGame')
      - de-prefixed match (e.g. 'HomeGame' if user passed 'AHomeGame')
      - re-prefixed match (try A/U prefix if user passed bare name)
    """
    if not parent_class_name:
        return None
    if parent_class_name in module_map:
        return module_map[parent_class_name]
    # try de-prefix
    if parent_class_name[0] in "AUF" and len(parent_class_name) > 1:
        stripped = parent_class_name[1:]
        if stripped in module_map:
            return module_map[stripped]
    # try re-prefix
    for pfx in ("A", "U", "F"):
        prefixed = pfx + parent_class_name
        if prefixed in module_map:
            return module_map[prefixed]
    return None


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Build C++ class -> Lua module map by scanning *.cpp")
    ap.add_argument("--project-root", default=r"F:\F3\LetsGoDevelop\LetsGo")
    ap.add_argument(
        "--cache-file",
        default=r"F:\F3\LetsGoDevelop\LetsGo\Content\.cursor\skills\ue-3c-lua-scan\cache\cpp_module_map.json",
    )
    ap.add_argument("--dump", default="", help="optional JSON of resolved map (for inspection)")
    ap.add_argument("--lookup", default="", help="quick test: lookup a class name")
    args = ap.parse_args()
    mm, stats = build_cpp_module_map(args.project_root, cache_file=args.cache_file)
    print(f"  stats: {stats}")
    if args.lookup:
        hit = lookup_native_parent(mm, args.lookup)
        print(f"  lookup({args.lookup!r}) -> {hit}")
    if args.dump:
        Path(args.dump).parent.mkdir(parents=True, exist_ok=True)
        # Dump unique (class, lua) pairs to keep file readable
        unique = {}
        for k, v in mm.items():
            unique.setdefault(v["lua_path"], {"class_keys": [], "source_file": v["source_file"]})
            unique[v["lua_path"]]["class_keys"].append(k)
        with open(args.dump, "w", encoding="utf-8") as fh:
            json.dump(unique, fh, ensure_ascii=False, indent=2)
        print(f"  dumped: {args.dump}")
