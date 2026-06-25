# -*- coding: utf-8 -*-
"""
binding_parser.py — 从 .uasset 二进制中抽取 UnLuaInterface 绑定的 Lua 路径

原理：
    UnLua 的 BP 重载 `GetModuleName()` 返回一个字符串（例如
    "LetsGo.Script.Community.Components.CharRPCComponent"），UE 序列化时把它当作
    FName 落到 .uasset 的 Names 表。我们扫 Names 表，用正则匹配三种前缀：
        - LetsGo.Script.*
        - LetsGo3C.Script.*
        - LetsGoSDK.Script.*
        - Feature.<X>.Script.*
    命中即认为是 UnLua 绑定。一个资产可能命中多条（罕见，多继承时），
    取第一个 + 把全部记到 candidates 字段供人工核查。

依赖：复用 `ue-recursive-deps-scan` 已落地的 UAssetParser 引导逻辑。
"""

import importlib
import os
import re
import sys

# ---------------------------------------------------------------------------
# UAssetParser bootstrap（与 scan_recursive_deps.py 完全一致，便于复用环境）
# ---------------------------------------------------------------------------
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
            "[fatal] 未找到 uasset_mcp。请确认任一前提：\n"
            "  - 当前 Python 已 pip install uasset_mcp；或\n"
            "  - 已通过 uvx uasset_mcp 安装；或\n"
            "  - 设置 UASSET_MCP_SITE_PACKAGES 指向其 site-packages。\n"
            f"原始错误: {e}"
        )


UAssetParser = _import_uasset_parser()


_LUA_PATH_RE = re.compile(
    r"^(?:LetsGo|LetsGo3C|LetsGoSDK|Feature\.[A-Za-z_]\w*)\.Script\.[A-Za-z_][\w.]*$"
)


def _package_to_uasset(pkg_path, content_root):
    """`/Game/X/Y` -> abs `<content_root>/X/Y.uasset`."""
    if not pkg_path.startswith("/Game/"):
        return None
    rel = pkg_path[len("/Game/"):]
    return os.path.join(content_root, rel.replace("/", os.sep) + ".uasset")


def _is_redirector(parser):
    """Detect if all non-MetaData exports are ObjectRedirector."""
    try:
        classes = [(e.class_name or "") for e in parser.exports]
    except Exception:
        return False
    non_meta = [c for c in classes if c and c != "MetaData"]
    return bool(non_meta) and all(c == "ObjectRedirector" for c in non_meta)


def _get_redirect_target_pkg(parser):
    """Pick the `/Game/...` package import that's the redirect target."""
    try:
        for imp in parser.imports:
            cls = (imp.class_name or "").strip()
            name = (imp.object_name or "").strip()
            if cls == "Package" and name.startswith("/Game/"):
                return name
    except Exception:
        pass
    return None


def _open_parser(uasset_path, content_root=None, follow_redirect=True, max_hops=5):
    """Open a .uasset and (optionally) transparently follow ObjectRedirector
    chains to the real target asset's parser.

    Args:
        uasset_path: absolute path to .uasset
        content_root: needed for redirector resolution; if None and redirect
                      needed, returns the redirector's parser (no chain follow).
        follow_redirect: if False, return whatever the file is (even redirector)
        max_hops: safety stop for redirector chains

    Returns:
        (parser, resolved_path) — resolved_path is the FS path of the final
        non-redirector asset. Or (None, uasset_path) on failure.
    """
    if not os.path.isfile(uasset_path):
        return None, uasset_path
    try:
        parser = UAssetParser(uasset_path)
    except Exception:
        return None, uasset_path

    if not follow_redirect or content_root is None:
        return parser, uasset_path

    cur_path = uasset_path
    seen = {os.path.normcase(os.path.abspath(uasset_path))}
    for _ in range(max_hops):
        if not _is_redirector(parser):
            return parser, cur_path
        target_pkg = _get_redirect_target_pkg(parser)
        if not target_pkg:
            return parser, cur_path  # redirector with no resolvable target
        next_path = _package_to_uasset(target_pkg, content_root)
        if not next_path or not os.path.isfile(next_path):
            return parser, cur_path  # target uasset missing
        key = os.path.normcase(os.path.abspath(next_path))
        if key in seen:
            return parser, cur_path  # cycle
        seen.add(key)
        try:
            parser = UAssetParser(next_path)
            cur_path = next_path
        except Exception:
            return parser, cur_path
    return parser, cur_path


def extract_unlua_paths(uasset_path, parser=None):
    """Parse a .uasset and return all distinct Lua module strings found in
    its Names table that look like UnLua GetModuleName outputs.

    Returns a list[str] (order preserved, deduped). Empty list = no UnLua
    binding detected.
    Returns None on parse failure.
    """
    p = parser if parser is not None else _open_parser(uasset_path)
    if p is None:
        return None

    seen = set()
    matches = []
    try:
        for n in p.names:
            raw = (n.name or "").rstrip("\x00")
            if not raw or "." not in raw:
                continue
            if _LUA_PATH_RE.match(raw):
                if raw not in seen:
                    seen.add(raw)
                    matches.append(raw)
    except Exception:
        return None
    return matches


