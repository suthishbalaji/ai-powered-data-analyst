import { useState, useRef, useEffect } from "react";
import { FiSend, FiUser, FiCpu } from "react-icons/fi";
import { askQuestion } from "../services/api";
import AnswerCard from "./AnswerCard";

const EXAMPLES = [
  "Which region has highest sales?",
  "Show monthly revenue trend.",
  "Find anomalies in the data.",
  "Top 5 customers by revenue.",
  "Generate SQL for total sales by category.",
  "Generate Pandas code for average profit.",
];

export default function ChatBox({ hasData, suggestedQuestions, selectedDataset }) {
  const [query, setQuery] = useState("");
  const [history, setHistory] = useState([]); // [{role, content, data}]
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef();

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history]);

  // Clear chat history when the active dataset changes so answers stay scoped
  useEffect(() => {
    if (selectedDataset) setHistory([]);
  }, [selectedDataset]);

  const send = async (q) => {
    const text = (q || query).trim();
    if (!text) return;
    if (!hasData) {
      setHistory((h) => [...h, { role: "assistant", content: "Please upload a CSV file first before asking questions." }]);
      return;
    }

    const chatHistory = history.map(({ role, content }) => ({ role, content }));
    setHistory((h) => [...h, { role: "user", content: text }]);
    setQuery("");
    setLoading(true);

    try {
      const res = await askQuestion(text, chatHistory, selectedDataset);
      setHistory((h) => [...h, { role: "assistant", content: res.data.answer, data: res.data }]);
    } catch (e) {
      const msg = e.response?.data?.detail || "Something went wrong. Please try again.";
      setHistory((h) => [...h, { role: "assistant", content: msg }]);
    } finally {
      setLoading(false);
    }
  };

  const displayExamples = (suggestedQuestions && suggestedQuestions.length > 0) ? suggestedQuestions : EXAMPLES;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-8">
      <h2 className="text-base font-semibold text-gray-800 mb-5">Ask AI</h2>

      {/* Example prompts */}
      <div className="flex flex-wrap gap-2 mb-5">
        {displayExamples.map((ex) => (
          <button
            key={ex}
            onClick={() => send(ex)}
            className="text-xs bg-slate-50 hover:bg-blue-50 hover:text-primary border border-slate-200 hover:border-primary text-gray-600 px-3 py-1.5 rounded-full transition-colors"
          >
            {ex}
          </button>
        ))}
      </div>

      {/* Chat history */}
      {history.length > 0 && (
        <div className="space-y-4 mb-5 max-h-[500px] overflow-y-auto pr-1">
          {history.map((msg, i) => (
            <div key={i} className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              {msg.role === "assistant" && (
                <div className="bg-primary text-white rounded-full p-1.5 h-7 w-7 flex items-center justify-center flex-shrink-0 mt-1">
                  <FiCpu className="text-xs" />
                </div>
              )}
              <div className={`max-w-[85%] ${msg.role === "user" ? "order-first" : ""}`}>
                {msg.role === "user" ? (
                  <div className="bg-primary text-white rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm">
                    {msg.content}
                  </div>
                ) : (
                  <AnswerCard data={msg.data} content={msg.content} />
                )}
              </div>
              {msg.role === "user" && (
                <div className="bg-slate-100 rounded-full p-1.5 h-7 w-7 flex items-center justify-center flex-shrink-0 mt-1">
                  <FiUser className="text-gray-500 text-xs" />
                </div>
              )}
            </div>
          ))}
          {loading && (
            <div className="flex gap-3">
              <div className="bg-primary text-white rounded-full p-1.5 h-7 w-7 flex items-center justify-center flex-shrink-0">
                <FiCpu className="text-xs" />
              </div>
              <div className="bg-slate-50 rounded-2xl rounded-tl-sm px-4 py-3">
                <div className="flex gap-1">
                  <span className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                  <span className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                  <span className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                </div>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      )}

      {/* Input */}
      <div className="flex gap-3">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
          placeholder="Ask anything about your data..."
          className="flex-1 border border-slate-200 rounded-xl px-4 py-3 text-sm text-gray-800 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
        />
        <button
          onClick={() => send()}
          disabled={loading || !query.trim()}
          className="bg-primary hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white px-5 py-3 rounded-xl transition-colors flex items-center gap-2 text-sm font-medium"
        >
          <FiSend /> Ask
        </button>
      </div>
    </div>
  );
}
