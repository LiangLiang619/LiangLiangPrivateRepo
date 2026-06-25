# -*- coding: utf-8 -*-
"""
Recursive UE asset dependency scanner.

输入：
  - 一份 CSV，至少含两列：
      外部资产名, 外部资产完整路径
    可以是【直接依赖】CSV，也可以是任意自定义的「根资产」列表。
  - Content root（默认 F:\\F3\\LetsGoDevelop\\LetsGo\\Content）
  - 可选：3CAssetsMigrationRecords.md（用于把 /Game/LetsGo3C/... 回写为 /Game/LetsGo/... 显示路径）
  - 可选：--exclude 逗号分隔的根资产名（默认空）

输出：
  18 列 CSV，列名固定为：
    外部资产名, 外部资产完整路径, 引用层级, 引用链路（被谁依赖了）, 当前进度,
    搬迁方式, 负责人, ProjectT资产路径（被该资产依赖）, 直接依赖外部资产数,
    直接依赖外部资产列表, 递归依赖外部资产总数, 递归依赖外部资产列表,
    玩法依赖数量, 全部引用玩法列表, 资产父目录, 资产子目录, 引用类型, 是否需要

依赖图构建：
  1) imports 表中 class_name=Package 的硬引用
  2) Names 表中以 /Game/ 开头的 FName 字符串（软引用 / SoftObjectPath / 类引用）
  跟随 ObjectRedirector 到迁移后的真实 .uasset。

过滤规则：
  - 只保留 /Game/ 下的资产
  - 默认排除 /Game/Feature/ProjectT/ 子树（可用 --keep-projectt 关闭）
  - /Script/、/Engine/ 等忽略
"""

import argparse
import csv
import importlib
import json
import os
import sys
import time
from collections import Counter, deque
from pathlib import Path

# csv 大字段
csv.field_size_limit(2**31 - 1)

# ---------------------------------------------------------------------------
# 定位 uasset_mcp（提供 UAssetParser）
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
    # 退而求其次：直接尝试 import（依赖运行解释器自身有 uasset_mcp）
    try:
        module = importlib.import_module("src.uasset_parser")
        return module.UAssetParser
    except ImportError as e:
        raise SystemExit(
            "[fatal] 未找到 uasset_mcp。请确认任一前提：\n"
            "  - 当前 Python 已 pip install uasset_mcp；或\n"
            "  - 已通过 uvx uasset_mcp 安装（项目 F4 默认路径会被自动发现）；或\n"
            "  - 设置 UASSET_MCP_SITE_PACKAGES 环境变量指向其 site-packages。\n"
            f"原始错误: {e}"
        )


UAssetParser = _import_uasset_parser()

OUTPUT_COLS = [
    "外部资产名",
    "外部资产完整路径",
    "引用层级",
    "引用链路（被谁依赖了）",
    "当前进度",
    "搬迁方式",
    "负责人",
    "ProjectT资产路径（被该资产依赖）",
    "直接依赖外部资产数",
    "直接依赖外部资产列表",
    "递归依赖外部资产总数",
    "递归依赖外部资产列表",
    "玩法依赖数量",
    "全部引用玩法列表",
    "资产父目录",
    "资产子目录",
    "引用类型",
    "是否需要",
]


def asset_short_name(path):
    return path.rsplit("/", 1)[-1] if "/" in path else path


def parse_migration_record(md_path):
    rev = {}
    if not md_path or not os.path.isfile(md_path):
        return rev
    with open(md_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line.startswith("|") or "源路径" in line or "---" in line:
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) < 4:
                continue
            src, dst = cells[2], cells[3]
            if src.startswith("/Game/") and dst.startswith("/Game/"):
                rev[dst] = src
    return rev


def package_to_uasset(pkg_path, content_root):
    rel = pkg_path[len("/Game/"):]
    return os.path.join(content_root, rel.replace("/", os.sep) + ".uasset")


