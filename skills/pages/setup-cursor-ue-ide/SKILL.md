---
name: setup-cursor-ue-ide
description: >-
  Set up Cursor IDE for UE (Unreal Engine) C++ and Lua code navigation
  (Go to Definition, Find References). Generates compile_commands.json
  from Rider project model, creates .clangd and .emmyrc.json configs.
  Use when the user asks to set up code jumping, 配置跳转, 代码导航,
  setup clangd, setup EmmyLua, or configure IDE for a UE project.
---

# Setup Cursor IDE for UE Projects

One-click setup for C++ (clangd) and Lua (EmmyLua) code navigation in UE projects.

## Prerequisites

- **clangd extension** installed (`llvm-vs-code-extensions.vscode-clangd`)
- **EmmyLua extension** installed (`theo.emmylua`)
- **clangd binary** available (user settings `clangd.path` configured)
- **Python 3** available in PATH

If extensions or clangd binary are missing, install them first:

```bash
# Install extensions
cursor --install-extension llvm-vs-code-extensions.vscode-clangd
cursor --install-extension theo.emmylua

# Download clangd (if not installed)
# Windows: download from https://github.com/clangd/clangd/releases
# Then set clangd.path in user settings.json
```

## User-Level Settings (one-time)

Ensure these are in the user `settings.json` (applies to all projects):

```json
{
    "clangd.path": "<path-to-clangd-binary>",
    "clangd.arguments": [
        "--background-index",
        "--clang-tidy=false",
        "--header-insertion=never",
        "--completion-style=detailed",
        "-j=4",
        "--pch-storage=memory"
    ],
    "C_Cpp.intelliSenseEngine": "disabled",
    "emmylua.runtime.version": "Lua 5.3",
    "emmylua.workspace.encoding": "utf-8"
}
```

## Per-Project Setup

Run the setup script, passing the UE project root (the folder containing `.uproject`):

```bash
python scripts/setup_cursor_ide.py <project_root>
```

The script auto-detects project root if run from within the project tree (walks up to find `.uproject`).

### What the script generates

| File | Purpose | Required |
|------|---------|----------|
| `compile_commands.json` | C++ compilation database for clangd | Rider JSON needed |
| `.clangd` | clangd behaviour (suppress diagnostics, enable background index) | Always |
| `.emmyrc.json` | EmmyLua workspace roots and global whitelist (project root) | Always |
| `Content/.emmyrc.json` | Same config for Content-only workspace | If Content/ exists |

### C++ compile_commands.json

The script reads Rider's project model from `Intermediate/ProjectFiles/.Rider/`. This requires the project to have been opened in Rider at least once. If the Rider JSON is missing, the script skips C++ setup and prints a warning.

### Lua .emmyrc.json

The script auto-detects Lua directories by scanning for common paths:
- `Content/LetsGo/Script`
- `Content/LetsGoSDK/Script`
- `Content/Feature/System/Script`
- `Content/Script`

Global variable whitelist is read from `.luacheckrc` if present.

## Workflow

1. Identify the UE project root (folder with `.uproject`)
2. Run: `python <skill-scripts-dir>/setup_cursor_ide.py <project_root>`
3. Reload Cursor window (`Ctrl+Shift+P` → `Developer: Reload Window`)
4. Wait for clangd indexing to complete (status bar shows progress)

## Notes

- clangd searches **parent directories** for `compile_commands.json`, so opening any sub-folder (e.g. `Plugins/`) works without extra config
- EmmyLua `.emmyrc.json` only works at the **workspace root**, which is why the script generates one at both project root and `Content/`
- First-time clangd indexing may take 5-10 minutes for large projects; results are cached in `.cache/clangd/`
- Re-run the script after adding new C++ modules or changing build dependencies
