import { useState, useEffect } from "react";
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer
} from "recharts";
import { getColumns, buildChart } from "../services/api";

const CHART_TYPES = [
  { id: "bar",     label: "Bar",     icon: "▊" },
  { id: "line",    label: "Line",    icon: "📈" },
  { id: "pie",     label: "Pie",     icon: "🥧" },
  { id: "scatter", label: "Scatter", icon: "⋅" },
];

const AGGREGATIONS = [
  { id: "sum",   label: "Sum" },
  { id: "mean",  label: "Mean / Avg" },
  { id: "count", label: "Count" },
];

const COLORS = [
  "#6366f1", "#22d3ee", "#f59e0b", "#10b981",
  "#f43f5e", "#8b5cf6", "#3b82f6", "#ec4899",
  "#14b8a6", "#f97316"
];

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-slate-200 rounded-lg shadow-lg px-3 py-2 text-xs">
      <p className="font-semibold text-gray-700 mb-1">{label}</p>
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.color }}>
          {p.name}: <strong>{typeof p.value === "number" ? p.value.toLocaleString() : p.value}</strong>
        </p>
      ))}
    </div>
  );
};

export default function ChartBuilder({ hasData, uploadedFile, selectedDataset }) {
  const [columns, setColumns] = useState({ all_columns: [], numeric_columns: [], categorical_columns: [] });
  const [xCol, setXCol] = useState("");
  const [yCol, setYCol] = useState("");
  const [chartType, setChartType] = useState("bar");
  const [aggregation, setAggregation] = useState("sum");
  const [chartData, setChartData] = useState(null);
  const [chartMeta, setChartMeta] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Load columns whenever data changes
  useEffect(() => {
    if (!hasData || !selectedDataset) return;
    setChartData(null);
    setChartMeta(null);
    getColumns(selectedDataset).then((res) => {
      const data = res.data;
      setColumns(data);
      // Smart defaults: x = first categorical, y = first numeric
      if (data.categorical_columns?.length) setXCol(data.categorical_columns[0]);
      else if (data.all_columns?.length) setXCol(data.all_columns[0]);
      if (data.numeric_columns?.length) setYCol(data.numeric_columns[0]);
    }).catch(() => {});
  }, [hasData, uploadedFile, selectedDataset]);

  const handleGenerate = async () => {
    if (!xCol || !yCol) return;
    setLoading(true);
    setError("");
    setChartData(null);
    try {
      const res = await buildChart({
        filename: selectedDataset,
        x_col: xCol,
        y_col: yCol,
        chart_type: chartType,
        aggregation: chartType === "scatter" ? "none" : aggregation,
      });
      setChartData(res.data.data);
      setChartMeta(res.data);
    } catch (e) {
      setError(e.response?.data?.detail || "Failed to generate chart.");
    } finally {
      setLoading(false);
    }
  };

  const renderChart = () => {
    if (!chartData || chartData.length === 0) return null;

    const sharedProps = {
      data: chartData,
      margin: { top: 10, right: 20, left: 0, bottom: 40 },
    };

    if (chartType === "bar") {
      return (
        <ResponsiveContainer width="100%" height={320}>
          <BarChart {...sharedProps}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis dataKey="name" tick={{ fontSize: 11 }} angle={-35} textAnchor="end" interval={0} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="value" radius={[4, 4, 0, 0]}>
              {chartData.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      );
    }

    if (chartType === "line") {
      return (
        <ResponsiveContainer width="100%" height={320}>
          <LineChart {...sharedProps}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis dataKey="name" tick={{ fontSize: 11 }} angle={-35} textAnchor="end" interval={0} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip content={<CustomTooltip />} />
            <Line type="monotone" dataKey="value" stroke="#6366f1" strokeWidth={2.5} dot={{ r: 4, fill: "#6366f1" }} />
          </LineChart>
        </ResponsiveContainer>
      );
    }

    if (chartType === "pie") {
      return (
        <ResponsiveContainer width="100%" height={320}>
          <PieChart>
            <Pie data={chartData} dataKey="value" nameKey="name" cx="50%" cy="50%"
              outerRadius={120} label={({ name, percent }) => `${name} (${(percent * 100).toFixed(1)}%)`}
              labelLine={true}>
              {chartData.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      );
    }

    if (chartType === "scatter") {
      return (
        <ResponsiveContainer width="100%" height={320}>
          <ScatterChart margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis dataKey="x" name={xCol} tick={{ fontSize: 11 }} />
            <YAxis dataKey="y" name={yCol} tick={{ fontSize: 11 }} />
            <Tooltip cursor={{ strokeDasharray: "3 3" }} />
            <Scatter data={chartData} fill="#6366f1" />
          </ScatterChart>
        </ResponsiveContainer>
      );
    }
  };

  if (!hasData) return null;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-8 mt-6">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="w-8 h-8 bg-indigo-50 rounded-lg flex items-center justify-center">
          <span className="text-indigo-600 text-base">📊</span>
        </div>
        <div>
          <h2 className="text-base font-semibold text-gray-800">Custom Chart Builder</h2>
          <p className="text-xs text-gray-400">Select columns and chart type to visualize your data</p>
        </div>
      </div>

      {/* Controls */}
      <div className="grid grid-cols-2 gap-4 mb-4 sm:grid-cols-4">
        {/* X Axis */}
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">X Axis (Category)</label>
          <select
            value={xCol}
            onChange={(e) => setXCol(e.target.value)}
            className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent"
          >
            {columns.all_columns.map((col) => (
              <option key={col} value={col}>{col}</option>
            ))}
          </select>
        </div>

        {/* Y Axis */}
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Y Axis (Numeric)</label>
          <select
            value={yCol}
            onChange={(e) => setYCol(e.target.value)}
            className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent"
          >
            {columns.numeric_columns.map((col) => (
              <option key={col} value={col}>{col}</option>
            ))}
          </select>
        </div>

        {/* Aggregation */}
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Aggregation</label>
          <select
            value={aggregation}
            onChange={(e) => setAggregation(e.target.value)}
            disabled={chartType === "scatter"}
            className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent disabled:opacity-50"
          >
            {AGGREGATIONS.map((a) => (
              <option key={a.id} value={a.id}>{a.label}</option>
            ))}
          </select>
        </div>

        {/* Generate Button */}
        <div className="flex items-end">
          <button
            onClick={handleGenerate}
            disabled={loading || !xCol || !yCol}
            className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <span className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Generating...
              </>
            ) : (
              "Generate Chart"
            )}
          </button>
        </div>
      </div>

      {/* Chart type selector */}
      <div className="flex gap-2 mb-6">
        {CHART_TYPES.map((t) => (
          <button
            key={t.id}
            onClick={() => setChartType(t.id)}
            className={`flex items-center gap-1.5 px-4 py-1.5 rounded-full text-xs font-medium border transition-all ${
              chartType === t.id
                ? "bg-indigo-600 text-white border-indigo-600 shadow-sm"
                : "bg-white text-gray-500 border-slate-200 hover:border-indigo-300 hover:text-indigo-600"
            }`}
          >
            <span>{t.icon}</span> {t.label}
          </button>
        ))}
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-100 rounded-lg px-4 py-3 text-sm text-red-600 mb-4">
          {error}
        </div>
      )}

      {/* Chart output */}
      {chartData && chartMeta && (
        <div>
          <p className="text-sm font-semibold text-gray-700 mb-3">{chartMeta.title}</p>
          <div className="bg-slate-50 rounded-xl p-4 border border-slate-100">
            {renderChart()}
          </div>
          <p className="text-xs text-gray-400 mt-2 text-right">
            {chartData.length} data points — {xCol} vs {yCol}
          </p>
        </div>
      )}

      {/* Empty state */}
      {!chartData && !loading && (
        <div className="bg-slate-50 rounded-xl border border-slate-100 border-dashed p-10 text-center">
          <p className="text-sm text-gray-400">Select columns and click <strong>Generate Chart</strong> to visualize your data</p>
        </div>
      )}
    </div>
  );
}
