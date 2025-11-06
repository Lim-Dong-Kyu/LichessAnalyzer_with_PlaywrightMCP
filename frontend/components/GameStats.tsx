"use client";

import { GameStats, PlayerStats } from "@/lib/api";

interface GameStatsProps {
  stats: GameStats;
}

const categoryLabels = {
  accurate: "정확함",
  good: "좋음",
  inaccuracy: "부정확",
  mistake: "실수",
  blunder: "블런더",
};

const assessmentColors: Record<string, string> = {
  "우수": "bg-green-100 text-green-800",
  "양호": "bg-blue-100 text-blue-800",
  "보통": "bg-yellow-100 text-yellow-800",
  "불안정": "bg-orange-100 text-orange-800",
  "개선 필요": "bg-red-100 text-red-800",
};

function PlayerStatsCard({ playerStats, playerName, playerColor }: { playerStats: PlayerStats; playerName: string; playerColor: "white" | "black" }) {
  const bgGradient = playerColor === "white" 
    ? "from-blue-50 to-indigo-50" 
    : "from-gray-50 to-gray-100";
  const borderColor = playerColor === "white"
    ? "border-blue-200"
    : "border-gray-300";
  
  return (
    <div className={`border-2 ${borderColor} rounded-lg p-6 bg-gradient-to-r ${bgGradient}`}>
      <h3 className="text-2xl font-bold mb-4 flex items-center gap-2 text-black">
        <span className={`w-5 h-5 rounded ${playerColor === "white" ? "bg-white border-2 border-gray-800" : "bg-gray-800"}`}></span>
        {playerName} 통계
      </h3>
      
      {/* 평가 */}
      <div className="mb-6 p-4 bg-white bg-opacity-60 rounded-lg">
        <div className="text-base text-gray-900 mb-2 font-semibold">평가</div>
        <div className="flex items-center gap-3">
          <span className={`px-4 py-2 rounded text-xl font-bold ${
            assessmentColors[playerStats.overall_assessment] || "bg-gray-100 text-gray-800"
          }`}>
            {playerStats.overall_assessment}
          </span>
          <span className="text-3xl font-bold text-gray-900">
            {playerStats.average_accuracy}%
          </span>
          <span className="text-base text-gray-900 font-semibold">평균 정확도</span>
        </div>
      </div>
      
      {/* 통계 그리드 */}
      <div className="grid grid-cols-5 gap-3">
        <div className="text-center p-3 bg-green-50 rounded-lg">
          <div className="text-2xl font-bold text-green-700 mb-1">
            {playerStats.accurate}
          </div>
          <div className="text-sm text-green-800 font-semibold">
            {categoryLabels.accurate}
          </div>
        </div>
        
        <div className="text-center p-3 bg-blue-50 rounded-lg">
          <div className="text-2xl font-bold text-blue-700 mb-1">
            {playerStats.good}
          </div>
          <div className="text-sm text-blue-800 font-semibold">
            {categoryLabels.good}
          </div>
        </div>
        
        <div className="text-center p-3 bg-yellow-50 rounded-lg">
          <div className="text-2xl font-bold text-yellow-700 mb-1">
            {playerStats.inaccuracy}
          </div>
          <div className="text-sm text-yellow-800 font-semibold">
            {categoryLabels.inaccuracy}
          </div>
        </div>
        
        <div className="text-center p-3 bg-orange-50 rounded-lg">
          <div className="text-2xl font-bold text-orange-700 mb-1">
            {playerStats.mistake}
          </div>
          <div className="text-sm text-orange-800 font-semibold">
            {categoryLabels.mistake}
          </div>
        </div>
        
        <div className="text-center p-3 bg-red-50 rounded-lg">
          <div className="text-2xl font-bold text-red-700 mb-1">
            {playerStats.blunder}
          </div>
          <div className="text-sm text-red-800 font-semibold">
            {categoryLabels.blunder}
          </div>
        </div>
      </div>
      
      {/* 총 수 */}
      <div className="mt-4 pt-3 border-t border-gray-300 text-center text-base text-gray-900 font-semibold">
        총 {playerStats.total_moves}수
      </div>
    </div>
  );
}

export default function GameStatsDisplay({ stats }: GameStatsProps) {
  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-3xl font-bold mb-6 text-black">게임 통계</h2>
      
      <div className="grid md:grid-cols-2 gap-6">
        <PlayerStatsCard 
          playerStats={stats.white} 
          playerName="백" 
          playerColor="white" 
        />
        <PlayerStatsCard 
          playerStats={stats.black} 
          playerName="흑" 
          playerColor="black" 
        />
      </div>
      
      {/* 전체 총 수 */}
      <div className="mt-6 pt-4 border-t text-center text-base text-gray-900 font-semibold">
        전체 총 {stats.total_moves}수
      </div>
    </div>
  );
}

