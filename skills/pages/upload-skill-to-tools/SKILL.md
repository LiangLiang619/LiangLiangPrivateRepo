---
name: upload-skill-to-tools
description: >-
  Copy a Cursor skill to the project's Tools repo under
  LetsGo/Tools/MoeAssetsToolSet/Skills and git push. Use when the user says
  "帮我上传这个skill", "上传skill到Tools", "upload skill", "同步skill到Tools仓库",
  or asks to push a skill to the MoeAssetsToolSet Skills directory.
---

# Upload Skill to Tools Repo

将指定的 Cursor skill 目录复制到项目 Tools 仓库的
`LetsGo/Tools/MoeAssetsToolSet/Skills` 目录下，并执行 git push。

## Prerequisites

- Tools 仓库已 clone 到本地
- 用户拥有 push 权限

## Workflow

### Step 1: Identify the skill to upload

确定要上传的 skill：

- 如果用户明确指定了 skill 名称，使用该名称
- 如果用户说"这个 skill"且上下文中刚创建/编辑过某个 skill，使用该 skill
- 如果不确定，询问用户

Skill 来源路径优先级：
1. `~/.cursor/skills/<skill-name>/` (personal skills)
2. `.cursor/skills/<skill-name>/` (project skills)

### Step 2: Locate the Tools repo

Tools 仓库与当前项目仓库是同一 git 仓库的子目录，路径关系固定为：
- 当前 git 仓库根目录下存在 `LetsGo/Tools/MoeAssetsToolSet/Skills/`

**自动发现策略（基于相对路径）**：
1. 运行 `git rev-parse --show-toplevel` 获取当前 git 仓库根目录，记为 `$GIT_ROOT`
2. 检查 `$GIT_ROOT/LetsGo/Tools/MoeAssetsToolSet/Skills/` 是否存在
3. 如果不存在，向 `$GIT_ROOT` 的上级目录查找（兼容 workspace 在子目录的情况）
4. 如果仍未找到，**询问用户** Tools 目录相对于仓库根目录的路径

目标目录：`$GIT_ROOT/LetsGo/Tools/MoeAssetsToolSet/Skills/<skill-name>/`

> **重要**：全程使用相对于 git 仓库根目录的路径进行操作，不要硬编码绝对路径，
> 以确保不同开发者在不同磁盘/目录下 clone 仓库后都能正常使用此 skill。

### Step 3: Copy skill files

将 skill 目录下的所有文件复制到目标路径。

先获取 git 仓库根目录，再拼接相对路径：

```powershell
# Windows PowerShell
$GIT_ROOT = git rev-parse --show-toplevel
$src = "$env:USERPROFILE\.cursor\skills\<skill-name>"
$dst = Join-Path $GIT_ROOT "LetsGo/Tools/MoeAssetsToolSet/Skills/<skill-name>"

if (-not (Test-Path $dst)) { New-Item -ItemType Directory -Path $dst -Force }
Copy-Item -Path "$src\*" -Destination $dst -Recurse -Force
```

```bash
# Linux/macOS
GIT_ROOT=$(git rev-parse --show-toplevel)
src="$HOME/.cursor/skills/<skill-name>"
dst="$GIT_ROOT/LetsGo/Tools/MoeAssetsToolSet/Skills/<skill-name>"

mkdir -p "$dst"
cp -r "$src/"* "$dst/"
```

### Step 4: Git commit and push

在 git 仓库根目录下执行：

```bash
cd "$(git rev-parse --show-toplevel)"
git add "LetsGo/Tools/MoeAssetsToolSet/Skills/<skill-name>"
git commit -m "chore: upload skill <skill-name> to MoeAssetsToolSet"
git push
```

- commit message 格式：`chore: upload skill <skill-name> to MoeAssetsToolSet`
- 如果是更新已有 skill，message 改为：`chore: update skill <skill-name> in MoeAssetsToolSet`
- push 前先 `git status` 确认变更内容正确

### Step 5: Confirm result

上传完成后向用户报告：
- 已复制的文件列表
- commit hash
- push 是否成功

## Notes

- 只复制 skill 目录本身（SKILL.md 及其子文件/目录），不要复制外层 `.cursor` 结构
- 如果目标目录已存在同名 skill，覆盖更新并在 commit message 中标注 update
- 遵循 Git Safety Protocol，不做 force push
