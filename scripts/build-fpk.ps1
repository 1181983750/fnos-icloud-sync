param(
  [string]$FnpackBin = $env:FNPACK_BIN
)

$ErrorActionPreference = "Stop"
$ProjectDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).ProviderPath
$DistDir = Join-Path $ProjectDir "dist"
$ManifestPath = Join-Path $ProjectDir "manifest"

function Get-ManifestValue([string]$Name) {
  $line = Get-Content $ManifestPath | Where-Object { $_ -match "^\s*$Name\s*=" } | Select-Object -First 1
  if (-not $line) { return "" }
  return (($line -split "=", 2)[1]).Trim()
}

if (-not $FnpackBin) {
  $command = Get-Command fnpack -ErrorAction SilentlyContinue
  if ($command) {
    $FnpackBin = $command.Source
  }
}

if (-not $FnpackBin) {
  $searchDirs = @($ProjectDir, (Join-Path $ProjectDir "tools")) | Where-Object { Test-Path $_ }
  $candidate = Get-ChildItem -Path $searchDirs -File -Filter "fnpack*" |
    Where-Object { $_.Name -match "windows|fnpack(\.exe)?$" } |
    Select-Object -First 1
  if ($candidate) {
    $FnpackBin = $candidate.FullName
  }
}

if (-not $FnpackBin -or -not (Test-Path $FnpackBin)) {
  throw "fnpack not found. Put fnpack in the project root, or set FNPACK_BIN=/abs/path/to/fnpack."
}

New-Item -ItemType Directory -Force -Path $DistDir | Out-Null
Get-ChildItem -Path $ProjectDir -Filter '*.fpk' -File -ErrorAction SilentlyContinue |
  Remove-Item -Force -ErrorAction SilentlyContinue

Push-Location $ProjectDir
try {
  & $FnpackBin build --directory $ProjectDir
  if ($LASTEXITCODE -ne 0) {
    throw "fnpack build failed with exit code $LASTEXITCODE"
  }
}
finally {
  Pop-Location
}

$appname = Get-ManifestValue "appname"
$version = Get-ManifestValue "version"
$built = Join-Path $ProjectDir "$appname.fpk"
if (-not (Test-Path $built)) {
  $built = Get-ChildItem -Path $ProjectDir -Filter "*.fpk" | Select-Object -First 1 -ExpandProperty FullName
}

if (-not $built -or -not (Test-Path $built)) {
  throw "fnpack did not generate an .fpk file."
}

$target = Join-Path $DistDir "$appname-$version.fpk"
Move-Item -Force $built $target
Write-Host "FPK generated: $target"
