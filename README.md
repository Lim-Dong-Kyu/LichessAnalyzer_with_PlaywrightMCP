# Lichess Replay Analyzer with Playwright MCP

Lichess 공식 API와 Playwright MCP(Model Context Protocol)를 통합하여 체스 기보를 자동 분석하고 각 수의 평가를 시각적으로 리포트하는 AI 기반 분석 플랫폼입니다.

## 기능

1. **Lichess API 연동**
   - 게임 데이터(PGN, 오프닝, 플레이어 정보) 수집
   - Cloud Eval을 통한 각 수의 평가 데이터 획득

2. **AI 기반 분석**
   - 각 수의 평가 차이(Δcp/mate) 계산
   - 카테고리 분류 (Accurate / Good / Inaccuracy / Mistake / Blunder)
   - OpenAI GPT를 통한 게임 총평 생성
   - OpenAI GPT를 통한 특정 수에 대한 AI 분석

3. **Playwright MCP 자동화**
   - MCP 세션을 애플리케이션 시작 시 전역으로 관리 (효율적인 연결 재사용)
   - 브라우저를 통해 Lichess 분석 도구 자동 열기
   - 현재 기보 상태로 분석 도구 설정

4. **웹 UI**
   - 분석 결과 요약 및 시각화
   - 게임 통계 (백/흑 각각의 통계)
   - 기보 네비게이션 (1수, 10수 단위 이동 지원)
   - 각 수에 대한 상세 평가 정보
   - AI 분석 결과 표시

## 프로젝트 구조

```
lichess_analyzer/
├── backend/          # Python FastAPI 백엔드
├── mcp-client/       # Node.js MCP 클라이언트
└── frontend/         # Next.js 프론트엔드
```

## 빠른 시작

가장 빠르게 시작하려면 `QUICKSTART.md` 파일을 참고하세요.

### Windows에서 빠른 실행

```bash
# 1. Backend 설정
cd backend
pip install -r requirements.txt

# 2. Frontend 설정
cd ../frontend
npm install

# 3. 환경 변수 설정 (선택사항)
cd ..
# .env 파일 생성 (LICHESS_API_TOKEN, OPENAI_API_KEY 등)

# 4. 실행
start.bat
```

`start.bat`을 실행하면 백엔드와 프론트엔드가 자동으로 시작됩니다.

### 수동 실행

```bash
# 1. Backend 설정
cd backend
pip install -r requirements.txt

# 2. 환경 변수 설정 (선택사항)
cd ..
# .env 파일 생성 (LICHESS_API_TOKEN, OPENAI_API_KEY 등)

# 3. Backend 실행 (터미널 1)
cd backend
uvicorn main:app --reload --port 8000

# 4. Frontend 설정 및 실행 (터미널 2)
cd frontend
npm install
npm run dev

# 5. 브라우저에서 http://localhost:3000 접속
```

## 설치 및 실행

### 사전 요구사항

- Python 3.9+
- Node.js 18+ (Frontend용)
- pip 및 npm이 설치되어 있어야 합니다

### 환경 변수 설정

프로젝트 루트에 `.env` 파일을 생성하여 다음 환경 변수들을 설정할 수 있습니다:

#### 프로젝트 루트 `.env` 파일 (Backend/MCP Client용)

```bash
# Lichess API 토큰 (선택사항, rate limit 완화를 위해 권장)
# 토큰 생성: https://lichess.org/account/oauth/token/create
LICHESS_API_TOKEN=your_lichess_api_token_here

# OpenAI API 키 (AI 분석 기능 사용 시 필요)
# API 키 생성: https://platform.openai.com/api-keys
OPENAI_API_KEY=your_openai_api_key_here

# MCP 서버 설정 (선택사항, Cursor 설정 파일에서 자동 읽기 가능)
# MCP 서버 명령어 (기본값: "npx")
MCP_SERVER_COMMAND=npx

# MCP 서버 인자 (기본값: "-y @playwright/mcp")
# 공백으로 구분된 인자들을 하나의 문자열로 입력
MCP_SERVER_ARGS=-y @playwright/mcp
```

#### Frontend `.env.local` 파일 (선택사항)

```bash
# API 베이스 URL (기본값: "http://localhost:8000")
# Backend가 다른 포트나 도메인에서 실행되는 경우에만 설정
NEXT_PUBLIC_API_BASE=http://localhost:8000
```

**참고**: 
- 프로젝트 루트: `backend/env.example` 파일을 참고하여 `.env` 파일 생성
- Frontend: 필요시 `frontend/.env.local` 파일을 직접 생성하여 `NEXT_PUBLIC_API_BASE` 설정
- 모든 환경 변수는 선택사항이며, 설정하지 않으면 기본값이 사용됩니다.

### 1. Backend 설정

```bash
cd backend
pip install -r requirements.txt
```

**참고**: 
- MCP SDK는 requirements.txt에 포함되어 있습니다
- OpenAI SDK도 requirements.txt에 포함되어 있습니다
- Cursor의 MCP 서버 설정이 필요합니다 (Cursor IDE에서 설정)
- MCP 세션은 애플리케이션 시작 시 자동으로 초기화됩니다

### 2. Frontend 설정

```bash
cd frontend
npm install
npm run dev
```

### 실행 순서

#### 방법 1: 자동 실행 (Windows)

