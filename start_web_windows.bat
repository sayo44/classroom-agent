@echo off
cd /d "%~dp0"
REM Web 版本地部署：使用项目自带 lib\python（不依赖用户 PC 安装 Python），起 FastAPI 服务 + 自动开浏览器
if not exist "lib\python\python.exe" (
    echo [!] lib\python not found. Run install_windows.bat first.
    pause
    exit /b 1
)
set OPEN_BROWSER=1
echo Using portable Python: lib\python\python.exe
echo Server will start, browser opens automatically.
echo If errors appear below, they show the real cause - screenshot and send to dev.
echo.
lib\python\python.exe run_app.py
pause
