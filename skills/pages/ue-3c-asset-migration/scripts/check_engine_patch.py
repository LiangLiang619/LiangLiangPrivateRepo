#!/usr/bin/env python3
"""Check whether AssetRenameManager.cpp contains the UGit redirector patch.

Exits with code 0 and prints PATCHED or NOT_PATCHED.
"""

import os
import re
import sys

MARKER_COMMENT = "UGit: Skip reference scanning entirely"
MARKER_CODE_A = "RenameData.bCreateRedirector = true"
MARKER_CODE_B = "RenameData.ReferencingPackageNames.Empty()"
FUNCTION_SIG = "FAssetRenameManager::FixReferencesAndRename"


def check_patch(cpp_path):
    if not os.path.isfile(cpp_path):
        print(f"ERROR: File not found: {cpp_path}", file=sys.stderr)
        sys.exit(1)

    with open(cpp_path, 'r', encoding='utf-8') as f:
        content = f.read()

    func_match = re.search(
        r'bool\s+FAssetRenameManager::FixReferencesAndRename\s*\(', content
    )
    if not func_match:
        print(f"ERROR: Cannot find {FUNCTION_SIG} in file", file=sys.stderr)
        sys.exit(1)

    func_body = content[func_match.start():]

    has_comment = MARKER_COMMENT in func_body
    has_code_a = MARKER_CODE_A in func_body
    has_code_b = MARKER_CODE_B in func_body

    if has_comment and has_code_a and has_code_b:
        print("PATCHED")
        print(f"  Found UGit redirector block in {FUNCTION_SIG}")
    else:
        print("NOT_PATCHED")
        missing = []
        if not has_comment:
            missing.append("marker comment")
        if not has_code_a:
            missing.append("bCreateRedirector = true")
        if not has_code_b:
            missing.append("ReferencingPackageNames.Empty()")
        print(f"  Missing: {', '.join(missing)}")
        print(f"  Suggested insertion point: after CDO warning block, before UpdatePackageStatus")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python check_engine_patch.py <AssetRenameManager.cpp>", file=sys.stderr)
        sys.exit(1)
    check_patch(sys.argv[1])
