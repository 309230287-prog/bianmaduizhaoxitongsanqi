param(
    [string]$PythonPath = "D:\Users\weis\Documents\New project\tools\runtime\python314\python.exe"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$desktopRoot = Join-Path $projectRoot "desktop-shell"
$buildRoot = Join-Path $projectRoot "build\desktop"
$backendDist = Join-Path $buildRoot "backend"
$workPath = Join-Path $buildRoot "pyinstaller-work"
$specPath = Join-Path $buildRoot "pyinstaller-spec"

function Assert-LastExitCode([string]$step) {
    if ($LASTEXITCODE -ne 0) {
        throw "$step failed with exit code $LASTEXITCODE"
    }
}

New-Item -ItemType Directory -Force -Path $backendDist, $workPath, $specPath | Out-Null

& $PythonPath -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --name product-matcher-server `
  --distpath $backendDist `
  --workpath $workPath `
  --specpath $specPath `
  --paths (Join-Path $projectRoot "src") `
  --add-data ((Join-Path $projectRoot "src\product_matcher\templates") + ";product_matcher\templates") `
  --add-data ((Join-Path $projectRoot "src\product_matcher\static") + ";product_matcher\static") `
  (Join-Path $projectRoot "src\product_matcher\desktop_server.py")
Assert-LastExitCode "PyInstaller build"

Push-Location $desktopRoot
try {
    if (-not (Test-Path (Join-Path $desktopRoot "node_modules"))) {
        npm install
        Assert-LastExitCode "npm install"
    }
    npm run build
    Assert-LastExitCode "electron-builder build"
}
finally {
    Pop-Location
}
