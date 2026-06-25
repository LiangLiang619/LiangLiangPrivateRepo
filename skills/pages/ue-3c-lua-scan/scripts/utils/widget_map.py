# -*- coding: utf-8 -*-
"""
widget_map.py — UIWndNameToLuaPath 配置解析器

数据源：
  - Content/LetsGo/Script/Config/UIWndNameToLuaPath*.lua
  - Content/LetsGoSDK/Script/Config/UIWndNameToLuaPath*.lua
  - Content/Feature/**/Script/Config/UIWndNameToLuaPath_*.lua

解析方式：纯文本正则。支持典型写法：
    ["WBP_Foo"] = "LetsGo.Script.UI.Home.FooView",
    ['WBP_Bar'] = 'LetsGo.Script.UI.Bar.BarView',

不支持的写法（跳过 + 控制台 warning）：
    [VAR_NAME] = ...
    ["WBP_Dyn"] = SomeFunc(...)

输出结构：
    { widgetName: { "lua_path": str, "source": file_path } }
"""

import os
import re
import sys
from pathlib import Path

_ENTRY_RE = re.compile(
    r"""\[\s*['"](?P<name>[A-Za-z_][\w]*)['"]\s*\]\s*=\s*['"](?P<lua>[\w.]+)['"]"""
)


def _iter_config_files(content_root):
    """Yield all UIWndNameToLuaPath*.lua under known config dirs."""
    content_root = Path(content_root)
    patterns = [
        content_root / "LetsGo" / "Script" / "Config",
        content_root / "LetsGoSDK" / "Script" / "Config",
        content_root / "LetsGo3C" / "Script",
    ]
    for base in patterns:
        if not base.is_dir():
            continue
        for p in base.rglob("UIWndNameToLuaPath*.lua"):
            if p.is_file():
                yield p

    feature_root = content_root / "Feature"
    if feature_root.is_dir():
        for p in feature_root.rglob("UIWndNameToLuaPath*.lua"):
            if p.is_file():
                yield p


def build_widget_map(content_root, verbose=True):
    """Return (widget_map, stats_per_file).

    widget_map: { widget_name: { 'lua_path', 'source', 'duplicates' } }
    stats_per_file: { file_path_str: entry_count }
    """
    widget_map = {}
    stats = {}
    files = list(_iter_config_files(content_root))
    if verbose:
        print(f"  [widget_map] found {len(files)} config files under {content_root}")

    for fp in files:
        try:
            text = fp.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            print(f"  [widget_map] warn: failed to read {fp}: {e}", file=sys.stderr)
            continue

        count = 0
        for m in _ENTRY_RE.finditer(text):
            name = m.group("name")
            lua = m.group("lua")
            existing = widget_map.get(name)
            if existing is None:
                widget_map[name] = {
                    "lua_path": lua,
                    "source": str(fp),
                    "duplicates": [],
                }
            elif existing["lua_path"] != lua:
                existing["duplicates"].append({
                    "lua_path": lua,
                    "source": str(fp),
                })
            count += 1
        stats[str(fp)] = count
        if verbose:
            print(f"    - {fp.name}: {count} entries")

    if verbose:
        dup = sum(1 for v in widget_map.values() if v["duplicates"])
        print(f"  [widget_map] total unique widgets: {len(widget_map)} (with {dup} dup-overrides)")
    return widget_map, stats


def lookup(widget_map, widget_name):
    """Return the lua_path bound to widget_name, or None."""
    entry = widget_map.get(widget_name)
    return entry["lua_path"] if entry else None


def dump_to_json(widget_map, stats, out_path):
    import json
    out = {
        "stats_per_file": stats,
        "total_entries": len(widget_map),
        "widget_map": {
            name: {
                "lua_path": v["lua_path"],
                "source": v["source"],
                "duplicates": v["duplicates"],
            }
            for name, v in widget_map.items()
        },
    }
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)
    return out_path


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Build widget_map from UIWndNameToLuaPath*.lua")
    ap.add_argument("--content-root", default=r"F:\F3\LetsGoDevelop\LetsGo\Content")
    ap.add_argument("--dump", default="", help="optional JSON output path")
    args = ap.parse_args()

    widget_map, stats = build_widget_map(args.content_root)
    if args.dump:
        path = dump_to_json(widget_map, stats, args.dump)
        print(f"  [widget_map] dumped to {path}")
    sample = list(widget_map.items())[:5]
    if sample:
        print("  [widget_map] sample:")
        for name, v in sample:
            print(f"    {name} -> {v['lua_path']}")
