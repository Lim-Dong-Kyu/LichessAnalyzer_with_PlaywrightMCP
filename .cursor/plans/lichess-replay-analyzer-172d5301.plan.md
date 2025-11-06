<!-- 172d5301-f2c1-4c62-95b4-6ed3fedec801 e8ea6c72-e4a6-423e-9c7c-61ef02269afe -->
# Lichess Replay Analyzer with Playwright MCP 구현 계획

## 프로젝트 구조

```
lichess_analyzer/
├── backend/                 # Python FastAPI 백엔드
│   ├── main.py             # FastAPI 앱 및 라우팅
│   ├── lichess_api.py      # Lichess API 클라이언트
│   ├── analyzer.py         # 평가 계산 및 분류 로직
│   ├── mcp_client.py       # MCP 클라이언트 호출 (Node.js 서브프로세스)
│   ├── models.py           # Pydantic 모델
│   ├── requirements.txt    # Python 의존성
│   └── .env.example        # 환경 변수 템플릿
├── mcp-client/             # Node.js MCP 클라이언트
│   ├── capture.js          # Playwright MCP 캡처 로직
│   └── package.json        # Node.js 의존성
├── frontend/               # Next.js 프론트엔드
│   ├── pages/              # Next.js Pages 라우팅
│   ├── components/         # React 컴포넌트
│   ├── styles/             # Tailwind CSS
│   ├── package.json
│   └── next.config.js
├── reports/                # JSON 리포트 저장소
├── captures/               # 리플레이 이미지 저장소
├── README.md               # 프로젝트 문서
└── .gitignore
```

## 구현 단계

### 1. 프로젝트 초기 설정 및 구조 생성

- 디렉토리 구조 생성
- `.gitignore` 설정
- `README.md` 작성

### 2. Backend 구현 (Python FastAPI)

**2.1 Lichess API 클라이언트 (`backend/lichess_api.py`)**

- `GET /api/game/export/{gameId}` - PGN, 오프닝, 플레이어 정보 수집
- `GET /api/cloud-eval?fen=<FEN>` - 각 수의 Cloud Eval 데이터 획득
- FEN 파싱 및 게임 상태 관리

**2.2 분석 로직 (`backend/analyzer.py`)**

- 각 수의 평가 차이(Δcp/mate) 계산
- 카테고리 분류 함수 (Accurate/Good/Inaccuracy/Mistake/Blunder)
- 평가 기준:
        - Accurate: |Δcp| < 10
        - Good: 10 ≤ |Δcp| < 50
        - Inaccuracy: 50 ≤ |Δcp| < 100
        - Mistake: 100 ≤ |Δcp| < 300
        - Blunder: |Δcp| ≥ 300

**2.3 데이터 모델 (`backend/models.py`)**

- GameData, MoveEvaluation, AnalysisReport 등 Pydantic 모델

**2.4 MCP 클라이언트 통합 (`backend/mcp_client.py`)**

- Node.js 스크립트를 서브프로세스로 실행
- Playwright MCP를 통해 리플레이 캡처
- `captures/{gameId}-{ply}.png` 형식으로 이미지 저장

**2.5 FastAPI 메인 앱 (`backend/main.py`)**

- `/api/analyze` - 게임 링크 입력 받아 분석 시작
- `/api/report/{gameId}` - 리포트 조회
- `/api/capture/{gameId}/{ply}` - 특정 수순 이미지 조회
- 정적 파일 서빙 (reports/, captures/)

### 3. MCP 클라이언트 구현 (Node.js)

**3.1 캡처 스크립트 (`mcp-client/capture.js`)**

- Playwright MCP 서버 연결 (별도 실행 중인 서버 사용)
- Lichess 리플레이 페이지 탐색
- 각 ply로 이동 (`keyboard` 입력으로 이전/다음 수 조작)
- `.cg-board` 영역 스크린샷
- `getAccessibilityTree`로 메타데이터 추출
- 이미지 저장

### 4. Frontend 구현 (Next.js)

**4.1 프로젝트 설정**

- Next.js 초기화
- Tailwind CSS 설정
- API 클라이언트 유틸리티

**4.2 메인 페이지 (`frontend/pages/index.tsx`)**

- 게임 링크 입력 폼
- 분석 상태 표시 (로딩/진행률)
- 결과 요약 표시

**4.3 리포트 페이지 (`frontend/pages/report/[gameId].tsx`)**

- 무브별 카드 리스트
- 각 카드 구성:
        - 썸네일 이미지
        - Δcp 값
        - 추천 수
        - 평가 카테고리 배지
        - "해당 수로 이동" 버튼

**4.4 컴포넌트 (`frontend/components/`)**

- `MoveCard.tsx` - 무브별 카드 컴포넌트
- `AnalysisSummary.tsx` - 요약 통계
- `GameHeader.tsx` - 게임 기본 정보

### 5. 통합 및 테스트

- 백엔드-프론트엔드 API 연동 확인
- MCP 클라이언트 호출 테스트
- 전체 플로우 검증

## 핵심 파일 상세

**`backend/main.py` 주요 엔드포인트:**

```python
POST /api/analyze
  - body: { gameUrl: string }
  - response: { gameId: string, status: string }

GET /api/report/{gameId}
  - response: AnalysisReport (JSON)

GET /api/capture/{gameId}/{ply}
  - response: image/png
```

**`backend/analyzer.py` 평가 함수:**

- `calculate_evaluation_delta()` - 평가 차이 계산
- `categorize_move()` - 카테고리 분류
- `generate_summary()` - 요약 텍스트 생성

**`mcp-client/capture.js` MCP 호출:**

- `navigate()` - Lichess 리플레이 페이지 접근
- `click()`, `keyboard()` - 수순 이동
- `screenshot()` - 보드 영역 캡처

## 의존성

**Backend:**

- fastapi, uvicorn
- httpx (Lichess API 클라이언트)
- pydantic (데이터 검증)
- python-chess (PGN/FEN 파싱)

**MCP Client:**

- @modelcontextprotocol/sdk
- playwright (브라우저 자동화)

**Frontend:**

- next, react, react-dom
- tailwindcss
- axios 또는 fetch API

## 실행 방법

1. Backend: `cd backend && pip install -r requirements.txt && uvicorn main:app --port 8000`
2. MCP Server: 별도로 실행 중이어야 함
3. Frontend: `cd frontend && npm install && npm run dev`
4. 브라우저에서 `http://localhost:3000` 접속

### To-dos

- [ ] 프로젝트 디렉토리 구조 생성 및 기본 설정 파일 작성 (.gitignore, README.md)
- [ ] Lichess API 클라이언트 구현 (게임 데이터 수집, Cloud Eval 호출)
- [ ] 평가 계산 및 분류 로직 구현 (Δcp 계산, 카테고리 분류, 요약 생성)
- [ ] MCP 클라이언트 통합 (Node.js 서브프로세스 호출)
- [ ] FastAPI 메인 앱 및 API 엔드포인트 구현
- [ ] Node.js MCP 클라이언트 구현 (Playwright MCP로 리플레이 캡처)
- [ ] Next.js 프로젝트 초기화 및 Tailwind CSS 설정
- [ ] React 컴포넌트 구현 (MoveCard, AnalysisSummary, GameHeader)
- [ ] Next.js 페이지 구현 (메인 페이지, 리포트 페이지)
- [ ] 전체 플로우 통합 테스트 및 버그 수정