class DepScanner:
    def __init__(self, content_root, migration_reverse, cache_file, keep_projectt):
        self.content_root = content_root
        self.migration_reverse = migration_reverse  # LetsGo3C → LetsGo
        self.migration_forward = {v: k for k, v in migration_reverse.items()}
        self.cache_file = cache_file
        self.keep_projectt = keep_projectt
        self.cache = {}
        self.unresolved = set()
        if cache_file and os.path.isfile(cache_file):
            try:
                self.cache = json.load(open(cache_file, encoding="utf-8"))
                print(f"  [cache] loaded {len(self.cache)} entries from {cache_file}")
            except Exception as e:
                print(f"  [cache] warning: failed to load cache ({e}); starting empty")

    def to_display(self, pkg_path):
        return self.migration_reverse.get(pkg_path, pkg_path)

    def is_external(self, pkg_path):
        if not pkg_path.startswith("/Game/"):
            return False
        if not self.keep_projectt and pkg_path.startswith("/Game/Feature/ProjectT/"):
            return False
        return True

    def resolve_uasset(self, pkg_path):
        """跟随 redirector 到实际 .uasset 路径。最多 5 跳。"""
        seen = set()
        cur = pkg_path
        for _ in range(5):
            if cur in seen:
                return None
            seen.add(cur)
            ufile = package_to_uasset(cur, self.content_root)
            if not os.path.isfile(ufile):
                # 已迁移的 LetsGo 原路径：跳到 3C 位置
                if cur in self.migration_forward:
                    cur = self.migration_forward[cur]
                    continue
                return None
            try:
                parser = UAssetParser(ufile)
                exports = parser.exports
                classes = [(e.class_name or "") for e in exports]
                non_meta = [c for c in classes if c and c != "MetaData"]
                if non_meta and all(c == "ObjectRedirector" for c in non_meta):
                    pkgs = [
                        i.object_name for i in parser.imports
                        if (i.class_name or "") == "Package"
                        and (i.object_name or "").startswith("/Game/")
                    ]
                    if pkgs:
                        cur = pkgs[0]
                        continue
                return ufile
            except Exception:
                return None
        return None

    def get_deps(self, pkg_path):
        display_key = self.to_display(pkg_path)
        if display_key in self.cache:
            return self.cache[display_key]

        ufile = self.resolve_uasset(pkg_path)
        if ufile is None:
            self.unresolved.add(pkg_path)
            self.cache[display_key] = []
            return []

        try:
            parser = UAssetParser(ufile)
            hard_pkgs = [
                i.object_name for i in parser.imports
                if (i.class_name or "") == "Package"
            ]
            soft_pkgs = []
            for n in parser.names:
                name = (n.name or "").rstrip("\x00")
                if not name.startswith("/Game/"):
                    continue
                soft_pkgs.append(name.split(".", 1)[0])
        except Exception as e:
            print(f"  [warn] parse failed: {ufile} ({e})")
            self.cache[display_key] = []
            return []

        deps = []
        seen = set()
        for p in list(hard_pkgs) + soft_pkgs:
            if not p.startswith("/Game/"):
                continue
            disp = self.to_display(p)
            if not self.is_external(disp):
                continue
            if disp == display_key or disp in seen:
                continue
            seen.add(disp)
            deps.append(disp)
        self.cache[display_key] = deps
        return deps

    def save_cache(self):
        if not self.cache_file:
            return
        Path(self.cache_file).parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_file, "w", encoding="utf-8") as fh:
            json.dump(self.cache, fh, ensure_ascii=False, indent=0)
        print(f"  [cache] saved {len(self.cache)} entries to {self.cache_file}")


def derive_parent_subdir(path):
    parts = path.split("/")
    if len(parts) >= 5:
        return parts[3], parts[4]
    if len(parts) >= 4:
        return parts[3], ""
    return "", ""


def bfs(scanner, roots, exclude_names, log_every=200):
    visited = {}
    direct_deps_map = {}
    queue = deque()
    for name, disp_path in roots:
        if name in exclude_names or disp_path in visited:
            continue
        visited[disp_path] = (0, [name])
        queue.append(disp_path)
    t0 = time.time()
    processed = 0
    while queue:
        cur = queue.popleft()
        processed += 1
        cur_depth, cur_chain = visited[cur]
        deps = scanner.get_deps(cur)
        direct_deps_map[cur] = deps
        for kid in deps:
            if kid in visited:
                continue
            kid_name = asset_short_name(kid)
            if kid_name in exclude_names:
                continue
            visited[kid] = (cur_depth + 1, cur_chain + [kid_name])
            queue.append(kid)
        if processed % log_every == 0:
            print(
                f"  [bfs] processed={processed}, queued={len(queue)},"
                f" visited={len(visited)}, elapsed={time.time()-t0:.1f}s"
            )
    print(
        f"  [bfs] done. processed={processed}, visited={len(visited)},"
        f" elapsed={time.time()-t0:.1f}s"
    )
    return visited, direct_deps_map


