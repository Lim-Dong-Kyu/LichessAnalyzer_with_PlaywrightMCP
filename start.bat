@echo off
setlocal
chcp 65001 >nul
REM Start Lichess Analyzer - Backend and Frontend servers

pushd "%~dp0"

echo ========================================
echo Starting Lichess Analyzer...
echo ========================================
echo.

REM Start backend server
echo [1/2] Starting backend server...
start "" cmd /k "%~dp0start_backend.bat"

REM Wait 3 seconds for backend to start
timeout /t 3 /nobreak >nul

REM Start frontend server
echo [2/2] Starting frontend server...
start "" cmd /k "%~dp0start_frontend.bat"

echo.
echo ========================================
echo Done!
echo ========================================
echo.
echo Backend: http://localhost:8000
echo Frontend: http://localhost:3000
echo.
echo Close each window to stop servers.
echo.
pause
popd
