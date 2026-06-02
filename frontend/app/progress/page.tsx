"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Loader2, Target, CheckCircle2, BarChart3 } from "lucide-react";
import { getProgressSummary, getRecentRecords, ProgressSummary, QuizRecord } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";

export default function ProgressPage() {
  const router = useRouter();
  const [summary, setSummary] = useState<ProgressSummary | null>(null);
  const [records, setRecords] = useState<QuizRecord[]>([]);
  const [loading, setLoading] = useState(true);

  const { loading: authLoading } = useAuth();

  useEffect(() => {
    Promise.all([getProgressSummary(), getRecentRecords(20)])
      .then(([s, r]) => {
        setSummary(s);
        setRecords(r);
      })
      .finally(() => setLoading(false));
  }, []);

  if (authLoading) {
    return <div className="min-h-screen flex items-center justify-center text-gray-500">加载中…</div>;
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (!summary) return null;

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center gap-3">
        <button onClick={() => router.push("/")} className="rounded-lg p-2 hover:bg-gray-100">
          <ArrowLeft className="w-5 h-5 text-gray-700" />
        </button>
        <h1 className="font-semibold text-gray-900">学习进度</h1>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-8">
        <section className="grid grid-cols-3 gap-4 mb-8">
          <div className="bg-white rounded-xl p-5 border border-gray-200">
            <div className="flex items-center gap-2 text-gray-500 text-sm mb-2">
              <BarChart3 className="w-4 h-4" />
              <span>总题数</span>
            </div>
            <div className="text-3xl font-bold text-gray-900">{summary.total}</div>
          </div>
          <div className="bg-white rounded-xl p-5 border border-gray-200">
            <div className="flex items-center gap-2 text-gray-500 text-sm mb-2">
              <CheckCircle2 className="w-4 h-4" />
              <span>正确率</span>
            </div>
            <div className="text-3xl font-bold text-green-600">
              {Math.round(summary.accuracy * 100)}%
            </div>
          </div>
          <div className="bg-white rounded-xl p-5 border border-gray-200">
            <div className="flex items-center gap-2 text-gray-500 text-sm mb-2">
              <Target className="w-4 h-4" />
              <span>平均分</span>
            </div>
            <div className="text-3xl font-bold text-blue-600">
              {Math.round(summary.avg_score * 100)}
            </div>
          </div>
        </section>

        {summary.weak_units.length > 0 && (
          <section className="mb-8">
            <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-3">
              薄弱单元（需加强）
            </h2>
            <div className="space-y-2">
              {summary.weak_units.map((u) => (
                <div
                  key={u.unit}
                  className="bg-white rounded-lg p-4 border border-gray-200 flex items-center gap-4"
                >
                  <div className="flex-1">
                    <div className="font-medium text-gray-900">{u.unit}</div>
                    <div className="text-xs text-gray-500 mt-0.5">
                      {u.correct} / {u.total} 正确
                    </div>
                  </div>
                  <div className="w-32 bg-gray-200 rounded-full h-2 overflow-hidden">
                    <div
                      className="bg-blue-600 h-full"
                      style={{ width: `${u.accuracy * 100}%` }}
                    />
                  </div>
                  <div className="text-sm text-gray-700 w-12 text-right">
                    {Math.round(u.accuracy * 100)}%
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        <section>
          <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-3">
            最近记录
          </h2>
          {records.length === 0 ? (
            <div className="bg-white rounded-lg p-8 text-center text-gray-500 border border-gray-200">
              还没有做题记录，去测试一下吧！
            </div>
          ) : (
            <div className="bg-white rounded-lg border border-gray-200 divide-y divide-gray-100">
              {records.map((r) => (
                <div key={r.id} className="px-4 py-3 flex items-center gap-3">
                  <div
                    className={`w-2 h-2 rounded-full ${
                      r.is_correct ? "bg-green-500" : "bg-red-500"
                    }`}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="text-sm text-gray-900 truncate">
                      {r.question}
                    </div>
                    <div className="text-xs text-gray-500 mt-0.5">
                      学期 {r.semester} · {r.unit} · {r.quiz_type}
                    </div>
                  </div>
                  <div
                    className={`text-sm font-medium ${
                      r.is_correct ? "text-green-600" : "text-red-600"
                    }`}
                  >
                    {Math.round(r.score * 100)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
