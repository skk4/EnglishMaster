"use client";

import { useState } from "react";
import { Send } from "lucide-react";

interface InputBarProps {
  onSend: (text: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function InputBar({
  onSend,
  disabled = false,
  placeholder = "输入你的问题，回车发送…",
}: InputBarProps) {
  const [text, setText] = useState("");

  const submit = () => {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText("");
  };

  return (
    <div className="border-t border-gray-200 bg-white px-4 py-3">
      <div className="max-w-3xl mx-auto flex items-end gap-2">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
          placeholder={placeholder}
          rows={1}
          disabled={disabled}
          className="flex-1 resize-none rounded-xl border border-gray-300 px-4 py-2.5 text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50 disabled:text-gray-400 max-h-32"
          style={{ minHeight: "44px" }}
        />
        <button
          onClick={submit}
          disabled={disabled || !text.trim()}
          className="rounded-xl bg-blue-600 text-white px-4 py-2.5 hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center gap-1.5"
        >
          <Send className="w-4 h-4" />
          <span>发送</span>
        </button>
      </div>
    </div>
  );
}
