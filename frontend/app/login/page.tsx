"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { GraduationCap, Loader2 } from "lucide-react";
import { login, register } from "@/lib/auth";

type Tab = "login" | "register";

export default function LoginPage() {
  const router = useRouter();
  const [tab, setTab] = useState<Tab>("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      if (tab === "login") {
        await login(username, password);
      } else {
        await register(username, password, displayName);
      }
      router.push("/");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50 flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-6">
          <GraduationCap className="w-12 h-12 mx-auto text-blue-600 mb-2" />
          <h1 className="text-2xl font-bold text-gray-900">EnglishMaster</h1>
          <p className="text-sm text-gray-500 mt-1">八年级英语 AI 学习助手</p>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
          <div className="flex gap-2 mb-6">
            <button
              onClick={() => { setTab("login"); setError(null); }}
              className={`flex-1 py-2 rounded-lg text-sm font-medium ${
                tab === "login"
                  ? "bg-blue-50 text-blue-700"
                  : "text-gray-600 hover:bg-gray-50"
              }`}
            >
              登录
            </button>
            <button
              onClick={() => { setTab("register"); setError(null); }}
              className={`flex-1 py-2 rounded-lg text-sm font-medium ${
                tab === "register"
                  ? "bg-blue-50 text-blue-700"
                  : "text-gray-600 hover:bg-gray-50"
              }`}
            >
              注册
            </button>
          </div>

          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">用户名</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                minLength={3}
                autoComplete="username"
                className="w-full rounded-lg border border-gray-300 px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder={tab === "register" ? "至少 3 个字符" : "你的用户名"}
              />
            </div>

            {tab === "register" && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">昵称（可选）</label>
                <input
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="显示用，不填则用用户名"
                />
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">密码</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={4}
                autoComplete={tab === "login" ? "current-password" : "new-password"}
                className="w-full rounded-lg border border-gray-300 px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder={tab === "register" ? "至少 4 个字符" : "你的密码"}
              />
            </div>

            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-lg bg-blue-600 text-white py-2.5 hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {loading && <Loader2 className="w-4 h-4 animate-spin" />}
              {loading ? "处理中…" : tab === "login" ? "登录" : "注册"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
