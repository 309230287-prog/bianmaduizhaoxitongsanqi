@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_workbench.ps1"
if errorlevel 1 pause
