# -*- coding: utf-8 -*-
"""
require_chain.py — Lua require BFS + 业务关键词命中 + ProjectT 硬编码扫描

提供两个核心 API：

    resolve_lua_path(module_path, content_root) -> Optional[str]
        把 "LetsGo.Script.X.Y" 解析为绝对 .lua 路径。

    Analyzer(content_root, exclude_sdk=True).analyze(root_module)
        -> dict 包含:
            direct_letsgo: list[str]      该 Lua 直接 require 的 LetsGo 仓库 Lua 模块
            recursive_letsgo: list[str]   BFS 闭包内 LetsGo 仓库 Lua 模块（去重排序）
            gameplay_hits: list[str]      命中业务关键词的模块列表
            gameplay_keywords: list[str]  命中关键词集合（去重）
            projectt_refs: list[str]      Lua 中 /Game/Feature/ProjectT/... 字面量
            unresolved: list[str]         require 了但找不到物理文件的模块
            dynamic_requires: list[str]   require(string.format ...) 之类的动态调用，文件:行号
"""

import os
import re
from pathlib import Path


# 业务关键词（与 ue-3c-lua-migration §业务逻辑识别规则保持一致）
GAMEPLAY_KEYWORDS = [
    "Farm", "Arena", "UGC", "Chase", "Chest",
    "Home", "StarP", "Community", "Lobby", "Commercial",
]

# 仓库前缀 → Content 下的根目录段
REPO_ROOTS = {
    "LetsGo": ("LetsGo",),
    "LetsGo3C": ("LetsGo3C",),
    "LetsGoSDK": ("LetsGoSDK",),
}

_REQUIRE_RE = re.compile(
    r"""require\s*\(\s*['"]([A-Za-z_][\w.]*)['"]\s*\)"""
)
# 动态 require: require(string.format(...)) / require(var) / require(a .. b)
_DYN_REQUIRE_RE = re.compile(r"""require\s*\(\s*(?!['"])""")

# /Game/Feature/ProjectT/... 字面量
_PROJECTT_RE = re.compile(r"""['"]/Game/Feature/ProjectT/[\w./]+['"]""")


def resolve_lua_path(module_path, content_root):
    """Convert dotted module path to absolute .lua file path. None if not found."""
    if not module_path:
        return None
    parts = module_path.split(".")
    if not parts:
        return None
    head = parts[0]

    candidates = []
    if head == "Feature" and len(parts) >= 3:
        # Feature.<Name>.Script.X.Y -> Content/Feature/<Name>/Script/X/Y.lua
        feature_name = parts[1]
        rel = os.path.join("Feature", feature_name, *parts[2:]) + ".lua"
        candidates.append(os.path.join(content_root, rel))
    elif head in REPO_ROOTS:
        rel = os.path.join(*parts) + ".lua"
        candidates.append(os.path.join(content_root, rel))
    else:
        # Bare module — try under common roots as a last resort
        for repo in ("LetsGo", "LetsGo3C", "LetsGoSDK"):
            rel = os.path.join(repo, *parts) + ".lua"
            candidates.append(os.path.join(content_root, rel))

    for c in candidates:
        if os.path.isfile(c):
            return os.path.normpath(c)
    return None


def is_letsgo_module(module_path):
    """LetsGo 仓库 Lua = 模块路径前缀为 LetsGo. 或 Feature. 的（非 SDK/3C 视为业务侧）。"""
    return module_path.startswith("LetsGo.") or module_path.startswith("Feature.")


def is_sdk_module(module_path):
    return module_path.startswith("LetsGoSDK.")


def is_3c_module(module_path):
    return module_path.startswith("LetsGo3C.")


def hit_gameplay_keywords(module_path):
    """Return list of gameplay keywords that appear in this module path.
    Rule: case-insensitive substring; `StarP` is prefix-match for `StarParty` etc.
    """
    low = module_path.lower()
    hits = []
    for kw in GAMEPLAY_KEYWORDS:
        kw_low = kw.lower()
        if kw_low == "starp":
            # match StarP / StarParty / StarPlatform etc — prefix anywhere
            if re.search(r"\bstarp\w*", low) or "starp" in low:
                hits.append(kw)
        else:
            if kw_low in low:
                hits.append(kw)
    return hits


def _scan_text_for_requires(text):
    """Return (static_requires: list[str], dynamic_lines: list[int])."""
    statics = list(set(_REQUIRE_RE.findall(text)))
    dyn_lines = []
    for i, line in enumerate(text.splitlines(), start=1):
        if _DYN_REQUIRE_RE.search(line):
            # exclude false positive: require("static")
            if not _REQUIRE_RE.search(line):
                dyn_lines.append(i)
    return statics, dyn_lines


