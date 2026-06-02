"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Loader2 } from "lucide-react";
import { generateQuiz, gradeAnswer, Question, GradeResult } from "@/lib/api";
import { QuizCard } from "@/components/quiz/QuizCard";
import { useAuth } from "@/hooks/useAuth";

const UNITS = Array.from({ length: 10 }, (_, i) => `Unit ${i + 1}`);
const QUIZ_TYPES = [
  { id: "multiple_choice", label: "单选题" },
  { id: "fill_blank",      label: "填空题" },
  { id: "translation",     label: "翻译题" },
];
const DIFFICULTIES = [
  { id: "easy",   label: "简单" },
  { id: "medium", label: "中等" },
  { id: "hard",   label: "困难" },
];

export default function QuizPage() {
  const router = useRouter();
  const [unit, setUnit] = useState("Unit 1");
  const [semester, setSemester] = useState(1);
  const [quizType, setQuizType] = useState<"multiple_choice" | "fill_blank" | "translation">("multiple_choice");
  const [count, setCount] = useState(3);
  const [difficulty, setDifficulty] = useState<"easy" | "medium" | "hard">("medium");

  const [questions, setQuestions] = useState<Question[]>([]);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [results, setResults] = useState<GradeResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [started, setStarted] = useState(false);
  const [finished, setFinished] = useState(false);

  const { loading: authLoading } = useAuth();
  if (authLoading) {
    return <div className="min-h-screen flex items-center justify-center text-gray-500">加载中…</div>;
  }

  const start = async () => {
    setLoading(true);
    setError(null);
    setStarted(false);
    setFinished(false);
    setQuestions([]);
    setResults([]);
    setCurrentIdx(0);
    try {
      const qs = await generateQuiz(unit, semester, quizType, count, difficulty);
      if (qs.length === 0) {
        setError("未能生成题目，请重试。");
        return;
      }
      setQuestions(qs);
      setStarted(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (q: Question, ans: string): Promise<GradeResult> => {
    const r = await gradeAnswer(q, ans, unit, semester);
    setResults((prev) => {
      const next = [...prev];
      next[currentIdx] = r;
      return next;
    });
    return r;
  };

  const handleNext = () => {
    if (currentIdx + 1 >= questions.length) {
      setFinished(true);
    } else {
      setCurrentIdx((i) => i + 1);
    }
  };

  const totalScore = results.reduce((sum, r) => sum + (r?.score || 0), 0);
  const correctCount = results.filter((r) => r?.is_correct).length;

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center gap-3">
        <button
          onClick={() => router.push("/")}
          className="rounded-lg p-2 hover:bg-gray-100"
        >
          <ArrowLeft className="w-5 h-5 text-gray-700" />
        </button>
        <h1 className="font-semibold text-gray-900">随堂测试</h1>
      </header>

      <main className="max-w-3xl mx-auto px-6 py-8">
        {!started && !finished && (
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-6">选择题库</h2>

            <div className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">学期</label>
                <div className="flex gap-2">
                  {[1, 2].map((s) => (
                    <button
                      key={s}
                      onClick={() => setSemester(s)}
                      className={`rounded-lg px-4 py-2 text-sm ${
                        semester === s
                          ? "bg-blue-600 text-white"
                          : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                      }`}
                    >
                      {s === 1 ? "上册" : "下册"}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">单元</label>
                <div className="grid grid-cols-5 gap-2">
                  {UNITS.map((u) => (
                    <button
                      key={u}
                      onClick={() => setUnit(u)}
                      className={`rounded-lg px-3 py-2 text-sm ${
                        unit === u
                          ? "bg-blue-600 text-white"
                          : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                      }`}
                    >
                      {u}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">题型</label>
                <div className="flex gap-2">
                  {QUIZ_TYPES.map((t) => (
                    <button
                      key={t.id}
                      onClick={() => setQuizType(t.id as typeof quizType)}
                      className={`rounded-lg px-4 py-2 text-sm ${
                        quizType === t.id
                          ? "bg-blue-600 text-white"
                          : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                      }`}
                    >
                      {t.label}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">题数</label>
                <div className="flex gap-2">
                  {[3, 5, 10].map((n) => (
                    <button
                      key={n}
                      onClick={() => setCount(n)}
                      className={`rounded-lg px-4 py-2 text-sm ${
                        count === n
                          ? "bg-blue-600 text-white"
                          : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                      }`}
                    >
                      {n} 题
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">难度</label>
                <div className="flex gap-2">
                  {DIFFICULTIES.map((d) => (
                    <button
                      key={d.id}
                      onClick={() => setDifficulty(d.id as typeof difficulty)}
                      className={`rounded-lg px-4 py-2 text-sm ${
                        difficulty === d.id
                          ? "bg-blue-600 text-white"
                          : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                      }`}
                    >
                      {d.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <button
              onClick={start}
              disabled={loading}
              className="w-full mt-8 rounded-lg bg-blue-600 text-white py-3 hover:bg-blue-700 disabled:bg-gray-300 flex items-center justify-center gap-2"
            >
              {loading && <Loader2 className="w-5 h-5 animate-spin" />}
              {loading ? "AI 出题中…" : "开始测试"}
            </button>

            {error && (
              <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                {error}
              </div>
            )}
          </div>
        )}

        {started && !finished && questions[currentIdx] && (
          <QuizCard
            question={questions[currentIdx]}
            index={currentIdx}
            total={questions.length}
            unit={unit}
            semester={semester}
            onSubmit={handleSubmit}
            onNext={handleNext}
          />
        )}

        {finished && (
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-2xl font-semibold text-gray-900 mb-6 text-center">
              测试完成！
            </h2>
            <div className="grid grid-cols-3 gap-4 mb-6">
              <div className="bg-blue-50 rounded-lg p-4 text-center">
                <div className="text-3xl font-bold text-blue-600">
                  {Math.round(totalScore * 100) / questions.length}
                </div>
                <div className="text-sm text-gray-600 mt-1">总分</div>
              </div>
              <div className="bg-green-50 rounded-lg p-4 text-center">
                <div className="text-3xl font-bold text-green-600">{correctCount}</div>
                <div className="text-sm text-gray-600 mt-1">答对</div>
              </div>
              <div className="bg-gray-50 rounded-lg p-4 text-center">
                <div className="text-3xl font-bold text-gray-600">{questions.length - correctCount}</div>
                <div className="text-sm text-gray-600 mt-1">答错</div>
              </div>
            </div>
            <button
              onClick={() => {
                setStarted(false);
                setFinished(false);
                setResults([]);
                setCurrentIdx(0);
              }}
              className="w-full rounded-lg bg-blue-600 text-white py-3 hover:bg-blue-700"
            >
              再测一次
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
