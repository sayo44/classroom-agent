@echo off
cd /d "%~dp0"
REM 桌面窗口版：使用项目自带 lib\python（不依赖用户 PC 安装 Python），开 pywebview 原生窗口
if not exist "lib\python\python.exe" (
    echo [!] lib\python not found. Run install_windows.bat first.
    pause
    exit /b 1
)
echo Using portable Python: lib\python\python.exe
echo Desktop window will open. If errors appear below, they show the real cause.
echo.
lib\python\python.exe launch_desktop.py
pause