def extract_native_parents(uasset_path, parser=None):
    """Best-effort: return the BP asset's native (C++) parent class candidates.

    Returns dict with:
      - 'primary': str or '' — the most likely native parent class name
                   (from BlueprintGeneratedClass export's super_name if available)
      - 'all_natives': list[str] — every imported native class name
                       (where class_package starts with '/Script/')
      - 'parent_package': str or '' — module package, e.g. '/Script/MoeGameCommonRuntime'

    Returns None on parse failure.

    Detection strategy:
      1) Find the main export (class_name == 'BlueprintGeneratedClass' or ending in '_C').
         Read its `super_name`. If non-empty, that's the parent class name.
      2) Walk imports: any with class_name == 'Class' AND class_package starts with
         '/Script/' is a native class import; collect all (BP can import many natives
         besides its direct parent — interfaces, used components, etc.).
      3) `primary` = step (1) result if found; else first match in step (2).

    Notes:
      - super_name might be empty for some asset shapes. Fall back to imports.
      - super_name might come without the A/U/F prefix; cpp_module_map.lookup_native_parent
        handles both forms.
    """
    p = parser if parser is not None else _open_parser(uasset_path)
    if p is None:
        return None

    result = {"primary": "", "all_natives": [], "parent_package": ""}

    # --- Step 1: BlueprintGeneratedClass export -> super_name ---
    try:
        bp_export = None
        for exp in p.exports:
            cls = (exp.class_name or "").strip()
            name = (exp.object_name or "").strip()
            if cls == "BlueprintGeneratedClass":
                bp_export = exp
                break
            # fallback heuristic: object_name ends with "_C"
            if name.endswith("_C") and bp_export is None:
                bp_export = exp
        if bp_export is not None:
            super_name = (getattr(bp_export, "super_name", "") or "").strip()
            if super_name:
                result["primary"] = super_name
    except Exception:
        pass

    # --- Step 2: Collect all native Class imports ---
    natives = []
    try:
        for imp in p.imports:
            cls = (imp.class_name or "").strip()
            pkg = (imp.class_package or "").strip()
            name = (imp.object_name or "").strip()
            if not name:
                continue
            if cls == "Class" and pkg.startswith("/Script/"):
                natives.append({"name": name, "package": pkg})
    except Exception:
        pass

    # de-dup preserving order
    seen = set()
    deduped = []
    for n in natives:
        if n["name"] in seen:
            continue
        seen.add(n["name"])
        deduped.append(n["name"])
    result["all_natives"] = deduped

    if not result["primary"] and deduped:
        result["primary"] = deduped[0]

    # Find the parent's package (for diagnostics)
    primary = result["primary"]
    if primary:
        for n in natives:
            if n["name"] == primary:
                result["parent_package"] = n["package"]
                break

    return result


_BP_EXPORT_CLASSES = frozenset({
    "BlueprintGeneratedClass",
    "AnimBlueprintGeneratedClass",
    "WidgetBlueprintGeneratedClass",
})


def is_blueprint_asset(parser):
    """Return True if the asset has a Blueprint-related export (e.g.
    BlueprintGeneratedClass), indicating it is a BP that could potentially
    bind Lua via C++ parent inheritance.  Non-BP assets (UserDefinedStruct,
    DataAsset, DataTable, etc.) return False.
    """
    if parser is None:
        return False
    try:
        for exp in parser.exports:
            cls = (exp.class_name or "").strip()
            if cls in _BP_EXPORT_CLASSES:
                return True
            obj = (exp.object_name or "").strip()
            if obj.endswith("_C") and cls not in ("MetaData",):
                return True
    except Exception:
        return False
    return False


def asset_short_name_from_path(uasset_path):
    """`.../BP_Foo.uasset` -> `BP_Foo`"""
    base = os.path.basename(uasset_path)
    if base.lower().endswith(".uasset"):
        return base[: -len(".uasset")]
    return base


def is_widget_asset(uasset_path, short_name=None):
    """Heuristic: WBP/UWBP prefix => Widget asset."""
    name = short_name or asset_short_name_from_path(uasset_path)
    low = name.lower()
    return low.startswith("wbp_") or low.startswith("uwbp_") or low.startswith("w_")


# ---------------------------------------------------------------------------
# Dynamic UnLua binding detection
# ---------------------------------------------------------------------------
# 这里对应"第 4 类绑定"：BP 实现了 IUnLuaInterface 并重载了 GetModuleName，
# 但返回值是 BP graph 拼接（如调用 BP_SharedLibrary 的某个函数返回字符串）。
# 静态分析无法拿到最终路径，只能识别"BP 绑了 Lua、但路径要去编辑器问"。