def _scan_text_for_projectt(text):
    return sorted(set(m.strip("'\"") for m in _PROJECTT_RE.findall(text)))


class Analyzer:
    def __init__(self, content_root, exclude_sdk=True, max_depth=0):
        self.content_root = content_root
        self.exclude_sdk = exclude_sdk
        self.max_depth = max_depth  # 0 = unlimited
        self._file_cache = {}   # module_path -> (direct_requires, dyn_lines, projectt_refs)

    def _scan_file(self, module_path):
        if module_path in self._file_cache:
            return self._file_cache[module_path]
        fpath = resolve_lua_path(module_path, self.content_root)
        if not fpath:
            self._file_cache[module_path] = (None, [], [])
            return self._file_cache[module_path]
        try:
            text = open(fpath, encoding="utf-8", errors="replace").read()
        except Exception:
            self._file_cache[module_path] = ([], [], [])
            return self._file_cache[module_path]
        statics, dyn_lines = _scan_text_for_requires(text)
        projectt = _scan_text_for_projectt(text)
        self._file_cache[module_path] = (statics, dyn_lines, projectt)
        return self._file_cache[module_path]

    def analyze(self, root_module):
        """BFS from root_module. Returns a dict (see file header)."""
        direct, dyn_lines_root, projectt_root = self._scan_file(root_module)
        result = {
            "direct_letsgo": [],
            "recursive_letsgo": [],
            "gameplay_hits": [],
            "gameplay_keywords": [],
            "projectt_refs": list(projectt_root),
            "unresolved": [],
            "dynamic_requires": [],
        }
        if direct is None:
            result["unresolved"].append(root_module)
            return result

        if dyn_lines_root:
            fpath = resolve_lua_path(root_module, self.content_root) or root_module
            for ln in dyn_lines_root:
                result["dynamic_requires"].append(f"{fpath}:{ln}")

        # direct LetsGo refs
        for mod in direct:
            if is_letsgo_module(mod):
                if mod not in result["direct_letsgo"]:
                    result["direct_letsgo"].append(mod)

        # BFS for recursive closure
        visited = {root_module}
        from collections import deque
        queue = deque()
        for m in direct:
            queue.append((m, 1))
            visited.add(m)
        all_modules = set()
        all_projectt = set(projectt_root)
        while queue:
            cur, depth = queue.popleft()
            if self.max_depth and depth > self.max_depth:
                continue
            all_modules.add(cur)
            kid_direct, kid_dyn, kid_projectt = self._scan_file(cur)
            if kid_direct is None:
                result["unresolved"].append(cur)
                continue
            for ref in kid_projectt:
                all_projectt.add(ref)
            if kid_dyn:
                fpath = resolve_lua_path(cur, self.content_root) or cur
                for ln in kid_dyn:
                    result["dynamic_requires"].append(f"{fpath}:{ln}")
            for kid in kid_direct:
                if kid in visited:
                    continue
                if self.exclude_sdk and is_sdk_module(kid):
                    continue
                visited.add(kid)
                queue.append((kid, depth + 1))

        # Filter recursive list to LetsGo only
        rec_letsgo = sorted(m for m in all_modules if is_letsgo_module(m))
        result["recursive_letsgo"] = rec_letsgo

        # gameplay hits
        for mod in rec_letsgo:
            hits = hit_gameplay_keywords(mod)
            if hits:
                result["gameplay_hits"].append(mod)
                for h in hits:
                    if h not in result["gameplay_keywords"]:
                        result["gameplay_keywords"].append(h)

        result["projectt_refs"] = sorted(all_projectt)
        # de-dup
        result["unresolved"] = sorted(set(result["unresolved"]))
        result["dynamic_requires"] = sorted(set(result["dynamic_requires"]))
        return result


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Analyze a Lua module's require chain")
    ap.add_argument("module", help="Lua module dotted path, e.g. LetsGo.Script.Foo")
    ap.add_argument("--content-root", default=r"F:\F3\LetsGoDevelop\LetsGo\Content")
    ap.add_argument("--max-depth", type=int, default=0)
    ap.add_argument("--include-sdk", action="store_true")
    args = ap.parse_args()
    az = Analyzer(args.content_root, exclude_sdk=not args.include_sdk, max_depth=args.max_depth)
    out = az.analyze(args.module)
    import json
    print(json.dumps(out, ensure_ascii=False, indent=2))
