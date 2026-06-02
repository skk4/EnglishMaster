import { Source } from "@/lib/types";
import { BookOpen, ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";

interface SourcePanelProps {
  sources: Source[];
}

export function SourcePanel({ sources }: SourcePanelProps) {
  const [expanded, setExpanded] = useState(false);

  if (sources.length === 0) return null;

  return (
    <div className="mt-3 pt-3 border-t border-gray-300">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1.5 text-xs text-gray-600 hover:text-gray-900"
      >
        <BookOpen className="w-3.5 h-3.5" />
        <span>教材来源 ({sources.length})</span>
        {expanded ? (
          <ChevronUp className="w-3.5 h-3.5" />
        ) : (
          <ChevronDown className="w-3.5 h-3.5" />
        )}
      </button>
      {expanded && (
        <ul className="mt-2 space-y-1.5 text-xs text-gray-600">
          {sources.map((s, i) => (
            <li key={i} className="flex items-start gap-2">
              <span className="font-mono text-gray-400">[{i + 1}]</span>
              <span>
                {s.unit} {s.section} · 第 {s.page_num} 页 · 学期 {s.semester}
                <span className="ml-2 text-gray-400">
                  (相关性 {(s.score * 100).toFixed(0)}%)
                </span>
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
