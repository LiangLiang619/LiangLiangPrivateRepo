<#
.SYNOPSIS
  letsgo-quick-pak: 扫描 configs/*.txt，每个生成一个加密 UE pak；
  对应的 Lua 挂载代码片段**直接打印到控制台**（不生成 .lua 文件），
  由用户手动拷贝到合适位置（推荐 LetsGoSDK/Script/Boot/AppEntry.lua）。

.EXAMPLE
  ./scripts/Build.ps1
  ./scripts/Build.ps1 -Config example_AssetNameMapping.txt
  ./scripts/Build.ps1 -OutDir D:/tmp
#>
[CmdletBinding()]
param(
  [string]$Config = "",
  [string]$OutDir = "",
  [string]$UnrealPak = "",
  [string]$Crypto    = "",
  [string]$Project   = ""    # 覆盖 .uproject 自动探测的工程名，用于 {project} 占位符替换
)

$ErrorActionPreference = "Stop"

# ---------- Path resolution ----------
$SkillRoot = Split-Path $PSScriptRoot -Parent      # .../letsgo-quick-pak
$ConfigDir = Join-Path $SkillRoot "configs"
$GenDir    = Join-Path $SkillRoot "generated"
$PakDir    = if ($OutDir) { $OutDir } else { Join-Path $GenDir "pak" }

# 根据 SkillRoot 动态算出 Lua require 路径（以 Content/ 为 require 根）。
# 例：  ...\LetsGo\Content\LetsGoSDK\Skill\letsgo-quick-pak
#   -> LetsGoSDK.Skill.letsgo-quick-pak.lua.QuickPakMount
function Resolve-LuaRequirePath {
  param([string]$AbsSkillRoot)
  $norm  = $AbsSkillRoot -replace '\\','/'
  $parts = $norm.Split('/')
  # 从后往前找最外层的 "Content"（有些工程 Content 里可能嵌套）
  $idx = -1
  for ($i = $parts.Length - 1; $i -ge 0; $i--) {
    if ($parts[$i] -ieq "Content") { $idx = $i; break }
  }
  if ($idx -lt 0 -or $idx -eq $parts.Length - 1) {
    Write-Warning "Cannot locate 'Content/' segment in skill path; falling back to default require path."
    return "LetsGoSDK.Skill.letsgo-quick-pak.lua.QuickPakMount"
  }
  $rel = $parts[($idx + 1)..($parts.Length - 1)]
  return (($rel -join '.') + ".lua.QuickPakMount")
}
$LuaRequirePath = Resolve-LuaRequirePath -AbsSkillRoot $SkillRoot

if (-not $Crypto)    { $Crypto    = Join-Path $PSScriptRoot "Crypto.json" }
if (-not $UnrealPak) { $UnrealPak = "E:\UGit\LetsGoDevelop\ue4_tracking_rdcsp\Engine\Binaries\Win64\UnrealPak.exe" }

if (-not (Test-Path $UnrealPak)) { throw "UnrealPak not found: $UnrealPak" }
if (-not (Test-Path $Crypto))    { throw "Crypto.json not found: $Crypto" }
if (-not (Test-Path $ConfigDir)) { throw "configs/ not found under $SkillRoot" }

New-Item -ItemType Directory -Force -Path $PakDir | Out-Null

# ---------- Project name resolution (for {project} placeholder) ----------
# 从 skill 目录往上最多 8 层找 *.uproject，取文件名（不含扩展名）作为工程名。
function Resolve-ProjectName {
  param([string]$Start)
  $dir = Get-Item -LiteralPath $Start
  for ($i = 0; $i -lt 8 -and $dir; $i++) {
    $up = Get-ChildItem -LiteralPath $dir.FullName -Filter *.uproject -File -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($up) { return [System.IO.Path]::GetFileNameWithoutExtension($up.Name) }
    if (-not $dir.Parent) { break }
    $dir = $dir.Parent
  }
  return $null
}
if (-not $Project) { $Project = Resolve-ProjectName -Start $SkillRoot }
if ($Project) {
  Write-Host ("Project name for '{{project}}' placeholder: {0}" -f $Project) -ForegroundColor DarkCyan
} else {
  Write-Warning "No .uproject found above skill dir; '{project}' placeholder will NOT be substituted. Pass -Project <name> or fix config manually."
}

function Expand-Placeholders {
  param([string]$Text)
  if (-not $Text) { return $Text }
  if ($Project) { return $Text -replace '\{project\}', $Project }
  return $Text
}

# ---------- Config parser ----------
function Parse-Config {
  param([string]$Path)

  $meta = @{
    pak                     = $null
    priority                = 100
    reloadAssetNameMapping  = $false
  }
  $files = New-Object System.Collections.Generic.List[object]

  foreach ($rawLine in (Get-Content -LiteralPath $Path -Encoding UTF8)) {
    $line = $rawLine.Trim()
    if (-not $line)        { continue }
    if ($line.StartsWith("#")) { continue }

    # key: value
    if ($line -match '^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.+)$' -and $line -notmatch '->') {
      $k = $matches[1].ToLowerInvariant()
      $v = $matches[2].Trim()
      switch ($k) {
        "pak"                     { $meta.pak = $v }
        "priority"                { $meta.priority = [int]$v }
        "reloadassetnamemapping"  { $meta.reloadAssetNameMapping = ($v -match '^(true|1|yes|on)$') }
        default {
          Write-Warning "Unknown key '$k' in $Path"
        }
      }
      continue
    }

    # source -> mount   或   source（自动挂到 Content/<filename>）
    if ($line -match '^(.+?)\s*->\s*(.+)$') {
      $src = $matches[1].Trim().Trim('"')
      $mnt = $matches[2].Trim().Trim('"')
    } else {
      $src = $line.Trim('"')
      $mnt = "Content/" + [System.IO.Path]::GetFileName($src)
    }
    $src = Expand-Placeholders -Text $src
    $mnt = Expand-Placeholders -Text $mnt
    $files.Add([pscustomobject]@{ Source = $src; Mount = $mnt }) | Out-Null
  }

  if (-not $meta.pak) { throw "Config '$Path' missing required key: pak" }
  if ($files.Count -eq 0) { throw "Config '$Path' has no files" }

  return [pscustomobject]@{ Meta = $meta; Files = $files; ConfigPath = $Path }
}

# ---------- Lua snippet builder ----------
function Build-LuaSnippet {
  param([pscustomobject[]]$Cfgs)

  $sb = New-Object System.Text.StringBuilder
  [void]$sb.AppendLine("-- ================================================================")
  [void]$sb.AppendLine("-- letsgo-quick-pak: paste into LetsGoSDK/Script/Boot/AppEntry.lua")
  [void]$sb.AppendLine("-- (or any boot stage before resources are first accessed)")
  [void]$sb.AppendLine("-- ================================================================")
  [void]$sb.AppendLine(('local QuickPakMount = require("{0}")' -f $LuaRequirePath))
  [void]$sb.AppendLine("")
  foreach ($c in $Cfgs) {
    $pak    = $c.Meta.pak
    $prio   = $c.Meta.priority
    $reload = if ($c.Meta.reloadAssetNameMapping) { "true" } else { "false" }
    [void]$sb.AppendLine("-- pak: $pak.pak")
    [void]$sb.AppendLine("QuickPakMount.MountFromInfo({")
    [void]$sb.AppendLine("    pakName  = `"$pak.pak`",")
    [void]$sb.AppendLine("    priority = $prio,")
    [void]$sb.AppendLine("    reload   = $reload,")
    [void]$sb.AppendLine("})")
    [void]$sb.AppendLine("")
  }
  return $sb.ToString().TrimEnd()
}

# ---------- UnrealPak invocation ----------
function Build-One {
  param([pscustomobject]$Cfg)

  $pakName = $Cfg.Meta.pak
  $pakFile = Join-Path $PakDir "$pakName.pak"
  $respFile = Join-Path $env:TEMP "quickpak_response_$($pakName).txt"

  foreach ($f in $Cfg.Files) {
    if (-not (Test-Path -LiteralPath $f.Source)) {
      throw "[${pakName}] Source not found: $($f.Source)"
    }
  }

  $lines = foreach ($f in $Cfg.Files) {
    $src = $f.Source -replace '/','\'
    $mnt = $f.Mount -replace '\\','/'
    '"{0}" "{1}"' -f $src, $mnt
  }
  [System.IO.File]::WriteAllLines($respFile, $lines, [System.Text.UTF8Encoding]::new($false))

  Write-Host ("==> [{0}] Packing {1} file(s)..." -f $pakName, $Cfg.Files.Count) -ForegroundColor Cyan

  $out1 = & $UnrealPak $pakFile "-Create=$respFile" "-cryptokeys=$Crypto" "-encryptindex" 2>&1
  $out1 | Where-Object { $_ -match "Added|Creating|Encryption -|Total:|executed in|Error" } | ForEach-Object { "    $_" }

  if (-not (Test-Path $pakFile)) {
    Write-Host "    [ERROR] pak was not created, full UnrealPak output:" -ForegroundColor Red
    $out1 | ForEach-Object { "    $_" }
    throw "Pak creation failed for $pakName"
  }

  Write-Host "    ---- Mount self-check ----" -ForegroundColor DarkGray
  $out2 = & $UnrealPak $pakFile -List "-cryptokeys=$Crypto" 2>&1
  $mount = ($out2 | Where-Object { $_ -match "Mount point" } | Select-Object -First 1)
  if ($mount) { Write-Host ("    {0}" -f $mount) }
  $fileCount = ($out2 | Where-Object { $_ -match 'offset:.*size:' }).Count
  Write-Host ("    files in pak: {0}" -f $fileCount)

  $fi = Get-Item -LiteralPath $pakFile
  $fi.Refresh()
  return $fi
}

# ---------- Main ----------
$configs = if ($Config) {
  $p = if (Test-Path $Config) { $Config } else { Join-Path $ConfigDir $Config }
  if (-not (Test-Path $p)) { throw "Config not found: $Config" }
  @(Get-Item $p)
} else {
  Get-ChildItem -LiteralPath $ConfigDir -Filter "*.txt" -File |
    Where-Object { $_.Name -ne "_template.txt" }
}

if ($configs.Count -eq 0) {
  Write-Warning "No config to build. Create a txt under configs/ (copy _template.txt)."
  return
}

$parsed   = @()
$pakInfos = @()
foreach ($c in $configs) {
  try {
    $cfg = Parse-Config -Path $c.FullName
    $pakItem = Build-One -Cfg $cfg
    $parsed   += $cfg
    $pakInfos += [pscustomobject]@{ Pak = $pakItem; Cfg = $cfg }
  } catch {
    Write-Host ("!! {0}: {1}" -f $c.Name, $_.Exception.Message) -ForegroundColor Red
  }
}

if ($parsed.Count -eq 0) { return }

# ---- Summary: output paths ----
Write-Host ""
Write-Host "================================================================" -ForegroundColor Yellow
Write-Host " OUTPUT PAK FILES (copy to device PersistentDownloadDir)" -ForegroundColor Yellow
Write-Host "================================================================" -ForegroundColor Yellow
foreach ($p in $pakInfos) {
  # re-read length right before printing to avoid stale FileInfo cache
  $len = (Get-Item -LiteralPath $p.Pak.FullName).Length
  Write-Host ("  {0}" -f $p.Pak.FullName) -ForegroundColor Green
  Write-Host ("    size     : {0:N0} bytes" -f $len)
  Write-Host ("    priority : {0}" -f $p.Cfg.Meta.priority)
  Write-Host ("    reload   : {0}" -f $p.Cfg.Meta.reloadAssetNameMapping)
}

# ---- Summary: lua snippet ----
$snippet = Build-LuaSnippet -Cfgs $parsed
Write-Host ""
Write-Host "================================================================" -ForegroundColor Yellow
Write-Host " LUA SNIPPET (paste into LetsGoSDK/Script/Boot/AppEntry.lua)" -ForegroundColor Yellow
Write-Host "================================================================" -ForegroundColor Yellow
Write-Host ""
Write-Host $snippet
Write-Host ""
Write-Host "----------------------------------------------------------------" -ForegroundColor DarkGray
Write-Host "Reminder:" -ForegroundColor Yellow
Write-Host "  1) Push the pak(s) above to the device's PersistentDownloadDir."
Write-Host "  2) Copy the Lua snippet into LetsGoSDK/Script/Boot/AppEntry.lua"
Write-Host "     (or any boot hook that runs before resources are accessed)."
Write-Host "  3) No Lua file is auto-generated on purpose - hand-placement only."
