@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0phase3_app\scripts\start_dev_debug.ps1"
if errorlevel 1 pause