1. Cursor에서 Playwright MCP 서버 설정 (이미 설정되어 있다면 생략 가능)
2. `start.bat` 실행 - 백엔드와 프론트엔드가 자동으로 시작됩니다
3. 브라우저에서 `http://localhost:3000` 접속

#### 방법 2: 수동 실행

1. Cursor에서 Playwright MCP 서버 설정 (이미 설정되어 있다면 생략 가능)
2. Backend 실행 (포트 8000): `cd backend && uvicorn main:app --reload --port 8000`
3. Frontend 실행 (포트 3000): `cd frontend && npm run dev`
4. 브라우저에서 `http://localhost:3000` 접속

**참고**: 
- Cursor의 Playwright MCP가 설정되어 있어야 합니다
- MCP 서버는 백엔드에서 자동으로 연결됩니다

## 사용 방법

1. Lichess 게임 링크 입력 (예: `https://lichess.org/ABC123`)
2. 분석 시작 버튼 클릭
3. 리포트 페이지에서 다음을 확인할 수 있습니다:
   - 게임 정보 (플레이어, 결과, 오프닝)
   - 게임 통계 (백/흑 각각의 통계)
   - AI 게임 총평 (OpenAI GPT 기반)
   - 기보 보기 (기보 네비게이션으로 수순 이동)
     - 이전/다음 버튼으로 1수씩 이동
     - -10/+10 버튼으로 10수씩 이동
   - 각 수에 대한 상세 평가 정보
   - AI 수 분석 기능 (각 수에 대한 GPT 분석)
   - 연구하기 기능 (Lichess 분석 도구 자동 열기)

## API 엔드포인트

- `POST /api/analyze` - 게임 분석 시작
  - Request: `{ "gameUrl": "https://lichess.org/ABC123" }`
  - Response: `{ "gameId": "ABC123", "status": "started", "message": "..." }`

- `GET /api/game/{gameId}` - 게임 데이터 조회
  - Response: 게임 정보 (플레이어, 기보, 오프닝 등)

- `GET /api/eval/{gameId}/{ply}` - 특정 수의 평가 정보 조회
  - Response: 평가 정보 (이전/이후 평가, Δcp, 카테고리 등)

- `GET /api/stats/{gameId}` - 게임 통계 조회
  - Response: 백/흑 각각의 통계 정보

- `GET /api/analysis/{gameId}` - AI 게임 총평 생성
  - Response: OpenAI를 통한 게임 총평

- `GET /api/move-analysis/{gameId}/{ply}` - AI 수 분석 생성
  - Response: OpenAI를 통한 특정 수에 대한 분석

- `POST /api/research/{gameId}/{ply}` - Lichess 분석 도구 열기
  - Response: 열린 브라우저 URL

- `GET /api/capture/{gameId}/{ply}` - 보드 이미지 URL 조회
  - Response: 보드 이미지 URL

- `GET /api/status/{gameId}` - 분석 상태 확인
  - Response: 분석 상태 정보

## 평가 카테고리 기준

- **Accurate**: |Δcp| < 10
- **Good**: 10 ≤ |Δcp| < 50
- **Inaccuracy**: 50 ≤ |Δcp| < 100
- **Mistake**: 100 ≤ |Δcp| < 300
- **Blunder**: |Δcp| ≥ 300

## 기술 스택

- **Backend**: 
  - FastAPI (웹 프레임워크)
  - Python 3.9+
  - httpx (비동기 HTTP 클라이언트)
  - python-chess (체스 기보 처리)
  - MCP SDK (Model Context Protocol)
  - OpenAI SDK (AI 분석 기능)
  
- **Frontend**: 
  - Next.js 16.0.1
  - React 19.2.0
  - TypeScript
  - Tailwind CSS
  
- **External API**: 
  - Lichess Cloud Eval API
  - OpenAI API (ChatGPT)
  
- **Browser Automation**: 
  - Cursor Playwright MCP (Python MCP SDK를 통해 연결, 전역 세션 관리)

## 문제 해결

### MCP 연결 오류
- MCP SDK가 설치되었는지 확인: `pip install mcp`
- Cursor에서 Playwright MCP 서버가 설정되어 있는지 확인
- 환경 변수 `MCP_SERVER_COMMAND` 및 `MCP_SERVER_ARGS` 설정 확인
- MCP 세션 초기화 로그 확인 (백엔드 시작 시 "MCP session initialized successfully" 메시지 확인)
- MCP 기본값: `MCP_SERVER_COMMAND=npx`, `MCP_SERVER_ARGS=-y @playwright/mcp`

### OpenAI API 오류
- OpenAI API 키가 설정되었는지 확인: `.env` 파일에 `OPENAI_API_KEY` 설정
- API 키 생성: https://platform.openai.com/api-keys
- API 키가 유효한지 확인 (충전된 계정인지 확인)
- API 호출 한도 확인

### API 호출 오류
- Backend가 실행 중인지 확인 (포트 8000)
- CORS 설정 확인 (프론트엔드는 localhost:3000에서 실행되어야 함)
- 네트워크 연결 확인

### 프론트엔드 오류
- Node.js 버전 확인 (18+ 필요): `node --version`
- 의존성 재설치: `cd frontend && rm -rf node_modules && npm install`
- 포트 충돌 시 다른 포트 사용: `npm run dev -- -p 3001`
