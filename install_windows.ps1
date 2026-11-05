# Classroom Agent - Windows portable install (no system Python required)
# Downloads an embedded Python into lib\python and installs all deps there.
# The app then runs with lib\python\python.exe, fully self-contained per project.
# (No system Python, no venv, nothing written to the system PATH.)
$ErrorActionPreference = 'Continue'
$root = $PSScriptRoot
Set-Location $root

Write-Host ""
Write-Host "===== Classroom Agent Install (Windows, portable) =====" -ForegroundColor Cyan
Write-Host ""

$pyVer  = "3.11.9"
$embedZip = "python-$pyVer-embed-amd64.zip"
$embedUrl = "https://www.python.org/ftp/python/$pyVer/$embedZip"
$libPy  = Join-Path $root "lib\python\python.exe"

# 1) Prepare embedded Python under lib\python (download once, reuse afterwards)
function Ensure-LibPython {
    if (Test-Path $script:libPy) {
        try {
            $v = & $script:libPy --version 2>&1
            Write-Host "[OK] lib\python exists: $v" -ForegroundColor Green
            return $true
        } catch {}
    }
    Write-Host "[!] Downloading embedded Python $pyVer into lib\python ..." -ForegroundColor Yellow
    $tmp = Join-Path $env:TEMP $embedZip
    try {
        Invoke-WebRequest -Uri $embedUrl -OutFile $tmp -ErrorAction Stop
    } catch {
        Write-Host "[X] Download failed: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
    $dest = Join-Path $root "lib\python"
    if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
    Expand-Archive -Path $tmp -DestinationPath $dest -Force
    Remove-Item $tmp -ErrorAction SilentlyContinue
    # Embedded Python disables 'import site' by default, which blocks any pip-installed
    # package from loading. Re-enable it and make sure Lib\site-packages is on the path.
    $pth = Get-ChildItem $dest -Filter "python3*._pth" | Select-Object -First 1
    if ($pth) {
        $txt = Get-Content $pth.FullName
        $txt = $txt -replace '#import site', 'import site'
        if (-not ($txt -match 'Lib\\site-packages')) { $txt += "`nLib\site-packages" }
        Set-Content $pth.FullName $txt -Encoding ASCII
    }
    Write-Host "[OK] Embedded Python ready at lib\python" -ForegroundColor Green
    return $true
}

if (-not (Ensure-LibPython)) {
    Read-Host "Press Enter to exit"
    exit 1
}

$libPip = Join-Path $root "lib\python\Scripts\pip.exe"

# 2) Bootstrap pip into lib\python if missing
if (-not (Test-Path $libPip)) {
    Write-Host "[!] Bootstrapping pip into lib\python ..." -ForegroundColor Yellow
    $getpip = Join-Path $env:TEMP "get-pip.py"
    try {
        Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile $getpip -ErrorAction Stop
        & $libPy $getpip --no-warn-script-location
        Remove-Item $getpip -ErrorAction SilentlyContinue
    } catch {
        Write-Host "[X] pip bootstrap failed: $($_.Exception.Message)" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
}

# 3) Install dependencies into lib\python\Lib\site-packages (first run downloads a lot)
Write-Host "[2/4] Installing dependencies into lib\python (first run is large, please wait)..." -ForegroundColor Green
& $libPip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --no-warn-script-location
if ($LASTEXITCODE -ne 0) {
    Write-Host "Mirror failed, retry without mirror..." -ForegroundColor Yellow
    & $libPip install -r requirements.txt --no-warn-script-location
}
# optional: traditional -> simplified Chinese (non-fatal if it fails)
& $libPip install opencc-python-reimplemented --no-warn-script-location 2>$null

# 4) .env
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") { Copy-Item ".env.example" ".env" }
    Write-Host "[3/4] Created .env from .env.example" -ForegroundColor Green
    Write-Host "      [!] Edit .env and set LLM_API_KEY, or chat will not work." -ForegroundColor Yellow
} else {
    Write-Host "[3/4] .env exists, skip" -ForegroundColor Green
}

# warn if local STT model is missing
if (-not (Test-Path "models\faster-whisper-base")) {
    Write-Host "[!] Local STT model models\faster-whisper-base not found; voice input disabled." -ForegroundColor Yellow
    Write-Host "    Run: lib\python\python.exe scripts\download_model.py" -ForegroundColor Yellow
}

Write-Host "[4/4] Environment ready." -ForegroundColor Green
Write-Host "Next: double-click start_windows.bat to launch (console stays open so you can see errors)." -ForegroundColor Cyan
Write-Host "Admin:  http://127.0.0.1:8000/    Chat: http://127.0.0.1:8000/c/congcong" -ForegroundColor Cyan
Read-Host "Press Enter to close this window"
