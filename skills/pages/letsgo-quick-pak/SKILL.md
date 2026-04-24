---
name: letsgo-quick-pak
description: >-
  Build encrypted UE pak files from arbitrary non-cook assets (fb, json, txt, csv, mp4, lua, etc.)
  and generate Lua mount snippets for local QA/hotfix verification in LetsGo / ProjectT (TMR) projects.
  Use when the user mentions quick pak, hot-patch pak, _N_P pak, AssetNameMapping override,
  pak mount, QuickPakMount, or wants to verify asset replacements without a full cook/HotPatcher pipeline.
---

# letsgo-quick-pak (in-repo skill)

> Developer usage: see [README.md](README.md).

## When to trigger

User is in a LetsGo / ProjectT (TMR) project and mentions any of:

- "打个 pak / 打一个热更包 / 快速 pak / 补丁 pak / _N_P 包"
- "验证 AssetNameMapping / 替换 Loading 视频 / 塞个 json 进去试"
- "配置 configs 下的 txt / 改 quickpak 的 config"
- "热更 mount / 强制 mount / lua mount pak"

## Action

1. **Locate the in-repo skill directory**. Priority search (first hit wins):
   - `<any LetsGoSDK sub-repo>/Skill/letsgo-quick-pak/`
     (known paths: `E:\UGit\LetsGoDevelop\LetsGo\Content\LetsGoSDK\Skill\letsgo-quick-pak\`,
      `F:\UGit\TMR_ProjectTDevelop\LetsGo\Content\LetsGoSDK\Skill\letsgo-quick-pak\`)
   - Detection: subdirectory contains `.git` and name starts with `LetsGoSDK`
   - If not found, **ask the user** to copy from an existing LetsGoSDK install (do NOT auto-bootstrap).
     If the project has no LetsGoSDK sub-repo, fall back to a bare UnrealPak workflow.
2. **Read `configs/*.txt`**. If the user specified a particular config (by name or path), process only that one;
   otherwise decide based on context whether to create a new config or run all.
3. **Config parsing rules** (see `configs/_template.txt`):
   - `pak: <name>` — required (no `.pak` suffix; must end with `_<N>_P` / `_<N>_p`)
   - `priority: <int>` — optional, default 100
   - `reloadAssetNameMapping: true/false` — optional, default false
   - Lines starting with `#` are comments
   - Other non-empty lines: `<absolute source path> -> <virtual path in pak>`.
     Omitting `-> ...` mounts to `Content/<source filename>`.
   - **`{project}` placeholder** is supported. `Build.ps1` walks up from the skill dir to find the first
     `.uproject` and substitutes `{project}` with the project name (LetsGo repo -> `LetsGo`, TMR repo -> `ProjectT`).
   - **Always use `{project}` in configs, never hard-code `ProjectT` or `LetsGo`** — same config works in both repos.
4. **Invoke `scripts/Build.ps1`** — never hand-roll UnrealPak commands (prevents parameter drift).
   If `.uproject` detection fails (script warns), tell the user to pass `-Project <name>` or replace the placeholder manually.
5. **Report to user**: each pak's output path + size + mount point + where to deploy (`FPaths::ProjectPersistentDownloadDir()`).

## Output rules (mandatory every time)

1. **Show absolute pak path prominently** — don't just say "generated to generated/"; give the full path.
2. **Never generate `.lua` files** — only output Lua code snippets for the user to paste manually.
3. **Re-print the Lua snippet in chat** — even though `Build.ps1` already prints it, always include it again in a
   ```lua fenced block so the user can copy in one shot.
4. **Recommend a call site**: default is `LetsGoSDK/Script/Boot/AppEntry.lua` (confirmed to exist).
   Respect the user's preference if they have a different boot hook.

## Forbidden actions

- Do NOT modify `scripts/Crypto.json` keys unless the user explicitly requests it (dev key, not release key).
- Do NOT add `generated/` to git (already in `.gitignore`) unless the user says "commit artifacts".
- Do NOT generate uasset-based paks; do NOT invoke cook / IoStore workflows.
- Do NOT auto-generate lua files (including `Mount_*.lua` / `QuickPakMountAll.lua`).
  Exception: `lua/QuickPakMount.lua` is a hand-written runtime helper and is fine to commit.

## Available context (quick reuse)

- UnrealPak: `E:\UGit\LetsGoDevelop\ue4_tracking_rdcsp\Engine\Binaries\Win64\UnrealPak.exe`
- Encryption key source: `LetsGo/Config/DefaultCrypto.ini`
- Runtime mount helper: `lua/QuickPakMount.lua` (multi-path fallback)
- User-level skill (more background / gotchas): `~/.cursor/skills-cursor/letsgo-quick-pak/SKILL.md`
