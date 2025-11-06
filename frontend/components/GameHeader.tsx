"use client";

import { GameData } from "@/lib/api";

interface GameHeaderProps {
  gameData: GameData;
}

export default function GameHeader({ gameData }: GameHeaderProps) {
  const resultLabels: Record<string, string> = {
    white: "백 승리",
    black: "흑 승리",
    draw: "무승부",
    "*": "진행 중",
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 mb-6">
      <h1 className="text-3xl font-bold mb-4 text-black">게임 분석</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <div className="text-base text-gray-900 mb-1 font-semibold">백 (White)</div>
          <div className="font-bold text-xl text-gray-900">{gameData.white.username}</div>
          {gameData.white.rating && (
            <div className="text-base text-gray-900 font-medium">레이팅: {gameData.white.rating}</div>
          )}
        </div>
        
        <div className="text-center">
          <div className="text-base text-gray-900 mb-1 font-semibold">결과</div>
          <div className="font-bold text-2xl text-gray-900">{resultLabels[gameData.result] || gameData.result}</div>
        </div>
        
        <div className="text-right">
          <div className="text-base text-gray-900 mb-1 font-semibold">흑 (Black)</div>
          <div className="font-bold text-xl text-gray-900">{gameData.black.username}</div>
          {gameData.black.rating && (
            <div className="text-base text-gray-900 font-medium">레이팅: {gameData.black.rating}</div>
          )}
        </div>
      </div>
      
      {gameData.opening && (
        <div className="mt-4 pt-4 border-t">
          <div className="text-base text-gray-900 font-semibold">오프닝</div>
          <div className="font-semibold text-lg text-gray-900">{gameData.opening}</div>
        </div>
      )}
    </div>
  );
}

