Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$appRoot = Split-Path -Parent $scriptDir
$backendDir = Join-Path $appRoot "backend"
$frontendDir = Join-Path $appRoot "frontend"
$desktopExe = Join-Path $appRoot "desktop\src-tauri\target\release\product-code-mapper.exe"
$backendSrc = Join-Path $backendDir "src"
$workbenchUrl = "http://127.0.0.1:5173"
$backendHealthUrl = "http://127.0.0.1:8000/health"

if (-not (Test-Path -LiteralPath $backendDir)) {
    throw "未找到后端目录：$backendDir"
}

if (-not (Test-Path -LiteralPath $frontendDir)) {
    throw "未找到前端目录：$frontendDir"
}

$backendCommand = @"
`$env:PYTHONPATH = '$backendSrc'
Set-Location -LiteralPath '$backendDir'
python -m uvicorn product_code_mapper.api.app:create_app --factory --host 127.0.0.1 --port 8000
"@

$frontendCommand = @"
Set-Location -LiteralPath '$frontendDir'
npm run dev -- --host 127.0.0.1 --port 5173
"@

Start-Process powershell -WindowStyle Hidden -ArgumentList "-NoExit", "-Command", $backendCommand

$backendReady = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        $health = Invoke-RestMethod -Uri $backendHealthUrl -TimeoutSec 1
        if ($health.status -eq "ok") {
            $backendReady = $true
            break
        }
    }
    catch {
        Start-Sleep -Milliseconds 500
    }
}

if (-not $backendReady) {
    Write-Warning "后端服务暂未响应，桌面工作台可能需要稍等几秒。"
}

if (Test-Path -LiteralPath $desktopExe) {
    Start-Process -FilePath $desktopExe
    Write-Host "三期桌面工作台已启动。"
}
else {
    if (-not (Test-Path -LiteralPath (Join-Path $frontendDir "node_modules"))) {
        Push-Location $frontendDir
        try {
            npm install
        }
        finally {
            Pop-Location
        }
    }
    Start-Process powershell -WindowStyle Hidden -ArgumentList "-NoExit", "-Command", $frontendCommand
    Start-Sleep -Seconds 4
    Start-Process $workbenchUrl
    Write-Host "未找到桌面程序，已启动浏览器开发模式：$workbenchUrl"
}

Write-Host "后端服务：http://127.0.0.1:8000"
