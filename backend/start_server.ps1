# 백엔드 서버를 가상 환경 Python으로 실행하는 PowerShell 스크립트

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

# 가상 환경 Python 경로
$venvPython = Join-Path $scriptPath "venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "Error: venv Python not found at $venvPython" -ForegroundColor Red
    Write-Host "Please create venv first: python -m venv venv" -ForegroundColor Yellow
    exit 1
}

Write-Host "Starting backend server with venv Python..." -ForegroundColor Green
Write-Host "Python: $venvPython" -ForegroundColor Cyan

# venv Python으로 uvicorn 실행
& $venvPython -m uvicorn main:app --reload --port 8000








