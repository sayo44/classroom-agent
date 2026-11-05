@echo off
cd /d "%~dp0"
echo Using portable Python: lib\python\python.exe
echo If errors appear below, they show the real cause - screenshot and send to dev.
echo.
lib\python\python.exe launch_desktop.py
pause
