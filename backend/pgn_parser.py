"""PGN에서 평가 정보 파싱"""
import re
import chess
import chess.pgn
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass


@dataclass
class PgnEval:
    """PGN에서 추출한 평가 정보"""
    cp: Optional[int] = None  # centipawns
    mate: Optional[int] = None  # mate in N moves
    depth: Optional[int] = None
    nodes: Optional[int] = None
    pv: List[str] = None  # principal variation
    
    def __post_init__(self):
        if self.pv is None:
            self.pv = []


def parse_pgn_evaluations(pgn: str) -> Dict[int, PgnEval]:
    """
    PGN에서 각 수순의 평가 정보 추출
    Lichess PGN 형식: 1. e4 {[%eval 0.23]} e5 {[%eval -0.45]} ...
    
    Returns:
        Dict[int, PgnEval]: ply 번호(1-based)를 키로 하는 평가 정보 딕셔너리
    """
    evaluations = {}
    
    # python-chess로 PGN 파싱
    try:
        game = chess.pgn.read_game(chess.pgn.StringIO(pgn))
        if not game:
            return evaluations
        
        node = game
        ply = 0
        
        while node.variations:
            node = node.variation(0)
            ply += 1
            
            # 노드의 주석에서 평가 정보 추출
            comment = node.comment if hasattr(node, 'comment') else ""
            
            if comment:
                eval_info = parse_eval_from_comment(comment)
                if eval_info:
                    evaluations[ply] = eval_info
            
            # 이전 수의 평가도 확인 (before move)
            if node.parent and hasattr(node.parent, 'comment'):
                parent_comment = node.parent.comment
                if parent_comment:
                    # ply-1에 대한 평가일 수 있음
                    eval_info = parse_eval_from_comment(parent_comment)
                    if eval_info and (ply - 1) not in evaluations:
                        evaluations[ply - 1] = eval_info
        
    except Exception as e:
        print(f"Error parsing PGN for evaluations: {e}")
        # 정규식 기반 파싱 폴백
        evaluations = parse_eval_from_pgn_text(pgn)
    
    return evaluations


def parse_eval_from_comment(comment: str) -> Optional[PgnEval]:
    """
    주석에서 평가 정보 추출
    형식: [%eval cp=20], [%eval 0.23], [%eval #3], [%eval #-2]
    """
    if not comment:
        return None
    
    # %eval 패턴 찾기
    # [%eval cp=20], [%eval 0.23], [%eval #3]
    eval_patterns = [
        r'\[%eval\s+cp=(-?\d+)\]',  # [%eval cp=20]
        r'\[%eval\s+(-?\d+\.?\d*)\]',  # [%eval 0.23] 또는 [%eval 20]
        r'\[%eval\s+#(-?\d+)\]',  # [%eval #3]
        r'\[%eval\s+#(\+?\d+)\]',  # [%eval #+3]
    ]
    
    cp = None
    mate = None
    
    for pattern in eval_patterns:
        match = re.search(pattern, comment)
        if match:
            value = match.group(1)
            if '#' in pattern:
                # mate 형식
                try:
                    mate = int(value.replace('+', ''))
                except:
                    pass
            else:
                # cp 형식
                try:
                    if '.' in value:
                        # 소수점 형식 (예: 0.23 = 23 centipawns)
                        cp_val = float(value)
                        cp = int(cp_val * 100)
                    else:
                        # 정수 형식 (이미 centipawns)
                        cp = int(value)
                except:
                    pass
            break
    
    # depth, nodes, pv는 Lichess PGN에 포함되지 않을 수 있음
    if cp is not None or mate is not None:
        return PgnEval(cp=cp, mate=mate)
    
    return None


def parse_eval_from_pgn_text(pgn: str) -> Dict[int, PgnEval]:
    """
    정규식으로 PGN 텍스트에서 직접 평가 정보 추출 (폴백 방법)
    """
    evaluations = {}
    
    # 이동 텍스트 부분 추출
    move_text = ""
    for line in pgn.split('\n'):
        line = line.strip()
        if line and not line.startswith('['):
            move_text += " " + line
    
    # 각 수에 대한 평가 정보 찾기
    # 패턴: 숫자. 이동 {[%eval ...]} 이동 {[%eval ...]}
    move_pattern = r'(\d+)\.\s+([^{]+(?:\{[^}]*\[%eval[^\]]+\][^}]*\}[^{]*)*)'
    matches = re.finditer(move_pattern, move_text)
    
    ply = 0
    for match in matches:
        move_num = int(match.group(1))
        move_text_part = match.group(2)
        
        # 각 수에서 평가 정보 추출
        eval_matches = re.finditer(r'\{[^}]*\[%eval[^\]]+\][^}]*\}', move_text_part)
        for eval_match in eval_matches:
            eval_comment = eval_match.group(0)
            eval_info = parse_eval_from_comment(eval_comment)
            if eval_info:
                ply += 1
                evaluations[ply] = eval_info
    
    return evaluations


