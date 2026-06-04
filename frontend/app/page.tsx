"use client";

import { useRef, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { BookOpen, Trash2, GraduationCap, ClipboardList, BookMarked, BarChart3, LogOut, Plus, MessageSquare } from "lucide-react";
import { useChat } from "@/hooks/useChat";
import { useAuth } from "@/hooks/useAuth";
import { clearAuth } from "@/lib/auth";
import { listSessions, deleteSession, ChatSessionMeta } from "@/lib/api";
import { MessageBubble } from "@/components/chat/MessageBubble";
import { InputBar } from "@/components/chat/InputBar";

type Mode = "general" | "grammar" | "quiz" | "conversation";

const MODES: { id: Mode; label: string; hint: string }[] = [
  { id: "general",      label: "通用问答", hint: "日常学习问题" },
  { id: "grammar",      label: "语法讲解", hint: "详细解释语法点" },
  { id: "quiz",         label: "出题练习", hint: "AI 出题给你做" },
  { id: "conversation", label: "对话练习", hint: "和 AI 练口语" },
];

export default function Home() {
  const { messages, sessionId, sessionTitle, isLoading, error, send, loadSession, startNew } = useChat();
  const { user, loading } = useAuth();
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("general");
  const [sessions, setSessions] = useState<ChatSessionMeta[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  const refreshSessions = async () => {
    if (!user) return;
    try {
      const list = await listSessions();
      setSessions(list);
    } catch (e) {
      console.error("Failed to load sessions:", e);
    }
  };

  useEffect(() => {
    if (user) refreshSessions();
  }, [user]);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages]);

  useEffect(() => {
    if (user && sessionId) refreshSessions();
  }, [sessionId]);

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center text-gray-500">加载中…</div>;
  }
  if (!user) return null;

  const handleLogout = () => {
    clearAuth();
    router.push("/login");
  };

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-gray-200 flex flex-col">
        <div className="px-4 py-4 border-b border-gray-200">
          <div className="flex items-center gap-2">
            <GraduationCap className="w-6 h-6 text-blue-600" />
            <div>
              <h1 className="font-semibold text-gray-900">EnglishMaster</h1>
              <p className="text-xs text-gray-500">八年级英语 AI 助手</p>
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-3">
          <div className="text-xs text-gray-500 uppercase tracking-wide mb-2 px-2">
            模式
          </div>
          <div className="space-y-1">
            {MODES.map((m) => (
              <button
                key={m.id}
                onClick={() => setMode(m.id)}
                className={`w-full text-left rounded-lg px-3 py-2 transition-colors ${
                  mode === m.id
                    ? "bg-blue-50 text-blue-700"
                    : "text-gray-700 hover:bg-gray-100"
                }`}
              >
                <div className="text-sm font-medium">{m.label}</div>
                <div className="text-xs text-gray-500 mt-0.5">{m.hint}</div>
              </button>
            ))}
          </div>

          <div className="mt-4 pt-4 border-t border-gray-200">
            <div className="flex items-center justify-between mb-2 px-2">
              <div className="text-xs text-gray-500 uppercase tracking-wide">对话历史</div>
              <button
                onClick={() => startNew()}
                className="rounded p-1 hover:bg-gray-100"
                title="新建对话"
              >
                <Plus className="w-3.5 h-3.5 text-gray-500" />
              </button>
            </div>
            {sessions.length === 0 ? (
              <div className="px-3 py-2 text-xs text-gray-400">暂无历史</div>
            ) : (
              <div className="space-y-1">
                {sessions.map((s) => (
                  <div
                    key={s.id}
                    className={`group flex items-center gap-2 rounded-lg px-3 py-2 cursor-pointer ${
                      sessionId === s.id
                        ? "bg-blue-50 text-blue-700"
                        : "text-gray-700 hover:bg-gray-100"
                    }`}
                  >
                    <MessageSquare className="w-3.5 h-3.5 flex-shrink-0" />
                    <div
                      onClick={() => loadSession(s.id)}
                      className="flex-1 min-w-0 text-sm truncate"
                    >
                      {s.title}
                    </div>
                    <button
                      onClick={async (e) => {
                        e.stopPropagation();
                        if (!confirm(`删除"${s.title}"？`)) return;
                        await deleteSession(s.id);
                        if (sessionId === s.id) startNew();
                        await refreshSessions();
                      }}
                      className="opacity-0 group-hover:opacity-100 rounded p-0.5 hover:bg-gray-200"
                      title="删除"
                    >
                      <Trash2 className="w-3 h-3 text-gray-500" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="mt-4 pt-4 border-t border-gray-200">
            <Link
              href="/quiz"
              className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-gray-700 hover:bg-gray-100"
            >
              <ClipboardList className="w-4 h-4" />
              随堂测试
            </Link>
            <Link
              href="/vocabulary"
              className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-gray-700 hover:bg-gray-100"
            >
              <BookMarked className="w-4 h-4" />
              词汇练习
            </Link>
            <Link
              href="/progress"
              className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-gray-700 hover:bg-gray-100"
            >
              <BarChart3 className="w-4 h-4" />
              学习进度
            </Link>
          </div>
        </div>

        <div className="p-3 border-t border-gray-200">
          <div className="flex items-center gap-2 px-3 py-2">
            <div className="w-7 h-7 rounded-full bg-blue-600 text-white text-xs flex items-center justify-center font-medium">
              {user.display_name.charAt(0).toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-gray-900 truncate">{user.display_name}</div>
            </div>
            <button
              onClick={handleLogout}
              title="退出登录"
              className="rounded-lg p-1.5 hover:bg-gray-100"
            >
              <LogOut className="w-4 h-4 text-gray-500" />
            </button>
          </div>
        </div>
      </aside>

      {/* Chat area */}
      <main className="flex-1 flex flex-col">
        <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-blue-600" />
          <h2 className="font-medium text-gray-900 truncate">
            {sessionTitle}
          </h2>
          <span className="text-xs text-gray-400 ml-2">
            {MODES.find((m) => m.id === mode)?.label}
          </span>
          <span className="ml-auto text-xs text-gray-400">
            基于人教版八年级英语
          </span>
        </header>

        <div ref={scrollRef} className="flex-1 overflow-y-auto px-6 py-6">
          <div className="max-w-3xl mx-auto">
            {messages.length === 0 && (
              <div className="text-center text-gray-400 mt-20">
                <GraduationCap className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p className="text-sm">开始你的英语学习之旅</p>
                <p className="text-xs mt-1">试试问：&ldquo;Unit 1 的 Grammar Focus 讲什么？&rdquo;</p>
              </div>
            )}
            {messages.map((m) => (
              <MessageBubble key={m.id} message={m} />
            ))}
            {error && (
              <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                {error}
              </div>
            )}
          </div>
        </div>

        <InputBar
          onSend={(text) => send(text, mode)}
          disabled={isLoading}
          placeholder={isLoading ? "AI 正在回答…" : "输入你的问题，回车发送…"}
        />
      </main>
    </div>
  );
}
