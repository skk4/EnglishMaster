"use client";

import { useState } from "react";
import { GradeResult, Question } from "@/lib/api";
import { CheckCircle2, XCircle, Loader2 } from "lucide-react";

interface QuizCardProps {
  question: Question;
  index: number;
  total: number;
  unit: string;
  semester: number;
  onSubmit: (question: Question, answer: string, unit: string, semester: number) => Promise<GradeResult>;
  onNext: () => void;
}

export function QuizCard({ question, index, total, unit, semester, onSubmit, onNext }: QuizCardProps) {
  const [answer, setAnswer] = useState("");
  const [result, setResult] = useState<GradeResult | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const submit = async () => {
    if (!answer.trim() || submitting) return;
    setSubmitting(true);
    try {
      const r = await onSubmit(question, answer, unit, semester);
      setResult(r);
    } finally {
      setSubmitting(false);
    }
  };

  const reset = () => {
    setAnswer("");
    setResult(null);
  };

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <span className="text-sm text-gray-500">
          第 {index + 1} / {total} 题
        </span>
        <span className="text-xs px-2 py-1 rounded bg-blue-50 text-blue-700">
          {question.type === "multiple_choice" ? "单选题" : question.type === "fill_blank" ? "填空题" : "翻译题"}
        </span>
      </div>

      <p className="text-lg text-gray-900 mb-5 leading-relaxed">{question.question}</p>

      {question.type === "multiple_choice" && (
        <div className="space-y-2 mb-4">
          {question.options.map((opt, i) => {
            const letter = opt.trim().charAt(0).toUpperCase();
            const isSelected = answer.toUpperCase() === letter;
            const isCorrectAnswer = question.answer.toUpperCase() === letter;
            const showAsCorrect = result && isCorrectAnswer;
            const showAsWrong = result && isSelected && !isCorrectAnswer;
            return (
              <button
                key={i}
                onClick={() => !result && setAnswer(letter)}
                disabled={!!result}
                className={`w-full text-left rounded-lg px-4 py-3 border-2 transition-colors ${
                  showAsCorrect
                    ? "border-green-500 bg-green-50"
                    : showAsWrong
                    ? "border-red-500 bg-red-50"
                    : isSelected
                    ? "border-blue-500 bg-blue-50"
                    : "border-gray-200 hover:border-gray-300"
                } disabled:cursor-default`}
              >
                <span className="text-gray-900">{opt}</span>
              </button>
            );
          })}
        </div>
      )}

      {(question.type === "fill_blank" || question.type === "translation") && (
        <textarea
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          disabled={!!result}
          placeholder="输入你的答案…"
          rows={3}
          className="w-full rounded-lg border border-gray-300 px-4 py-2 mb-4 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50"
        />
      )}

      {result && (
        <div
          className={`rounded-lg p-4 mb-4 ${
            result.is_correct ? "bg-green-50 border border-green-200" : "bg-red-50 border border-red-200"
          }`}
        >
          <div className="flex items-center gap-2 mb-2">
            {result.is_correct ? (
              <CheckCircle2 className="w-5 h-5 text-green-600" />
            ) : (
              <XCircle className="w-5 h-5 text-red-600" />
            )}
            <span className={`font-medium ${result.is_correct ? "text-green-800" : "text-red-800"}`}>
              {result.is_correct ? "答对了！" : "答错了"} （{Math.round(result.score * 100)}分）
            </span>
          </div>
          <p className="text-sm text-gray-700 mb-1">{result.feedback}</p>
          {result.correction && (
            <p className="text-sm text-gray-600">
              <span className="font-medium">正确答案：</span>
              {result.correction}
            </p>
          )}
          {question.explanation && (
            <p className="text-sm text-gray-600 mt-2">
              <span className="font-medium">教材解析：</span>
              {question.explanation}
            </p>
          )}
        </div>
      )}

      <div className="flex justify-end gap-2">
        {!result ? (
          <button
            onClick={submit}
            disabled={!answer.trim() || submitting}
            className="rounded-lg bg-blue-600 text-white px-5 py-2 hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
            {submitting ? "批改中…" : "提交"}
          </button>
        ) : (
          <>
            <button
              onClick={reset}
              className="rounded-lg border border-gray-300 text-gray-700 px-5 py-2 hover:bg-gray-50"
            >
              重做
            </button>
            <button
              onClick={onNext}
              className="rounded-lg bg-blue-600 text-white px-5 py-2 hover:bg-blue-700"
            >
              {index + 1 === total ? "查看结果" : "下一题"}
            </button>
          </>
        )}
      </div>
    </div>
  );
}
