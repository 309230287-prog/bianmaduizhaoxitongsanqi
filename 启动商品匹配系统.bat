@echo off
chcp 65001 >nul
setlocal

set "APP_ROOT=%~dp0"
cd /d "%APP_ROOT%"

set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "PYTHONPATH=%APP_ROOT%src"

where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Please install Python or add it to PATH.
  pause
  exit /b 1
)

python -c "import fastapi, uvicorn, jinja2, openpyxl, multipart" >nul 2>nul
if errorlevel 1 (
  echo First run: installing dependencies, please wait...
  python -m pip install -r "%APP_ROOT%requirements.txt"
  if errorlevel 1 (
    echo Dependency installation failed. Please send the error above to the developer.
    pause
    exit /b 1
  )
)

echo Starting Product Matcher. The browser should open automatically...
python "%APP_ROOT%scripts\start_app.py"

if errorlevel 1 (
  echo Startup failed. Please send the error above to the developer.
  pause
  exit /b 1
)
