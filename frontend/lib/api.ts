const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// 게임 데이터 타입
export interface GameData {
  game_id: string;
  white: {
    username: string;
    rating: number;
  };
  black: {
    username: string;
    rating: number;
  };
  result: string;
  opening?: string;
  moves: string[];
  pgn: string;
}

// 수 평가 타입
export interface MoveEvaluation {
  ply: number;
  move: string;
  player: "white" | "black";
  category: "accurate" | "good" | "inaccuracy" | "mistake" | "blunder";
  delta_cp: number | null;
  delta_mate: number | null;
  summary: string;
  best_move?: string;
  current_turn?: boolean; // true면 백 차례, false면 흑 차례
}

// 게임 통계 타입
export interface PlayerStats {
  total_moves: number;
  average_accuracy: number;
  overall_assessment: string;
  accurate: number;
  good: number;
  inaccuracy: number;
  mistake: number;
  blunder: number;
}

export interface GameStats {
  white: PlayerStats;
  black: PlayerStats;
  total_moves: number;
}

// 진행 상황 타입
export interface ProgressResponse {
  status: "pending" | "loading" | "analyzing" | "completed" | "error";
  progress: number;
  message: string;
  current?: number;
  total?: number;
  error?: string;
}

// 게임 가져오기
export async function getGame(gameId: string): Promise<GameData> {
  const response = await fetch(`${API_BASE_URL}/api/game/${gameId}`);
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to fetch game: ${response.status} - ${errorText}`);
  }
  return response.json();
}

// 수 평가 가져오기
export async function getEvaluation(gameId: string, ply: number): Promise<MoveEvaluation> {
  const response = await fetch(`${API_BASE_URL}/api/eval/${gameId}/${ply}`);
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to fetch evaluation: ${response.status} - ${errorText}`);
  }
  return response.json();
}

// 게임 통계 가져오기
export async function getGameStats(gameId: string): Promise<GameStats> {
  const response = await fetch(`${API_BASE_URL}/api/stats/${gameId}`);
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to fetch game stats: ${response.status} - ${errorText}`);
  }
  return response.json();
}

// 진행 상황 가져오기
export async function getProgress(gameId: string): Promise<ProgressResponse> {
  const response = await fetch(`${API_BASE_URL}/api/progress/${gameId}`);
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to fetch progress: ${response.status} - ${errorText}`);
  }
  return response.json();
}

// 게임 분석 시작
export async function analyzeGame(gameUrl: string): Promise<{ gameId: string }> {
  const response = await fetch(`${API_BASE_URL}/api/analyze`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ gameUrl }),
  });
  
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to start analysis: ${response.status} - ${errorText}`);
  }
  
  return response.json();
}

// 캡처 URL 가져오기
export async function getCaptureUrl(gameId: string, moveNumber: number): Promise<string> {
  const response = await fetch(`${API_BASE_URL}/api/capture/${gameId}/${moveNumber}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch capture URL: ${response.status}`);
  }
  const data = await response.json();
  return data.url || `${API_BASE_URL}/api/capture/${gameId}/${moveNumber}`;
}

// 게임 총평 가져오기
export interface GameAnalysis {
  game_id: string;
  analysis: string;
  model: string;
}

export async function getGameAnalysis(gameId: string): Promise<GameAnalysis> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/analysis/${gameId}`);
    
    // response가 없는 경우 (네트워크 에러)
    if (!response) {
      throw new Error('백엔드 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인해주세요.');
    }
    
    if (!response.ok) {
      let errorText = '';
      try {
        errorText = await response.text();
      } catch {
        errorText = '응답을 읽을 수 없습니다.';
      }
      
      // 500 에러인 경우 더 구체적인 메시지
      if (response.status === 500) {
        let errorDetail = errorText;
        try {
          const errorJson = JSON.parse(errorText);
          errorDetail = errorJson.detail || errorText;
        } catch {
          // JSON 파싱 실패 시 원본 텍스트 사용
        }
        
        // OpenAI API 키 관련 에러 체크
        if (errorDetail.includes('OpenAI API key')) {
          throw new Error('OpenAI API 키가 설정되지 않았습니다. 백엔드 .env 파일에 OPENAI_API_KEY를 설정해주세요.');
        }
        
        throw new Error(`백엔드 서버 오류 (500): ${errorDetail}`);
      }
      throw new Error(`Failed to fetch game analysis: ${response.status} - ${errorText}`);
    }
    return response.json();
  } catch (error: any) {
    // 네트워크 에러 처리 (CORS 또는 연결 실패)
    if (error.name === 'TypeError' && error.message?.includes('Failed to fetch')) {
      throw new Error('백엔드 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인해주세요.');
    }
    // 이미 처리된 에러는 그대로 전달
    throw error;
  }
}

// 특정 수에 대한 AI 분석 인터페이스
export interface MoveAnalysis {
  game_id: string;
  ply: number;
  analysis: string;
}

export async function getMoveAnalysis(gameId: string, ply: number): Promise<MoveAnalysis> {
  const response = await fetch(`${API_BASE_URL}/api/move-analysis/${gameId}/${ply}`);
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to fetch move analysis: ${response.status} - ${errorText}`);
  }
  return response.json();
}

// 연구 도구 열기
export interface ResearchResponse {
  success: boolean;
  url: string;
  game_id: string;
  ply: number;
  message: string;
  opened_via_mcp: boolean;
}

export async function openResearchTool(gameId: string, ply: number): Promise<ResearchResponse> {
  const response = await fetch(`${API_BASE_URL}/api/research/${gameId}/${ply}`, {
    method: "POST"
  });
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to open research tool: ${response.status} - ${errorText}`);
  }
  
  const result = await response.json();
  
  // MCP로 성공적으로 브라우저가 열렸다면 프론트엔드에서는 새 창을 열지 않음
  // MCP가 실패했을 때만 프론트엔드에서 FEN URL을 열기
  if (result.url) {
    if (result.opened_via_mcp) {
      // MCP로 이미 브라우저가 열렸으므로 추가 작업 불필요
      console.log("Research tool opened via MCP, no additional window needed:", result.url);
    } else {
      // MCP 실패 시에만 프론트엔드에서 FEN URL 열기
      const newWindow = window.open(result.url, '_blank');
      if (newWindow) {
        console.log("Research tool opened in new window (FEN only, MCP failed):", result.url);
      } else {
        console.warn("Failed to open new window - popup may be blocked");
        window.location.href = result.url;
      }
    }
  }
  
  return result;
}