_CALLFUNC_RE = re.compile(r"^CallFunc_([A-Za-z_]\w*)_(.+)$")


def has_unlua_interface(parser):
    """Return True if the asset's imports table contains the UnLuaInterface
    UCLASS — strong signal the BP intends to bind Lua.
    """
    if parser is None:
        return False
    try:
        for imp in parser.imports:
            name = (imp.object_name or "").strip()
            if name == "UnLuaInterface":
                return True
    except Exception:
        return False
    return False


def generate_lua_name_candidates(asset_short_name):
    """For a BP asset like `BP_FootprintComponent`, generate candidate Lua
    filename stems to try in the project-wide lua index.

    Empirically, this project uses several conventions:
      A. Strip `BP_` prefix              → `FootprintComponent.lua`
      B. Keep `BP_` prefix as-is         → `BP_FootprintComponent.lua`
      C. Strip `BP_` + strip `Base` suffix → `MoeAblAbilityInstance.lua` (from `BP_MoeAblAbilityInstanceBase`)
      D. Strip `BP_` + add `Moe` prefix  → `MoeMainCharChineseDragonComponent.lua` (from `BP_MainCharChineseDragonComponent`)
      E. UnLua `Class->GetName()` 兜底   → `BP_FootprintComponent_C` (rare)

    Returned in priority order — the first candidate that gets a hit in the
    lua index wins. We keep order-preservation for false-positive minimization;
    the index lookup itself also picks the best match within each candidate hit.
    """
    if not asset_short_name:
        return []
    cands = []

    n = asset_short_name
    stripped = n[3:] if n.startswith("BP_") else n

    # ---- A. strip BP_ prefix（最常见）----
    if stripped != n:
        cands.append(stripped)

    # ---- C. strip Base suffix（与 A 叠加，命中如 MoeAblAbilityInstance）----
    if stripped.endswith("Base") and len(stripped) > len("Base"):
        cands.append(stripped[: -len("Base")])

    # ---- D. add Moe prefix（项目命名习惯，BP 不带 Moe、Lua 加上）----
    if stripped and not stripped.startswith("Moe"):
        cands.append("Moe" + stripped)
        # Also try Moe + (stripped Base)
        if stripped.endswith("Base"):
            cands.append("Moe" + stripped[: -len("Base")])

    # ---- B. keep as-is ----
    cands.append(n)

    # ---- E. _C suffix（UnLua Class->GetName() format）----
    if not n.endswith("_C"):
        cands.append(n + "_C")
    if stripped != n and not stripped.endswith("_C"):
        cands.append(stripped + "_C")

    # de-dup preserving order
    seen = set()
    out = []
    for c in cands:
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out


def extract_dynamic_resolver_hints(parser):
    """Scan FName table for BP graph node names like
        'CallFunc_FullLuaModuleName_FullModuleName'
    Returns a sorted list of unique resolver-function names (the captured first
    group), e.g. ['FullLuaModuleName']. These are functions that the BP's
    GetModuleName override calls to compute the Lua path at runtime.

    Empty list = no obvious dynamic resolver call detected.
    """
    if parser is None:
        return []
    hits = set()
    try:
        for n in parser.names:
            raw = (n.name or "").rstrip("\x00")
            m = _CALLFUNC_RE.match(raw)
            if not m:
                continue
            fname = m.group(1)
            # Filter obvious non-Lua-related calls (e.g., CallFunc_GetActorLocation_*)
            # Keep only ones that look related to module/lua/path/name composition.
            low = fname.lower()
            if any(k in low for k in ("module", "lua", "path", "script", "luamod", "fullname")):
                hits.add(fname)
    except Exception:
        return []
    return sorted(hits)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Extract UnLua module path(s) + native parent class from a .uasset")
    ap.add_argument("uasset", help="absolute path to .uasset")
    ap.add_argument("--content-root", default=r"F:\F3\LetsGoDevelop\LetsGo\Content",
                    help="Used for ObjectRedirector following")
    ap.add_argument("--no-follow-redirect", action="store_true")
    args = ap.parse_args()
    p, resolved = _open_parser(
        args.uasset,
        content_root=None if args.no_follow_redirect else args.content_root,
        follow_redirect=not args.no_follow_redirect,
    )
    if p is None:
        print("[error] parse failed")
        sys.exit(1)
    if os.path.normcase(os.path.abspath(resolved)) != os.path.normcase(os.path.abspath(args.uasset)):
        print(f"[redirector] followed to: {resolved}")
    paths = extract_unlua_paths(resolved, parser=p) or []
    parents = extract_native_parents(resolved, parser=p) or {}
    print(f"[unlua paths] {len(paths)} match(es):")
    for x in paths:
        print(f"  - {x}")
    print(f"[native parents] primary={parents.get('primary')!r}")
    print(f"  package: {parents.get('parent_package')}")
    print(f"  all imports: {parents.get('all_natives')}")
