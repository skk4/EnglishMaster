"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Message } from "@/lib/types";
import { SourcePanel } from "./SourcePanel";

const MODE_LABELS: Record<string, { icon: string; label: string }> = {
  general:      { icon: "💡", label: "通用" },
  grammar:      { icon: "📖", label: "语法" },
  quiz:         { icon: "📝", label: "出题" },
  conversation: { icon: "💬", label: "对话" },
};

interface MessageBubbleProps {
  message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const modeInfo = message.mode ? MODE_LABELS[message.mode] : null;

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
      <div className="max-w-[80%]">
        {!isUser && modeInfo && (
          <div className="text-xs text-gray-500 mb-1 px-3 flex items-center gap-1">
            <span>{modeInfo.icon}</span>
            <span>{modeInfo.label}</span>
          </div>
        )}
        <div
          className={`rounded-2xl px-4 py-3 ${
            isUser
              ? "bg-blue-600 text-white"
              : "bg-gray-100 text-gray-900"
          }`}
        >
          {isUser ? (
            <div className="whitespace-pre-wrap break-words">{message.content}</div>
          ) : (
            <>
              <div className="prose prose-sm max-w-none prose-headings:mt-3 prose-headings:mb-2 prose-p:my-2 prose-li:my-1">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {message.content || (message.streaming ? "..." : "")}
                </ReactMarkdown>
                {message.streaming && message.content && (
                  <span className="inline-block w-2 h-4 ml-1 bg-gray-500 animate-pulse" />
                )}
              </div>
              {message.sources && message.sources.length > 0 && (
                <SourcePanel sources={message.sources} />
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
