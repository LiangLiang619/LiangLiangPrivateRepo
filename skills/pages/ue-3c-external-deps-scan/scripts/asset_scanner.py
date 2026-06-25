"""
asset_scanner.py — Scan .uasset files for external dependencies.

Two modes:
  - binary (default): Directly parse .uasset using uasset_mcp.UAssetParser
  - editor-mcp: Use UE Editor MCP batch API (editor.get_asset_dependencies)
"""

import importlib
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Whitelist
# ---------------------------------------------------------------------------

ASSET_WHITELIST_PREFIXES = (
    "/Game/LetsGo3C/",
    "/Game/LetsGoSDK/",
    "/Game/Engine/",
    "/Game/Developers/",
)

ASSET_IGNORE_PREFIXES = (
    "/Script/",
    "/Engine/",
    "/Memory/",
    "/Paper2D/",
    "/Niagara/",
)


def _is_whitelisted(path: str, extra: Tuple[str, ...] = ()) -> bool:
    for prefix in ASSET_IGNORE_PREFIXES:
        if path.startswith(prefix):
            return True
    all_prefixes = ASSET_WHITELIST_PREFIXES + extra
    for prefix in all_prefixes:
        if path.startswith(prefix):
            return True
    return False


def classify_asset_dep(path: str) -> str:
    if path.startswith("/Game/Feature/ProjectT/") or path.startswith("/Game/ProjectT/"):
        return "ProjectT"
    if path.startswith("/Game/LetsGo/"):
        return "LetsGo"
    if path.startswith("/Game/Feature/"):
        return "Feature"
    return "Other"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class AssetDepHit:
    asset_path: str
    external_dep_path: str
    category: str
    via_redirector_from: str = ""


@dataclass
class AssetScanResult:
    hits: List[AssetDepHit] = field(default_factory=list)
    assets_scanned: int = 0
    redirector_follows: int = 0
    parse_errors: int = 0


# ---------------------------------------------------------------------------
# UAssetParser loader (same logic as ue-recursive-deps-scan)
# ---------------------------------------------------------------------------

_UAssetParser = None


def _get_parser_class():
    global _UAssetParser
    if _UAssetParser is not None:
        return _UAssetParser

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
                _UAssetParser = module.UAssetParser
                return _UAssetParser
            except ImportError:
                continue
    try:
        module = importlib.import_module("src.uasset_parser")
        _UAssetParser = module.UAssetParser
        return _UAssetParser
    except ImportError as e:
        raise RuntimeError(
            "[fatal] 未找到 uasset_mcp。请确认：\n"
            "  - pip install uasset_mcp；或\n"
            "  - 设置 UASSET_MCP_SITE_PACKAGES 环境变量。\n"
            f"原始错误: {e}"
        )


# ---------------------------------------------------------------------------
# ObjectRedirector detection + follow
# ---------------------------------------------------------------------------


def _is_redirector(parser) -> bool:
    """Check if all non-MetaData exports are ObjectRedirector."""
    classes = [(e.class_name or "") for e in parser.exports]
    non_meta = [c for c in classes if c and c != "MetaData"]
    return bool(non_meta) and all(c == "ObjectRedirector" for c in non_meta)


def _follow_redirector(parser) -> Optional[str]:
    """Get redirect target package path from imports."""
    for imp in parser.imports:
        if (imp.class_name or "") == "Package":
            obj = imp.object_name or ""
            if obj.startswith("/Game/"):
                return obj
    return None


def resolve_asset(uasset_path: Path, content_root: Path, max_hops: int = 5) -> Tuple[Optional[Path], str]:
    """
    Resolve a .uasset, following ObjectRedirectors.
    Returns (resolved_path_or_None, redirector_source_if_followed).
    """
    UAssetParser = _get_parser_class()
    original_pkg = ""
    cur_path = uasset_path
    for hop in range(max_hops):
        if not cur_path.is_file():
            return None, ""
        try:
            parser = UAssetParser(str(cur_path))
        except Exception:
            return None, ""
        if _is_redirector(parser):
            target_pkg = _follow_redirector(parser)
            if not target_pkg:
                return None, ""
            if hop == 0:
                rel = str(uasset_path.relative_to(content_root)).replace("\\", "/")
                original_pkg = f"/Game/{rel}".replace(".uasset", "")
            rel_target = target_pkg[len("/Game/"):]
            cur_path = content_root / (rel_target.replace("/", os.sep) + ".uasset")
            continue
        return cur_path, original_pkg
    return None, ""


# ---------------------------------------------------------------------------
# Binary mode scanner
# ---------------------------------------------------------------------------


