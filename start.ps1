# Lichess Analyzer - 백엔드와 프론트엔드를 동시에 실행하는 PowerShell 스크립트

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Lichess Analyzer 시작 중..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 프로젝트 루트로 이동
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

# 백엔드 경로 확인
$backendPath = Join-Path $projectRoot "backend"
$venvPython = Join-Path $backendPath "venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "오류: 가상 환경을 찾을 수 없습니다." -ForegroundColor Red
    Write-Host "백엔드 폴더에서 가상 환경을 생성하세요: python -m venv venv" -ForegroundColor Yellow
    exit 1
}

# 프론트엔드 경로 확인
$frontendPath = Join-Path $projectRoot "frontend"
$nodeModules = Join-Path $frontendPath "node_modules"

if (-not (Test-Path $nodeModules)) {
    Write-Host "경고: node_modules를 찾을 수 없습니다." -ForegroundColor Yellow
    Write-Host "프론트엔드 폴더에서 의존성을 설치하세요: npm install" -ForegroundColor Yellow
    Write-Host ""
}

Write-Host "[1/2] 백엔드 서버 시작 중..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$backendPath'; .\venv\Scripts\Activate.ps1; python -m uvicorn main:app --reload --port 8000" -WindowStyle Normal

# 백엔드가 시작될 시간 대기
Start-Sleep -Seconds 3

Write-Host "[2/2] 프론트엔드 서버 시작 중..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$frontendPath'; npm run dev" -WindowStyle Normal

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "실행 완료!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "백엔드: http://localhost:8000" -ForegroundColor Yellow
Write-Host "프론트엔드: http://localhost:3000" -ForegroundColor Yellow
Write-Host ""
Write-Host "종료하려면 각 PowerShell 창을 닫으세요." -ForegroundColor Gray
Write-Host ""
Write-Host "계속하려면 아무 키나 누르세요..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")



