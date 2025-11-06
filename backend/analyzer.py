import chess
import chess.pgn
from typing import List, Optional, Tuple
from datetime import datetime
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
backend_dir = Path(__file__).parent
project_root = backend_dir.parent
sys.path.insert(0, str(project_root))

from backend.models import (
    GameData, MoveEvaluation, AnalysisReport, CloudEval
)
from backend.lichess_api import fetch_cloud_eval


def categorize_move(delta_cp: Optional[int], delta_mate: Optional[int]) -> str:
    """평가 차이에 따라 카테고리를 분류"""
    if delta_mate is not None:
        # 메이트 관련 평가는 특별 처리
        if delta_mate < 0:
            return "blunder"
        elif delta_mate > 0:
            return "good"
        else:
            return "accurate"
    
    if delta_cp is None:
        return "accurate"
    
    abs_delta = abs(delta_cp)
    
    if abs_delta < 10:
        return "accurate"
    elif abs_delta < 50:
        return "good"
    elif abs_delta < 100:
        return "inaccuracy"
    elif abs_delta < 300:
        return "mistake"
    else:
        return "blunder"


def calculate_evaluation_delta(
    before_eval: CloudEval,
    after_eval: CloudEval,
    is_white_turn: bool
) -> Tuple[Optional[int], Optional[int]]:
    """평가 차이 계산 (Δcp, Δmate)"""
    # 평가값이 None인 경우 처리
    if before_eval.mate is not None or after_eval.mate is not None:
        # 메이트 평가
        before_mate = before_eval.mate
        after_mate = after_eval.mate
        
        if before_mate is None and after_mate is not None:
            # 메이트가 새로 나타남
            delta_mate = after_mate
            delta_cp = None
        elif before_mate is not None and after_mate is None:
            # 메이트가 사라짐 (큰 손실)
            delta_mate = -999  # 매우 큰 음수로 표시
            delta_cp = None
        elif before_mate is not None and after_mate is not None:
            delta_mate = after_mate - before_mate
            delta_cp = None
        else:
            delta_mate = None
            delta_cp = None
    else:
        # Centipawn 평가
        before_cp = before_eval.cp or 0
        after_cp = after_eval.cp or 0
        
        # 백의 관점에서 평가 (흑 차례면 부호 반전)
        if is_white_turn:
            delta_cp = after_cp - before_cp
        else:
            delta_cp = before_cp - after_cp
        
        delta_mate = None
    
    return delta_cp, delta_mate


def format_eval_value(eval_obj: CloudEval) -> str:
    """평가값을 문자열로 포맷팅"""
    if eval_obj.mate is not None:
        return f"M{eval_obj.mate}"
    elif eval_obj.cp is not None:
        cp_val = eval_obj.cp / 100.0  # centipawns to pawns
        return f"{cp_val:+.1f}"
    else:
        return "N/A"


def generate_summary(
    move: str,
    category: str,
    delta_cp: Optional[int],
    delta_mate: Optional[int],
    best_move: Optional[str]
) -> str:
    """이동에 대한 요약 텍스트 생성"""
    category_kr = {
        "accurate": "정확함",
        "good": "좋음",
        "inaccuracy": "부정확",
        "mistake": "실수",
        "blunder": "블런더"
    }
    
    cat_kr = category_kr.get(category, category)
    
    if delta_mate is not None:
        if delta_mate < 0:
            delta_str = f"Δ = {delta_mate} 메이트"
        else:
            delta_str = f"Δ = +{delta_mate} 메이트"
    elif delta_cp is not None:
        delta_val = delta_cp / 100.0
        delta_str = f"Δ = {delta_val:+.0f} cp"
    else:
        delta_str = ""
    
    if best_move and best_move != move:
        return f"{move} ({cat_kr}) | 추천: {best_move} ({delta_str})"
    else:
        return f"{move} ({cat_kr}) {delta_str}".strip()


