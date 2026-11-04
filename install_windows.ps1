# Classroom Agent - Windows one-click install & deploy
# Launched by install_windows.bat
$ErrorActionPreference = 'Continue'
$root = $PSScriptRoot
Set-Location $root

Write-Host ""
Write-Host "===== Classroom Agent Install (Windows) =====" -ForegroundColor Cyan
Write-Host ""

# 1) Detect Python >= 3.10
function Find-Python {
    $cands = @('py', 'python', 'python3')
    foreach ($c in $cands) {
        try {
            $out = & $c --version 2>&1
            if ($out -match 'Python (\d+)\.(\d+)') {
                return @{cmd=$c; maj=[int]$matches[1]; min=[int]$matches[2]; ver=$out}
            }
        } catch {}
    }
    return $null
}

# 自动下载并静默安装 Python（用户级，自动加入 PATH），无需手动安装
function Install-Python {
    # 锁版本：3.11 系列对 PyInstaller / faster-whisper 兼容性最稳
    $ver = "3.11.9"
    $url = "https://www.python.org/ftp/python/$ver/python-$ver-amd64.exe"
    $installer = Join-Path $env:TEMP "python-$ver-amd64.exe"
    Write-Host "[!] Python not found. Auto-downloading & installing Python $ver ..." -ForegroundColor Yellow
    try {
        Invoke-WebRequest -Uri $url -OutFile $installer -ErrorAction Stop
    } catch {
        Write-Host "[X] Download failed: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "    Install Python 3.10+ manually: https://www.python.org/downloads/" -ForegroundColor Yellow
        Read-Host "Press Enter to exit"
        exit 1
    }
    Write-Host "[!] Installing Python silently (user-level, added to PATH)..." -ForegroundColor Yellow
    # /quiet 静默；PrependPath=1 加入当前用户 PATH；Include_pip=1 确保 pip
    Start-Process -FilePath $installer -ArgumentList "/quiet", "PrependPath=1", "Include_pip=1" -Wait
    Remove-Item $installer -ErrorAction SilentlyContinue
    # 安装程序改写了用户 PATH 注册表，但当前进程需手动重读才能找到 python
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "User") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "Machine")
    Write-Host "[OK] Python installed." -ForegroundColor Green
}

$py = Find-Python
if (-not $py) {
    Install-Python
    $py = Find-Python
    if (-not $py) {
        Write-Host "[X] Python auto-install failed. Install 3.10+ manually: https://www.python.org/downloads/" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
}
if ($py.maj -lt 3 -or ($py.maj -eq 3 -and $py.min -lt 10)) {
    Write-Host "[X] Python too old: $($py.ver). Need 3.10 or newer. Please upgrade manually." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "[1/5] Python: $($py.ver)" -ForegroundColor Green

# 2) Virtual environment
$venvPy = Join-Path $root "venv\Scripts\python.exe"
$venvPip = Join-Path $root "venv\Scripts\pip.exe"
if (-not (Test-Path $venvPy)) {
    Write-Host "[2/5] Creating venv ..." -ForegroundColor Green
    & $py.cmd -m venv venv
} else {
    Write-Host "[2/5] venv exists, skip" -ForegroundColor Green
}

# 3) Install dependencies (Tsinghua mirror for CN; remove -i for other regions)
Write-Host "[3/5] Installing dependencies (first run is large, please wait)..." -ForegroundColor Green
& $venvPip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
if ($LASTEXITCODE -ne 0) {
    Write-Host "Mirror failed, retry without mirror..." -ForegroundColor Yellow
    & $venvPip install -r requirements.txt
}
# optional: traditional -> simplified Chinese (non-fatal if it fails)
& $venvPip install opencc-python-reimplemented 2>$null

# 4) .env
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") { Copy-Item ".env.example" ".env" }
    Write-Host "[4/5] Created .env from .env.example" -ForegroundColor Green
    Write-Host "      [!] Edit .env and set LLM_API_KEY, or chat will not work." -ForegroundColor Yellow
} else {
    Write-Host "[4/5] .env exists, skip" -ForegroundColor Green
}

# warn if local STT model is missing
if (-not (Test-Path "models\faster-whisper-base")) {
    Write-Host "[!] Local STT model models\faster-whisper-base not found; voice input disabled." -ForegroundColor Yellow
    Write-Host "    Run: venv\Scripts\python.exe scripts\download_model.py" -ForegroundColor Yellow
}

# 5) Start service
Write-Host "[5/5] Starting service..." -ForegroundColor Green
try {
    $conns = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Where-Object { $_.State -eq 'Listen' }
    foreach ($c in $conns) { Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue }
} catch {}

Start-Process -FilePath $venvPy -ArgumentList "run.py" -RedirectStandardOutput "server.log" -RedirectStandardError "server.log" -WindowStyle Hidden

Start-Sleep -Seconds 5
try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:8000/" -UseBasicParsing -TimeoutSec 6
    if ($r.StatusCode -eq 200) { Write-Host "[OK] Server is up." -ForegroundColor Green }
} catch {
    Write-Host "[!] Server may not be ready yet, check server.log" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Admin:  http://127.0.0.1:8000/" -ForegroundColor Cyan
Write-Host "Chat:   http://127.0.0.1:8000/c/congcong" -ForegroundColor Cyan
Start-Process "http://127.0.0.1:8000/c/congcong"
Read-Host "Press Enter to close this window (server keeps running in background)"
