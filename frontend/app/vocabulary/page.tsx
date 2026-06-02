"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Loader2, RotateCw, Check, X, Volume2 } from "lucide-react";
import { getPracticeWords, updateVocabProgress, Word } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";

export default function VocabularyPage() {
  const router = useRouter();
  const [semester, setSemester] = useState(1);
  const [words, setWords] = useState<Word[]>([]);
  const [idx, setIdx] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [loading, setLoading] = useState(false);

  const { loading: authLoading } = useAuth();

  const loadNew = async (s: number) => {
    setLoading(true);
    setFlipped(false);
    setIdx(0);
    const ws = await getPracticeWords(s, 10);
    setWords(ws);
    setLoading(false);
  };

  useEffect(() => {
    loadNew(semester);
  }, [semester]);

  if (authLoading) {
    return <div className="min-h-screen flex items-center justify-center text-gray-500">加载中…</div>;
  }

  const mark = async (mastered: boolean) => {
    if (words[idx]) {
      await updateVocabProgress(words[idx].word, words[idx].unit, semester, mastered);
    }
    if (idx + 1 >= words.length) {
      setIdx(0);
      setFlipped(false);
      await loadNew(semester);
    } else {
      setIdx(idx + 1);
      setFlipped(false);
    }
  };

  const speak = (word: string) => {
    if (typeof window === "undefined" || !window.speechSynthesis) return;
    const u = new SpeechSynthesisUtterance(word);
    u.lang = "en-US";
    u.rate = 0.85;
    window.speechSynthesis.speak(u);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center gap-3">
        <button onClick={() => router.push("/")} className="rounded-lg p-2 hover:bg-gray-100">
          <ArrowLeft className="w-5 h-5 text-gray-700" />
        </button>
        <h1 className="font-semibold text-gray-900">词汇练习</h1>
        <div className="ml-auto flex gap-2">
          {[1, 2].map((s) => (
            <button
              key={s}
              onClick={() => setSemester(s)}
              className={`rounded-lg px-3 py-1.5 text-sm ${
                semester === s
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
            >
              {s === 1 ? "上册" : "下册"}
            </button>
          ))}
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-6 py-8">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
          </div>
        ) : words.length === 0 ? (
          <div className="text-center text-gray-500 py-20">该学期暂无词汇数据</div>
        ) : (
          <div>
            <div className="text-sm text-gray-500 text-center mb-4">
              第 {idx + 1} / {words.length} 个
            </div>

            <div
              onClick={() => setFlipped(!flipped)}
              className="bg-white rounded-2xl shadow-sm border-2 border-gray-200 min-h-[320px] p-8 flex flex-col items-center justify-center cursor-pointer hover:border-blue-300 transition-colors"
            >
              {!flipped ? (
                <>
                  <h2 className="text-5xl font-bold text-gray-900 mb-3 text-center">
                    {words[idx].word}
                  </h2>
                  {words[idx].phonetic && (
                    <p className="text-gray-500 text-lg mb-4">{words[idx].phonetic}</p>
                  )}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      speak(words[idx].word);
                    }}
                    className="rounded-full p-2 hover:bg-gray-100"
                  >
                    <Volume2 className="w-5 h-5 text-gray-500" />
                  </button>
                  <p className="text-xs text-gray-400 mt-6">点击卡片查看释义</p>
                </>
              ) : (
                <>
                  <p className="text-sm text-gray-500 mb-2">{words[idx].pos}</p>
                  <p className="text-2xl text-gray-900 text-center leading-relaxed">
                    {words[idx].translation}
                  </p>
                  <p className="text-xs text-gray-400 mt-4">
                    {words[idx].unit} · 学期 {semester}
                  </p>
                </>
              )}
            </div>

            {flipped && (
              <div className="grid grid-cols-2 gap-3 mt-6">
                <button
                  onClick={() => mark(false)}
                  className="rounded-xl border-2 border-red-200 text-red-700 py-3 hover:bg-red-50 flex items-center justify-center gap-2"
                >
                  <X className="w-5 h-5" />
                  不认识
                </button>
                <button
                  onClick={() => mark(true)}
                  className="rounded-xl border-2 border-green-200 text-green-700 py-3 hover:bg-green-50 flex items-center justify-center gap-2"
                >
                  <Check className="w-5 h-5" />
                  认识了
                </button>
              </div>
            )}

            <div className="mt-4 text-center">
              <button
                onClick={() => loadNew(semester)}
                className="text-sm text-gray-500 hover:text-gray-700 inline-flex items-center gap-1"
              >
                <RotateCw className="w-3.5 h-3.5" />
                换一批
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
