"use client";

import { GameAnalysis as GameAnalysisType } from "@/lib/api";
import { useState, useEffect } from "react";

interface GameAnalysisProps {
  gameId: string;
}

export default function GameAnalysis({ gameId }: GameAnalysisProps) {
  const [analysis, setAnalysis] = useState<GameAnalysisType | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(true);

  const fetchAnalysis = async () => {
    if (analysis) return; // 이미 가져온 경우 재요청하지 않음
    
    setLoading(true);
    setError(null);
    try {
      const { getGameAnalysis } = await import("@/lib/api");
      const data = await getGameAnalysis(gameId);
      setAnalysis(data);
    } catch (err: any) {
      console.error("Error fetching analysis:", err);
      // 에러 메시지 처리
      let errorMessage = "총평을 가져올 수 없습니다.";
      if (err.message) {
        if (err.message.includes("서버에 연결할 수 없습니다")) {
          errorMessage = "백엔드 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인해주세요.";
        } else if (err.message.includes("OpenAI API key")) {
          errorMessage = "OpenAI API 키가 설정되지 않았습니다.";
        } else {
          errorMessage = err.message;
        }
      }
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  // 컴포넌트 마운트 시 자동으로 가져오기
  useEffect(() => {
    fetchAnalysis();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (loading && !analysis) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-3xl font-bold text-black">AI 게임 총평</h2>
        </div>
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-900 font-semibold text-lg">총평을 생성하는 중...</p>
        </div>
      </div>
    );
  }

  if (error && !analysis) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-3xl font-bold text-black">AI 게임 총평</h2>
        </div>
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
        <button
          onClick={fetchAnalysis}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          다시 시도
        </button>
      </div>
    );
  }

  if (!analysis) {
    return null;
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <h2 className="text-3xl font-bold text-black">AI 게임 총평</h2>
          <span className="text-sm text-black bg-gray-100 px-3 py-1 rounded font-semibold">
            {analysis.model}
          </span>
        </div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-black hover:text-gray-900 font-semibold text-lg"
          aria-label={expanded ? "접기" : "펼치기"}
        >
          {expanded ? "▲" : "▼"}
        </button>
      </div>
      
      {expanded && (
        <div className="prose prose-sm max-w-none">
          <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-6 border-l-4 border-blue-500">
            <p className="text-base text-gray-900 leading-relaxed whitespace-pre-wrap font-medium">
              {analysis.analysis}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}


