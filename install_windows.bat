@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "install_windows.ps1"
