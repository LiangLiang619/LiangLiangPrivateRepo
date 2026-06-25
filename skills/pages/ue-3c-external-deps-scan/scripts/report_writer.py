"""
report_writer.py — Write 8 CSV files + 1 Markdown overview report.
"""

import csv
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from lua_scanner import (
    LuaScanResult, RequireHit, HardpathHit, GlobalHit, DynamicRequireWarning,
    ConfigTableHit, EventKeyHit, UICouplingHit, BizKeywordHit, CommonDefineHit,
)
from asset_scanner import AssetScanResult, AssetDepHit


def _ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def write_require_csv(hits: List[RequireHit], out_path: Path):
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["file", "line", "require_module", "category", "suggested_action"])
        for h in hits:
            writer.writerow([h.file, h.line, h.require_module, h.category, h.suggested_action])


def write_hardpath_csv(hits: List[HardpathHit], out_path: Path):
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["file", "line", "hardcoded_path", "category", "suggested_action"])
        for h in hits:
            writer.writerow([h.file, h.line, h.hardcoded_path, h.category, h.suggested_action])


def write_globals_csv(hits: Dict[str, GlobalHit], out_path: Path):
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["global_expr", "usage_count", "files", "suggested_action"])
        for gh in hits.values():
            files_str = "|".join(gh.locations)
            writer.writerow([gh.global_expr, gh.usage_count, files_str, gh.suggested_action])


def write_assets_csv(hits: List[AssetDepHit], out_path: Path):
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["asset_path", "external_dep_path", "category", "via_redirector_from"])
        for h in hits:
            writer.writerow([h.asset_path, h.external_dep_path, h.category, h.via_redirector_from])


def write_config_tables_csv(hits: Dict[str, ConfigTableHit], out_path: Path):
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["table_name", "access_type", "usage_count", "files", "status"])
        for ct in hits.values():
            files_str = "|".join(ct.files)
            writer.writerow([ct.table_name, ct.access_type, ct.usage_count, files_str, "待验证"])


def write_event_keys_csv(hits: Dict[str, EventKeyHit], out_path: Path):
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["event_key", "usage_type", "usage_count", "files", "status"])
        for ek in hits.values():
            files_str = "|".join(ek.files)
            writer.writerow([ek.event_key, ek.usage_type, ek.usage_count, files_str, "待验证"])


def write_ui_coupling_csv(hits: List[UICouplingHit], out_path: Path):
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["file", "line", "call_type", "window_name", "suggested_action"])
        for h in hits:
            writer.writerow([h.file, h.line, h.call_type, h.window_name, h.suggested_action])


def write_biz_keywords_csv(hits: List[BizKeywordHit], out_path: Path):
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["file", "line", "keyword", "context", "suggested_action"])
        for h in hits:
            writer.writerow([h.file, h.line, h.keyword, h.context, h.suggested_action])


def write_common_define_csv(hits: Dict[str, CommonDefineHit], out_path: Path):
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["define_name", "usage_count", "files", "status"])
        for cd in hits.values():
            files_str = "|".join(cd.files)
            writer.writerow([cd.define_name, cd.usage_count, files_str, "待验证"])


def write_globals_detail_csv(hits: Dict[str, GlobalHit], out_path: Path, repo_root: Path):
    """Write one row per usage location with source code (detail view for line-by-line fixing)."""
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["file", "line", "global_expr", "code", "suggested_action"])
        for gh in hits.values():
            for loc in gh.locations:
                parts = loc.rsplit(":", 1)
                file_path = parts[0] if len(parts) == 2 else loc
                line_no = parts[1] if len(parts) == 2 else ""
                code = _read_line(repo_root / file_path, int(line_no)) if line_no else ""
                writer.writerow([file_path, line_no, gh.global_expr, code, gh.suggested_action])


def _read_line(filepath: Path, line_no: int) -> str:
    """Read a single line from file, return stripped content."""
    try:
        raw = filepath.read_bytes()
        if raw.startswith(b'\xef\xbb\xbf'):
            raw = raw[3:]
        lines = raw.decode("utf-8", errors="replace").split("\n")
        if 0 < line_no <= len(lines):
            return lines[line_no - 1].strip()
    except (OSError, UnicodeDecodeError):
        pass
    return ""


