# 빠른 시작 가이드

## 1단계: 프로젝트 클론 및 위치 이동

```bash
cd c:\Projects\lichess_analyzer
```

## 2단계: Backend 설정

### Python 가상 환경 생성 (권장)

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### 의존성 설치

```bash
pip install -r requirements.txt
```

### MCP SDK 설치 확인

MCP SDK는 `requirements.txt`에 포함되어 있으므로 별도 설치가 필요 없습니다.
필요한 경우:
```bash
pip install mcp
```

### 환경 변수 설정 (선택사항)

프로젝트 루트에 `.env` 파일 생성:

```bash
cd ..  # 프로젝트 루트로 이동
copy backend\env.example .env
```

`.env` 파일을 열어서 필요시 수정:

```env
LICHESS_API_TOKEN=your_token_here  # 선택사항, rate limit 완화
OPENAI_API_KEY=your_openai_api_key_here  # 선택사항, AI 분석 기능 사용 시 필요
```

## 3단계: Frontend 설정

### 새 터미널에서 실행 (Backend 실행과 별도로)

```bash
cd frontend
npm install
```

## 4단계: Backend 실행

Backend 터미널에서:

```bash
cd backend
uvicorn main:app --reload --port 8000
```

성공하면 다음과 같은 메시지가 표시됩니다:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

## 5단계: Frontend 실행

Frontend 터미널에서:

```bash
cd frontend
npm run dev
```

성공하면 다음과 같은 메시지가 표시됩니다:
```
  ▲ Next.js 14.x.x
  - Local:        http://localhost:3000
```

## 6단계: 브라우저에서 접속

브라우저를 열고 다음 주소로 접속:
```
http://localhost:3000
```

## 사용하기

1. Lichess 게임 링크 입력 (예: `https://lichess.org/ABC123`)
2. "분석 시작" 버튼 클릭
3. 분석 완료 후 리포트 페이지에서 결과 확인

## 문제 해결

### Backend 실행 오류

**오류: `ModuleNotFoundError`**
```bash
# 가상 환경이 활성화되어 있는지 확인
# requirements.txt 재설치
pip install -r requirements.txt
```

**오류: `mcp` 모듈을 찾을 수 없음**
```bash
pip install mcp
```

### Frontend 실행 오류

**오류: `npm`을 찾을 수 없음**
- Node.js가 설치되어 있는지 확인: `node --version`
- Node.js 18 이상이 필요합니다

**오류: 포트 3000이 이미 사용 중**
```bash
# 다른 포트 사용
npm run dev -- -p 3001
```

### MCP 연결 오류

**오류: MCP 서버를 찾을 수 없음**
- 환경 변수 확인:
  ```bash
  echo %MCP_SERVER_COMMAND%
  echo %MCP_SERVER_ARGS%
  ```
- `.env` 파일에서 MCP 설정 확인

## 실행 순서 요약

1. ✅ Backend 디렉토리에서 의존성 설치 (`pip install -r requirements.txt`)
2. ✅ MCP SDK 설치 (`pip install mcp`)
3. ✅ Backend 실행 (`uvicorn main:app --reload --port 8000`)
4. ✅ Frontend 디렉토리에서 의존성 설치 (`npm install`)
5. ✅ Frontend 실행 (`npm run dev`)
6. ✅ 브라우저에서 `http://localhost:3000` 접속