async def analyze_game(game_data: GameData, progress_callback=None) -> AnalysisReport:
    """게임 전체를 분석하여 리포트 생성"""
    board = chess.Board()
    evaluations: List[MoveEvaluation] = []
    
    # 초기 위치 평가
    initial_fen = board.fen()
    try:
        initial_eval = await fetch_cloud_eval(initial_fen)
    except Exception as e:
        print(f"Error fetching initial cloud eval: {e}")
        initial_eval = CloudEval(
            fen=initial_fen,
            cp=0,
            mate=None,
            depth=0,
            nodes=0,
            pv=[]
        )
    
    previous_eval = initial_eval
    is_white = True
    
    # 모든 FEN을 먼저 계산
    fens_to_eval = []
    board_copy = chess.Board()
    
    for move_san in game_data.moves:
        try:
            move = board_copy.parse_san(move_san)
            board_copy.push(move)
            fens_to_eval.append(board_copy.fen())
        except:
            fens_to_eval.append(None)
    
    # 병렬로 모든 평가 가져오기 (API 토큰 있으면 더 많은 동시 요청 가능)
    import asyncio
    from backend.lichess_api import LICHESS_API_TOKEN
    
    # API 토큰이 있으면 더 많은 동시 요청 허용 (토큰 없으면 제한적)
    max_concurrent = 20 if LICHESS_API_TOKEN else 5
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def fetch_with_semaphore(fen, index, progress_callback=None):
        if fen is None:
            return CloudEval(fen="", cp=0, mate=None, depth=0, nodes=0, pv=[])
        async with semaphore:
            # 지연 시간 완전히 제거
            
            try:
                return await fetch_cloud_eval(fen)
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "rate limit" in error_str.lower():
                    # Rate limit 발생 시 재시도 (최소 대기 시간만 유지)
                    wait_time = 0.5  # Rate limit을 피하기 위한 최소 대기
                    if index < 5:  # 처음 몇 개만 로그 출력
                        print(f"Rate limit hit for move {index + 1}, waiting {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    # 재시도
                    try:
                        return await fetch_cloud_eval(fen)
                    except:
                        pass
                elif "404" not in error_str and "not available" not in error_str.lower():
                    if index < 5:  # 처음 몇 개만 로그 출력
                        print(f"Error fetching cloud eval for move {index + 1}: {e}")
                
                return CloudEval(fen=fen, cp=0, mate=None, depth=0, nodes=0, pv=[])
    
    token_status = "with API token" if LICHESS_API_TOKEN else "without API token"
    print(f"Fetching {len(fens_to_eval)} cloud evals in parallel (max {max_concurrent} concurrent, {token_status})...")
    
    # 진행 상황 추적을 위한 변수
    completed_count = 0
    total_count = len(fens_to_eval)
    
    async def fetch_with_progress(fen, index):
        nonlocal completed_count
        result = await fetch_with_semaphore(fen, index, progress_callback)
        completed_count += 1
        if progress_callback:
            progress = int((completed_count / total_count) * 100)
            progress_callback(progress, completed_count, total_count)
        return result
    
    after_evals = await asyncio.gather(*[fetch_with_progress(fen, i) for i, fen in enumerate(fens_to_eval)])
    
    # 각 이동 분석
    board = chess.Board()
    previous_eval = initial_eval
    is_white = True
    
    for ply, (move_san, after_eval) in enumerate(zip(game_data.moves, after_evals), start=1):
        try:
            move = board.parse_san(move_san)
            board.push(move)
            
            # 평가 차이 계산
            delta_cp, delta_mate = calculate_evaluation_delta(
                previous_eval, after_eval, is_white
            )
            
            # 카테고리 분류
            category = categorize_move(delta_cp, delta_mate)
            
            # 최선의 수 추출
            best_move = None
            if after_eval.pv:
                try:
                    temp_board = chess.Board(board.fen())
                    best_move_obj = temp_board.parse_san(after_eval.pv[0])
                    best_move = temp_board.san(best_move_obj)
                except:
                    pass
            
            # 요약 생성
            summary = generate_summary(
                move_san, category, delta_cp, delta_mate, best_move
            )
            
            eval_obj = MoveEvaluation(
                ply=ply,
                move=move_san,
                player="white" if is_white else "black",
                before_eval=previous_eval,
                after_eval=after_eval,
                delta_cp=delta_cp,
                delta_mate=delta_mate,
                category=category,
                best_move=best_move,
                summary=summary
            )
            
            evaluations.append(eval_obj)
            
            previous_eval = after_eval
            is_white = not is_white
            
        except Exception as e:
            print(f"Error analyzing move {ply} ({move_san}): {e}")
            continue
    
    # 통계 계산
    white_mistakes = sum(1 for e in evaluations if e.player == "white" and e.category in ["mistake", "blunder"])
    black_mistakes = sum(1 for e in evaluations if e.player == "black" and e.category in ["mistake", "blunder"])
    white_blunders = sum(1 for e in evaluations if e.player == "white" and e.category == "blunder")
    black_blunders = sum(1 for e in evaluations if e.player == "black" and e.category == "blunder")
    
    return AnalysisReport(
        game_id=game_data.game_id,
        game_data=game_data,
        evaluations=evaluations,
        total_moves=len(evaluations),
        white_mistakes=white_mistakes,
        black_mistakes=black_mistakes,
        white_blunders=white_blunders,
        black_blunders=black_blunders,
        created_at=datetime.now()
    )
