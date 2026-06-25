# -*- coding: utf-8 -*-
"""
scan_3c_lua_bindings.py — 3C 资产→Lua 绑定扫描主脚本

输入二选一：
    --asset-csv <path>       兼容 ue-recursive-deps-scan 输出（含 `外部资产完整路径` 列）
    --root-dir  <abs|/Game/> 目录递归 glob 所有 .uasset

输出：
    19 列 CSV，与 ue-recursive-deps-scan 列结构对齐，
    但语义改成"以 Lua 为单位"（详见 refs/column-schema.md）。

工作流见同目录 SKILL.md。
"""

import argparse
import csv
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

csv.field_size_limit(2**31 - 1)

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR))

from utils.widget_map import build_widget_map, lookup as widget_lookup, dump_to_json as dump_widget_map
from utils.binding_parser import (
    extract_unlua_paths,
    extract_native_parents,
    has_unlua_interface,
    is_blueprint_asset,
    extract_dynamic_resolver_hints,
    generate_lua_name_candidates,
    asset_short_name_from_path,
    is_widget_asset,
    _open_parser as open_uasset_parser,
)
from utils.require_chain import (
    Analyzer,
    resolve_lua_path,
    GAMEPLAY_KEYWORDS,
)
from utils.cpp_module_map import build_cpp_module_map, lookup_native_parent
from utils.lua_index import build_lua_index, lookup_by_candidates
from utils.mcp_resolver import write_pending_request, load_mcp_result
from utils.asset_filter import collect_and_filter, DEFAULT_EXCLUDE_METHODS


OUTPUT_COLS = [
    "lua文件名",                       # 替代 外部资产名
    "lua模块完整路径",                 # 替代 外部资产完整路径
    "3C仓库目标路径",
    "引用链路（被谁依赖了）",
    "负责人",
    "进度",
    "搬迁方式",
    "Lua中ProjectT硬编码引用",         # 替代 ProjectT资产路径（被该资产依赖）
    "直接依赖Lua数",                   # 替代 直接依赖LetsGo资产数
    "直接依赖Lua列表",
    "递归依赖Lua总数",
    "递归依赖Lua列表",
    "玩法依赖数量",
    "全部引用玩法列表",
    "Lua父目录",                       # 替代 资产父目录
    "Lua子目录",                       # 替代 资产子目录
    "引用类型",
    # 删除 引用层级 (恒为"直接绑定"，无信息量)
    # 删除 是否需要 (与"进度"列重复)
]

# 3C 目录归类关键词（仅作为 BP 物理路径不可用时的兜底）
SUBDIR_RULES = [
    ("Character", [
        "Character", "Char", "Pawn", "Avatar", "Anim", "ABP", "Mesh",
        "Skeletal", "IK", "Physics", "Footprint", "Billboard",
        "LerpLocation", "Sound", "ReceiveHit", "Push", "RPC",
    ]),
    ("Controller", [
        "Controller", "Input", "Movement", "Locomotion", "Move",
    ]),
    ("Camera", [
        "Camera", "View", "Spring", "Boom", "FOV",
    ]),
]

# 3C 标准 C 类型集
C_TYPES = ("Character", "Controller", "Camera")


