<#
.SYNOPSIS
  letsgo-quick-pak: 把一个目录或单文件快速打成加密 UE Pak（res_base-Android_ASTCClient_<N>_P.pak）。

.EXAMPLE
  # 用全量 AssetNameMapping，打到桌面 _2_P.pak（默认 ProjectT）
  ./QuickPak.ps1 -SourceDir "D:\AssetNameMapping_8000" -Index 2

.EXAMPLE
  # Loading 视频，走短 mount，便于 Lua 直接挂到 Content/Movies
  ./QuickPak.ps1 -SourceDir "F:\...\Loading_V4.mp4" -Index 6 `
                 -SubPath "Content/Movies" -ShortMount

.EXAMPLE
  # 切回 LetsGo 项目
  ./QuickPak.ps1 -SourceDir "E:\src" -Index 9 -ProjectName "LetsGo"
#>
param(
  [Parameter(Mandatory=$true)][string]$SourceDir,
  [Parameter(Mandatory=$true)][int]$Index,
  [string]$ProjectName = "ProjectT",
  [string]$SubPath = "Content/LetsGo/Data/AssetData/AssetNameMapping",
  [string]$OutDir = "$env:USERPROFILE\Desktop",
  [switch]$ShortMount,
  [string]$UnrealPak = "E:\UGit\LetsGoDevelop\ue4_tracking_rdcsp\Engine\Binaries\Win64\UnrealPak.exe",
  [string]$Crypto    = "E:\UGit\LetsGoDevelop\Saved\Crypto.json"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $UnrealPak)) { throw "UnrealPak not found: $UnrealPak" }
if (-not (Test-Path $Crypto))    { throw "Crypto.json not found: $Crypto" }

$Resp = Join-Path $env:TEMP ("QuickPakResponse_{0}_P.txt" -f $Index)
$Pak  = Join-Path $OutDir   ("res_base-Android_ASTCClient_{0}_P.pak" -f $Index)

$items = if (Test-Path $SourceDir -PathType Container) {
  Get-ChildItem -Path $SourceDir -Recurse -File
} else {
  @(Get-Item $SourceDir)
}

if ($items.Count -eq 0) { throw "No files under: $SourceDir" }

$lines = foreach ($f in $items) {
  $mount = if ($ShortMount) { "$SubPath/$($f.Name)" }
           else            { "../../../$ProjectName/$SubPath/$($f.Name)" }
  '"{0}" "{1}"' -f $f.FullName, $mount
}
[System.IO.File]::WriteAllLines($Resp, $lines, [System.Text.UTF8Encoding]::new($false))

Write-Host "Response -> $Resp"
Get-Content $Resp | ForEach-Object { "  $_" }

& $UnrealPak $Pak "-Create=$Resp" "-cryptokeys=$Crypto" "-encryptindex" | `
  Select-String -Pattern "Added|Creating|Encryption -|Total:|executed in|Error" | ForEach-Object { "  $_" }

Write-Host "`n---- Listing ----"
& $UnrealPak $Pak -List "-cryptokeys=$Crypto" 2>&1 | `
  Select-String -Pattern "Mount|size:" | ForEach-Object { "  $_" }

$size = (Get-Item $Pak).Length
Write-Host ("`nDone: {0}  ({1:N0} bytes)" -f $Pak, $size) -ForegroundColor Green
