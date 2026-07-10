import { useState } from "react";
import { FiCopy, FiCheck, FiChevronDown, FiChevronUp } from "react-icons/fi";
import ChartCard from "./ChartCard";

function CodeBlock({ code, label }) {
  const [copied, setCopied] = useState(false);

  const copy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="mt-3">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-medium text-gray-500">{label}</span>
        <button onClick={copy} className="text-xs text-gray-400 hover:text-primary flex items-center gap-1 transition-colors">
          {copied ? <><FiCheck className="text-green-500" /> Copied</> : <><FiCopy /> Copy</>}
        </button>
      </div>
      <pre className="code-block text-xs">{code}</pre>
    </div>
  );
}

// Simple markdown-like renderer for bold text
function MarkdownText({ text }) {
  if (!text) return null;
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return (
    <span>
      {parts.map((part, i) =>
        part.startsWith("**") && part.endsWith("**")
          ? <strong key={i}>{part.slice(2, -2)}</strong>
          : part
      )}
    </span>
  );
}

export default function AnswerCard({ data, content }) {
  const [showReasoning, setShowReasoning] = useState(false);

  if (!data && !content) return null;

  const answer = data?.answer || content;
  const reasoning = data?.reasoning;
  const sqlCode = data?.sql_code;
  const pandasCode = data?.pandas_code;
  const chart = data?.chart;

  // Safely validate chart data to avoid crashes on malformed payloads
  const safeChart = (() => {
    try {
      if (!chart || !Array.isArray(chart.data) || chart.data.length === 0) return null;
      const valid = chart.data.every(
        (d) => d !== null && typeof d === "object" && ("value" in d || ("x" in d && "y" in d))
      );
      return valid ? chart : null;
    } catch {
      return null;
    }
  })();

  return (
    <div className="bg-slate-50 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-gray-800 space-y-3">
      {/* Answer text */}
      <div className="leading-relaxed whitespace-pre-wrap">
        {answer?.split("\n").map((line, i) => (
          <p key={i} className={line.startsWith("- ") ? "ml-2" : ""}>
            <MarkdownText text={line} />
          </p>
        ))}
      </div>

      {/* Inline chart — only rendered when chart data is valid */}
      {safeChart && <ChartCard chart={safeChart} compact />}

      {/* SQL Code */}
      {sqlCode && <CodeBlock code={sqlCode} label="SQL Query" />}

      {/* Pandas Code */}
      {pandasCode && <CodeBlock code={pandasCode} label="Pandas Code" />}

      {/* Reasoning toggle */}
      {reasoning && (
        <div>
          <button
            onClick={() => setShowReasoning((v) => !v)}
            className="text-xs text-gray-400 hover:text-primary flex items-center gap-1 transition-colors"
          >
            {showReasoning ? <FiChevronUp /> : <FiChevronDown />}
            Why this answer?
          </button>
          {showReasoning && (
            <p className="mt-2 text-xs text-gray-500 bg-white rounded-lg px-3 py-2 border border-slate-100">
              {reasoning}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
