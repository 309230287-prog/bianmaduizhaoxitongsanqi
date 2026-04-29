@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_dev_debug.ps1"
if errorlevel 1 pause
