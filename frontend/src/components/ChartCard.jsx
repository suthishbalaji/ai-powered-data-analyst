import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from "recharts";

const COLORS = ["#2563EB", "#7C3AED", "#059669", "#D97706", "#DC2626", "#0891B2", "#BE185D", "#65A30D"];

const fmt = (v) => (typeof v === "number" ? v.toLocaleString(undefined, { maximumFractionDigits: 1 }) : v);

export default function ChartCard({ chart, compact = false }) {
  if (!chart || !chart.data?.length) return null;

  const height = compact ? 220 : 300;

  const renderChart = () => {
    switch (chart.chart_type) {
      case "bar":
        return (
          <BarChart data={chart.data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis dataKey="name" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} tickFormatter={fmt} />
            <Tooltip formatter={fmt} />
            <Bar dataKey="value" fill="#2563EB" radius={[4, 4, 0, 0]}>
              {chart.data.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
            </Bar>
          </BarChart>
        );

      case "line":
        return (
          <LineChart data={chart.data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis dataKey="name" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} tickFormatter={fmt} />
            <Tooltip formatter={fmt} />
            <Line type="monotone" dataKey="value" stroke="#2563EB" strokeWidth={2} dot={{ r: 3 }} />
          </LineChart>
        );

      case "pie":
        return (
          <PieChart>
            <Pie data={chart.data} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={compact ? 80 : 110} label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`} labelLine={false}>
              {chart.data.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
            </Pie>
            <Tooltip formatter={fmt} />
            <Legend />
          </PieChart>
        );

      case "scatter":
        return (
          <ScatterChart>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis dataKey="x" name={chart.x_axis} tick={{ fontSize: 11 }} tickFormatter={fmt} />
            <YAxis dataKey="y" name={chart.y_axis} tick={{ fontSize: 11 }} tickFormatter={fmt} />
            <Tooltip cursor={{ strokeDasharray: "3 3" }} formatter={fmt} />
            <Scatter data={chart.data} fill="#2563EB" />
          </ScatterChart>
        );

      default:
        return null;
    }
  };

  return (
    <div className={compact ? "" : "bg-white rounded-xl shadow-sm border border-slate-100 p-6"}>
      {!compact && <p className="text-sm font-semibold text-gray-800 mb-4">{chart.title}</p>}
      {compact && chart.title && <p className="text-xs font-medium text-gray-500 mb-2">{chart.title}</p>}
      <ResponsiveContainer width="100%" height={height}>
        {renderChart()}
      </ResponsiveContainer>
    </div>
  );
}
