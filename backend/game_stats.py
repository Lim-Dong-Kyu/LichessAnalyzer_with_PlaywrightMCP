"""
게임 통계 계산 - Lichess PGN에서 평가 정보 추출
"""
import chess
import chess.pgn
from io import StringIO
from typing import Dict, List, Optional
from backend.models import CloudEval


def parse_pgn_with_evals(pgn_text: str) -> List[Dict]:
    """
    PGN 텍스트에서 모든 수의 평가 정보 추출
    
    Returns:
        List of dicts with keys: ply, move, eval_cp, eval_mate, category
    """
    evaluations = []
    
    try:
        pgn_io = StringIO(pgn_text)
        game = chess.pgn.read_game(pgn_io)
        
        if not game:
            return evaluations
        
        board = game.board()
        ply = 0
        
        # 초기 위치 평가 (있다면)
        initial_comment = game.comment
        if initial_comment and '[%eval' in initial_comment:
            eval_data = parse_eval_comment(initial_comment)
            if eval_data:
                evaluations.append({
                    "ply": 0,
                    "move": None,
                    "before_eval": eval_data,
                    "after_eval": eval_data,
                    "category": "accurate"
                })
        
        # 각 수의 평가 정보 추출
        for node in game.mainline():
            ply += 1
            move = node.move
            
            # 이전 평가
            before_eval = None
            if ply > 1:
                prev_eval = evaluations[-1]["after_eval"] if evaluations else None
                before_eval = prev_eval
            
            # 현재 수 이후 평가
            after_eval = None
            comment = node.comment
            if comment and '[%eval' in comment:
                eval_data = parse_eval_comment(comment)
                after_eval = eval_data
            
            # 평가 차이 계산하여 카테고리 분류
            category = categorize_move_from_evals(before_eval, after_eval)
            
            evaluations.append({
                "ply": ply,
                "move": board.san(move),
                "before_eval": before_eval,
                "after_eval": after_eval,
                "category": category
            })
            
            board.push(move)
        
        return evaluations
    
    except Exception as e:
        print(f"Error parsing PGN with evals: {e}")
        import traceback
        traceback.print_exc()
        return evaluations


def parse_eval_comment(comment: str) -> Optional[Dict]:
    """PGN 주석에서 평가 정보 추출"""
    import re
    
    # [%eval 0.2] 또는 [%eval #3] 형식
    eval_match = re.search(r'\[%eval\s+([^\]]+)\]', comment)
    if not eval_match:
        return None
    
    eval_str = eval_match.group(1).strip()
    
    try:
        if eval_str.startswith('#'):
            # 메이트: #3 = 3수 후 메이트
            mate_value = int(eval_str[1:])
            return {"cp": None, "mate": mate_value}
        else:
            # cp 값 (백분율): 0.2 -> 20cp
            cp_value = float(eval_str) * 100
            return {"cp": int(cp_value), "mate": None}
    except:
        return None


def categorize_move_from_evals(before_eval: Optional[Dict], after_eval: Optional[Dict]) -> str:
    """평가 정보를 기반으로 수의 카테고리 분류"""
    if not before_eval or not after_eval:
        return "accurate"
    
    before_cp = before_eval.get("cp")
    after_cp = after_eval.get("cp")
    
    # 메이트가 있으면 accurate로 처리
    if before_eval.get("mate") is not None or after_eval.get("mate") is not None:
        return "accurate"
    
    if before_cp is None or after_cp is None:
        # 평가 정보가 불완전하면 accurate로 처리
        return "accurate"
    
    # 평가 차이 계산 (항상 화이트 관점)
    # after_cp가 더 크면 좋은 수, 작으면 나쁜 수
    delta_cp = after_cp - before_cp
    
    # 절대값으로 분류
    abs_delta = abs(delta_cp)
    
    if abs_delta < 50:
        return "accurate"
    elif abs_delta < 100:
        return "good"
    elif abs_delta < 200:
        return "inaccuracy"
    elif abs_delta < 300:
        return "mistake"
    else:
        return "blunder"


def calculate_player_stats(evaluations: List[Dict], is_white: bool) -> Dict:
    """플레이어별 통계 계산 (백 또는 흑)"""
    # ply가 홀수면 백, 짝수면 흑
    player_evaluations = [
        eval_data for eval_data in evaluations
        if eval_data.get("ply", 0) > 0 and ((eval_data["ply"] % 2 == 1) == is_white)
    ]
    
    total_moves = len(player_evaluations)
    
    if total_moves == 0:
        return {
            "total_moves": 0,
            "accurate": 0,
            "good": 0,
            "inaccuracy": 0,
            "mistake": 0,
            "blunder": 0,
            "average_accuracy": 0.0,
            "overall_assessment": "N/A"
        }
    
    category_counts = {
        "accurate": 0,
        "good": 0,
        "inaccuracy": 0,
        "mistake": 0,
        "blunder": 0
    }
    
    for eval_data in player_evaluations:
        category = eval_data.get("category", "accurate")
        if category in category_counts:
            category_counts[category] += 1
    
    # 평균 정확도 계산 (accurate + good 비율)
    accurate_moves = category_counts["accurate"] + category_counts["good"]
    average_accuracy = (accurate_moves / total_moves * 100) if total_moves > 0 else 0.0
    
    # 전체 게임 평가
    blunder_count = category_counts["blunder"]
    mistake_count = category_counts["mistake"]
    inaccuracy_count = category_counts["inaccuracy"]
    
    if average_accuracy >= 90:
        overall = "우수"
    elif average_accuracy >= 80:
        overall = "양호"
    elif average_accuracy >= 70:
        overall = "보통"
    elif blunder_count > mistake_count:
        overall = "불안정"
    else:
        overall = "개선 필요"
    
    return {
        "total_moves": total_moves,
        "accurate": category_counts["accurate"],
        "good": category_counts["good"],
        "inaccuracy": category_counts["inaccuracy"],
        "mistake": category_counts["mistake"],
        "blunder": category_counts["blunder"],
        "average_accuracy": round(average_accuracy, 1),
        "overall_assessment": overall
    }


def calculate_game_stats(evaluations: List[Dict]) -> Dict:
    """게임 전체 통계 계산 (백과 흑 각각)"""
    white_stats = calculate_player_stats(evaluations, is_white=True)
    black_stats = calculate_player_stats(evaluations, is_white=False)
    
    return {
        "white": white_stats,
        "black": black_stats,
        "total_moves": white_stats["total_moves"] + black_stats["total_moves"]
    }

