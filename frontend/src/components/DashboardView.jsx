import { useEffect, useState } from "react";
import { FiX, FiFileText, FiDatabase, FiGrid, FiAlertTriangle, FiTrendingUp, FiCheckCircle, FiChevronDown, FiChevronUp, FiPrinter } from "react-icons/fi";
import { getDashboardData } from "../services/api";
import ChartCard from "./ChartCard";

// Helper for rendering **bold** markdown tags in executive narrative
function SimpleMarkdown({ text }) {
  if (!text) return null;
  return text.split("\n\n").map((para, i) => {
    // Check if paragraph is list item
    const lineParts = para.split("\n");
    return (
      <div key={i} className="mb-4">
        {lineParts.map((line, idx) => {
          const isBullet = line.trim().startsWith("- ");
          const cleanLine = isBullet ? line.trim().substring(2) : line;
          
          const textParts = cleanLine.split(/(\*\*[^*]+\*\*)/g);
          const content = textParts.map((part, pidx) => {
            if (part.startsWith("**") && part.endsWith("**")) {
              return <strong key={pidx} className="text-white font-bold">{part.slice(2, -2)}</strong>;
            }
            return part;
          });
          
          if (isBullet) {
            return (
              <ul key={idx} className="list-disc pl-5 my-1 text-slate-300">
                <li>{content}</li>
              </ul>
            );
          }
          return <p key={idx} className="leading-relaxed text-slate-300 text-sm mb-2">{content}</p>;
        })}
      </div>
    );
  });
}

const StatCard = ({ icon, label, value, colorClass = "from-blue-500/20 to-indigo-500/20 border-blue-500/30 text-blue-400" }) => (
  <div className={`backdrop-blur-md bg-slate-900/60 border rounded-2xl p-5 flex items-center gap-4 shadow-xl transition-all hover:scale-105 hover:bg-slate-900/80 bg-gradient-to-br ${colorClass}`}>
    <div className="text-3xl p-3 bg-slate-950/60 rounded-xl">{icon}</div>
    <div>
      <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">{label}</p>
      <p className="text-2xl font-black text-white mt-1">{value}</p>
    </div>
  </div>
);

