@echo off
setlocal
chcp 65001 >nul
REM Start backend server with virtual environment Python

pushd "%~dp0"

REM Activate virtual environment
call "venv\Scripts\activate.bat"

REM Run uvicorn with venv Python
python -m uvicorn main:app --reload --port 8000

popd