def infer_3c_target(module_path, asset_pkg_path=""):
    """Return suggested 3C target Lua module path.

    设计原则（顺序判定）：
      1) 模块已是 3C / SDK / 非 LetsGo 业务：直接返回特殊标记
      2) **优先使用 BP 资产在 LetsGo3C/Assets/Base/{C}/{subtype}/ 的真实物理位置**反推：
            /Game/LetsGo3C/Assets/Base/Character/Components/BP_Foo
                -> LetsGo3C.Script.Base.Character.Components.<LuaLeafName>Base
         规则严格匹配 user 提供的目录约定：Base/{Character|Controller|Camera}/{资产类型}/
      3) BP 路径不可用 → 退回关键词兜底，仅判 {C}，subtype 默认 'Components'
      4) 都判不出 → '[待确认]'

    参数:
        module_path: Lua 模块点号路径（绑定指向的 Lua），如
                     'LetsGo.Script.Modplay.Character.Component.CharRPCComponent'
        asset_pkg_path: 触发该绑定的 .uasset package path，
                        如 '/Game/LetsGo3C/Assets/Base/Character/Components/BP_Foo'
                        或绝对 fs 路径
    """
    if not module_path:
        return "[待编辑器查询]"
    if module_path.startswith("LetsGo3C."):
        return module_path  # 已在 3C
    if module_path.startswith("LetsGoSDK."):
        return "[已在SDK]"
    if not (module_path.startswith("LetsGo.") or module_path.startswith("Feature.")):
        return "[待确认]"

    # Lua leaf 保留原模块名，不加 Base 后缀
    lua_leaf = module_path.rsplit(".", 1)[-1]

    # ---- Strategy 1: 优先用 BP 真实物理位置反推 ----
    if asset_pkg_path:
        norm = asset_pkg_path.replace("\\", "/")
        # 兼容两种形态：/Game/LetsGo3C/...  或  abs path containing /LetsGo3C/Assets/Base/
        marker = "/LetsGo3C/Assets/Base/"
        idx = norm.find(marker)
        if idx >= 0:
            tail = norm[idx + len(marker):].strip("/")
            parts = tail.split("/")
            if len(parts) >= 2:
                c_type = parts[0]
                sub_type = parts[1]
                if c_type in C_TYPES and sub_type and not sub_type.lower().endswith(".uasset"):
                    return ".".join([
                        "LetsGo3C", "Script", "Base", c_type, sub_type, lua_leaf
                    ])

    # ---- Strategy 2: 关键词兜底（只在 BP 路径不可用 / 不在 3C 标准目录时使用）----
    full_lower = module_path.lower()
    matched_c = None
    for category, keywords in SUBDIR_RULES:
        for kw in keywords:
            if kw.lower() in full_lower:
                matched_c = category
                break
        if matched_c:
            break
    if not matched_c:
        return "[待确认]"

    # 默认 subtype = Components（最常见的形态；如不是 Component 类，请人工修正）
    return ".".join([
        "LetsGo3C", "Script", "Base", matched_c, "Components", lua_leaf
    ])


def derive_parent_subdir(module_path):
    """Take 3rd / 4th dotted segments. Empty if missing."""
    parts = module_path.split(".")
    parent = parts[2] if len(parts) > 2 else ""
    sub = parts[3] if len(parts) > 3 else ""
    return parent, sub


