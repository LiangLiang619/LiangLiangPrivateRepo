"""
scan_lua_refs.py - 扫描 Lua 代码中对指定 UE Blueprint 资产的引用

用法:
    python scan_lua_refs.py <BP短名> [额外搜索关键词...] [--threshold N]

示例:
    python scan_lua_refs.py BP_MainCharAvatarComponent
    python scan_lua_refs.py BP_MainCharAvatarComponent UMainCharAvatarComponent --threshold 30

功能:
    - 自动检测 Content 根目录（从 cwd 向上查找），支持从任意项目层级打开
    - 扫描 Content/LetsGo/Script/、Content/Feature/、Content/LetsGoSDK/Script/ 下的 .lua 文件
    - 匹配 BP 短名、C++ 类名、资产路径片段
    - 引用数 <= 阈值（默认 30）：输出完整表格
    - 引用数 > 阈值：输出路径分布概览 + 硬耦合引用明细 + 耦合度汇总
"""

import os
import re
import sys
from collections import defaultdict
from pathlib import Path

DEFAULT_THRESHOLD = 30

LUA_SCAN_DIRS = [
    "LetsGo/Script",
    "Feature",
    "LetsGoSDK/Script",
]

HARD_TYPES = {"实例名访问 self.Xxx", "实例名访问", "字符串常量"}
WEAK_TYPES = {"GetComponentByClass(基类类型)", "FindComponentByClass(基类类型)"}


def find_content_root(start_path=None):
    """从 start_path 向上查找包含 Content 目录的路径，返回 Content 目录的绝对路径。"""
    if start_path is None:
        start_path = Path.cwd()
    else:
        start_path = Path(start_path).resolve()

    current = start_path
    if current.name == "Content" and current.is_dir():
        return current
    content_child = current / "Content"
    if content_child.is_dir():
        return content_child

    for parent in current.parents:
        if parent.name == "Content" and parent.is_dir():
            return parent
        content_child = parent / "Content"
        if content_child.is_dir():
            return content_child

    return None


def classify_reference(line, keyword):
    """根据行内容和关键词判断引用方式。"""
    stripped = line.strip()

    if re.search(r'self\.' + re.escape(keyword), stripped):
        return "实例名访问 self.Xxx"
    if re.search(r'["\']' + re.escape(keyword) + r'["\']', stripped):
        return "字符串常量"
    if "GetComponentByClass" in stripped:
        return "GetComponentByClass(基类类型)"
    if "FindComponentByClass" in stripped:
        return "FindComponentByClass(基类类型)"
    if "UE4.UObject.Load" in stripped or "LoadObject" in stripped or "LoadAsset" in stripped:
        return "动态加载"
    if "require" in stripped:
        return "require 引用"
    if re.search(r'\.' + re.escape(keyword) + r'[:\.]', stripped):
        return "实例名访问"
    return "名称引用"


def truncate_snippet(snippet, keyword, max_len=120):
    if len(snippet) <= max_len:
        return snippet
    idx = snippet.find(keyword)
    start = max(0, idx - 40)
    end = min(len(snippet), idx + len(keyword) + 40)
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(snippet) else ""
    return prefix + snippet[start:end] + suffix


def scan_lua_files(content_root, keywords):
    """扫描 Lua 文件，返回匹配结果列表。"""
    results = []
    content_root = Path(content_root)

    for scan_dir in LUA_SCAN_DIRS:
        full_dir = content_root / scan_dir
        if not full_dir.exists():
            continue
        for lua_file in full_dir.rglob("*.lua"):
            try:
                text = lua_file.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for line_no, line in enumerate(text.splitlines(), start=1):
                for kw in keywords:
                    if kw in line:
                        rel_path = lua_file.relative_to(content_root)
                        ref_type = classify_reference(line, kw)
                        snippet = truncate_snippet(line.strip(), kw)
                        results.append({
                            "file": str(rel_path).replace("\\", "/"),
                            "line": line_no,
                            "keyword": kw,
                            "ref_type": ref_type,
                            "snippet": snippet,
                        })
                        break

    return results


def get_dir_key(file_path, depth=2):
    """取文件路径的前 depth 级目录作为分组 key。"""
    parts = Path(file_path).parts
    return "/".join(parts[:min(depth, len(parts) - 1)]) + "/"


