Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$appRoot = Split-Path -Parent $scriptDir
$backendDir = Join-Path $appRoot "backend"
$frontendDir = Join-Path $appRoot "frontend"
$backendSrc = Join-Path $backendDir "src"
$workbenchUrl = "http://127.0.0.1:5173"

if (-not (Test-Path -LiteralPath $backendDir)) {
    throw "未找到后端目录：$backendDir"
}

if (-not (Test-Path -LiteralPath $frontendDir)) {
    throw "未找到前端目录：$frontendDir"
}

if (-not (Test-Path -LiteralPath (Join-Path $frontendDir "node_modules"))) {
    Push-Location $frontendDir
    try {
        npm install
    }
    finally {
        Pop-Location
    }
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
Start-Process powershell -WindowStyle Hidden -ArgumentList "-NoExit", "-Command", $frontendCommand

Start-Sleep -Seconds 4
Start-Process $workbenchUrl

Write-Host "三期工作台已启动：$workbenchUrl"
Write-Host "后端服务：http://127.0.0.1:8000"

