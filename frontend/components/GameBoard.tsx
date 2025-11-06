"use client";

import { useState, useEffect } from "react";
import { getEvaluation, MoveEvaluation, getCaptureUrl } from "@/lib/api";

interface GameBoardProps {
  gameId: string;
  moves: string[];
  totalPlies: number;
}

const categoryColors = {
  accurate: "bg-green-100 text-green-800",
  good: "bg-blue-100 text-blue-800",
  inaccuracy: "bg-yellow-100 text-yellow-800",
  mistake: "bg-orange-100 text-orange-800",
  blunder: "bg-red-100 text-red-800",
};

const categoryLabels = {
  accurate: "정확함",
  good: "좋음",
  inaccuracy: "부정확",
  mistake: "실수",
  blunder: "블런더",
};

export default function GameBoard({ gameId, moves, totalPlies }: GameBoardProps) {
  const [currentPly, setCurrentPly] = useState(0); // 0 = 초기 위치
  const [evaluation, setEvaluation] = useState<MoveEvaluation | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [evaluationCache, setEvaluationCache] = useState<Record<number, MoveEvaluation>>({});
  const [moveAnalysis, setMoveAnalysis] = useState<string | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [analysisCache, setAnalysisCache] = useState<Record<number, string>>({});
  const [researchLoading, setResearchLoading] = useState(false);

  const fetchEvaluation = async (ply: number) => {
    if (ply === 0) {
      setEvaluation(null);
      return;
    }

    // 캐시 확인
    if (evaluationCache[ply]) {
      setEvaluation(evaluationCache[ply]);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const data = await getEvaluation(gameId, ply);
      setEvaluation(data);
      setEvaluationCache(prev => ({ ...prev, [ply]: data }));
    } catch (err: any) {
      console.error("Error fetching evaluation:", err);
      setError(err.message || "평가를 가져올 수 없습니다.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEvaluation(currentPly);
    // 분석은 별도로 요청하므로 여기서는 초기화만
    if (currentPly === 0 || !analysisCache[currentPly]) {
      setMoveAnalysis(null);
    } else {
      setMoveAnalysis(analysisCache[currentPly]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentPly]);

  const fetchMoveAnalysis = async () => {
    if (currentPly === 0) {
      setMoveAnalysis(null);
      return;
    }

    // 캐시 확인
    if (analysisCache[currentPly]) {
      setMoveAnalysis(analysisCache[currentPly]);
      return;
    }

    setAnalysisLoading(true);
    setAnalysisError(null);
    try {
      const { getMoveAnalysis } = await import("@/lib/api");
      const data = await getMoveAnalysis(gameId, currentPly);
      setMoveAnalysis(data.analysis);
      setAnalysisCache(prev => ({ ...prev, [currentPly]: data.analysis }));
    } catch (err: any) {
      console.error("Error fetching move analysis:", err);
      setAnalysisError(err.message || "AI 분석을 가져올 수 없습니다.");
      setMoveAnalysis(null);
    } finally {
      setAnalysisLoading(false);
    }
  };

  const handleResearch = async () => {
    if (currentPly === 0) {
      alert("첫 수로 이동한 후 연구하기를 사용해주세요.");
      return;
    }

    setResearchLoading(true);
    try {
      const { openResearchTool } = await import("@/lib/api");
      const result = await openResearchTool(gameId, currentPly);
      
      if (result.success && result.url) {
        // openResearchTool에서 이미 새 창을 열었으므로 여기서는 처리하지 않음
        // MCP로 열렸는지 여부는 로그만 확인
        if (result.opened_via_mcp) {
          console.log("Research tool opened via MCP");
        }
      } else {
        alert("연구 도구를 열 수 없습니다.");
      }
    } catch (err: any) {
      console.error("Error opening research tool:", err);
      alert(err.message || "연구 도구를 열 수 없습니다.");
    } finally {
      setResearchLoading(false);
    }
  };

  const handlePrevious = () => {
    if (currentPly > 0) {
      setCurrentPly(prev => prev - 1);
    }
  };

  const handleNext = () => {
    if (currentPly < totalPlies) {
      setCurrentPly(prev => prev + 1);
    }
  };

  const handleFirst = () => {
    setCurrentPly(0);
  };

  const handleLast = () => {
    setCurrentPly(totalPlies);
  };

  const handlePrevious10 = () => {
    const newPly = Math.max(0, currentPly - 10);
    setCurrentPly(newPly);
  };

  const handleNext10 = () => {
    const newPly = Math.min(totalPlies, currentPly + 10);
    setCurrentPly(newPly);
  };

  // ply 계산:
  // ply 0 = 초기 위치 (표시용, 실제 이동 없음)
  // ply 1 = 백의 첫 번째 수 (백 차례)
  // ply 2 = 흑의 첫 번째 수 (흑 차례)
  // ply 3 = 백의 두 번째 수 (백 차례)
  
  // moveNumber 계산: ply 1,2 = 1수, ply 3,4 = 2수, ...
  const moveNumber = currentPly === 0 ? 0 : Math.floor((currentPly + 1) / 2);
  
  // 현재 차례: ply 0=백(초기), ply 1=백, ply 2=흑, ply 3=백, ply 4=흑, ...
  // 백엔드의 current_turn은 after_fen 기준(다음 차례)이므로 사용하지 않음
  // ply 기반으로 직접 계산: ply가 홀수면 백, 짝수면 흑 (단, ply 0은 백)
  const isWhite = currentPly === 0 
    ? true  // 초기 위치는 항상 백 차례
    : currentPly % 2 === 1;  // ply 1=백, 2=흑, 3=백, 4=흑, ...
  
  // 표시할 이동
  const displayMove = currentPly === 0 
    ? null 
    : moves[currentPly - 1];
  
  // 백의 수인지 흑의 수인지 확인 (ply 1,3,5... = 백의 수, ply 2,4,6... = 흑의 수)
  const isWhiteMove = currentPly > 0 && currentPly % 2 === 1;
  const [captureUrl, setCaptureUrl] = useState<string | null>(null);

  // 보드 이미지 URL 가져오기
  useEffect(() => {
    if (currentPly > 0) {
      getCaptureUrl(gameId, currentPly).then(url => {
        setCaptureUrl(url);
      }).catch(err => {
        console.error("Error fetching capture URL:", err);
        setCaptureUrl(null);
      });
    } else {
      setCaptureUrl(null);
    }
  }, [currentPly, gameId]);

  const formatDelta = () => {
    if (!evaluation) return "";
    
    if (evaluation.delta_mate !== null && evaluation.delta_mate !== undefined) {
      return evaluation.delta_mate < 0 
        ? `Δ = ${evaluation.delta_mate} 메이트`
        : `Δ = +${evaluation.delta_mate} 메이트`;
    }
    if (evaluation.delta_cp !== null && evaluation.delta_cp !== undefined) {
      const deltaVal = evaluation.delta_cp / 100.0;
      return `Δ = ${deltaVal >= 0 ? '+' : ''}${deltaVal.toFixed(1)} cp`;
    }
    return "";
  };

  const formatEval = (eval_obj: { cp?: number; mate?: number }) => {
    if (eval_obj.mate !== null && eval_obj.mate !== undefined) {
      return `M${eval_obj.mate}`;
    }
    if (eval_obj.cp !== null && eval_obj.cp !== undefined) {
      const cpVal = eval_obj.cp / 100.0;
      return `${cpVal >= 0 ? '+' : ''}${cpVal.toFixed(1)}`;
    }
    return "N/A";
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      {/* 기보 네비게이션 */}
      <div className="flex items-center justify-between mb-6">
        <button
          onClick={handleFirst}
          disabled={currentPly === 0}
          className="px-4 py-2.5 bg-gray-200 rounded hover:bg-gray-300 disabled:opacity-50 text-base font-semibold"
          title="처음으로"
        >
          ⏮
        </button>
        <button
          onClick={handlePrevious10}
          disabled={currentPly === 0}
          className="px-4 py-2.5 bg-gray-400 text-white rounded hover:bg-gray-500 disabled:opacity-50 disabled:cursor-not-allowed text-base font-semibold"
          title="10수 이전"
        >
          ⏪ -10
        </button>
        <button
          onClick={handlePrevious}
          disabled={currentPly === 0}
          className="px-5 py-2.5 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-base font-semibold"
        >
          ← 이전
        </button>
        
        <div className="text-center flex-1 mx-4">
          <div className="text-2xl font-bold text-black">
            {currentPly === 0 
              ? "초기 위치" 
              : isWhiteMove
                ? `${moveNumber}. ${displayMove}`
                : `${moveNumber}... ${displayMove}`}
          </div>
          <div className="text-base text-gray-900 mt-1 font-semibold">
            {/* ply 0 = 초기 위치 (백 차례), ply 1 = 첫 번째 수 (백), ply 2 = 두 번째 수 (흑), ... */}
            {isWhite ? "백" : "흑"} 차례 · {currentPly}/{totalPlies}
          </div>
        </div>
        
        <button
          onClick={handleNext}
          disabled={currentPly >= totalPlies}
          className="px-5 py-2.5 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-base font-semibold"
        >
          다음 →
        </button>
        <button
          onClick={handleNext10}
          disabled={currentPly >= totalPlies}
          className="px-4 py-2.5 bg-gray-400 text-white rounded hover:bg-gray-500 disabled:opacity-50 disabled:cursor-not-allowed text-base font-semibold"
          title="10수 다음"
        >
          +10 ⏩
        </button>
        <button
          onClick={handleLast}
          disabled={currentPly >= totalPlies}
          className="px-4 py-2.5 bg-gray-200 rounded hover:bg-gray-300 disabled:opacity-50 text-base font-semibold"
          title="마지막으로"
        >
          ⏭
        </button>
      </div>

      {/* 보드 이미지 */}
      {captureUrl && (
        <div className="mb-4 flex justify-center">
          <div className="relative">
            <img
              src={captureUrl}
              alt={`Move ${currentPly}`}
              className="max-w-full h-auto rounded shadow-md"
              onError={(e) => {
                (e.target as HTMLImageElement).style.display = "none";
              }}
            />
          </div>
        </div>
      )}

      {/* 평가 정보 */}
      {loading && (
        <div className="text-center py-4">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p className="text-black mt-2 font-medium">평가 가져오는 중...</p>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

            {evaluation && !loading && (
              <div className="border-t pt-4 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-lg text-black">
                      {evaluation.move}
                    </span>
                    <span className={`px-2 py-1 rounded text-xs font-semibold ${categoryColors[evaluation.category as keyof typeof categoryColors]}`}>
                      {categoryLabels[evaluation.category as keyof typeof categoryLabels]}
                    </span>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={fetchMoveAnalysis}
                      disabled={analysisLoading}
                      className="px-3 py-1.5 text-sm bg-purple-600 text-white rounded hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
                    >
                      {analysisLoading ? (
                        <>
                          <span className="animate-spin">⟳</span> 분석 중...
                        </>
                      ) : moveAnalysis ? (
                        "🔄 다시 분석"
                      ) : (
                        "🤖 AI 분석"
                      )}
                    </button>
                    <button
                      onClick={handleResearch}
                      disabled={researchLoading || currentPly === 0}
                      className="px-3 py-1.5 text-sm bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
                      title="Lichess 분석 도구에서 현재 기보 상태로 열기"
                    >
                      {researchLoading ? (
                        <>
                          <span className="animate-spin">⟳</span> 열기 중...
                        </>
                      ) : (
                        <>
                          🔬 연구하기
                        </>
                      )}
                    </button>
                  </div>
                </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-sm text-black font-medium">이전 평가</div>
              <div className="text-lg font-semibold text-black">
                {formatEval(evaluation.before_eval)}
              </div>
            </div>
            <div>
              <div className="text-sm text-black font-medium">이후 평가</div>
              <div className="text-lg font-semibold text-black">
                {formatEval(evaluation.after_eval)}
              </div>
            </div>
          </div>

          {formatDelta() && (
            <div className="bg-gray-50 p-3 rounded">
              <div className="text-sm text-black font-medium">평가 변화</div>
              <div className="text-lg font-semibold text-gray-900">
                {formatDelta()}
              </div>
            </div>
          )}

          {evaluation.best_move && evaluation.best_move !== evaluation.move && (
            <div className="bg-blue-50 p-3 rounded">
              <div className="text-sm text-blue-600">추천 수</div>
              <div className="text-lg font-semibold text-blue-900">
                {evaluation.best_move}
              </div>
            </div>
          )}

          <div className="text-sm text-black pt-2 border-t font-medium">
            {evaluation.summary}
          </div>

                <div className="text-xs text-black font-medium">
                  깊이: {evaluation.after_eval.depth} · 노드: {evaluation.after_eval.nodes.toLocaleString()}
                </div>

                {/* AI 분석 결과 */}
                {analysisError && (
                  <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mt-4">
                    {analysisError}
                  </div>
                )}
                {moveAnalysis && (
                  <div className="mt-4 p-4 bg-gradient-to-r from-purple-50 to-indigo-50 rounded-lg border-l-4 border-purple-500">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-sm font-semibold text-purple-700">🤖 AI 분석</span>
                      <span className="text-xs text-black">gpt-4o-mini</span>
                    </div>
                    <p className="text-black leading-relaxed whitespace-pre-wrap text-sm">
                      {moveAnalysis}
                    </p>
                  </div>
                )}
              </div>
            )}

      {currentPly === 0 && !loading && (
        <div className="border-t pt-4 text-center text-black font-medium">
          첫 수로 이동하여 평가를 확인하세요.
        </div>
      )}
    </div>
  );
}

