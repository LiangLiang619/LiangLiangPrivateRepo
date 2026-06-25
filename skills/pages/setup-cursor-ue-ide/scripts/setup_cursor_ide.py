"""
One-click Cursor IDE setup for UE (LetsGo / TMR) projects.

Generates:
  1. compile_commands.json   (C++ clangd index)
  2. .clangd                 (clangd behaviour)
  3. .emmyrc.json            (Lua EmmyLua, at project root)
  4. Content/.emmyrc.json    (Lua EmmyLua, for Content-only workspace)

Usage:
    python setup_cursor_ide.py                      # auto-detect project root
    python setup_cursor_ide.py  D:\\Other\\Project   # specify project root
"""
import json
import os
import sys
import glob as globmod

CPP_EXTENSIONS = {".cpp", ".cc", ".cxx", ".c"}

CLANGD_CONFIG = """\
CompileFlags:
  CompilationDatabase: .
  Add:
    - -ferror-limit=0
    - -Wno-everything

Diagnostics:
  Suppress: '*'
  UnusedIncludes: None

InlayHints:
  Enabled: No

Index:
  Background: Build
"""


def find_project_root(start=None):
    d = os.path.abspath(start or os.getcwd())
    while True:
        if globmod.glob(os.path.join(d, "*.uproject")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return None


def find_rider_json(project_root):
    pattern = os.path.join(
        project_root, "Intermediate", "ProjectFiles", ".Rider", "**", "*.json"
    )
    candidates = globmod.glob(pattern, recursive=True)
    best = None
    best_size = 0
    for c in candidates:
        sz = os.path.getsize(c)
        if sz > best_size:
            best_size = sz
            best = c
    return best


def find_lua_roots(project_root):
    candidates = [
        "Content/LetsGo/Script",
        "Content/LetsGoSDK/Script",
        "Content/Feature/System/Script",
        "Content/Script",
    ]
    found = []
    for c in candidates:
        if os.path.isdir(os.path.join(project_root, c)):
            found.append(c)
    return found


def read_luacheckrc_globals(project_root):
    rc_path = os.path.join(project_root, ".luacheckrc")
    defaults = ["UE4", "_MOE", "LuaPanda", "loadstring", "GlobalVar"]
    if not os.path.isfile(rc_path):
        return defaults

    globals_list = []
    in_globals = False
    with open(rc_path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith("globals") and "=" in stripped:
                in_globals = True
                continue
            if in_globals:
                if stripped == "}":
                    break
                name = stripped.strip(",' \t")
                if name:
                    globals_list.append(name)
    return globals_list or defaults


def collect_sources(directory):
    sources = []
    for root, _dirs, files in os.walk(directory):
        for f in files:
            if os.path.splitext(f)[1].lower() in CPP_EXTENSIONS:
                sources.append(os.path.join(root, f))
    return sources


def is_project_module(mod_dir, project_root):
    """Only include modules whose source lives under the project tree."""
    norm_dir = os.path.normcase(os.path.normpath(mod_dir))
    norm_root = os.path.normcase(os.path.normpath(project_root))
    return norm_dir.startswith(norm_root + os.sep)


def gen_compile_commands(project_root, rider_json_path, project_only=True):
    with open(rider_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    env_includes = data.get("EnvironmentIncludePaths", [])
    env_definitions = data.get("EnvironmentDefinitions", [])
    modules = data.get("Modules", {})

    compile_commands = []
    skipped = 0
    for _mod_name, mod in modules.items():
        mod_dir = mod.get("Directory", "")
        if not mod_dir or not os.path.isdir(mod_dir):
            continue

        if project_only and not is_project_module(mod_dir, project_root):
            skipped += 1
            continue

        includes = set()
        includes.update(mod.get("PublicIncludePaths", []))
        includes.update(mod.get("PrivateIncludePaths", []))
        includes.update(mod.get("LegacyPublicIncludePaths", []))
        includes.update(env_includes)

        gen_dir = mod.get("GeneratedCodeDirectory", "")
        if gen_dir:
            includes.add(gen_dir)

        definitions = list(env_definitions)
        for key in ("PublicDefinitions", "PrivateDefinitions",
                     "ProjectDefinitions", "ApiDefinitions"):
            definitions.extend(mod.get(key, []))

        args = ["clang++", "-std=c++17", "-ferror-limit=0"]
        for inc in sorted(includes):
            if os.path.isdir(inc):
                args.append(f"-I{inc}")
        for d in definitions:
            args.append(f"-D{d}")
        args.extend([
            "-DWITH_EDITOR=1", "-DWITH_ENGINE=1",
            "-DWITH_UNREAL_DEVELOPER_TOOLS=1",
            "-DPLATFORM_WINDOWS=1", "-DUE_BUILD_DEVELOPMENT=1",
        ])

        for src in collect_sources(mod_dir):
            fwd = src.replace("\\", "/")
            compile_commands.append({
                "directory": project_root,
                "file": fwd,
                "arguments": args + ["-c", fwd],
            })

    output = os.path.join(project_root, "compile_commands.json")
    with open(output, "w", encoding="utf-8") as f:
        json.dump(compile_commands, f, indent=2)
    return output, len(compile_commands), skipped


def gen_emmyrc(target_dir, lua_roots, lua_globals, ignore_dirs=None):
    if ignore_dirs is None:
        ignore_dirs = [".git", ".svn"]

    emmyrc = {
        "$schema": "https://raw.githubusercontent.com/EmmyLua/EmmyLuaAnalyzer/master/docs/.emmyrc.schema.json",
        "runtime": {"version": "Lua5.3"},
        "workspace": {
            "roots": lua_roots,
            "encoding": "utf-8",
            "ignoreDir": ignore_dirs,
        },
        "diagnostics": {"globals": lua_globals},
    }
    out = os.path.join(target_dir, ".emmyrc.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(emmyrc, f, indent=4, ensure_ascii=False)
        f.write("\n")
    return out


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Setup Cursor IDE for UE projects")
    parser.add_argument("project_root", nargs="?", help="UE project root (auto-detect if omitted)")
    parser.add_argument("--all", action="store_true",
                        help="Index ALL modules including engine (default: project-only)")
    args = parser.parse_args()

    if args.project_root:
        project_root = os.path.abspath(args.project_root)
    else:
        project_root = find_project_root()

    if not project_root:
        print("ERROR: Cannot find project root (no .uproject found).")
        print("Usage: python setup_cursor_ide.py <project_root>")
        sys.exit(1)

    project_only = not args.all
    print(f"Project root: {project_root}")
    print(f"Index scope:  {'project modules only' if project_only else 'ALL modules (including engine)'}")
    print()

    rider_json = find_rider_json(project_root)
    if rider_json:
        print(f"Found Rider JSON: {rider_json}")
        output, count, skipped = gen_compile_commands(
            project_root, rider_json, project_only=project_only)
        print(f"  -> Generated {output} ({count} entries, {skipped} engine modules skipped)")
    else:
        print("WARNING: No Rider project JSON found in Intermediate/ProjectFiles/.Rider/")
        print("  To generate it, open the project once in Rider.")
        print("  Skipping compile_commands.json generation.")
    print()

    clangd_path = os.path.join(project_root, ".clangd")
    with open(clangd_path, "w", encoding="utf-8") as f:
        f.write(CLANGD_CONFIG)
    print(f"  -> Generated {clangd_path}")
    print()

    lua_roots = find_lua_roots(project_root)
    lua_globals = read_luacheckrc_globals(project_root)
    if lua_roots:
        out = gen_emmyrc(
            project_root, lua_roots, lua_globals,
            ignore_dirs=[".git", ".svn", "Binaries", "DerivedDataCache",
                         "Intermediate", "Saved"],
        )
        print(f"  -> Generated {out}")
        print(f"     Lua roots: {lua_roots}")

        content_dir = os.path.join(project_root, "Content")
        if os.path.isdir(content_dir):
            content_roots = [r.replace("Content/", "", 1) for r in lua_roots]
            out2 = gen_emmyrc(content_dir, content_roots, lua_globals)
            print(f"  -> Generated {out2}")
    else:
        print("WARNING: No Lua script directories found. Skipping .emmyrc.json.")
    print()

    print("Done! Reload Cursor window (Ctrl+Shift+P -> Reload Window) to activate.")


if __name__ == "__main__":
    main()