def gather_targets_from_csv(csv_path):
    """Return list of (asset_short_name, uasset_abs_path)."""
    targets = []
    with open(csv_path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if "外部资产完整路径" not in reader.fieldnames:
            raise SystemExit(
                f"[fatal] CSV 缺少列 '外部资产完整路径': {csv_path}\n"
                f"  实际列: {reader.fieldnames}"
            )
        for row in reader:
            path = (row.get("外部资产完整路径") or "").strip()
            name = (row.get("外部资产名") or "").strip()
            if not path:
                continue
            targets.append((name, path))
    return targets


def gather_targets_from_dir(root_dir, content_root):
    """Walk root_dir (absolute or `/Game/...` form) for *.uasset.
    Return list of (short_name, /Game/... package path).
    """
    if root_dir.startswith("/Game/"):
        abs_root = os.path.join(content_root, root_dir[len("/Game/"):].replace("/", os.sep))
    else:
        abs_root = root_dir
    if not os.path.isdir(abs_root):
        raise SystemExit(f"[fatal] root-dir 不存在: {abs_root}")
    targets = []
    for p in Path(abs_root).rglob("*.uasset"):
        short = p.stem
        rel = p.resolve().relative_to(Path(content_root).resolve())
        pkg = "/Game/" + rel.as_posix().replace(".uasset", "")
        targets.append((short, pkg))
    return targets


def package_to_uasset(pkg_path, content_root):
    """`/Game/X/Y` -> abs `Content/X/Y.uasset`. Accepts already-abs path too."""
    if os.path.isabs(pkg_path) and pkg_path.lower().endswith(".uasset"):
        return pkg_path
    if pkg_path.startswith("/Game/"):
        rel = pkg_path[len("/Game/"):]
        return os.path.join(content_root, rel.replace("/", os.sep) + ".uasset")
    # bare package, prepend Content/Game-style assumption
    return os.path.join(content_root, pkg_path.replace("/", os.sep) + ".uasset")


def load_user(user_json_path):
    try:
        if os.path.isfile(user_json_path):
            with open(user_json_path, encoding="utf-8") as fh:
                data = json.load(fh)
            return (data.get("user") or "").strip()
    except Exception:
        pass
    return ""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument(
        "--asset-csv",
        nargs="+",
        help="资产 CSV (1 个或多个；含 `外部资产完整路径` 列)。多个 CSV 会合并去重再扫描。",
    )
    g.add_argument("--root-dir", help="资产根目录（绝对路径 或 /Game/LetsGo3C/...）")
    ap.add_argument("--output-csv", required=True)
    # 资产 CSV 模式专属：预过滤参数
    ap.add_argument(
        "--filter-exclude-method",
        nargs="*",
        default=DEFAULT_EXCLUDE_METHODS,
        help="排除哪些 `搬迁方式` 值的资产（默认 ['无需搬迁']）；传空列表 (--filter-exclude-method) 关闭此过滤",
    )
    ap.add_argument(
        "--filter-bp-only",
        action="store_true",
        help="只保留 BP 系资产（命名前缀 BP_ / WBP_ / UWBP_ / ABP_ / W_）",
    )
    ap.add_argument("--content-root", default=r"F:\F3\LetsGoDevelop\LetsGo\Content")
    ap.add_argument(
        "--user-json",
        default=r"F:\F3\LetsGoDevelop\LetsGo\Content\LetsGo3C\Intermediate\user.json",
    )
    ap.add_argument("--max-depth", type=int, default=0, help="require BFS 最大深度 (0=无限)")
    ap.add_argument("--include-sdk-deps", action="store_true", help="把 LetsGoSDK.* 也计入依赖统计")
    ap.add_argument("--widget-map-dump", default="", help="可选: 把 widget_map 转储到该 JSON 路径用于复查")
    ap.add_argument(
        "--project-root",
        default=r"F:\F3\LetsGoDevelop\LetsGo",
        help="UE 项目根目录（含 Source/ Plugins/），用于扫 C++ 的 GetModuleName_Implementation",
    )
    ap.add_argument(
        "--cpp-cache",
        default=r"F:\F3\LetsGoDevelop\LetsGo\Content\.cursor\skills\ue-3c-lua-scan\cache\cpp_module_map.json",
        help="C++ 模块映射缓存文件（按文件 mtime 增量）",
    )
    ap.add_argument(
        "--skip-cpp-scan",
        action="store_true",
        help="跳过 C++ 父类扫描（提速；BP 继承 native 类的绑定将漏扫）",
    )
    ap.add_argument(
        "--lua-index-cache",
        default=r"F:\F3\LetsGoDevelop\LetsGo\Content\.cursor\skills\ue-3c-lua-scan\cache\lua_index.json",
        help="Lua 文件索引缓存（用于动态绑定的文件名匹配）",
    )
    ap.add_argument(
        "--skip-lua-index",
        action="store_true",
        help="跳过 Lua 文件名索引（提速；动态绑定无法靠文件名启发式解析）",
    )
    ap.add_argument(
        "--mcp-pending-out",
        default="",
        help="动态绑定中文件名解析失败的 BP，写到该 JSON 给 MCP 工具兜底解析（路径默认放 cache/）",
    )
    ap.add_argument(
        "--apply-mcp-result",
        default="",
        help="读取 MCP 解析回填 JSON，覆盖对应行的 Lua 路径",
    )
    args = ap.parse_args()

    t0 = time.time()
    print(f"[Phase 0] 输入归一")
    user = load_user(args.user_json)
    if not user:
        print(f"  [warn] 未读到 user.json 的 user 字段: {args.user_json}; 负责人列将留空")
    else:
        print(f"  负责人: {user}")

    if args.asset_csv:
        csv_list = args.asset_csv if isinstance(args.asset_csv, list) else [args.asset_csv]
        print(f"  来源: {len(csv_list)} 个资产 CSV，应用预过滤")
        targets, filter_stats = collect_and_filter(
            csv_list,
            exclude_methods=args.filter_exclude_method or [],
            bp_only=args.filter_bp_only,
            verbose=True,
        )
        # 把统计塞到全局供 Phase 4 报告引用
        globals()["_PREFILTER_STATS"] = filter_stats
    else:
        targets = gather_targets_from_dir(args.root_dir, args.content_root)
        print(f"  来源: 根目录 ({args.root_dir}) -> 发现 {len(targets)} 个 .uasset")

    if not targets:
        print("  [warn] 无目标资产，提前退出")
        return 0

    print(f"\n[Phase 1a] 构建 Widget 映射表")
    widget_map, stats = build_widget_map(args.content_root, verbose=True)
    if args.widget_map_dump:
        dump_widget_map(widget_map, stats, args.widget_map_dump)
        print(f"  widget_map 已转储: {args.widget_map_dump}")

    if args.skip_cpp_scan:
        print(f"\n[Phase 1b] (跳过) C++ 父类映射表 — BP 继承 native 类的绑定将不识别")
        cpp_map = {}
    else:
        print(f"\n[Phase 1b] 构建 C++ 父类→Lua 映射表 (project_root={args.project_root})")
        cpp_map, cpp_stats = build_cpp_module_map(
            args.project_root, cache_file=args.cpp_cache, verbose=True
        )

    if args.skip_lua_index:
        print(f"\n[Phase 1c] (跳过) 全工程 Lua 文件索引 — 动态绑定将无法靠文件名解析")
        lua_index = {"by_stem": {}, "by_basename": {}, "total": 0}
    else:
        print(f"\n[Phase 1c] 构建全工程 Lua 文件索引 (content_root={args.content_root})")
        lua_index = build_lua_index(
            args.content_root, cache_file=args.lua_index_cache, verbose=True
        )

    # Pre-loaded MCP results (asset_short_name -> resolved_module)
    mcp_results = load_mcp_result(args.apply_mcp_result) if args.apply_mcp_result else {}
    if mcp_results:
        print(f"  [mcp] loaded {len(mcp_results)} pre-resolved entries from {args.apply_mcp_result}")

    print(f"\n[Phase 2] 抽取 Lua 绑定")
    # 统计
    stats_unlua = 0
    stats_widget = 0
    stats_cpp = 0
    stats_dynamic = 0
    stats_unbound = 0
    stats_missing = 0
    stats_redirector_followed = 0   # 跟随重定向器命中真实资产的次数
    # 同一个 Lua 模块被多个资产绑时，合并 chain 列
    # key = (lua_module, source_type)
    seen_bindings = {}

    for idx, (short_name, pkg_or_path) in enumerate(targets, 1):
        ufile = package_to_uasset(pkg_or_path, args.content_root)
        if not os.path.isfile(ufile):
            print(f"  [{idx}/{len(targets)}] {short_name}  [FILE MISSING] {ufile}")
            stats_missing += 1
            key = (f"[文件缺失]{short_name}", "[文件缺失]")
            seen_bindings.setdefault(key, {
                "lua_module": "",
                "source_type": "[文件缺失]",
                "asset_chain": set(),
            })["asset_chain"].add(short_name)
            continue

        # Open parser once and reuse for both extractions.
        # Transparently follow ObjectRedirector chains to the real target asset.
        parser, resolved_path = open_uasset_parser(
            ufile, content_root=args.content_root, follow_redirect=True
        )
        if parser is None:
            print(f"  [{idx}/{len(targets)}] {short_name}  [PARSE FAIL]")
            stats_missing += 1
            continue
        if os.path.normcase(os.path.abspath(resolved_path)) != os.path.normcase(os.path.abspath(ufile)):
            stats_redirector_followed += 1
            # Keep the original short_name (asset's BP_FootprintComponent) but
            # use the resolved path for downstream logic that needs the actual
            # asset location (e.g. infer_3c_target via asset_pkg_path).
            rel = os.path.relpath(resolved_path, args.content_root).replace(os.sep, "/")
            pkg_or_path = "/Game/" + rel[:-len(".uasset")] if rel.lower().endswith(".uasset") else "/Game/" + rel

        # A. UnLua self-binding (BP overrides GetModuleName)
        unlua_matches = extract_unlua_paths(ufile, parser=parser) or []

        bindings_for_this_asset = []
        if unlua_matches:
            primary = unlua_matches[0]
            extras = unlua_matches[1:]
            bindings_for_this_asset.append(("UnLuaInterface", primary, extras, ""))
            stats_unlua += 1
            print(f"  [{idx}/{len(targets)}] {short_name}  UnLua(self): {primary}"
                  + (f"  (+{len(extras)} extras)" if extras else ""))

        # B. UnLua inherited from C++ parent (only if BP didn't override AND
        #    the asset is actually a Blueprint — prevents false positives on
        #    UserDefinedStruct / DataAsset / non-BP assets that merely
        #    reference a native class in their imports)
        if not unlua_matches and cpp_map and is_blueprint_asset(parser):
            parents_info = extract_native_parents(ufile, parser=parser) or {}
            primary_parent = parents_info.get("primary", "")
            hit = lookup_native_parent(cpp_map, primary_parent) if primary_parent else None
            # If primary parent didn't hit, try every imported native class as a fallback
            # (covers cases where super_name is empty/wrong but interfaces hit)
            extra_parent_hits = []
            if not hit and primary_parent:
                for cand in parents_info.get("all_natives", []):
                    if cand == primary_parent:
                        continue
                    h = lookup_native_parent(cpp_map, cand)
                    if h:
                        extra_parent_hits.append((cand, h))
                if extra_parent_hits:
                    hit = extra_parent_hits[0][1]
                    primary_parent = extra_parent_hits[0][0]
                    extra_parent_hits = extra_parent_hits[1:]
            if hit:
                lua_path = hit["lua_path"]
                extras = [f"{cand}->{h['lua_path']}" for cand, h in extra_parent_hits]
                bindings_for_this_asset.append(
                    ("UnLuaInterface(C++继承)", lua_path, extras, f"native_parent={primary_parent}")
                )
                stats_cpp += 1
                print(
                    f"  [{idx}/{len(targets)}] {short_name}  UnLua(C++ parent: {primary_parent}): {lua_path}"
                )

        # C'. UnLua dynamic binding — BP implements IUnLuaInterface but has no
        # static GetModuleName literal. Multi-strategy resolution:
        #   1) MCP pre-resolved (if user supplied --apply-mcp-result)
        #   2) Filename heuristic: search project Lua index for matching .lua
        #   3) Fall back to [动态] placeholder + record for MCP follow-up
        if not bindings_for_this_asset and has_unlua_interface(parser):
            resolvers = extract_dynamic_resolver_hints(parser)
            resolver_hint = ("调用 " + " | ".join(resolvers)) if resolvers else "未识别 resolver"

            resolved_mod = None
            resolver_strategy = ""
            extras_for_row = []

            # Strategy 1: MCP pre-resolved
            if short_name in mcp_results:
                resolved_mod = mcp_results[short_name]
                resolver_strategy = "MCP"

            # Strategy 2: filename heuristic
            if not resolved_mod and lua_index.get("total"):
                candidates = generate_lua_name_candidates(short_name)
                pick, all_matches = lookup_by_candidates(lua_index, candidates)
                if pick:
                    resolved_mod = pick
                    resolver_strategy = "filename"
                    if len(all_matches) > 1:
                        # Record other candidates for human review
                        for m in all_matches[1:5]:
                            extras_for_row.append(m["module_path"])

            if resolved_mod:
                src_type = "UnLuaInterface(动态-{0})".format(
                    "MCP" if resolver_strategy == "MCP" else "文件名匹配"
                )
                note = f"resolver_hint={resolver_hint}"
                if extras_for_row:
                    note += f"; 文件名同名候选共 {1+len(extras_for_row)} 个"
                bindings_for_this_asset.append((src_type, resolved_mod, extras_for_row, note))
                stats_dynamic += 1
                print(
                    f"  [{idx}/{len(targets)}] {short_name}  "
                    f"UnLua(动态/{resolver_strategy}): {resolved_mod}"
                    + (f"  (+{len(extras_for_row)} 同名候选)" if extras_for_row else "")
                )
            else:
                bindings_for_this_asset.append(
                    ("UnLuaInterface(动态)", "", [], f"dynamic_resolver={resolver_hint}")
                )
                stats_dynamic += 1
                print(
                    f"  [{idx}/{len(targets)}] {short_name}  "
                    f"UnLua(动态路径, {resolver_hint}) — 文件名启发式也未命中"
                )

        # C. WBP -> widget_map lookup
        if is_widget_asset(ufile, short_name):
            lua_path = widget_lookup(widget_map, short_name)
            if lua_path:
                bindings_for_this_asset.append(("UIWndNameToLuaPath", lua_path, [], ""))
                stats_widget += 1
                print(f"  [{idx}/{len(targets)}] {short_name}  Widget: {lua_path}")
            else:
                bindings_for_this_asset.append(("[未绑定]", "", [], ""))
                stats_unbound += 1
                print(f"  [{idx}/{len(targets)}] {short_name}  [WBP NOT BOUND]")

        if not bindings_for_this_asset:
            # BP without any binding => no binding row needed
            continue

        for source_type, lua_module, extras, note in bindings_for_this_asset:
            # 不可解析的绑定类型按资产独立行（每个 BP 的真实 Lua 路径需独立人工填）；
            # 可解析的按 (lua_module, source_type) 合并（一个 Lua 被多个资产引用合并 chain）
            placeholder_types = ("UnLuaInterface(动态)", "[未绑定]", "[文件缺失]")
            if source_type in placeholder_types or not lua_module:
                key = (source_type, short_name)
            else:
                key = (lua_module, source_type)
            entry = seen_bindings.setdefault(key, {
                "lua_module": lua_module,
                "source_type": source_type,
                "asset_chain": set(),
                "asset_pkgs": {},   # short_name -> pkg path (for 3C target inference)
                "extras": extras,
                "note": note,
                # For dynamic bindings, remember the original asset name for placeholder row generation
                "anchor_asset": short_name,
            })
            entry["asset_chain"].add(short_name)
            entry["asset_pkgs"][short_name] = pkg_or_path

    # Optional: write a JSON of still-unresolved dynamic BPs for MCP follow-up
    if args.mcp_pending_out or any(
        e["source_type"] == "UnLuaInterface(动态)" for e in seen_bindings.values()
    ):
        pending = [
            {
                "asset_short_name": e["anchor_asset"],
                "asset_pkg_path": next(iter(e.get("asset_pkgs", {}).values()), ""),
                "resolver_hint": (e.get("note") or "").replace("dynamic_resolver=", ""),
            }
            for e in seen_bindings.values()
            if e["source_type"] == "UnLuaInterface(动态)"
        ]
        if pending:
            pending_path = args.mcp_pending_out or os.path.join(
                str(THIS_DIR), "..", "cache", "pending_mcp_resolution.json"
            )
            pending_path = os.path.abspath(pending_path)
            write_pending_request(pending, pending_path)
            print(
                f"\n  [mcp] {len(pending)} dynamic BPs still unresolved; "
                f"wrote pending request -> {pending_path}"
            )
            print(
                f"  [mcp] hint: run graph.describe on each + assemble result JSON, "
                f"then re-run with --apply-mcp-result <result.json>"
            )

    print(f"\n[Phase 3] Lua require 链 BFS (target_lua={len(seen_bindings)})")
    analyzer = Analyzer(
        content_root=args.content_root,
        exclude_sdk=not args.include_sdk_deps,
        max_depth=args.max_depth,
    )

    analyzed_rows = []
    depth_dist = []
    for key, entry in seen_bindings.items():
        lua_module = entry["lua_module"]
        source_type = entry["source_type"]
        asset_chain = sorted(entry["asset_chain"])
        extras = entry.get("extras", [])

        if not lua_module or source_type in ("[未绑定]", "[文件缺失]", "UnLuaInterface(动态)"):
            # placeholder row — one row per asset to keep them distinguishable in CSV
            row = {col: "" for col in OUTPUT_COLS}
            anchor = entry.get("anchor_asset", "")
            if source_type == "UnLuaInterface(动态)":
                row["lua文件名"] = f"(动态路径@{anchor})"
                note = entry.get("note", "")
                row["lua模块完整路径"] = f"[动态计算: {note.replace('dynamic_resolver=', '')}]"
            elif source_type == "[未绑定]":
                row["lua文件名"] = f"(无绑定@{anchor})"
                row["lua模块完整路径"] = ""
            else:
                row["lua文件名"] = f"(文件缺失@{anchor})"
                row["lua模块完整路径"] = ""
            row["3C仓库目标路径"] = "[待编辑器查询]" if source_type == "UnLuaInterface(动态)" else "[待确认]"
            row["引用链路（被谁依赖了）"] = " | ".join(asset_chain)
            row["负责人"] = user
            row["进度"] = "□"
            row["搬迁方式"] = ""
            row["Lua中ProjectT硬编码引用"] = ""
            row["直接依赖Lua数"] = "0"
            row["直接依赖Lua列表"] = ""
            row["递归依赖Lua总数"] = "0"
            row["递归依赖Lua列表"] = ""
            row["玩法依赖数量"] = "0"
            row["全部引用玩法列表"] = ""
            row["Lua父目录"] = ""
            row["Lua子目录"] = ""
            row["引用类型"] = source_type
            analyzed_rows.append(row)
            continue

        result = analyzer.analyze(lua_module)
        direct = result["direct_letsgo"]
        rec = result["recursive_letsgo"]
        gp_hits = result["gameplay_hits"]
        gp_kws = result["gameplay_keywords"]
        projectt = result["projectt_refs"]
        depth_dist.append(len(rec))

        note = entry.get("note", "")

        # 列 2 — 多 UnLua 命中时把候选 join；附加 native_parent 标注
        path_field = lua_module
        suffix_parts = []
        if extras:
            suffix_parts.append("候选: " + " | ".join(extras))
        if note:
            suffix_parts.append(note)
        if suffix_parts:
            path_field = lua_module + "  [" + "; ".join(suffix_parts) + "]"

        # 选一个代表性的 asset pkg 路径用于反推 3C 目标——优先取在 LetsGo3C/Assets/Base/
        # 标准目录下的那个；都没有则取任意一个
        asset_pkgs = entry.get("asset_pkgs", {})
        rep_pkg = ""
        for _name, _pkg in sorted(asset_pkgs.items()):
            if "/LetsGo3C/Assets/Base/" in _pkg.replace("\\", "/"):
                rep_pkg = _pkg
                break
        if not rep_pkg and asset_pkgs:
            rep_pkg = next(iter(sorted(asset_pkgs.values())))

        target_3c = infer_3c_target(lua_module, rep_pkg)
        parent, sub = derive_parent_subdir(lua_module)

        row = {
            "lua文件名": lua_module.rsplit(".", 1)[-1],
            "lua模块完整路径": path_field,
            "3C仓库目标路径": target_3c,
            "引用链路（被谁依赖了）": " | ".join(asset_chain),
            "负责人": user,
            "进度": "□",
            "搬迁方式": "",
            "Lua中ProjectT硬编码引用": " | ".join(projectt),
            "直接依赖Lua数": str(len(direct)),
            "直接依赖Lua列表": " | ".join(direct),
            "递归依赖Lua总数": str(len(rec)),
            "递归依赖Lua列表": " | ".join(rec),
            "玩法依赖数量": str(len(gp_hits)),
            "全部引用玩法列表": " | ".join(gp_kws),
            "Lua父目录": parent,
            "Lua子目录": sub,
            "引用类型": source_type,
        }
        analyzed_rows.append(row)
        if result["unresolved"]:
            print(f"  [warn] {lua_module}: 未解析模块 {len(result['unresolved'])} 个")
        if result["dynamic_requires"]:
            print(f"  [warn] {lua_module}: 动态 require {len(result['dynamic_requires'])} 处 -> {result['dynamic_requires'][:3]}")

    print(f"\n[Phase 4] 写出 CSV")
    out_path = Path(args.output_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # 排序：BP 自绑定 > C++ 继承 > 动态-MCP > 动态-文件名 > Widget > 动态占位 > 缺失
    type_order = {
        "UnLuaInterface": 0,
        "UnLuaInterface(C++继承)": 1,
        "UnLuaInterface(动态-MCP)": 2,
        "UnLuaInterface(动态-文件名匹配)": 3,
        "UIWndNameToLuaPath": 4,
        "UnLuaInterface(动态)": 5,
        "[未绑定]": 6,
        "[文件缺失]": 7,
    }
    analyzed_rows.sort(
        key=lambda r: (
            type_order.get(r["引用类型"], 99),
            r["lua模块完整路径"],
        )
    )
    with open(out_path, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=OUTPUT_COLS, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        for row in analyzed_rows:
            writer.writerow(row)

    avg_rec = (sum(depth_dist) / len(depth_dist)) if depth_dist else 0
    print(f"\n============== 扫描简报 ==============")
    pf = globals().get("_PREFILTER_STATS")
    if pf:
        print(f"资产预过滤:")
        for c in pf["per_csv"]:
            print(f"  - {os.path.basename(c['path'])}: {c['total_rows']} 行")
        print(f"  合并去重后: {pf['pre_filter_total']}")
        print(f"  排除 搬迁方式 ∈ {pf['exclude_methods']}: -{pf['excluded_by_method']}")
        if pf["bp_only"]:
            print(f"  排除 非BP资产: -{pf['bp_excluded']}")
        print(f"  最终进入扫描: {pf['final_total']}")
    print(f"输入资产: {len(targets)}")
    print(f"UnLua(self) 命中: {stats_unlua}")
    print(f"UnLua(C++继承) 命中: {stats_cpp}")
    print(f"UnLua(动态) 命中: {stats_dynamic}  ← 含文件名匹配/MCP/纯占位")
    if stats_redirector_followed:
        print(f"已跟随 ObjectRedirector: {stats_redirector_followed} 个原路径资产实际是重定向桩")
    print(f"Widget 命中: {stats_widget}")
    print(f"WBP 未命中: {stats_unbound}")
    print(f"文件缺失/解析失败: {stats_missing}")
    print(f"输出行数: {len(analyzed_rows)}")
    print(f"平均递归依赖: {avg_rec:.1f}")
    print(f"输出: {out_path}")
    print(f"耗时: {time.time()-t0:.1f}s")
    print(f"=====================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
