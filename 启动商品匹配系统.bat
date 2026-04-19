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
  echo 没有找到 Python。请先安装 Python，或者把 Python 加入 PATH。
  pause
  exit /b 1
)

python -c "import fastapi, uvicorn, jinja2, openpyxl, multipart" >nul 2>nul
if errorlevel 1 (
  echo 首次启动：正在安装依赖，请稍等...
  python -m pip install -r "%APP_ROOT%requirements.txt"
  if errorlevel 1 (
    echo 依赖安装失败，请把上面的错误发给开发人员。
    pause
    exit /b 1
  )
)

echo 正在启动系统，浏览器会自动打开二期工作台...
python "%APP_ROOT%scripts\start_app.py"

if errorlevel 1 (
  echo 系统启动失败，请把上面的错误发给开发人员。
  pause
  exit /b 1
)
