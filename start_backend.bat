@echo off
setlocal
chcp 65001 >nul
REM Start backend server

pushd "%~dp0backend"
call "start_server.bat"
pause
popd
