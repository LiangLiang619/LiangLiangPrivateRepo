#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scan_external_deps.py — LetsGo3C External Dependency Scanner

Scans the LetsGo3C repository for all external dependencies across 8 categories:
  1. Lua require cross-repo references + UE4.Class inheritance
  2. Lua hardcoded /Game/ asset paths
  3. Lua implicit global variable coupling (_MOE.*, MOE_3C fallback, _G.LetsGo*)
  4. UE asset imports pointing outside 3C/SDK
  5. Config/Tables registration source audit
  6. EventEnum key origin audit
  7. UI/WindowName coupling in 3C base code
  8. Business keyword presence (functions/paths)

Outputs 8 CSV files + 1 Markdown overview report.
"""

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lua_scanner import scan_lua_directory, LuaScanResult, MOE_3C_EXTERNAL_FIELDS, load_sdk_event_keys, load_sdk_commondefine_keys
from asset_scanner import scan_assets_binary, scan_assets_editor_mcp, AssetScanResult
from report_writer import (
    write_require_csv,
    write_hardpath_csv,
    write_globals_csv,
    write_globals_detail_csv,
    write_assets_csv,
    write_config_tables_csv,
    write_event_keys_csv,
    write_ui_coupling_csv,
    write_biz_keywords_csv,
    write_common_define_csv,
    write_markdown_report,
    print_summary,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Scan LetsGo3C repo for external dependencies"
    )
    parser.add_argument(
        "--repo-root",
        default="Content/LetsGo3C",
        help="3C repository root (absolute or relative to CWD). Default: Content/LetsGo3C",
    )
    parser.add_argument(
        "--content-root",
        default=None,
        help="UE Content directory. Default: <repo-root>/..",
    )
    parser.add_argument(
        "--out-dir",
        default=None,
        help="Output directory. Default: <repo-root>/Migration/Analysis/ExternalDeps",
    )
    parser.add_argument(
        "--asset-mode",
        choices=["binary", "editor-mcp"],
        default="binary",
        help="Asset scanning mode. Default: binary (offline parsing)",
    )
    parser.add_argument(
        "--whitelist-extra",
        default="",
        help="Extra whitelist prefixes (comma-separated, e.g. 'MyPlugin.,/Game/MyPlugin/')",
    )
    parser.add_argument(
        "--lua-globs",
        default="Script/**/*.lua,StartUp/**/*.lua,HookConfig/**/*.lua,Hooks/**/*.lua,Data/**/*.lua",
        help="Lua file glob patterns relative to repo-root (comma-separated)",
    )
    parser.add_argument(
        "--skip-categories",
        default="",
        help="Skip categories (comma-separated): require,hardpath,globals,assets,config,events,ui,biz",
    )
    parser.add_argument(
        "--moe3c-fallback-fields",
        default=None,
        help="Override MOE_3C fallback fields (comma-separated). Default uses built-in set.",
    )
    parser.add_argument(
        "--biz-keywords",
        default=None,
        help="Override business keywords (comma-separated). Default: Farm,Arena,UGC,Chase,Chest,Home,StarP,Community,Lobby,Commercial",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    start_time = time.time()

    # Phase 0: Resolve paths
    repo_root = Path(args.repo_root).resolve()
    if not repo_root.is_dir():
        print(f"[error] repo-root does not exist: {repo_root}")
        sys.exit(1)

    content_root = Path(args.content_root).resolve() if args.content_root else repo_root.parent
    if not content_root.is_dir():
        print(f"[error] content-root does not exist: {content_root}")
        sys.exit(1)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out_dir) if args.out_dir else (repo_root / "Migration" / "Analysis" / "ExternalDeps")
    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    skip = set(s.strip().lower() for s in args.skip_categories.split(",") if s.strip())
    lua_globs = [g.strip() for g in args.lua_globs.split(",") if g.strip()]

    # Parse extra whitelist
    extra_require_prefixes = tuple(
        p.strip() for p in args.whitelist_extra.split(",")
        if p.strip() and not p.strip().startswith("/")
    )
    extra_asset_prefixes = tuple(
        p.strip() for p in args.whitelist_extra.split(",")
        if p.strip() and p.strip().startswith("/")
    )

    # Parse MOE_3C fallback fields override
    moe3c_fields = None
    if args.moe3c_fallback_fields:
        moe3c_fields = set(f.strip() for f in args.moe3c_fallback_fields.split(",") if f.strip())

    # Parse business keywords override
    if args.biz_keywords:
        import lua_scanner
        lua_scanner.BUSINESS_KEYWORDS = [k.strip() for k in args.biz_keywords.split(",") if k.strip()]

    print(f"[Phase 0] 配置")
    print(f"  repo-root:    {repo_root}")
    print(f"  content-root: {content_root}")
    print(f"  out-dir:      {out_dir}")
    print(f"  asset-mode:   {args.asset_mode}")
    print(f"  lua-globs:    {lua_globs}")
    print(f"  skip:         {skip or '(none)'}")
    if moe3c_fields:
        print(f"  fallback-fields: {moe3c_fields}")
    print()

    # Load SDK event keys for filtering
    sdk_event_keys = None
    if "events" not in skip:
        print("[Phase 0.5] 加载 SDK 事件定义（用于过滤已迁移事件）...")
        sdk_event_keys = load_sdk_event_keys(content_root)
        print(f"  已加载 {len(sdk_event_keys)} 个 SDK 已定义事件 Key")

    # Load SDK CommonDefine keys for filtering
    sdk_commondefine_keys = None
    if "commondefine" not in skip:
        print("[Phase 0.5] 加载 SDK CommonDefine 定义（用于过滤已迁移字段）...")
        sdk_commondefine_keys = load_sdk_commondefine_keys(content_root)
        print(f"  已加载 {len(sdk_commondefine_keys)} 个 SDK 已定义 CommonDefine 字段")

    print()

    # Phase 1: Lua scanning
    lua_result = LuaScanResult()
    if not ({"require", "hardpath", "globals", "config", "events", "ui", "biz"} <= skip):
        print("[Phase 1] Lua 扫描...")
        lua_result = scan_lua_directory(
            repo_root=repo_root,
            lua_globs=lua_globs,
            extra_require_prefixes=extra_require_prefixes,
            extra_asset_prefixes=extra_asset_prefixes,
            moe3c_fallback_fields=moe3c_fields,
            sdk_event_keys=sdk_event_keys,
            sdk_commondefine_keys=sdk_commondefine_keys,
        )

        if "require" in skip:
            lua_result.require_hits = []
        if "hardpath" in skip:
            lua_result.hardpath_hits = []
        if "globals" in skip:
            lua_result.global_hits = {}
        if "config" in skip:
            lua_result.config_table_hits = {}
        if "events" in skip:
            lua_result.event_key_hits = {}
        if "commondefine" in skip:
            lua_result.common_define_hits = {}
        if "ui" in skip:
            lua_result.ui_coupling_hits = []
        if "biz" in skip:
            lua_result.biz_keyword_hits = []

        print(f"  扫描完成: {lua_result.files_scanned} 文件")
        print(f"    require+继承: {len(lua_result.require_hits)}, "
              f"硬编码路径: {len(lua_result.hardpath_hits)}, "
              f"全局变量: {len(lua_result.global_hits)}")
        print(f"    Config/Tables: {len(lua_result.config_table_hits)}, "
              f"EventEnum: {len(lua_result.event_key_hits)}, "
              f"CommonDefine: {len(lua_result.common_define_hits)}, "
              f"UI: {len(lua_result.ui_coupling_hits)}, "
              f"业务关键词: {len(lua_result.biz_keyword_hits)}")
        print()

    # Phase 2: Asset scanning
    asset_result = AssetScanResult()
    if "assets" not in skip:
        print("[Phase 2] 资产 imports 扫描...")
        if args.asset_mode == "editor-mcp":
            asset_result = scan_assets_editor_mcp(
                repo_root, content_root, extra_asset_prefixes
            )
        else:
            asset_result = scan_assets_binary(
                repo_root, content_root, extra_asset_prefixes
            )
        print(f"  扫描完成: {asset_result.assets_scanned} 资产, "
              f"{len(asset_result.hits)} 外部依赖命中")
        print()

    # Phase 3: Write output
    print("[Phase 3] 写出报告...")

    write_require_csv(lua_result.require_hits, out_dir / "external_deps_lua_require.csv")
    write_hardpath_csv(lua_result.hardpath_hits, out_dir / "external_deps_lua_hardpath.csv")
    write_globals_csv(lua_result.global_hits, out_dir / "external_deps_lua_globals.csv")
    write_globals_detail_csv(lua_result.global_hits, out_dir / "external_deps_lua_globals_detail.csv", repo_root)
    write_assets_csv(asset_result.hits, out_dir / "external_deps_assets.csv")
    write_config_tables_csv(lua_result.config_table_hits, out_dir / "external_deps_config_tables.csv")
    write_event_keys_csv(lua_result.event_key_hits, out_dir / "external_deps_event_keys.csv")
    write_common_define_csv(lua_result.common_define_hits, out_dir / "external_deps_common_define.csv")
    write_ui_coupling_csv(lua_result.ui_coupling_hits, out_dir / "external_deps_ui_coupling.csv")
    write_biz_keywords_csv(lua_result.biz_keyword_hits, out_dir / "external_deps_biz_keywords.csv")
    write_markdown_report(
        lua_result, asset_result,
        out_dir / "LetsGo3C_External_Deps_Report.md",
        repo_root=str(repo_root),
        timestamp=timestamp,
    )

    elapsed = time.time() - start_time
    print(f"  耗时: {elapsed:.1f}s")

    print_summary(lua_result, asset_result, str(out_dir))


if __name__ == "__main__":
    main()
