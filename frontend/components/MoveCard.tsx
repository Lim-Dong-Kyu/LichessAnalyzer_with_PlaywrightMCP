"use client";

import { MoveEvaluation } from "@/lib/api";

interface MoveCardProps {
  evaluation: MoveEvaluation;
  gameId: string;
  moveNumber: number;
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

export default function MoveCard({ evaluation, gameId, moveNumber }: MoveCardProps) {
  const captureUrl = `${process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000"}/api/capture/${gameId}/${evaluation.ply}`;
  const categoryColor = categoryColors[evaluation.category];
  const categoryLabel = categoryLabels[evaluation.category];

  const formatDelta = () => {
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

  return (
    <div className="bg-white rounded-lg shadow-md p-4 hover:shadow-lg transition-shadow">
      <div className="flex gap-4">
        {/* 썸네일 이미지 */}
        <div className="flex-shrink-0">
          <div className="w-32 h-32 bg-gray-200 rounded relative overflow-hidden">
            <img
              src={captureUrl}
              alt={`Move ${moveNumber}`}
              className="w-full h-full object-cover"
              onLoad={(e) => {
                // 이미지 로드 성공 시 로딩 메시지 숨기기
                const container = (e.target as HTMLImageElement).parentElement;
                if (container) {
                  const loadingText = container.querySelector('.loading-text');
                  if (loadingText) {
                    (loadingText as HTMLElement).style.display = "none";
                  }
                }
              }}
              onError={(e) => {
                // 이미지 로드 실패 시 이미지 숨기고 로딩 메시지 유지
                const target = e.target as HTMLImageElement;
                target.style.display = "none";
                const container = target.parentElement;
                if (container) {
                  const loadingText = container.querySelector('.loading-text');
                  if (loadingText) {
                    (loadingText as HTMLElement).textContent = "이미지를 사용할 수 없음";
                    (loadingText as HTMLElement).className = "absolute inset-0 flex items-center justify-center text-gray-600 text-xs loading-text";
                  }
                }
              }}
            />
            <div className="absolute inset-0 flex items-center justify-center text-gray-600 text-xs loading-text pointer-events-none">
              이미지 로딩 중...
            </div>
          </div>
        </div>

        {/* 정보 영역 */}
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <span className="font-bold text-lg">
              {moveNumber}. {evaluation.move}
            </span>
            <span className={`px-2 py-1 rounded text-xs font-semibold ${categoryColor}`}>
              {categoryLabel}
            </span>
          </div>

          <div className="text-sm text-gray-900 mb-2 font-medium">
            {evaluation.player === "white" ? "백" : "흑"} 차례
          </div>

          {formatDelta() && (
            <div className="text-sm font-medium text-gray-900 mb-2">
              {formatDelta()}
            </div>
          )}

          {evaluation.best_move && evaluation.best_move !== evaluation.move && (
            <div className="text-sm text-gray-900 mb-2">
              추천 수: <span className="font-semibold">{evaluation.best_move}</span>
            </div>
          )}

          <div className="text-xs text-gray-900 mt-2">
            {evaluation.summary}
          </div>

          <button
            onClick={() => {
              window.open(`https://lichess.org/${gameId}`, "_blank");
            }}
            className="mt-3 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm transition-colors"
          >
            해당 수로 이동
          </button>
        </div>
      </div>
    </div>
  );
}

