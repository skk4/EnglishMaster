"use client";

import { useCallback, useRef, useState } from "react";
import { chatStream, getSession, ChatSessionDetail } from "@/lib/api";
import { Message, Source } from "@/lib/types";

function parseSources(raw: string): Source[] {
  if (!raw) return [];
  try {
    return JSON.parse(raw);
  } catch {
    return [];
  }
}

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [sessionTitle, setSessionTitle] = useState<string>("新对话");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const idCounter = useRef(0);

  const newId = useCallback(() => {
    idCounter.current += 1;
    return `msg_${Date.now()}_${idCounter.current}`;
  }, []);

  const loadSession = useCallback(async (sid: number) => {
    try {
      const data: ChatSessionDetail = await getSession(sid);
      setSessionId(data.id);
      setSessionTitle(data.title);
      setMessages(
        data.messages.map((m) => ({
          id: `hist_${m.id}`,
          role: m.role as "user" | "assistant",
          content: m.content,
          sources: parseSources(m.sources_json),
        }))
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  const startNew = useCallback(() => {
    setSessionId(null);
    setSessionTitle("新对话");
    setMessages([]);
    setError(null);
  }, []);

  const send = useCallback(
    async (text: string, mode: "general" | "grammar" | "quiz" | "conversation" = "general") => {
      if (!text.trim() || isLoading) return;

      setError(null);
      const userMsg: Message = { id: newId(), role: "user", content: text };
      const assistantId = newId();
      const assistantMsg: Message = {
        id: assistantId,
        role: "assistant",
        content: "",
        streaming: true,
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setIsLoading(true);

      const history = messages
        .filter((m) => m.role === "user" || m.role === "assistant")
        .filter((m) => !m.streaming)
        .map((m) => ({ role: m.role, content: m.content }));

      // 客户端 think 块过滤状态机（双保险：后端已剥，前端再过滤）
      let thinkBuf = "";
      let inThink = false;

      await chatStream(
        { message: text, history, mode, session_id: sessionId ?? undefined },
        (delta) => {
          thinkBuf += delta;
          let visibleDelta = "";

          while (true) {
            if (!inThink) {
              const idx = thinkBuf.indexOf("<think>");
              if (idx === -1) {
                visibleDelta += thinkBuf;
                thinkBuf = "";
                break;
              }
              if (idx > 0) visibleDelta += thinkBuf.slice(0, idx);
              thinkBuf = thinkBuf.slice(idx + "<think>".length);
              inThink = true;
            } else {
              const idx = thinkBuf.indexOf("</think>");
              if (idx === -1) break;  // 等下个 chunk
              thinkBuf = thinkBuf.slice(idx + "</think>".length);
              inThink = false;
            }
          }

          if (visibleDelta) {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId ? { ...m, content: m.content + visibleDelta } : m
              )
            );
          }
        },
        (sources: Source[], sid: number | null) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? { ...m, sources, streaming: false }
                : m
            )
          );
          if (sid && !sessionId) {
            setSessionId(sid);
            setSessionTitle(text.slice(0, 30) + (text.length > 30 ? "..." : ""));
          }
          setIsLoading(false);
        },
        (err: Error) => {
          setError(err.message);
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? {
                    ...m,
                    content: m.content || "抱歉，回答出错了，请重试。",
                    streaming: false,
                  }
                : m
            )
          );
          setIsLoading(false);
        }
      );
    },
    [messages, isLoading, sessionId, newId]
  );

  const clear = useCallback(() => {
    setMessages([]);
    setSessionId(null);
    setSessionTitle("新对话");
    setError(null);
  }, []);

  return {
    messages,
    sessionId,
    sessionTitle,
    isLoading,
    error,
    send,
    clear,
    loadSession,
    startNew,
  };
}
