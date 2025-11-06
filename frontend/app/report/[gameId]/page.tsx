"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { getGame, GameData, getGameStats, GameStats } from "@/lib/api";
import GameHeader from "@/components/GameHeader";
import GameBoard from "@/components/GameBoard";
import GameStatsDisplay from "@/components/GameStats";
import GameAnalysis from "@/components/GameAnalysis";

export default function ReportPage() {
  const params = useParams();
  const router = useRouter();
  const gameId = params.gameId as string;
  const [gameData, setGameData] = useState<GameData | null>(null);
  const [gameStats, setGameStats] = useState<GameStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchGame() {
      try {
        setLoading(true);
        const [data, stats] = await Promise.all([
          getGame(gameId),
          getGameStats(gameId).catch(err => {
            console.warn("Failed to fetch game stats:", err);
            return null;
          })
        ]);
        setGameData(data);
        setGameStats(stats);
        setError(null);
      } catch (err) {
        console.error("Error fetching game:", err);
        setError("게임 데이터를 불러올 수 없습니다. 게임 ID를 확인해주세요.");
      } finally {
        setLoading(false);
      }
    }

    if (gameId) {
      fetchGame();
    }
  }, [gameId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4">
        <div className="max-w-4xl mx-auto">
          <div className="bg-white rounded-lg shadow-xl p-8 text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-600">리포트를 불러오는 중...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error || !gameData) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4">
        <div className="max-w-4xl mx-auto">
          <div className="bg-white rounded-lg shadow-xl p-8">
            <div className="text-center">
              <h1 className="text-2xl font-bold text-red-600 mb-4">오류</h1>
              <p className="text-gray-700 mb-6">
                {error || "게임 데이터를 찾을 수 없습니다."}
              </p>
              <button
                onClick={() => router.push("/")}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                홈으로 돌아가기
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4">
      <div className="max-w-4xl mx-auto">
        {/* 헤더 */}
        <div className="mb-6">
          <button
            onClick={() => router.push("/")}
            className="text-blue-600 hover:text-blue-800 font-medium mb-4 inline-flex items-center"
          >
            ← 홈으로 돌아가기
          </button>
        </div>

        {/* 게임 정보 */}
        <GameHeader gameData={gameData} />

        {/* 게임 통계 */}
        {gameStats && (
          <div className="mb-6">
            <GameStatsDisplay stats={gameStats} />
          </div>
        )}

        {/* AI 게임 총평 */}
        <div className="mb-6">
          <GameAnalysis gameId={gameId} />
        </div>

        {/* 기보 보기 */}
        <div className="mb-6">
          <GameBoard 
            gameId={gameId}
            moves={gameData.moves}
            totalPlies={gameData.moves.length}
          />
        </div>

        {/* 안내 */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm text-blue-800">
          💡 <strong>팁:</strong> 이전/다음 버튼으로 수순을 이동하면서 각 수의 평가를 확인할 수 있습니다. 
          평가는 자동으로 캐시되어 다시 로드할 필요가 없습니다.
        </div>
      </div>
    </div>
  );
}

