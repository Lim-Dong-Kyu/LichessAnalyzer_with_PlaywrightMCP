from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from contextlib import asynccontextmanager
import json
import asyncio
import sys
from dotenv import load_dotenv

# .env 파일 로드
backend_dir = Path(__file__).parent
env_file = backend_dir.parent / ".env"
if env_file.exists():
    load_dotenv(env_file)

# 프로젝트 루트를 Python 경로에 추가
project_root = backend_dir.parent
sys.path.insert(0, str(project_root))

from backend.models import AnalysisReport
from backend.lichess_api import extract_game_id, fetch_game_data
from backend.mcp_research import initialize_mcp_session, cleanup_mcp_session
# analyze_game은 더 이상 사용하지 않음 (Lazy Loading 방식 사용)
# from backend.analyzer import analyze_game
# board_image 모듈은 더 이상 사용하지 않음 (Lichess API 직접 사용)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작 시 MCP 세션 초기화, 종료 시 정리"""
    # 시작 시
    print("Initializing MCP session...")
    await initialize_mcp_session()
    
    yield
    
    # 종료 시
    print("Cleaning up MCP session...")
    await cleanup_mcp_session()


app = FastAPI(title="Lichess Replay Analyzer", lifespan=lifespan)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# 모든 응답에 CORS 헤더 강제 추가하는 미들웨어
@app.middleware("http")
async def add_cors_header(request: Request, call_next):
    """모든 응답에 CORS 헤더 추가"""
    origin = request.headers.get("origin")
    if origin and origin in ["http://localhost:3000", "http://127.0.0.1:3000"]:
        allowed_origin = origin
    else:
        allowed_origin = "http://localhost:3000"
    
    try:
        response = await call_next(request)
    except Exception as e:
        # 예외 발생 시에도 CORS 헤더가 있는 응답 반환
        headers = {
            "Access-Control-Allow-Origin": allowed_origin,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
        return JSONResponse(
            status_code=500,
            content={"detail": f"Internal server error: {str(e)}"},
            headers=headers
        )
    
    # CORS 헤더가 없으면 추가 (소문자로도 확인)
    if "access-control-allow-origin" not in response.headers and "Access-Control-Allow-Origin" not in response.headers:
        response.headers["Access-Control-Allow-Origin"] = allowed_origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
    
    return response


# HTTPException에 CORS 헤더 추가하는 예외 핸들러
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTPException에도 CORS 헤더 추가"""
    origin = request.headers.get("origin")
    if origin and origin in ["http://localhost:3000", "http://127.0.0.1:3000"]:
        allowed_origin = origin
    else:
        allowed_origin = "http://localhost:3000"
    
    headers = {
        "Access-Control-Allow-Origin": allowed_origin,
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "*",
        "Access-Control-Allow-Headers": "*",
    }
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=headers
    )

# 진행 상황 추적을 위한 전역 딕셔너리
analysis_progress: dict[str, dict] = {}


class AnalyzeRequest(BaseModel):
    gameUrl: str


class AnalyzeResponse(BaseModel):
    gameId: str
    status: str
    message: str


# analyze_game_task 함수 제거 - load_game_data_task에 통합됨


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze_game_endpoint(request: AnalyzeRequest):
    """게임 분석 시작 (비동기로 실행)"""
    try:
        # 게임 ID 추출 (디버깅을 위해 로그 출력)
        print(f"Received game URL: '{request.gameUrl}'")
        game_id = extract_game_id(request.gameUrl)
        print(f"Extracted game ID: '{game_id}'")
        
        # 진행 상황을 즉시 완료로 설정 (게임 데이터는 리포트 페이지에서 로드)
        # 이렇게 하면 사용자가 즉시 리포트 페이지로 이동할 수 있음
        analysis_progress[game_id] = {
            "status": "completed",
            "progress": 100,
            "current": 0,
            "total": 0,
            "message": "게임 데이터는 리포트 페이지에서 로드됩니다"
        }
        
        # 즉시 응답 반환 (게임 데이터는 리포트 페이지에서 직접 로드)
        return AnalyzeResponse(
            gameId=game_id,
            status="started",
            message="Ready - game data will be loaded on report page"
        )
    
    except ValueError as e:
        print(f"ValueError: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Exception: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.get("/api/game/{game_id}")
async def get_game(game_id: str):
    """게임 데이터만 반환 (평가 없음)"""
    try:
        print(f"[get_game] Fetching game data for: {game_id}")
        game_data = await fetch_game_data(game_id)
        print(f"[get_game] Game data fetched successfully: {game_data.white.username} vs {game_data.black.username}")
        
        return JSONResponse(content={
            "game_id": game_data.game_id,
            "white": {
                "username": game_data.white.username,
                "rating": game_data.white.rating
            },
            "black": {
                "username": game_data.black.username,
                "rating": game_data.black.rating
            },
            "moves": game_data.moves,
            "opening": game_data.opening,
            "result": game_data.result,
            "pgn": game_data.pgn
        })
    except ValueError as e:
        print(f"[get_game] ValueError: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"[get_game] Exception: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to fetch game: {str(e)}")


@app.get("/api/eval/{game_id}/{ply}")
async def get_evaluation(game_id: str, ply: int):
    """Lichess API에서 평가 정보 가져오기 (PGN with evals)"""
    import chess
    import httpx
    from backend.models import CloudEval
    from backend.lichess_api import get_auth_headers
    from backend.game_stats import parse_pgn_with_evals
    
    try:
        # 게임 데이터 가져오기
        game_data = await fetch_game_data(game_id)
        
        if ply < 1 or ply > len(game_data.moves):
            raise HTTPException(status_code=400, detail=f"Invalid ply: {ply}. Game has {len(game_data.moves)} moves.")
        
        # Lichess에서 평가 정보가 포함된 PGN 가져오기
        pgn_url = f"https://lichess.org/game/export/{game_id}?evals=1"
        headers = get_auth_headers()
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(pgn_url, headers=headers)
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Failed to fetch PGN with evals")
            
            pgn_with_evals = response.text
        
        # PGN에서 모든 평가 정보 파싱
        evaluations = parse_pgn_with_evals(pgn_with_evals)
        
        # 해당 ply의 평가 정보 찾기
        eval_data = None
        for eval_item in evaluations:
            if eval_item["ply"] == ply:
                eval_data = eval_item
                break
        
        if not eval_data:
            # 평가 정보가 없으면 기본값 반환
            eval_data = {
                "ply": ply,
                "move": game_data.moves[ply - 1],
                "before_eval": None,
                "after_eval": None,
                "category": "accurate"
            }
        
        # 해당 ply까지 보드 상태 재현
        board = chess.Board()
        
        # ply가 1이면 첫 번째 수만 적용
        # ply가 2 이상이면 ply-1까지 적용 후 ply번째 수 적용
        for i in range(ply - 1):
            if i < len(game_data.moves):
                try:
                    move = board.parse_san(game_data.moves[i])
                    board.push(move)
                except Exception as move_error:
                    print(f"Error parsing move {i} ({game_data.moves[i]}): {move_error}")
                    print(f"Board FEN: {board.fen()}")
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Invalid move at position {i}: {game_data.moves[i]}"
                    )
        
        before_fen = board.fen()
        
        # 현재 수 적용 (ply번째 수)
        if ply <= len(game_data.moves) and ply > 0:
            try:
                move = board.parse_san(game_data.moves[ply - 1])
                board.push(move)
                after_fen = board.fen()
            except Exception as move_error:
                print(f"Error parsing current move {ply - 1} ({game_data.moves[ply - 1]}): {move_error}")
                print(f"Board FEN before move: {board.fen()}")
                raise HTTPException(
                    status_code=400, 
                    detail=f"Invalid move at ply {ply}: {game_data.moves[ply - 1]}"
                )
        else:
            after_fen = before_fen
        
        # ply의 이동을 둔 플레이어: ply가 홀수면 백, 짝수면 흑
        # ply 1 = 백이 둔 수, ply 2 = 흑이 둔 수, ply 3 = 백이 둔 수, ...
        move_player_is_white = (ply % 2 == 1)
        # 현재 차례 (after_fen 기준): 보드 상태의 turn이 백이면 True
        # after_fen을 파싱하여 현재 차례 확인
        if after_fen:
            current_turn_is_white = after_fen.split()[1] == 'w'  # FEN의 두 번째 필드
        else:
            # ply가 홀수면 백이 둔 후이므로 다음은 흑 차례, ply가 짝수면 흑이 둔 후이므로 다음은 백 차례
            current_turn_is_white = (ply % 2 == 0)
        
        before_eval_data = eval_data.get("before_eval") or {}
        after_eval_data = eval_data.get("after_eval") or {}
        
        before_eval = CloudEval(
            fen=before_fen,
            cp=before_eval_data.get("cp"),
            mate=before_eval_data.get("mate"),
            depth=0,
            nodes=0,
            pv=[]
        )
        
        after_eval = CloudEval(
            fen=after_fen,
            cp=after_eval_data.get("cp"),
            mate=after_eval_data.get("mate"),
            depth=0,
            nodes=0,
            pv=[]
        )
        
        # 평가 차이 계산
        if after_eval.cp is not None and before_eval.cp is not None:
            delta_cp = after_eval.cp - before_eval.cp
            if not move_player_is_white:
                delta_cp = -delta_cp
        else:
            delta_cp = None
        
        delta_mate = after_eval.mate if after_eval.mate else None
        
        category = eval_data.get("category", "accurate")
        best_move = None
        summary = f"{game_data.moves[ply - 1]} (Lichess 평가)"
        
        return JSONResponse(content={
            "ply": ply,
            "move": game_data.moves[ply - 1] if ply > 0 else None,
            "player": "white" if move_player_is_white else "black",
            "current_turn": "white" if current_turn_is_white else "black",
            "before_eval": {
                "fen": before_eval.fen,
                "cp": before_eval.cp,
                "mate": before_eval.mate,
                "depth": after_eval.depth,
                "nodes": after_eval.nodes
            },
            "after_eval": {
                "fen": after_eval.fen,
                "cp": after_eval.cp,
                "mate": after_eval.mate,
                "depth": after_eval.depth,
                "nodes": after_eval.nodes,
                "pv": after_eval.pv
            },
            "delta_cp": delta_cp,
            "delta_mate": delta_mate,
            "category": category,
            "best_move": best_move,
            "summary": summary,
            "fen": after_fen
        })
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to get evaluation: {str(e)}")


@app.get("/api/stats/{game_id}")
async def get_game_stats(game_id: str):
    """게임 통계 가져오기 (백과 흑 각각)"""
    import httpx
    import sys
    
    # 디버깅: Python 경로와 chess 모듈 확인
    print(f"[get_game_stats] Python executable: {sys.executable}")
    print(f"[get_game_stats] Python path: {sys.path[:3]}")
    try:
        import chess
        print(f"[get_game_stats] Chess module found: {chess.__file__}")
    except ImportError as e:
        print(f"[get_game_stats] Chess import error: {e}")
        raise HTTPException(status_code=500, detail=f"Chess module not available: {e}")
    
    from backend.lichess_api import get_auth_headers
    
    try:
        from backend.game_stats import parse_pgn_with_evals, calculate_game_stats
    except ImportError as e:
        print(f"[get_game_stats] game_stats import error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to import game_stats: {e}")
    
    try:
        print(f"[get_game_stats] Starting stats fetch for game: {game_id}")
        
        # Lichess에서 평가 정보가 포함된 PGN 가져오기
        pgn_url = f"https://lichess.org/game/export/{game_id}?evals=1"
        headers = get_auth_headers()
        
        print(f"[get_game_stats] Fetching PGN from: {pgn_url}")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(pgn_url, headers=headers)
            print(f"[get_game_stats] PGN response status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"[get_game_stats] Failed to fetch PGN: {response.status_code}")
                raise HTTPException(status_code=response.status_code, detail="Failed to fetch PGN with evals")
            
            pgn_with_evals = response.text
            print(f"[get_game_stats] PGN fetched, length: {len(pgn_with_evals)}")
        
        # PGN에서 모든 평가 정보 파싱
        print(f"[get_game_stats] Parsing evaluations from PGN...")
        evaluations = parse_pgn_with_evals(pgn_with_evals)
        print(f"[get_game_stats] Parsed {len(evaluations)} evaluations")
        
        # 통계 계산 (백과 흑 각각)
        print(f"[get_game_stats] Calculating stats...")
        stats = calculate_game_stats(evaluations)
        print(f"[get_game_stats] Stats calculated successfully")
        
        return JSONResponse(content=stats)
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_msg = f"Failed to get game stats: {str(e)}"
        print(f"[get_game_stats] ERROR: {error_msg}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=error_msg)


@app.get("/api/move-analysis/{game_id}/{ply}")
async def get_move_analysis(game_id: str, ply: int):
    """ChatGPT API를 사용하여 특정 수에 대한 AI 분석 생성"""
    import os
    import chess
    import httpx
    from backend.lichess_api import get_auth_headers
    from backend.game_stats import parse_pgn_with_evals
    
    # OpenAI API 키 확인
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise HTTPException(
            status_code=500, 
            detail="OpenAI API key not configured. Please set OPENAI_API_KEY in environment variables."
        )
    
    try:
        # 게임 데이터 가져오기
        game_data = await fetch_game_data(game_id)
        
        if ply < 1 or ply > len(game_data.moves):
            raise HTTPException(status_code=400, detail=f"Invalid ply: {ply}. Game has {len(game_data.moves)} moves.")
        
        # 해당 수의 평가 정보 가져오기
        pgn_url = f"https://lichess.org/game/export/{game_id}?evals=1"
        headers = get_auth_headers()
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(pgn_url, headers=headers)
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Failed to fetch PGN with evals")
            
            pgn_with_evals = response.text
        
        # PGN에서 평가 정보 파싱
        evaluations = parse_pgn_with_evals(pgn_with_evals)
        
        # 해당 ply의 평가 정보 찾기
        eval_data = None
        for eval_item in evaluations:
            if eval_item["ply"] == ply:
                eval_data = eval_item
                break
        
        # 보드 상태 재현
        board = chess.Board()
        for i in range(ply - 1):
            if i < len(game_data.moves):
                try:
                    move = board.parse_san(game_data.moves[i])
                    board.push(move)
                except Exception as move_error:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Invalid move at position {i}: {game_data.moves[i]}"
                    )
        
        before_fen = board.fen()
        
        # 현재 수
        current_move = game_data.moves[ply - 1]
        move_player_is_white = (ply % 2 == 1)
        
        # 현재 수 적용
        try:
            move = board.parse_san(current_move)
            board.push(move)
            after_fen = board.fen()
        except Exception as move_error:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid move at ply {ply}: {current_move}"
            )
        
        # 평가 정보
        before_eval_data = eval_data.get("before_eval") if eval_data else {}
        after_eval_data = eval_data.get("after_eval") if eval_data else {}
        
        before_cp = before_eval_data.get("cp") if before_eval_data else None
        after_cp = after_eval_data.get("cp") if after_eval_data else None
        category = eval_data.get("category", "accurate") if eval_data else "accurate"
        
        # 평가 변화 계산
        if after_cp is not None and before_cp is not None:
            delta_cp = after_cp - before_cp
            if not move_player_is_white:
                delta_cp = -delta_cp
        else:
            delta_cp = None
        
        # 수 정보
        move_number = (ply + 1) // 2
        move_text = f"{move_number}. {current_move}" if move_player_is_white else f"{move_number}... {current_move}"
        
        # ChatGPT 프롬프트 작성
        eval_str_before = f"{before_cp / 100.0:.1f}" if before_cp is not None else "N/A"
        eval_str_after = f"{after_cp / 100.0:.1f}" if after_cp is not None else "N/A"
        delta_str = f"{delta_cp / 100.0:+.1f}" if delta_cp is not None else "N/A"
        
        category_kr = {
            "accurate": "정확함",
            "good": "좋음",
            "inaccuracy": "부정확",
            "mistake": "실수",
            "blunder": "블런더"
        }.get(category, category)
        
        prompt = f"""체스 게임에서 특정 수에 대해 분석해주세요.

수 정보:
- 수: {move_text}
- 플레이어: {"백 (White)" if move_player_is_white else "흑 (Black)"}
- 카테고리: {category_kr}

평가 정보:
- 수 이전 평가: {eval_str_before}
- 수 이후 평가: {eval_str_after}
- 평가 변화: {delta_str}

보드 상태 (FEN):
- 수 이전: {before_fen}
- 수 이후: {after_fen}

다음 내용을 포함하여 이 수에 대한 분석을 한국어로 작성해주세요:
1. 이 수의 의도와 전략적 목적
2. 수의 강점 또는 약점
3. 더 나은 대안이 있다면 제안
4. 이 수가 게임에 미친 영향

분석은 150-250자 정도로 간결하게 작성해주세요."""

        # OpenAI API 호출
        from openai import OpenAI
        client = OpenAI(api_key=openai_api_key)
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "당신은 체스 분석 전문가입니다. 특정 수에 대해 명확하고 유용한 분석을 한국어로 제공합니다."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=400
        )
        
        analysis_text = response.choices[0].message.content
        
        return JSONResponse(content={
            "game_id": game_id,
            "ply": ply,
            "move": current_move,
            "analysis": analysis_text,
            "model": "gpt-4o-mini"
        })
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate move analysis: {str(e)}")


@app.get("/api/analysis/{game_id}")
async def get_game_analysis(game_id: str):
    """ChatGPT API를 사용하여 게임 총평 생성"""
    import os
    import httpx
    import sys
    
    # 디버깅: Python 경로와 chess 모듈 확인
    print(f"[get_game_analysis] Python executable: {sys.executable}")
    print(f"[get_game_analysis] Python path: {sys.path[:3]}")
    try:
        import chess
        print(f"[get_game_analysis] Chess module found: {chess.__file__}")
    except ImportError as e:
        print(f"[get_game_analysis] Chess import error: {e}")
        raise HTTPException(status_code=500, detail=f"Chess module not available: {e}")
    
    from backend.lichess_api import get_auth_headers
    
    try:
        from backend.game_stats import parse_pgn_with_evals, calculate_game_stats
    except ImportError as e:
        print(f"[get_game_analysis] game_stats import error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to import game_stats: {e}")
    
    # OpenAI API 키 확인
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise HTTPException(
            status_code=500, 
            detail="OpenAI API key not configured. Please set OPENAI_API_KEY in environment variables."
        )
    
    try:
        print(f"[get_game_analysis] Starting analysis for game: {game_id}")
        
        # 게임 데이터 가져오기
        print(f"[get_game_analysis] Fetching game data...")
        game_data = await fetch_game_data(game_id)
        print(f"[get_game_analysis] Game data fetched: {game_data.white.username} vs {game_data.black.username}")
        
        # 통계 가져오기
        pgn_url = f"https://lichess.org/game/export/{game_id}?evals=1"
        headers = get_auth_headers()
        
        print(f"[get_game_analysis] Fetching PGN with evals from: {pgn_url}")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(pgn_url, headers=headers)
            print(f"[get_game_analysis] PGN response status: {response.status_code}")
            
            if response.status_code != 200:
                error_msg = f"Failed to fetch PGN with evals: {response.status_code}"
                print(f"[get_game_analysis] ERROR: {error_msg}")
                raise HTTPException(status_code=response.status_code, detail=error_msg)
            
            pgn_with_evals = response.text
            print(f"[get_game_analysis] PGN fetched, length: {len(pgn_with_evals)}")
        
        # 통계 계산
        print(f"[get_game_analysis] Parsing evaluations...")
        evaluations = parse_pgn_with_evals(pgn_with_evals)
        print(f"[get_game_analysis] Parsed {len(evaluations)} evaluations")
        
        print(f"[get_game_analysis] Calculating stats...")
        stats = calculate_game_stats(evaluations)
        print(f"[get_game_analysis] Stats calculated successfully")
        
        # 결과 라벨
        result_labels = {
            "white": "백 승리",
            "black": "흑 승리",
            "draw": "무승부",
            "*": "진행 중"
        }
        
        # ChatGPT 프롬프트 작성
        prompt = f"""다음 체스 게임을 분석하여 한국어로 총평을 작성해주세요.

게임 정보:
- 백 (White): {game_data.white.username} (레팅: {game_data.white.rating})
- 흑 (Black): {game_data.black.username} (레팅: {game_data.black.rating})
- 결과: {result_labels.get(game_data.result, game_data.result)}
- 오프닝: {game_data.opening or 'N/A'}

백의 통계:
- 총 {stats['white']['total_moves']}수
- 평균 정확도: {stats['white']['average_accuracy']}%
- 평가: {stats['white']['overall_assessment']}
- 정확함: {stats['white']['accurate']}, 좋음: {stats['white']['good']}, 부정확: {stats['white']['inaccuracy']}, 실수: {stats['white']['mistake']}, 블런더: {stats['white']['blunder']}

흑의 통계:
- 총 {stats['black']['total_moves']}수
- 평균 정확도: {stats['black']['average_accuracy']}%
- 평가: {stats['black']['overall_assessment']}
- 정확함: {stats['black']['accurate']}, 좋음: {stats['black']['good']}, 부정확: {stats['black']['inaccuracy']}, 실수: {stats['black']['mistake']}, 블런더: {stats['black']['blunder']}

기보 (PGN):
{game_data.pgn}

다음 내용을 포함하여 총평을 작성해주세요:
1. 게임 전체적인 흐름과 특징
2. 주요 결정적 순간 (중요한 실수나 좋은 수)
3. 백과 흑의 플레이 비교
4. 개선할 수 있는 부분

총평은 300-500자 정도로 작성해주세요."""

        # OpenAI API 호출
        from openai import OpenAI
        client = OpenAI(api_key=openai_api_key)
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # 비용 효율적인 모델 사용
            messages=[
                {
                    "role": "system",
                    "content": "당신은 체스 분석 전문가입니다. 체스 게임을 분석하고 명확하고 유용한 총평을 한국어로 작성합니다."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=800
        )
        
        analysis_text = response.choices[0].message.content
        print(f"[get_game_analysis] Analysis generated, length: {len(analysis_text)}")
        
        return JSONResponse(content={
            "game_id": game_id,
            "analysis": analysis_text,
            "model": "gpt-4o-mini"
        })
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_msg = f"Failed to generate game analysis: {str(e)}"
        print(f"[get_game_analysis] ERROR: {error_msg}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=error_msg)


@app.post("/api/research/{game_id}/{ply}")
async def open_research_tool(game_id: str, ply: int):
    """Playwright MCP를 사용하여 Lichess 분석 도구 열고 현재 기보 상태 설정"""
    try:
        # 게임 데이터 가져오기
        game_data = await fetch_game_data(game_id)
        
        if ply < 0 or ply > len(game_data.moves):
            raise HTTPException(status_code=400, detail=f"Invalid ply: {ply}. Game has {len(game_data.moves)} moves.")
        
        # ply까지의 수 목록
        moves_to_ply = game_data.moves[:ply] if ply > 0 else []
        
        # FEN 기반 URL 생성
        from backend.mcp_research import setup_lichess_board_via_playwright
        
        # URL 생성
        analysis_url = await setup_lichess_board_via_playwright(game_id, ply, moves_to_ply)
        
        # Playwright MCP를 사용하여 브라우저 열고 PGN 입력 시도
        mcp_url = None
        opened_via_mcp = False
        
        try:
            from backend.mcp_research import open_lichess_analysis_with_playwright
            
            # MCP 작업 수행
            mcp_url = await open_lichess_analysis_with_playwright(game_id, ply, moves_to_ply)
            if mcp_url:
                opened_via_mcp = True
                print(f"MCP로 브라우저 열기 및 PGN 입력 성공: {mcp_url}")
        except Exception as mcp_error:
            import traceback
            print(f"MCP 연결 실패 또는 PGN 입력 실패, URL만 제공: {mcp_error}")
            traceback.print_exc()
            # MCP 실패 시에도 URL은 제공
        
        # MCP URL이 있으면 사용, 없으면 FEN 기반 URL 사용
        final_url = mcp_url if mcp_url else analysis_url
        
        return JSONResponse(content={
            "success": True,
            "url": final_url,
            "game_id": game_id,
            "ply": ply,
            "message": "Lichess 분석 도구가 브라우저에서 열렸습니다." if opened_via_mcp else "Lichess 분석 도구 URL이 생성되었습니다. 새 창에서 열립니다.",
            "opened_via_mcp": opened_via_mcp
        })
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to open research tool: {str(e)}")


@app.get("/api/capture/{game_id}/{ply}")
async def get_capture_url(game_id: str, ply: int):
    """보드 이미지 URL 반환 (프론트엔드에서 직접 사용)"""
    import chess
    from urllib.parse import quote
    
    try:
        # 게임 데이터 가져오기
        game_data = await fetch_game_data(game_id)
        
        # ply가 0이면 초기 위치
        if ply < 0 or ply > len(game_data.moves):
            raise HTTPException(status_code=400, detail=f"Invalid ply: {ply}. Game has {len(game_data.moves)} moves.")
        
        # 해당 ply까지 보드 상태 재현
        board = chess.Board()
        # ply가 0이면 초기 위치, 1 이상이면 해당 수까지 적용
        if ply > 0:
            for i in range(ply):
                if i < len(game_data.moves):
                    try:
                        move = board.parse_san(game_data.moves[i])
                        board.push(move)
                    except Exception as move_error:
                        print(f"Error parsing move {i} ({game_data.moves[i]}): {move_error}")
                        print(f"Board FEN: {board.fen()}")
                        raise HTTPException(
                            status_code=400, 
                            detail=f"Invalid move at position {i}: {game_data.moves[i]}"
                        )
        
        # FEN 문자열 가져오기
        fen = board.fen()
        
        # Lichess 보드 이미지 URL 생성
        # 참고: Lichess는 공개 보드 이미지 엔드포인트를 제공하지 않을 수 있으므로
        # 대안으로 다른 서비스를 사용하거나 프론트엔드에서 직접 처리
        # 예: chess.com의 보드 이미지 서비스나 기타 무료 서비스
        # 또는 게임 리플레이 페이지를 iframe으로 임베드
        
        # 임시: FEN을 기반으로 한 공개 보드 이미지 서비스 URL
        # 예시: chess.com board image (공개 서비스)
        board_image_url = f"https://www.chess.com/dynboard?fen={quote(fen)}&size=2"
        
        # 또는 Lichess 게임 리플레이 페이지로 리디렉션
        # game_replay_url = f"https://lichess.org/{game_id}#{ply}"
        
        return JSONResponse(content={
            "url": board_image_url,
            "fen": fen,
            "game_id": game_id,
            "ply": ply
        })
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error generating capture URL: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate capture URL: {str(e)}")


@app.get("/api/progress/{game_id}")
async def get_progress(game_id: str):
    """분석 진행 상황 조회"""
    if game_id not in analysis_progress:
        # 진행 상황이 없으면 pending 상태 반환
        return {
            "status": "pending",
            "progress": 0,
            "current": 0,
            "total": 0,
            "message": "게임 데이터 로딩 대기 중..."
        }
    
    return analysis_progress[game_id]


@app.get("/api/status/{game_id}")
async def get_status(game_id: str):
    """분석 상태 확인"""
    if game_id in analysis_progress:
        progress = analysis_progress[game_id]
        return {"status": progress["status"], "gameId": game_id}
    else:
        return {"status": "not_found", "gameId": game_id}


@app.get("/")
async def root():
    return {"message": "Lichess Replay Analyzer API", "version": "1.0.0"}

