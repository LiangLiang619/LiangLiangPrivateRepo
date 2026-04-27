#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Scan Lua files for UI framework interface calls (wiki-aligned list) and emit CSV
for short-path -> long-path migration, with:
  - arg_expression: primary asset-name argument to the call (per-interface index)
  - resolve_hint: script-side clue for the agent/LLM (see SKILL.md)
  - wiki_longpath: from wiki (True/False/empty=NA) — False means C++ path not supported
"""
from __future__ import print_function, unicode_literals

import os
import re
import sys
import io
import datetime

# asset_arg: which 0-based argument in the call carries the "asset name / path" for migration
# (OpenWindowWithWidget: index 1 is the widget long path; index 0 is logical window id)
def _i(wiki, name, cat, risk, apath, wlp):
    return {
        "wiki": wiki, "name": name, "cat": cat, "risk": risk,
        "asset_arg": apath, "wiki_longpath": wlp,
    }


INTERFACE_META = [
    # windows
    _i(1, "OpenWindow", "OpenWindow", "high", 0, True),
    _i(2, "OpenWindowWithWidget", "OpenWindow", "low", 1, True),
    _i(3, "OpenWindowWithAssetObject", "OpenWindow", "low", 0, True),
    _i(4, "OpenWindowUnvisiable", "OpenWindow", "high", 0, True),
    _i(5, "LoadWindowToOuter", "OpenWindow", "high", 0, True),
    # widgets
    _i(6, "CreateWidgetByName", "CreateWidget", "low", 0, True),
    _i(7, "CreateWidgetNoLua", "CreateWidget", "low", 0, True),
    _i(8, "AddWidgetAndLua", "CreateWidget", "low", 0, True),
    _i(9, "AddChildWidgetWithLuaName", "CreateWidget", "low", 0, True),
    _i(10, "CreateWidgetAndBindLua", "CreateWidget", "medium", 0, True),
    _i(11, "AddWidget", "CreateWidget", "medium", 0, True),
    _i(12, "AddChildWidget", "CreateWidget", "medium", 0, True),
    _i(13, "CreateDragWidget", "CreateWidget", "medium", 0, True),
    _i(14, "AddWidgetAsyn", "CreateWidget", "medium", 0, True),
    _i(15, "CreateWidgetAsyn", "CreateWidget", "medium", 0, True),
    _i(16, "AddView", "CreateWidget", "none", 0, None),
    # image
    _i(17, "ImgSetImage", "ImgSet", "low", 1, True),
    _i(18, "ImgLoadThenShow", "ImgSet", "low", 1, True),
    _i(19, "ImgSetImageAsync", "ImgSet", "high", 1, False),
    _i(20, "ImgSetImageSync", "ImgSet", "high", 1, False),
    _i(21, "ImgSetCutoutImage", "ImgSet", "low", 1, True),
    _i(22, "BtnSetImage", "ImgSet", "low", 1, True),
    _i(24, "ImgSetCDNImage", "ImgSet", "none", 1, None),
    _i(25, "ImgSetMaterialCDNTexture", "ImgSet", "none", 1, None),
    _i(26, "ImgSetTexture", "ImgSet", "none", 1, None),
    _i(27, "SetBrushFromMaterial", "ImgSet", "none", 1, None),
    _i(28, "SetBrushFromAtlasInterface", "ImgSet", "none", 1, None),
    _i(28, "ImgSetMaterialTexture", "ImgSet", "none", 1, None),
    # load
    _i(29, "LoadAssetObject", "LoadAsset", "low", 0, True),
    _i(30, "AsyncLoadAssetObject", "LoadAsset", "high", 0, False),
    _i(31, "AsyncLoadAssetObjects", "LoadAsset", "high", 0, False),
    _i(32, "AsyncLoadSoftObjectPath", "LoadAsset", "low", 0, True),
    _i(33, "AsyncLoadLongPath", "LoadAsset", "low", 0, True),
    _i(34, "AsyncLoadLongPaths", "LoadAsset", "low", 0, True),
    _i(35, "MoeAsyncLoadPath", "LoadAsset", "medium", 0, None),
    _i(37, "MoeAsyncLoadPaths", "LoadAsset", "medium", 0, None),
    _i(41, "TryLoadWidgetAsset", "LoadAsset", "medium", 0, True),
    _i(42, "TryGetTexture", "LoadAsset", "low", 0, True),
    _i(43, "CheckAndSetCDNImg", "LoadAsset", "high", 1, None),
    _i(46, "CheckAndSetCDNImgWithDefault", "LoadAsset", "high", 1, False),
    _i(49, "IsAssetExistsInAssetNameMap", "LoadAsset", "low", 0, True),
    # spine
    _i(47, "PlaySpineAnim", "Spine", "low", 0, True),
    _i(48, "PlaySpineAnimAsync", "Spine", "high", 0, False),
    # save
    _i(52, "GetSaveData", "SaveData", "medium", 0, True),
    _i(53, "CreateSaveData", "SaveData", "medium", 0, True),
    # cpp
    _i(55, "ButtonSetNormalImage", "ImgSet_CppDirect", "low", 1, True),
    _i(56, "ButtonSetHoveredImage", "ImgSet_CppDirect", "low", 1, True),
    _i(57, "ButtonSetPressedImage", "ImgSet_CppDirect", "low", 1, True),
]

_LONG_PATH_PREFIX = "/Game/"

_FUNC_DEF_RE = re.compile(
    r"^\s*(?:local\s+)?function\s+[\w.:]+\s*\(", re.UNICODE
)


def _build_call_pattern(name):
    return re.compile(
        r"(?:[:.])\s*" + re.escape(name) + r"\s*\("
        + r"|"
        + r"\b" + re.escape(name) + r"\s*\(",
        re.UNICODE,
    )


_PATTERNS = [
    (meta, _build_call_pattern(meta["name"]))
    for meta in INTERFACE_META
]

_STRING_ARG_RE = re.compile(
    r"""[(:.,]\s*["']([^"']+)["']""", re.UNICODE
)

# SaveDataName / WindowName / GameModelName style
_RE_CONFIG = re.compile(
    r"^(?:(?:SDK|_MOE|UE4)\.)?(?:SaveDataName|WindowName)\.([A-Za-z0-9_]+)$"
)
_RE_OR_FALLBACK = re.compile(
    r"(.+?)\s+or\s+[\"']([^\"']+)[\"']$", re.UNICODE
)
_RE_FUNC_HEAD = re.compile(
    r"^\s*(?:local\s+)?function\s+[\w.:]*\s*\(([^)]*)\)",
    re.UNICODE,
)
_RE_LOCAL_STR = re.compile(
    r"^\s*local\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*[\"']([^\"']+)[\"']"
)


def _is_function_definition(line):
    return bool(_FUNC_DEF_RE.match(line))


def _compute_block_comment_mask(lines):
    """True = skip; line is inside a --[[ block from line start state."""
    mask = [False] * len(lines)
    in_block = False
    for i, l in enumerate(lines):
        mask[i] = in_block
        j = 0
        while j < len(l):
            if not in_block and l[j : j + 4] == "--[[":
                in_block = True
                j += 4
            elif in_block and l[j : j + 2] == "]]":
                in_block = False
                j += 2
            else:
                j += 1
    return mask


def _strip_line_comment(line):
    in_sq = False
    in_dq = False
    i = 0
    while i < len(line):
        c = line[i]
        if c == '"' and not in_sq:
            in_dq = not in_dq
        elif c == "'" and not in_dq:
            in_sq = not in_sq
        elif c == "-" and not in_sq and not in_dq:
            if i + 1 < len(line) and line[i + 1] == "-":
                if i + 3 < len(line) and line[i + 2 : i + 4] == "[[":
                    return line
                return line[:i]
        i += 1
    return line


def _split_lua_top_level_args(inside):
    args = []
    cur = []
    depth = 0
    in_sq = False
    in_dq = False
    i = 0
    while i < len(inside):
        c = inside[i]
        if in_dq:
            cur.append(c)
            if c == "\\" and i + 1 < len(inside):
                cur.append(inside[i + 1])
                i += 2
                continue
            if c == '"':
                in_dq = False
            i += 1
            continue
        if in_sq:
            cur.append(c)
            if c == "\\" and i + 1 < len(inside):
                cur.append(inside[i + 1])
                i += 2
                continue
            if c == "'":
                in_sq = False
            i += 1
            continue
        if c == '"':
            in_dq = True
            cur.append(c)
            i += 1
            continue
        if c == "'":
            in_sq = True
            cur.append(c)
            i += 1
            continue
        if c in "({[":
            depth += 1
            cur.append(c)
            i += 1
            continue
        if c in ")}]":
            if depth > 0:
                depth -= 1
            cur.append(c)
            i += 1
            continue
        if c == "," and depth == 0:
            args.append("".join(cur).strip())
            cur = []
            i += 1
            continue
        cur.append(c)
        i += 1
    if cur or args:
        args.append("".join(cur).strip())
    return args


def _find_call_substring(stripped, interface_name):
    m = re.search(
        r"(?:[:.]\s*|\b)" + re.escape(interface_name) + r"\s*\(",
        stripped,
    )
    if not m:
        return None, None
    paren = m.end() - 1
    depth = 0
    in_sq = in_dq = False
    i = paren
    # inside starts at paren+1
    j = paren + 1
    while j < len(stripped):
        c = stripped[j]
        if in_dq:
            if c == "\\" and j + 1 < len(stripped):
                j += 2
                continue
            if c == '"':
                in_dq = False
            j += 1
            continue
        if in_sq:
            if c == "\\" and j + 1 < len(stripped):
                j += 2
                continue
            if c == "'":
                in_sq = False
            j += 1
            continue
        if c == '"':
            in_dq = True
            j += 1
            continue
        if c == "'":
            in_sq = True
            j += 1
            continue
        if c in "({[":
            depth += 1
        elif c in ")]}":
            if c == ")" and depth == 0:
                ins = stripped[paren + 1 : j]
                return m.start(), ins
            if depth > 0:
                depth -= 1
        j += 1
    ins = stripped[paren + 1 :]
    return m.start(), ins


def _get_nth_arg(stripped, interface_name, n):
    pos, ins = _find_call_substring(stripped, interface_name)
    if ins is None:
        return "", ""
    args = _split_lua_top_level_args(ins)
    if n < 0 or n >= len(args):
        return "", ins
    return args[n], ins


def _extract_first_string_arg(code):
    m = _STRING_ARG_RE.search(code)
    return m.group(1) if m else ""


def _detect_call_style(code):
    if "::" in code:
        return "cpp_static"
    if ".bp:" in code or "self.bp:" in code or "self:" in code:
        return "bp_method"
    if ":" in code.split("(")[0]:
        return "method"
    return "function"


def _last_function_start(lines, line_idx, max_look=400):
    for k in range(line_idx, max(0, line_idx - max_look) - 1, -1):
        s = _strip_line_comment(lines[k])
        m = _RE_FUNC_HEAD.match(s)
        if m:
            return k, m.group(1)
    return None, ""


def _parse_param_names(paren_innards):
    if not paren_innards or not paren_innards.strip():
        return []
    out = []
    for p in paren_innards.split(","):
        t = p.strip()
        if not t or t == "...":
            continue
        t = t.split("=")[0].strip()
        t = t.split(":")[0].strip()
        toks = t.split()
        name = toks[-1] if toks else ""
        if name in ("self", "..."):
            continue
        if re.match(r"^([A-Za-z_][A-Za-z0-9_]*)$", name or ""):
            out.append(name)
    return out


def _is_lua_identifier(s):
    return bool(re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", (s or "").strip()))


def _quoted_inner(expr):
    e = (expr or "").strip()
    if len(e) < 2:
        return None
    if e[0] == e[-1] and e[0] in ("'", '"'):
        return e[1:-1]
    return None


def _derive_is_long_path(arg_expr, first_str_in_line):
    q = _quoted_inner(arg_expr)
    if q is not None:
        return "yes" if q.startswith(_LONG_PATH_PREFIX) else "no"
    if first_str_in_line and first_str_in_line.startswith(_LONG_PATH_PREFIX):
        return "yes"
    if first_str_in_line and first_str_in_line:
        return "no"
    return "no"


def _search_local_string_assign(lines, start_line, end_line, var_name):
    for li in range(end_line - 1, start_line - 1, -1):
        if li < 0 or li >= len(lines):
            continue
        s = _strip_line_comment(lines[li])
        if _is_function_definition(s) and li < end_line - 1:
            break
        m = re.match(
            r"^\s*local\s+" + re.escape(var_name) + r"\s*=\s*[\"']([^\"']+)[\"']",
            s,
        )
        if m:
            return m.group(1)
        m = re.match(
            r"^\s*" + re.escape(var_name) + r"\s*=\s*[\"']([^\"']+)[\"']",
            s,
        )
        if m:
            return m.group(1)
    return None


def _build_resolve_hint(arg_expr, interface_name, file_lines, line_idx, first_str, meta):
    expr = (arg_expr or "").strip()
    wlp = meta.get("wiki_longpath")

    if wlp is None and meta["cat"] in ("CreateWidget",) and interface_name == "AddView":
        if expr and not (expr.startswith('"') or expr.startswith("'")):
            return "N/A:widget_ref", wlp
    if wlp is None and (
        "CDN" in interface_name
        or interface_name
        in (
            "SetBrushFromMaterial",
            "SetBrushFromAtlasInterface",
            "ImgSetTexture",
            "ImgSetMaterialTexture",
        )
    ):
        return "CDN_N/A", wlp
    if wlp is None and interface_name in (
        "MoeAsyncLoadPath",
        "MoeAsyncLoadPaths",
        "CheckAndSetCDNImg",
    ):
        return "needs_moe_flag_or_branch", wlp
    if wlp is False:
        return "cpp_unsupported:wiki_longpath_false", wlp

    if not expr:
        if first_str:
            return "literal:legacy_line_substring", True
        return "unknown:empty", True

    if (expr.startswith('"') or expr.startswith("'")) and len(expr) >= 2:
        s = expr[1:-1] if expr[-1] in ('"', "'") else expr[1:]
        f = "literal:" + s[:200]
        return f, wlp

    mcf = _RE_CONFIG.match(expr.strip())
    if mcf:
        g = mcf.group(0)
        if "WindowName." in g or ".WindowName." in g or g.endswith("WindowName." + mcf.group(1)):
            return "window_name:" + mcf.group(1), wlp
        if "SaveDataName." in g or ".SaveDataName." in g or "SaveDataName" in g:
            return "config_ref:" + g, wlp

    win_m = re.search(
        r"\.WindowName\.(UI_[A-Za-z0-9_]+)", expr,
    ) or re.search(
        r"WindowName\.(UI_[A-Za-z0-9_]+)", expr,
    )
    if win_m:
        return "window_name:" + win_m.group(1), wlp

    sdm = re.search(
        r"\.SaveDataName\.([A-Za-z0-9_]+)", expr,
    ) or re.search(
        r"SaveDataName\.([A-Za-z0-9_]+)", expr,
    )
    if sdm:
        return "config_ref:SaveDataName." + sdm.group(1), wlp

    ofb = _RE_OR_FALLBACK.match(expr.strip())
    if ofb:
        return "or_fallback:" + ofb.group(2)[:200], wlp

    fstart = _last_function_start(file_lines, line_idx)[0]
    start_ln = 0 if fstart is None else fstart
    st = _search_local_string_assign(file_lines, start_ln, line_idx, expr.strip())
    if st is not None:
        vn = expr.strip()
        if "." not in expr:
            return "local_var:%s=%s" % (vn, st)[:500], wlp
        return "local_var_expr:%s=>%s" % (expr[:100], st)[:500], wlp

    fs, paren = _last_function_start(file_lines, line_idx)
    if fs is not None and paren and _is_lua_identifier(expr):
        for pn in _parse_param_names(paren):
            if pn == expr:
                return "func_param:" + expr, wlp
        for pn in paren.split(","):
            t = pn.strip().split()[-1].strip() if pn.strip() else ""
            t = t.split("=")[0].strip().split(":")[0].strip()
            if t == expr:
                return "func_param:" + expr, wlp

    if re.match(r"^self\.[A-Za-z0-9_]+$", expr) or re.match(
        r"^_[A-Z][A-Za-z0-9_]+(\.[A-Za-z0-9_]+)*$", expr
    ):
        return "likely_member_or_state:" + expr, wlp

    return "unknown:" + expr[:200], wlp


def _wiki_longpath_str(wlp):
    if wlp is True:
        return "yes"
    if wlp is False:
        return "no"
    if wlp is None:
        return "N/A"
    return ""


def scan_file(filepath, lines=None):
    if lines is None:
        with io.open(filepath, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

    block_mask = _compute_block_comment_mask(lines)
    results = []
    for idx, raw_line in enumerate(lines):
        if block_mask[idx]:
            continue
        stripped = _strip_line_comment(raw_line)
        if not stripped.strip():
            continue
        if _is_function_definition(stripped):
            continue

        for meta, pat in _PATTERNS:
            iname = meta["name"]
            if not pat.search(stripped):
                continue
            aidx = max(0, int(meta.get("asset_arg", 0)))
            arg_expr, _inside = _get_nth_arg(stripped, iname, aidx)
            first_str = _extract_first_string_arg(stripped)
            is_long = _derive_is_long_path(arg_expr, first_str)
            rhint, _ = _build_resolve_hint(
                arg_expr, iname, lines, idx, first_str, meta,
            )
            results.append(
                {
                    "file": filepath,
                    "line": idx + 1,
                    "interface": iname,
                    "category": meta["cat"],
                    "risk": meta["risk"],
                    "first_string_arg": first_str,
                    "is_long_path": is_long,
                    "arg_expression": arg_expr,
                    "resolve_hint": rhint,
                    "wiki_longpath": _wiki_longpath_str(meta.get("wiki_longpath")),
                    "call_style": _detect_call_style(stripped),
                    "code": raw_line.rstrip(),
                }
            )
    return results


def scan_directory(root):
    all_results = []
    for dirpath, _, filenames in os.walk(root):
        for fname in filenames:
            if not fname.endswith(".lua"):
                continue
            fpath = os.path.join(dirpath, fname)
            try:
                all_results.extend(scan_file(fpath))
            except Exception as e:
                print("WARN: failed to scan %s: %s" % (fpath, e), file=sys.stderr)
    return all_results


def write_csv(results, csv_path):
    columns = [
        "file",
        "line",
        "interface",
        "category",
        "risk",
        "first_string_arg",
        "is_long_path",
        "arg_expression",
        "resolve_hint",
        "wiki_longpath",
        "call_style",
        "code",
    ]
    bom = "\ufeff"
    with io.open(csv_path, "w", encoding="utf-8", newline="") as f:
        f.write(bom)
        f.write(",".join(columns) + "\n")
        for row in results:
            cells = []
            for col in columns:
                val = str(row.get(col, ""))
                if "," in val or '"' in val or "\n" in val:
                    val = '"' + val.replace('"', '""') + '"'
                cells.append(val)
            f.write(",".join(cells) + "\n")


def main():
    if len(sys.argv) < 2:
        print("Usage: python scan_longpath_usage.py <root_dir> [--output <csv>]")
        sys.exit(1)

    root = sys.argv[1]
    csv_path = None
    if "--output" in sys.argv:
        oi = sys.argv.index("--output")
        if oi + 1 < len(sys.argv):
            csv_path = sys.argv[oi + 1]

    if csv_path is None:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = os.path.join(root, "Intermediate", "LuaCheck")
        os.makedirs(out_dir, exist_ok=True)
        csv_path = os.path.join(out_dir, "longpath_migration_scan_%s.csv" % ts)

    print("Scanning: %s" % root)
    results = scan_directory(root)
    write_csv(results, csv_path)
    print("Found %d interface calls" % len(results))
    print("CSV written to: %s" % csv_path)
    sc = sum(
        1
        for r in results
        if r.get("is_long_path") == "no" and r.get("first_string_arg")
    )
    lc = sum(1 for r in results if r.get("is_long_path") == "yes")
    unk = sum(1 for r in results if (r.get("resolve_hint", "").startswith("unknown")))
    print("  (legacy) Short literal paths: %d" % sc)
    print("  (legacy) Long literal paths:  %d" % lc)
    print("  resolve_hint == unknown: %d" % unk)


if __name__ == "__main__":
    main()
