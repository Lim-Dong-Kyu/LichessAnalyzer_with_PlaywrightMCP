#!/bin/bash
# Lichess Analyzer - 백엔드와 프론트엔드를 동시에 실행하는 스크립트 (Linux/Mac)

echo "========================================"
echo "Lichess Analyzer 시작 중..."
echo "========================================"
echo ""

# 프로젝트 루트로 이동
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 백엔드 경로 확인
BACKEND_DIR="$SCRIPT_DIR/backend"
VENV_PYTHON="$BACKEND_DIR/venv/bin/python"

if [ ! -f "$VENV_PYTHON" ]; then
    echo "오류: 가상 환경을 찾을 수 없습니다."
    echo "백엔드 폴더에서 가상 환경을 생성하세요: python -m venv venv"
    exit 1
fi

# 프론트엔드 경로 확인
FRONTEND_DIR="$SCRIPT_DIR/frontend"
NODE_MODULES="$FRONTEND_DIR/node_modules"

if [ ! -d "$NODE_MODULES" ]; then
    echo "경고: node_modules를 찾을 수 없습니다."
    echo "프론트엔드 폴더에서 의존성을 설치하세요: npm install"
    echo ""
fi

echo "[1/2] 백엔드 서버 시작 중..."
cd "$BACKEND_DIR"
source venv/bin/activate
python -m uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!

# 백엔드가 시작될 시간 대기
sleep 3

echo "[2/2] 프론트엔드 서버 시작 중..."
cd "$FRONTEND_DIR"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "========================================"
echo "실행 완료!"
echo "========================================"
echo ""
echo "백엔드: http://localhost:8000"
echo "프론트엔드: http://localhost:3000"
echo ""
echo "종료하려면 Ctrl+C를 누르세요."
echo ""

# 종료 시그널 처리
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM

# 프로세스가 종료될 때까지 대기
wait