def print_full_table(results):
    """完整表格模式（引用数 <= 阈值）。"""
    print(f"\n共找到 **{len(results)}** 处 Lua 引用。\n")
    print("| # | Lua 文件 | 行号 | 引用方式 | 引用内容摘要 |")
    print("|---|---------|------|---------|------------|")
    for i, r in enumerate(results, 1):
        snippet_escaped = r["snippet"].replace("|", "\\|")
        print(f'| {i} | `{r["file"]}` | {r["line"]} | {r["ref_type"]} | `{snippet_escaped}` |')


def print_summary_mode(results, threshold):
    """摘要模式（引用数 > 阈值）：路径分布 + 硬耦合明细。"""
    print(f"\n共找到 **{len(results)}** 处 Lua 引用（超过阈值 {threshold}，以摘要模式展示）。\n")

    # --- 路径分布 ---
    dir_counts = defaultdict(lambda: {"total": 0, "hard": 0, "weak": 0, "other": 0})
    for r in results:
        key = get_dir_key(r["file"])
        dir_counts[key]["total"] += 1
        if r["ref_type"] in HARD_TYPES:
            dir_counts[key]["hard"] += 1
        elif r["ref_type"] in WEAK_TYPES:
            dir_counts[key]["weak"] += 1
        else:
            dir_counts[key]["other"] += 1

    print("**路径分布概览**：\n")
    print("| 目录 | 总引用 | 硬耦合 | 弱耦合 | 其他 |")
    print("|------|-------|-------|-------|------|")
    for key in sorted(dir_counts.keys()):
        c = dir_counts[key]
        print(f"| `{key}` | {c['total']} | {c['hard']} | {c['weak']} | {c['other']} |")

    # --- 硬耦合引用明细 ---
    hard_refs = [r for r in results if r["ref_type"] in HARD_TYPES]
    if hard_refs:
        print(f"\n**硬耦合引用明细**（{len(hard_refs)} 处，迁移后需同步改动）：\n")
        print("| # | Lua 文件 | 行号 | 引用方式 | 引用内容摘要 |")
        print("|---|---------|------|---------|------------|")
        for i, r in enumerate(hard_refs, 1):
            snippet_escaped = r["snippet"].replace("|", "\\|")
            print(f'| {i} | `{r["file"]}` | {r["line"]} | {r["ref_type"]} | `{snippet_escaped}` |')


def print_coupling_summary(results):
    """耦合度汇总（两种模式通用）。"""
    hard_count = sum(1 for r in results if r["ref_type"] in HARD_TYPES)
    weak_count = sum(1 for r in results if r["ref_type"] in WEAK_TYPES)
    other_count = len(results) - hard_count - weak_count

    print("\n**引用耦合度汇总**：\n")
    if hard_count:
        print(f"- **硬耦合（实例名/字符串常量）**：{hard_count} 处，迁移后需同步改动")
    if weak_count:
        print(f"- **弱耦合（基类类型查找）**：{weak_count} 处，迁移不受影响")
    if other_count:
        print(f"- **其他引用**：{other_count} 处，需逐条确认")


def main():
    if len(sys.argv) < 2:
        print("用法: python scan_lua_refs.py <BP短名> [额外关键词...] [--threshold N]")
        print("示例: python scan_lua_refs.py BP_MainCharAvatarComponent UMainCharAvatarComponent --threshold 30")
        sys.exit(1)

    threshold = DEFAULT_THRESHOLD
    keywords = []
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--threshold" and i + 1 < len(sys.argv):
            threshold = int(sys.argv[i + 1])
            i += 2
        else:
            keywords.append(sys.argv[i])
            i += 1

    if not keywords:
        print("错误：至少提供一个搜索关键词。")
        sys.exit(1)

    content_root = find_content_root()
    if content_root is None:
        print("错误：无法自动检测 Content 根目录。请在 UE 项目目录下运行此脚本。")
        print(f"当前工作目录: {Path.cwd()}")
        sys.exit(1)

    print(f"Content 根目录: {content_root}")
    print(f"搜索关键词: {keywords}")
    print(f"展示阈值: {threshold}")
    print(f"扫描目录:")
    for d in LUA_SCAN_DIRS:
        full = content_root / d
        status = "✓" if full.exists() else "✗ (不存在)"
        print(f"  - {d}/ {status}")

    results = scan_lua_files(content_root, keywords)

    if not results:
        print("\n未找到任何 Lua 引用。\n")
        return

    if len(results) <= threshold:
        print_full_table(results)
    else:
        print_summary_mode(results, threshold)

    print_coupling_summary(results)


if __name__ == "__main__":
    main()