def _extract_external_deps(
    uasset_path: Path,
    content_root: Path,
    extra_whitelist: Tuple[str, ...] = (),
) -> Tuple[List[str], bool, str]:
    """
    Parse a single .uasset and return external /Game/ dependencies.
    Returns (dep_paths, is_redirector_followed, redirector_source).
    """
    UAssetParser = _get_parser_class()
    resolved_path, redir_source = resolve_asset(uasset_path, content_root)
    if resolved_path is None:
        return [], False, ""

    try:
        parser = UAssetParser(str(resolved_path))
    except Exception:
        return [], False, ""

    deps: Set[str] = set()

    # Hard refs from imports table
    for imp in parser.imports:
        if (imp.class_name or "") == "Package":
            obj = imp.object_name or ""
            if obj.startswith("/Game/"):
                deps.add(obj)

    # Soft refs from FName table
    for n in parser.names:
        name = (n.name or "").rstrip("\x00")
        if name.startswith("/Game/"):
            pkg = name.split(".", 1)[0]
            deps.add(pkg)

    # Filter
    external = []
    for dep in deps:
        if _is_whitelisted(dep, extra_whitelist):
            continue
        # Skip self-reference
        rel = str(resolved_path.relative_to(content_root)).replace("\\", "/")
        self_pkg = f"/Game/{rel}".replace(".uasset", "")
        if dep == self_pkg:
            continue
        external.append(dep)

    return external, bool(redir_source), redir_source


def scan_assets_binary(
    repo_root: Path,
    content_root: Path,
    extra_whitelist: Tuple[str, ...] = (),
) -> AssetScanResult:
    """Scan all .uasset under repo_root/Assets/ using binary parsing."""
    result = AssetScanResult()

    # Ensure parser is available before scanning
    try:
        _get_parser_class()
    except RuntimeError as e:
        print(str(e))
        return result

    assets_dir = repo_root / "Assets"
    if not assets_dir.is_dir():
        print(f"  [warn] Assets directory not found: {assets_dir}")
        return result

    uasset_files = list(assets_dir.rglob("*.uasset"))
    result.assets_scanned = len(uasset_files)

    for ufile in uasset_files:
        try:
            ext_deps, followed, redir_src = _extract_external_deps(
                ufile, content_root, extra_whitelist
            )
        except Exception as e:
            result.parse_errors += 1
            continue

        if followed:
            result.redirector_follows += 1

        rel_path = str(ufile.relative_to(repo_root)).replace("\\", "/")
        for dep in ext_deps:
            result.hits.append(AssetDepHit(
                asset_path=rel_path,
                external_dep_path=dep,
                category=classify_asset_dep(dep),
                via_redirector_from=redir_src,
            ))

    return result


# ---------------------------------------------------------------------------
# Editor MCP mode (placeholder — requires UE running + MCP server)
# ---------------------------------------------------------------------------


def scan_assets_editor_mcp(
    repo_root: Path,
    content_root: Path,
    extra_whitelist: Tuple[str, ...] = (),
) -> AssetScanResult:
    """
    Scan assets using UE Editor MCP batch API.
    This requires the UE editor to be running with the MCP plugin active.
    Uses editor.get_asset_dependencies action via ue_batch.
    """
    result = AssetScanResult()

    assets_dir = repo_root / "Assets"
    if not assets_dir.is_dir():
        print(f"  [warn] Assets directory not found: {assets_dir}")
        return result

    uasset_files = list(assets_dir.rglob("*.uasset"))
    result.assets_scanned = len(uasset_files)

    # Convert file paths to /Game/ paths
    asset_game_paths = []
    for ufile in uasset_files:
        rel = str(ufile.relative_to(content_root)).replace("\\", "/")
        game_path = f"/Game/{rel}".replace(".uasset", "")
        asset_game_paths.append((ufile, game_path))

    # Build batch actions (25 assets per batch = 25 actions for deps only)
    BATCH_SIZE = 25
    all_deps_raw = {}

    for batch_start in range(0, len(asset_game_paths), BATCH_SIZE):
        batch = asset_game_paths[batch_start:batch_start + BATCH_SIZE]
        actions = []
        for _, game_path in batch:
            actions.append({
                "action_id": "editor.get_asset_dependencies",
                "params": {"asset_path": game_path},
            })

        # NOTE: This would call MCP tool `ue_batch` — in skill context,
        # the AI agent handles this call. We store the action structure
        # for the agent to execute.
        print(f"  [editor-mcp] Batch {batch_start // BATCH_SIZE + 1}: "
              f"{len(actions)} actions (assets {batch_start+1}-{batch_start+len(batch)})")
        print("  [editor-mcp] NOTE: Editor MCP mode requires the AI agent to "
              "call ue_batch and feed results back. Use binary mode for offline scanning.")

    print(f"  [editor-mcp] Total: {len(asset_game_paths)} assets in "
          f"{(len(asset_game_paths) + BATCH_SIZE - 1) // BATCH_SIZE} batches")
    print("  [editor-mcp] Falling back to binary mode for this run.")
    print("  [editor-mcp] To use editor-mcp interactively, run this script "
          "from the AI agent context with --asset-mode editor-mcp.")

    # Fallback to binary
    return scan_assets_binary(repo_root, content_root, extra_whitelist)