def write_markdown_report(
    lua_result: LuaScanResult,
    asset_result: AssetScanResult,
    out_path: Path,
    repo_root: str,
    timestamp: str,
):
    lines = []
    lines.append(f"# LetsGo3C 外部依赖扫描报告")
    lines.append("")
    lines.append(f"- **扫描时间**: {timestamp}")
    lines.append(f"- **仓库根目录**: `{repo_root}`")
    lines.append("")

    # Summary
    req_cats = {}
    for h in lua_result.require_hits:
        req_cats[h.category] = req_cats.get(h.category, 0) + 1

    lines.append("## 汇总")
    lines.append("")
    lines.append("| 类别 | 数量 | 严重等级 |")
    lines.append("|------|------|----------|")
    req_total = len(lua_result.require_hits)
    cat_detail = ", ".join(f"{k}={v}" for k, v in sorted(req_cats.items()))
    lines.append(f"| Lua require + UE4.Class 外部引用 | {req_total} ({cat_detail}) | HIGH |")
    lines.append(f"| Lua 硬编码外部路径 | {len(lua_result.hardpath_hits)} | MEDIUM |")

    global_moe3c = sum(1 for k in lua_result.global_hits if k.startswith("MOE_3C."))
    global_moe = sum(1 for k in lua_result.global_hits if k.startswith("_MOE."))
    global_g = sum(1 for k in lua_result.global_hits if k.startswith("_G."))
    lines.append(f"| Lua 隐式全局耦合 | {len(lua_result.global_hits)} unique (_MOE.* {global_moe}, MOE_3C fallback {global_moe3c}, _G.* {global_g}) | HIGH |")
    lines.append(f"| UE 资产外部 imports | {len(asset_result.hits)} | MEDIUM |")
    lines.append(f"| Config/Tables 待审计 | {len(lua_result.config_table_hits)} 表名 | AUDIT |")
    lines.append(f"| EventEnum Key 待审计 | {len(lua_result.event_key_hits)} 事件 | AUDIT |")
    lines.append(f"| CommonDefine 待审计 | {len(lua_result.common_define_hits)} 字段 | AUDIT |")
    lines.append(f"| UI/WindowName 耦合 | {len(lua_result.ui_coupling_hits)} 处调用 | HIGH |")
    lines.append(f"| 业务关键词命中 | {len(lua_result.biz_keyword_hits)} 处 | HIGH |")
    lines.append("")

    # Top 20 requires
    if lua_result.require_hits:
        lines.append("## Top 20 外部 require / UE4.Class 继承")
        lines.append("")
        lines.append("| module | category | file:line | action |")
        lines.append("|--------|----------|-----------|--------|")
        for h in lua_result.require_hits[:20]:
            lines.append(f"| `{h.require_module}` | {h.category} | {h.file}:{h.line} | {h.suggested_action} |")
        lines.append("")

    # Top 20 globals
    if lua_result.global_hits:
        lines.append("## Top 20 全局变量耦合（按使用频次）")
        lines.append("")
        lines.append("| 表达式 | 使用次数 | 示例位置 | 建议 |")
        lines.append("|--------|----------|----------|------|")
        sorted_globals = sorted(lua_result.global_hits.values(), key=lambda g: -g.usage_count)
        for gh in sorted_globals[:20]:
            example = gh.locations[0] if gh.locations else ""
            lines.append(f"| `{gh.global_expr}` | {gh.usage_count} | {example} | {gh.suggested_action} |")
        lines.append("")

    # Config/Tables audit
    if lua_result.config_table_hits:
        lines.append("## Config/Tables 注册来源待审计")
        lines.append("")
        lines.append("> 以下表名通过 `MOE_3C.Config.X` / `MOE_3C.Tables.X` 访问，需验证注册方是否在 SDK/3C 内。")
        lines.append("")
        lines.append("| 表名 | 类型 | 使用次数 | 涉及文件 |")
        lines.append("|------|------|----------|----------|")
        for ct in list(lua_result.config_table_hits.values())[:30]:
            files_short = ", ".join(ct.files[:3])
            if len(ct.files) > 3:
                files_short += f" (+{len(ct.files) - 3})"
            lines.append(f"| `{ct.table_name}` | {ct.access_type} | {ct.usage_count} | {files_short} |")
        lines.append("")

    # Event keys audit
    if lua_result.event_key_hits:
        lines.append("## EventEnum Key 来源待审计")
        lines.append("")
        lines.append("> 需确认每个事件 Key 的定义位置（SDK/3C = OK, GlobalEvents.lua = 需迁入 LetsGo3CEvents 或下沉业务子类）。")
        lines.append("")
        lines.append("| 事件 Key | 使用次数 | 涉及文件 |")
        lines.append("|----------|----------|----------|")
        for ek in list(lua_result.event_key_hits.values())[:30]:
            files_short = ", ".join(ek.files[:3])
            if len(ek.files) > 3:
                files_short += f" (+{len(ek.files) - 3})"
            lines.append(f"| `{ek.event_key}` | {ek.usage_count} | {files_short} |")
        lines.append("")

    # CommonDefine audit
    if lua_result.common_define_hits:
        lines.append("## CommonDefine 定义来源待审计")
        lines.append("")
        lines.append("> 以下字段通过 `MOE_3C.CommonDefine.X` 访问，需验证定义方是否在 SDK（LetsGoSDKCommonDefine）内。")
        lines.append("")
        lines.append("| 字段名 | 使用次数 | 涉及文件 |")
        lines.append("|--------|----------|----------|")
        for cd in list(lua_result.common_define_hits.values())[:30]:
            files_short = ", ".join(cd.files[:3])
            if len(cd.files) > 3:
                files_short += f" (+{len(cd.files) - 3})"
            lines.append(f"| `{cd.define_name}` | {cd.usage_count} | {files_short} |")
        lines.append("")

    # UI coupling
    if lua_result.ui_coupling_hits:
        lines.append("## UI/WindowName 耦合（3C 基类原则上不应包含）")
        lines.append("")
        lines.append("| file | line | 调用类型 | 窗口名 |")
        lines.append("|------|------|----------|--------|")
        for h in lua_result.ui_coupling_hits[:30]:
            lines.append(f"| {h.file} | {h.line} | {h.call_type} | {h.window_name} |")
        lines.append("")

    # Business keywords
    if lua_result.biz_keyword_hits:
        lines.append("## 业务关键词命中（应下沉到业务子类）")
        lines.append("")
        lines.append("> 命中关键词: Farm / Arena / UGC / Chase / Chest / Home / StarP / Community / Lobby / Commercial")
        lines.append("")
        lines.append("| file | line | 关键词 | 上下文 |")
        lines.append("|------|------|--------|--------|")
        for h in lua_result.biz_keyword_hits[:30]:
            lines.append(f"| {h.file} | {h.line} | {h.keyword} | {h.context} |")
        lines.append("")

    # Top 20 asset deps
    if asset_result.hits:
        lines.append("## Top 20 资产外部依赖")
        lines.append("")
        lines.append("| 本仓库资产 | 外部依赖 | category |")
        lines.append("|-----------|---------|----------|")
        for h in asset_result.hits[:20]:
            lines.append(f"| `{h.asset_path}` | `{h.external_dep_path}` | {h.category} |")
        lines.append("")

    # Dynamic require warnings
    if lua_result.dynamic_warnings:
        lines.append("## 动态 require 告警（无法静态分析）")
        lines.append("")
        lines.append("| file | line | expression |")
        lines.append("|------|------|------------|")
        for w in lua_result.dynamic_warnings:
            lines.append(f"| {w.file} | {w.line} | `{w.expression}` |")
        lines.append("")

    # Priority suggestions
    lines.append("## 修复优先级建议")
    lines.append("")
    lines.append("1. **高优先级**：`require` / `UE4.Class` 外部引用 — 直接阻塞仓库独立运行")
    lines.append("2. **高优先级**：业务关键词命中 — 表示业务逻辑残留在 3C 基类")
    lines.append("3. **高优先级**：UI/WindowName 耦合 — 3C 基类不应感知 UI")
    lines.append("4. **高优先级**：`_MOE.*` / MOE_3C fallback 全局耦合 — 运行期隐式依赖")
    lines.append("5. **中优先级**：UE 资产外部 imports — 影响打包独立性")
    lines.append("6. **中优先级**：硬编码资产路径 — 运行时才触发，可后续批量替换")
    lines.append("7. **审计项**：EventEnum Key / Config/Tables — 需人工确认定义归属")
    lines.append("")

    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))


