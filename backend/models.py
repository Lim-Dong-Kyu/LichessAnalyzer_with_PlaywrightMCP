from pydantic import BaseModel
from typing import List, Optional, Literal
from datetime import datetime


class Player(BaseModel):
    username: str
    rating: Optional[int] = None


class GameData(BaseModel):
    game_id: str
    white: Player
    black: Player
    pgn: str
    opening: Optional[str] = None
    result: str
    moves: List[str]  # SAN notation moves
    # 평가 정보는 PGN에서 추출되므로 별도 필드로 저장하지 않음 (lazy parsing)


class CloudEval(BaseModel):
    fen: str
    cp: Optional[int] = None  # centipawns
    mate: Optional[int] = None  # mate in N moves
    depth: int = 0
    nodes: int = 0
    pv: List[str] = []  # principal variation


class MoveEvaluation(BaseModel):
    ply: int  # half-move number (1-based)
    move: str  # SAN notation
    player: Literal["white", "black"]
    before_eval: CloudEval
    after_eval: CloudEval
    delta_cp: Optional[int] = None  # evaluation difference
    delta_mate: Optional[int] = None
    category: Literal["accurate", "good", "inaccuracy", "mistake", "blunder"]
    best_move: Optional[str] = None
    summary: str


class AnalysisReport(BaseModel):
    game_id: str
    game_data: GameData
    evaluations: List[MoveEvaluation]
    total_moves: int
    white_mistakes: int
    black_mistakes: int
    white_blunders: int
    black_blunders: int
    created_at: datetime