def build_recursive_deps(direct_deps_map):
    cache = {}

    def rec(node):
        if node in cache:
            return cache[node]
        result = set()
        seen = {node}
        stack = [node]
        while stack:
            cur = stack.pop()
            for kid in direct_deps_map.get(cur, []):
                if kid in seen:
                    continue
                seen.add(kid)
                result.add(kid)
                stack.append(kid)
        cache[node] = result
        return result

    return {n: rec(n) for n in direct_deps_map}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root-csv", required=True, help="包含「外部资产名/外部资产完整路径」两列的根资产 CSV")
    ap.add_argument("--output-csv", required=True)
    ap.add_argument("--content-root", default=r"F:\F3\LetsGoDevelop\LetsGo\Content")
    ap.add_argument(
        "--migration-record",
        default=r"F:\F3\LetsGoDevelop\LetsGo\Content\LetsGo3C\Migration\AssetsMigration\3CAssetsMigrationRecords.md",
    )
    ap.add_argument("--exclude", default="", help="逗号分隔的排除直接资产名")
    ap.add_argument(
        "--cache-file",
        default=r"F:\F3\LetsGoDevelop\LetsGo\Content\.cursor\skills\ue-recursive-deps-scan\dep_cache.json",
    )
    ap.add_argument("--keep-projectt", action="store_true", help="保留 /Game/Feature/ProjectT/ 子树（默认排除）")
    args = ap.parse_args()

    exclude_names = {n.strip() for n in args.exclude.split(",") if n.strip()}

    print(f"[1/6] 读取迁移记录: {args.migration_record}")
    migration_reverse = parse_migration_record(args.migration_record)
    print(f"      解析到 {len(migration_reverse)} 条 LetsGo3C→LetsGo 反向映射")

    print(f"[2/6] 读取根 CSV: {args.root_csv}")
    with open(args.root_csv, encoding="utf-8-sig", newline="") as fh:
        rows = [r for r in csv.DictReader(fh) if r.get("外部资产名") and r.get("外部资产完整路径")]
    roots = [(r["外部资产名"], r["外部资产完整路径"]) for r in rows]
    allowed = [n for n, _ in roots if n not in exclude_names]
    print(f"      root rows: {len(roots)} ; allowed: {len(allowed)} ; exclude: {sorted(exclude_names) or '(none)'}")

    print(f"[3/6] 初始化解析器（content_root = {args.content_root}）")
    scanner = DepScanner(args.content_root, migration_reverse, args.cache_file, args.keep_projectt)

    print("[4/6] 真实 BFS（解析 .uasset 文件）")
    visited, direct_deps_map = bfs(scanner, roots, exclude_names)
    scanner.save_cache()
    if scanner.unresolved:
        print(f"      警告：{len(scanner.unresolved)} 个 package 路径未找到 .uasset（按叶子处理）")

    print("[5/6] 计算每个节点的递归依赖闭包")
    rec_map = build_recursive_deps(direct_deps_map)

    print(f"[6/6] 写出 CSV: {args.output_csv}")
    direct_paths = {disp for n, disp in roots if n not in exclude_names}
    indirect_paths = sorted(
        (p for p in visited if p not in direct_paths),
        key=lambda p: (visited[p][0], p),
    )

    depth_dist = Counter()
    out_path = Path(args.output_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=OUTPUT_COLS, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        for p in indirect_paths:
            depth, chain_names = visited[p]
            chain_str = " -> ".join(chain_names[:-1]) if len(chain_names) > 1 else (
                chain_names[0] if chain_names else ""
            )
            parent_dir, sub_dir = derive_parent_subdir(p)
            d_deps = direct_deps_map.get(p, [])
            r_deps = sorted(rec_map.get(p, set()))
            writer.writerow({
                "外部资产名": asset_short_name(p),
                "外部资产完整路径": p,
                "引用层级": f"间接引用(深度{depth})",
                "引用链路（被谁依赖了）": chain_str,
                "当前进度": "",
                "搬迁方式": "",
                "负责人": "",
                "ProjectT资产路径（被该资产依赖）": "",
                "直接依赖外部资产数": str(len(d_deps)),
                "直接依赖外部资产列表": " | ".join(d_deps),
                "递归依赖外部资产总数": str(len(r_deps)),
                "递归依赖外部资产列表": " | ".join(r_deps),
                "玩法依赖数量": "",
                "全部引用玩法列表": "",
                "资产父目录": parent_dir,
                "资产子目录": sub_dir,
                "引用类型": "serialized",
                "是否需要": "□",
            })
            depth_dist[depth] += 1

    print(f"      深度分布: {dict(sorted(depth_dist.items()))}")
    print(f"完成，已写入 {len(indirect_paths)} 行 → {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
