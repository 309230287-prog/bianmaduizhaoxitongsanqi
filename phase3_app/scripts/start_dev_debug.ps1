Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$appRoot = Split-Path -Parent $scriptDir
$backendDir = Join-Path $appRoot "backend"
$frontendDir = Join-Path $appRoot "frontend"
$backendSrc = Join-Path $backendDir "src"
$workbenchUrl = "http://127.0.0.1:5173"
$backendHealthUrl = "http://127.0.0.1:8000/health"

if (-not (Test-Path -LiteralPath $backendDir)) {
    throw "Backend directory not found: $backendDir"
}

if (-not (Test-Path -LiteralPath $frontendDir)) {
    throw "Frontend directory not found: $frontendDir"
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
    Write-Warning "Backend is not ready yet. The debug page may need a few seconds."
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

Start-Process powershell -WindowStyle Hidden -ArgumentList "-NoExit", "-Command", $frontendCommand
Start-Sleep -Seconds 4
Start-Process $workbenchUrl

Write-Host "Development debug mode started."
Write-Host "Frontend debug page: $workbenchUrl"
Write-Host "Backend service: http://127.0.0.1:8000"
