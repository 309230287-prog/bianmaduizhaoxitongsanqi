Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$appRoot = Split-Path -Parent $scriptDir
$desktopExe = Join-Path $appRoot "desktop\src-tauri\target\release\product-code-mapper.exe"

if (Test-Path -LiteralPath $desktopExe) {
    Start-Process -FilePath $desktopExe
    Write-Host "Phase 3 desktop client started. The desktop client owns the local backend."
    exit 0
}

Write-Host "Desktop client not found: $desktopExe"
Write-Host "Build it first:"
Write-Host "  cd phase3_app\desktop"
Write-Host "  npm run build"
Read-Host "Press Enter to exit"
exit 1
