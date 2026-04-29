Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$appRoot = Split-Path -Parent $scriptDir
$desktopExe = Join-Path $appRoot "desktop\src-tauri\target\release\product-code-mapper.exe"

if (Test-Path -LiteralPath $desktopExe) {
    Start-Process -FilePath $desktopExe
    Write-Host "三期桌面工作台已启动。桌面程序会自动连接本地后端。"
    exit 0
}

Write-Host "未找到桌面客户端：$desktopExe"
Write-Host "请先构建桌面客户端：cd phase3_app\desktop && npm run build"
Read-Host "按回车退出"
exit 1