export default function DashboardView({ onClose, selectedDataset }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showAnomalies, setShowAnomalies] = useState(true);

  useEffect(() => {
    getDashboardData(selectedDataset)
      .then((res) => {
        if (res.data.error) {
          setError(res.data.error);
        } else {
          setData(res.data);
        }
      })
      .catch((err) => {
        setError(err.response?.data?.detail || "Failed to fetch dashboard data. Please try again.");
      })
      .finally(() => setLoading(false));
  }, [selectedDataset]);

  const handlePrint = () => {
    window.print();
  };

  if (loading) {
    return (
      <div className="fixed inset-0 z-50 bg-slate-950 flex flex-col items-center justify-center text-white p-6">
        <div className="flex gap-2 mb-4">
          <span className="w-4 h-4 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
          <span className="w-4 h-4 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
          <span className="w-4 h-4 bg-emerald-500 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
        </div>
        <p className="text-sm font-medium tracking-wide text-slate-430 animate-pulse">Running data analyzer engine...</p>
        <span className="text-xs text-slate-600 mt-2">Computing aggregates, trend patterns, and AI insights</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="fixed inset-0 z-50 bg-slate-950 flex flex-col items-center justify-center text-white p-6">
        <div className="bg-slate-900 border border-red-500/20 p-8 rounded-2xl max-w-md text-center shadow-2xl">
          <FiAlertTriangle className="text-5xl text-red-500 mx-auto mb-4" />
          <h3 className="text-lg font-bold text-white mb-2">Failed to Build Dashboard</h3>
          <p className="text-sm text-slate-400 mb-6">{error}</p>
          <button
            onClick={onClose}
            className="w-full py-2.5 bg-red-650 hover:bg-red-700 bg-red-600 active:bg-red-800 transition-colors text-sm font-semibold rounded-xl text-white"
          >
            Close
          </button>
        </div>
      </div>
    );
  }

  // Deduplicate and aggregate datasets
  const fileNames = Object.keys(data.summaries || {});
  const totalRows = Object.values(data.summaries || {}).reduce((acc, curr) => acc + (curr.rows || 0), 0);
  const totalCols = Object.values(data.summaries || {}).reduce((acc, curr) => acc + (curr.columns || 0), 0);
  const totalMissing = Object.values(data.summaries || {}).reduce((acc, curr) => acc + (curr.missing_values || 0), 0);
  const totalAnomalies = data.anomalies?.length || 0;

  const narrative = data.narrative || {};
  const insights = data.insights || [];
  const charts = data.charts || [];
  const anomalies = data.anomalies || [];

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-950 text-slate-100 flex flex-col font-sans print:bg-white print:text-gray-900 print:relative print:inset-auto">
      {/* Navbar overlay */}
      <header className="sticky top-0 z-10 backdrop-blur-lg bg-slate-950/80 border-b border-slate-800 px-6 py-4 flex items-center justify-between shadow-md print:hidden">
        <div className="flex items-center gap-3">
          <div className="bg-gradient-to-tr from-blue-500 to-purple-600 rounded-xl p-2.5 shadow-lg shadow-blue-500/20">
            <FiGrid className="text-white text-xl" />
          </div>
          <div>
            <h1 className="text-lg font-black bg-gradient-to-r from-white via-slate-100 to-slate-400 bg-clip-text text-transparent">
              Executive Business Insights Dashboard
            </h1>
            <p className="text-xs text-slate-500">Comprehensive AI Analytics and Visual Reports</p>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          <button
            onClick={handlePrint}
            className="flex items-center gap-2 px-4 py-2 bg-slate-900 hover:bg-slate-850 border border-slate-700/80 text-slate-200 hover:text-white rounded-xl text-sm font-medium transition-all"
          >
            <FiPrinter className="text-base" />
            Print Report
          </button>
          
          <button
            onClick={onClose}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-rose-600 to-red-650 hover:from-rose-500 hover:to-red-600 text-white rounded-xl text-sm font-semibold transition-all shadow-lg hover:shadow-red-600/10 active:scale-95"
          >
            <FiX className="text-base" />
            Close Dashboard
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8 space-y-8 flex-1 w-full print:p-0 print:space-y-6">
        
        {/* KPI Panel */}
        <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 print:grid-cols-4">
          <StatCard
            icon={<FiFileText />}
            label="Target Datasets"
            value={`${fileNames.length} CSV (${fileNames.join(", ")})`}
            colorClass="from-blue-500/10 to-indigo-500/10 border-blue-500/20 text-blue-400"
          />
          <StatCard
            icon={<FiDatabase />}
            label="Total Rows Parsed"
            value={totalRows.toLocaleString()}
            colorClass="from-purple-500/10 to-pink-500/10 border-purple-500/20 text-purple-400"
          />
          <StatCard
            icon={<FiGrid />}
            label="Data Columns"
            value={totalCols}
            colorClass="from-emerald-500/10 to-teal-500/10 border-emerald-500/20 text-emerald-400"
          />
          <StatCard
            icon={<FiAlertTriangle />}
            label="Outlier Anomalies"
            value={totalAnomalies}
            colorClass={totalAnomalies > 0 
              ? "from-amber-500/10 to-orange-500/10 border-amber-500/20 text-amber-505 text-amber-500" 
              : "from-slate-500/10 to-slate-500/10 border-slate-700/30 text-slate-500"
            }
          />
        </section>

        {/* Executive Summary & Recommendations row */}
        <section className="grid grid-cols-1 lg:grid-cols-12 gap-8 print:grid-cols-1">
          {/* Executive Narrative */}
          <div className="backdrop-blur-md bg-slate-900/40 border border-slate-800/80 rounded-3xl p-6 lg:col-span-8 shadow-2xl relative overflow-hidden bg-gradient-to-tr from-slate-900/60 to-slate-950/20">
            <div className="absolute top-0 right-0 bg-blue-500/10 rounded-bl-3xl px-4 py-1.5 border-l border-b border-blue-500/15 text-xs text-blue-450 font-medium tracking-wide">
              AI Generated Overview
            </div>
            <h2 className="text-lg font-black text-white mb-4 tracking-tight flex items-center gap-2">
              <FiCheckCircle className="text-blue-500" /> Executive summary
            </h2>
            <div className="text-slate-300 font-medium">
              <SimpleMarkdown text={narrative.executive_summary} />
            </div>
          </div>

          {/* Recommendations Panel */}
          <div className="backdrop-blur-md bg-slate-900/40 border border-slate-800/80 rounded-3xl p-6 lg:col-span-4 shadow-2xl bg-gradient-to-bl from-slate-900/60 to-slate-950/20">
            <h2 className="text-lg font-black text-white mb-4 tracking-tight flex items-center gap-2">
              <FiTrendingUp className="text-emerald-500" /> Strategic Action Items
            </h2>
            
            <div className="space-y-4">
              {narrative.recommendations?.map((rec, i) => (
                <div key={i} className="flex gap-3 items-start bg-slate-950/50 p-4 border border-slate-800/50 rounded-2xl shadow-inner">
                  <div className="bg-emerald-500/10 text-emerald-450 border border-emerald-500/20 rounded-lg text-xs font-bold h-6 w-6 flex items-center justify-center flex-shrink-0 mt-0.5">
                    {i + 1}
                  </div>
                  <p className="text-xs text-slate-350 leading-relaxed font-semibold">{rec}</p>
                </div>
              ))}
              {(!narrative.recommendations || narrative.recommendations.length === 0) && (
                <p className="text-xs text-slate-500 italic">No recommendations produced.</p>
              )}
            </div>
          </div>
        </section>

        {/* Charts & Visualizations Section */}
        {charts.length > 0 && (
          <section className="space-y-5">
            <h2 className="text-lg font-black text-white hover:text-blue-400 transition-colors tracking-tight flex items-center gap-2">
              <FiGrid className="text-purple-500" /> Core Visual Portfolio
            </h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 print:grid-cols-2">
              {charts.map((c, i) => (
                <div key={i} className="backdrop-blur-md bg-slate-900/30 border border-slate-800/80 rounded-2xl p-5 hover:border-slate-700/50 shadow-xl transition-all overflow-hidden relative">
                  <div className="absolute top-4 right-4 bg-slate-950 text-slate-400 text-2xs px-2 py-0.5 rounded border border-slate-800 uppercase font-bold tracking-wider">
                    {c.chart_type}
                  </div>
                  <p className="text-sm font-extrabold text-slate-205 mb-4 text-slate-200">{c.title}</p>
                  
                  {/* We inject customized config inside Recharts to style nicely in dark theme */}
                  <div className="rounded-xl overflow-hidden bg-slate-950/80 border border-slate-900">
                    <ChartCard chart={c} compact />
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Key Findings List Section */}
        {narrative.key_findings && narrative.key_findings.length > 0 && (
          <section className="backdrop-blur-md bg-slate-900/40 border border-slate-800/80 rounded-3xl p-6 shadow-2xl">
            <h2 className="text-lg font-black text-white mb-4 tracking-tight flex items-center gap-2">
              <FiFileText className="text-indigo-500" /> Statistical Key Findings
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {narrative.key_findings.map((finding, i) => (
                <div key={i} className="bg-slate-950/40 p-4 border border-slate-900 rounded-2xl flex items-start gap-3 flex-wrap sm:flex-nowrap">
                  <span className="h-5 w-5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 text-xs font-black flex items-center justify-center flex-shrink-0 mt-0.5">
                    ✓
                  </span>
                  <p className="text-xs leading-relaxed text-slate-300 font-semibold">
                    {finding.split(/(\*\*[^*]+\*\*)/g).map((part, pidx) => {
                      if (part.startsWith("**") && part.endsWith("**")) {
                        return <strong key={pidx} className="text-white font-bold">{part.slice(2, -2)}</strong>;
                      }
                      return part;
                    })}
                  </p>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Anomalies Details Section */}
        {anomalies.length > 0 && (
          <section className="backdrop-blur-md bg-slate-900/30 border border-slate-800/80 rounded-3xl p-6 shadow-xl">
            <button
              onClick={() => setShowAnomalies(!showAnomalies)}
              className="w-full flex items-center justify-between text-left text-white focus:outline-none"
            >
              <h2 className="text-lg font-black tracking-tight flex items-center gap-2">
                <FiAlertTriangle className="text-amber-500" /> Outliers & Anomalies Review
                <span className="bg-amber-500/20 text-amber-450 border border-amber-500/30 text-xs px-2.5 py-0.5 rounded-full font-bold ml-2">
                  {anomalies.length} Flagged
                </span>
              </h2>
              <div className="text-xl text-slate-400 hover:text-white transition-colors">
                {showAnomalies ? <FiChevronUp /> : <FiChevronDown />}
              </div>
            </button>
            
            {showAnomalies && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">
                {anomalies.map((a, i) => (
                  <div key={i} className="bg-slate-950/60 border border-slate-900 rounded-2xl p-4 flex gap-3.5 items-start">
                    <div className="p-2 bg-amber-500/10 rounded-xl text-amber-500 border border-amber-500/10 mt-0.5 flex-shrink-0">
                      <FiAlertTriangle />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h4 className="text-xs font-bold text-white">{a.anomaly_type}</h4>
                        <span className={`text-4xs px-2 py-0.5 rounded uppercase font-black tracking-wider border ${
                          a.severity === "High" ? "bg-red-500/15 border-red-500/30 text-red-400" :
                          a.severity === "Medium" ? "bg-orange-500/15 border-orange-500/30 text-orange-400" :
                          "bg-amber-500/15 border-amber-500/30 text-amber-400"
                        }`}>
                          {a.severity}
                        </span>
                      </div>
                      <p className="text-xs text-slate-400 mt-1.5 leading-relaxed font-semibold">{a.description}</p>
                      <div className="text-4xs text-slate-500 mt-2 uppercase font-extrabold tracking-wider">
                        Column: {a.column}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}
      </main>

      {/* Styled inline custom print stylesheet */}
      <style>{`
        @media print {
          body, html {
            background: white !important;
            color: #111827 !important;
          }
          .fixed {
            position: relative !important;
            inset: auto !important;
            height: auto !important;
            background: white !important;
          }
          main {
            max-width: 100% !important;
            padding: 0 !important;
            color: #111827 !important;
          }
          .backdrop-blur-md, .bg-slate-900\\/40, .bg-slate-900\\/30, .bg-slate-950\\/40, .bg-slate-950\\/60 {
            background-color: #f8fafc !important;
            border-color: #e2e8f0 !important;
            box-shadow: none !important;
            color: #111827 !important;
          }
          h1, h2, h3, h4, p, strong, span, li {
            color: #111827 !important;
          }
          .text-white, .text-slate-100, .text-slate-200, .text-slate-350, .text-slate-300, .text-slate-400 {
            color: #1f2937 !important;
          }
          svg, canvas, select {
            color: #111827 !important;
            stroke: #cbd5e1 !important;
          }
        }
      `}</style>
    </div>
  );
}
