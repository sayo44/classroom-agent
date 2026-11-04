@echo off
cd /d "%~dp0"
set PORT=8000
echo Stopping old service on port %PORT% ...
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":%PORT%" ^| findstr "LISTENING"') do taskkill /PID %%P /F >nul 2>&1
timeout /t 1 >nul
echo Starting server ...
start "" /MIN cmd /c "venv\Scripts\python.exe run.py > server.log 2>&1"
timeout /t 5 >nul
start http://127.0.0.1:%PORT%/c/congcong
echo Server started. Log: server.log
pause