def print_summary(lua_result: LuaScanResult, asset_result: AssetScanResult, out_dir: str):
    req_cats = {}
    for h in lua_result.require_hits:
        req_cats[h.category] = req_cats.get(h.category, 0) + 1
    cat_str = ", ".join(f"{k}={v}" for k, v in sorted(req_cats.items()))

    global_moe = sum(1 for k in lua_result.global_hits if k.startswith("_MOE."))
    global_moe3c = sum(1 for k in lua_result.global_hits if k.startswith("MOE_3C."))
    global_g = sum(1 for k in lua_result.global_hits if k.startswith("_G."))

    print()
    print("=" * 60)
    print("       LetsGo3C 外部依赖扫描简报")
    print("=" * 60)
    print(f"扫描 Lua: {lua_result.files_scanned} 文件")
    print(f"  require + UE4.Class 外部命中: {len(lua_result.require_hits)} ({cat_str})")
    print(f"  硬编码 /Game/ 外部路径: {len(lua_result.hardpath_hits)}")
    print(f"  隐式全局耦合: {len(lua_result.global_hits)} unique "
          f"(_MOE.* {global_moe}, MOE_3C fallback {global_moe3c}, _G.* {global_g})")
    print(f"  Config/Tables 待审计: {len(lua_result.config_table_hits)} 表名")
    print(f"  EventEnum Key 待审计: {len(lua_result.event_key_hits)} 事件")
    print(f"  CommonDefine 待审计: {len(lua_result.common_define_hits)} 字段")
    print(f"  UI/WindowName 耦合: {len(lua_result.ui_coupling_hits)} 处")
    print(f"  业务关键词命中: {len(lua_result.biz_keyword_hits)} 处")
    print(f"扫描资产: {asset_result.assets_scanned} .uasset")
    print(f"  外部 imports: {len(asset_result.hits)} 处 "
          f"(跟随 ObjectRedirector {asset_result.redirector_follows} 次)")
    if asset_result.parse_errors:
        print(f"  解析失败: {asset_result.parse_errors}")
    if lua_result.dynamic_warnings:
        print(f"  动态 require 告警: {len(lua_result.dynamic_warnings)}")
    print(f"输出: {out_dir}")
    print("=" * 60)
    print()
