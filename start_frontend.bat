@echo off
setlocal
chcp 65001 >nul
REM Start frontend server

pushd "%~dp0frontend"
npm run dev
pause
popd
