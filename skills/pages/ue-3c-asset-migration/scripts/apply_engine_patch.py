#!/usr/bin/env python3
"""Apply the UGit redirector patch to AssetRenameManager.cpp.

Creates a .bak backup before modifying. Inserts the UGit redirector block
between the CDO warning block and UpdatePackageStatus/PopulateAssetReferencers.
"""

import os
import re
import shutil
import sys

PATCH_BLOCK = r"""
	// UGit: Skip reference scanning entirely. Always leave a redirector at the old location and
	// never load, checkout, or save any referencing packages. This is required for large projects
	// under version control (UGit) where touching referencing files is prohibitively expensive
	// and causes merge conflicts across branches. The redirector handles all reference resolution
	// at runtime regardless of whether the reference is hard or soft.
	for (FAssetRenameDataWithReferencers& RenameData : AssetsToRename)
	{
		RenameData.bCreateRedirector = true;
		RenameData.ReferencingPackageNames.Empty();
	}

	// Only check out the packages being renamed (not any referencing packages)
	UpdatePackageStatus(AssetsToRename);

	PerformAssetRename(AssetsToRename);

	// Issue post rename event
	AssetPostRenameEvent.Broadcast(AssetsAndNames);

	// Finally, report any failures that happened during the rename
	return ReportFailures(AssetsToRename, bWithDialog) == 0;
}"""


def apply_patch(cpp_path):
    if not os.path.isfile(cpp_path):
        print(f"ERROR: File not found: {cpp_path}", file=sys.stderr)
        sys.exit(1)

    bak_path = cpp_path + ".bak"
    shutil.copy2(cpp_path, bak_path)
    print(f"Backup created: {bak_path}")

    with open(cpp_path, 'r', encoding='utf-8') as f:
        content = f.read()

    func_pattern = re.compile(
        r'(bool\s+FAssetRenameManager::FixReferencesAndRename\s*\([^)]*\)\s*const\s*\{)',
        re.DOTALL
    )
    func_match = func_pattern.search(content)
    if not func_match:
        print("ERROR: Cannot find FixReferencesAndRename function signature", file=sys.stderr)
        sys.exit(1)

    func_start = func_match.start()
    remaining = content[func_start:]

    # Find the end of the CDO warning block (the closing brace of the
    # "if (FMessageDialog::Open..." block, followed by a closing brace for
    # "if (CDOAssets.Num())")
    cdo_marker = "if (CDOAssets.Num())"
    cdo_pos = remaining.find(cdo_marker)
    if cdo_pos == -1:
        print("ERROR: Cannot find CDO warning block marker", file=sys.stderr)
        sys.exit(1)

    # From CDO marker, find the matching closing braces
    # We need to find the end of the "if (CDOAssets.Num()) { ... }" block
    search_start = cdo_pos
    brace_count = 0
    cdo_block_end = -1
    in_block = False

    for i in range(search_start, len(remaining)):
        if remaining[i] == '{':
            brace_count += 1
            in_block = True
        elif remaining[i] == '}':
            brace_count -= 1
            if in_block and brace_count == 0:
                cdo_block_end = i + 1
                break

    if cdo_block_end == -1:
        print("ERROR: Cannot find end of CDO warning block", file=sys.stderr)
        sys.exit(1)

    # Now find the closing brace of the entire FixReferencesAndRename function
    # by counting braces from the function opening
    func_brace_count = 0
    func_end = -1
    for i in range(0, len(remaining)):
        if remaining[i] == '{':
            func_brace_count += 1
        elif remaining[i] == '}':
            func_brace_count -= 1
            if func_brace_count == 0:
                func_end = i + 1
                break

    if func_end == -1:
        print("ERROR: Cannot find end of FixReferencesAndRename function", file=sys.stderr)
        sys.exit(1)

    # Replace everything from after CDO block end to function end with patch block
    abs_cdo_end = func_start + cdo_block_end
    abs_func_end = func_start + func_end

    new_content = content[:abs_cdo_end] + PATCH_BLOCK + content[abs_func_end:]

    with open(cpp_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print("PATCH_APPLIED")
    print(f"  Modified: {cpp_path}")
    print(f"  Replaced function tail (CDO block end to function end) with UGit redirector block")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python apply_engine_patch.py <AssetRenameManager.cpp>", file=sys.stderr)
        sys.exit(1)
    apply_patch(sys.argv[1])
