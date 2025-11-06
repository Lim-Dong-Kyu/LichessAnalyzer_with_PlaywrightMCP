"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { analyzeGame, getProgress, ProgressResponse } from "@/lib/api";

export default function Home() {
  const [gameUrl, setGameUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<ProgressResponse | null>(null);
  const [currentGameId, setCurrentGameId] = useState<string | null>(null);
  const progressIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const router = useRouter();

  // 진행 상황 폴링
  useEffect(() => {
    console.log("useEffect triggered:", { currentGameId, loading }); // 디버깅용
    
    if (!currentGameId || !loading) {
      console.log("Early return:", { currentGameId, loading }); // 디버깅용
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current);
        progressIntervalRef.current = null;
      }
      return;
    }
    
    console.log("Starting progress polling"); // 디버깅용

    const checkProgress = async () => {
      try {
        const progressData = await getProgress(currentGameId);
        setProgress(progressData);
        
        console.log("Progress check:", progressData); // 디버깅용

        // status가 "completed"이면 리포트 페이지로 즉시 이동
        if (progressData.status === "completed") {
          console.log("Status is completed, navigating to report page"); // 디버깅용
          setLoading(false);
          if (progressIntervalRef.current) {
            clearInterval(progressIntervalRef.current);
            progressIntervalRef.current = null;
          }
          router.push(`/report/${currentGameId}`);
          return;
        } 
        // status가 "error"이면 에러 메시지 표시
        else if (progressData.status === "error") {
          setLoading(false);
          setError(progressData.message || progressData.error || "분석 중 오류가 발생했습니다.");
          if (progressIntervalRef.current) {
            clearInterval(progressIntervalRef.current);
            progressIntervalRef.current = null;
          }
          return;
        }
        // status가 "loading" 또는 "analyzing"이면 계속 대기
        // status가 "pending"이면 아직 시작되지 않았으므로 계속 대기
        
        // 최대 30초 대기 후 타임아웃 (안전장치)
        // 실제로는 즉시 completed 상태가 되어야 함
      } catch (err) {
        console.error("Progress check error:", err);
      }
    };

    // 즉시 한 번 체크하고, 이후 200ms마다 체크 (더 빠른 반응)
    checkProgress();
    progressIntervalRef.current = setInterval(checkProgress, 200);

    return () => {
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current);
        progressIntervalRef.current = null;
      }
    };
  }, [currentGameId, loading, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setProgress(null);
    setLoading(true);

    try {
      console.log("Starting analysis for:", gameUrl); // 디버깅용
      const response = await analyzeGame(gameUrl);
      console.log("Analysis response:", response); // 디버깅용
      setCurrentGameId(response.gameId);
      console.log("Set currentGameId to:", response.gameId); // 디버깅용
      // 진행 상황 폴링은 useEffect에서 처리됨
    } catch (err) {
      console.error("Analysis error:", err); // 디버깅용
      setError(err instanceof Error ? err.message : "분석 중 오류가 발생했습니다.");
      setLoading(false);
      setCurrentGameId(null);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4">
      <div className="max-w-2xl mx-auto">
        <div className="bg-white rounded-lg shadow-xl p-8">
          <h1 className="text-4xl font-bold text-center mb-2 text-gray-800">
            Lichess Replay Analyzer
          </h1>
          <p className="text-center text-gray-600 mb-8">
            Lichess 게임 링크를 입력하여 자동으로 분석하세요
          </p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="gameUrl" className="block text-sm font-medium text-gray-700 mb-2">
                게임 URL
              </label>
              <input
                id="gameUrl"
                type="url"
                value={gameUrl}
                onChange={(e) => setGameUrl(e.target.value)}
                placeholder="https://lichess.org/ABC123"
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                required
                disabled={loading}
              />
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
                {error}
              </div>
            )}

            {loading && progress && (
              <div className="space-y-2">
                <div className="flex justify-between text-sm text-gray-600">
                  <span>{progress.message}</span>
                  <span>{progress.progress}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                  <div
                    className="bg-blue-600 h-3 rounded-full transition-all duration-300 ease-out"
                    style={{ width: `${progress.progress}%` }}
                  ></div>
                </div>
                {progress.total > 0 && (
                  <div className="text-xs text-gray-500 text-center">
                    {progress.current} / {progress.total} 수 평가 완료
                  </div>
                )}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-blue-600 text-white py-3 px-6 rounded-lg font-semibold hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? (
                <span className="flex items-center justify-center">
                  <svg
                    className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    ></circle>
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    ></path>
                  </svg>
                  분석 중...
                </span>
              ) : (
                "분석 시작"
              )}
            </button>
          </form>

          <div className="mt-8 text-sm text-gray-500 space-y-2">
            <p className="font-semibold">사용 방법:</p>
            <ol className="list-decimal list-inside space-y-1 ml-2">
              <li>Lichess.org에서 게임 링크를 복사하세요</li>
              <li>링크를 입력란에 붙여넣으세요</li>
              <li>분석 시작 버튼을 클릭하세요</li>
              <li>분석 완료 후 상세 리포트를 확인하세요</li>
            </ol>
          </div>
        </div>
      </div>
    </div>
  );
}
