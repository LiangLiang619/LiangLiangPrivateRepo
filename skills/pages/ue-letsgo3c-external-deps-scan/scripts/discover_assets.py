"""
discover_assets.py
------------------
Recursively walk a UE Content sub-directory and emit one /Game/... path per
line for every .uasset / .umap found.

Usage:
  python discover_assets.py \
    --repo-root "E:\\Dev2\\LetsGoDevelop\\LetsGo\\Content\\LetsGo3C" \
    --content-root "E:\\Dev2\\LetsGoDevelop\\LetsGo\\Content" \
    --out assets.txt
"""

import argparse
import os
import sys


SKIP_SUFFIXES = (
    "_BuiltData.uasset",
    ".umap_BuildData",
)

ASSET_EXTENSIONS = (".uasset", ".umap")


def infer_content_root(repo_root):
    """Walk upward from repo_root to find the nearest directory named 'Content'."""
    path = os.path.normpath(repo_root)
    while True:
        parent = os.path.dirname(path)
        if os.path.basename(path).lower() == "content":
            return path
        if parent == path:
            break
        path = parent
    return None


def fs_path_to_game_path(file_path, content_root):
    """Convert an absolute file path under Content/ to a /Game/... package path."""
    rel = os.path.relpath(file_path, content_root)
    rel_no_ext = os.path.splitext(rel)[0]
    game_path = "/Game/" + rel_no_ext.replace("\\", "/")
    return game_path


def should_skip(file_name):
    for suffix in SKIP_SUFFIXES:
        if file_name.endswith(suffix):
            return True
    return False


def discover(repo_root, content_root):
    assets = []
    for dirpath, _dirnames, filenames in os.walk(repo_root):
        for fname in filenames:
            if should_skip(fname):
                continue
            _base, ext = os.path.splitext(fname)
            if ext.lower() not in ASSET_EXTENSIONS:
                continue
            full_path = os.path.join(dirpath, fname)
            game_path = fs_path_to_game_path(full_path, content_root)
            assets.append(game_path)
    assets.sort()
    return assets


def main():
    parser = argparse.ArgumentParser(description="Discover UE assets under a repo root")
    parser.add_argument("--repo-root", required=True,
                        help="Absolute path to the repository root directory")
    parser.add_argument("--content-root", default=None,
                        help="UE project Content directory (auto-inferred if omitted)")
    parser.add_argument("--out", required=True,
                        help="Output file path (one /Game/... path per line)")
    args = parser.parse_args()

    repo_root = os.path.normpath(args.repo_root)
    if not os.path.isdir(repo_root):
        print(f"[error] repo-root does not exist: {repo_root}", file=sys.stderr)
        sys.exit(1)

    content_root = args.content_root
    if content_root:
        content_root = os.path.normpath(content_root)
    else:
        content_root = infer_content_root(repo_root)
        if not content_root:
            print("[error] Cannot infer content-root from repo-root. "
                  "Please specify --content-root explicitly.", file=sys.stderr)
            sys.exit(1)

    print(f"Repo root:    {repo_root}")
    print(f"Content root: {content_root}")

    assets = discover(repo_root, content_root)

    out_dir = os.path.dirname(args.out)
    if out_dir and not os.path.isdir(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    with open(args.out, "w", encoding="utf-8") as f:
        for a in assets:
            f.write(a + "\n")

    print(f"Discovered {len(assets)} assets -> {args.out}")


if __name__ == "__main__":
    main()
