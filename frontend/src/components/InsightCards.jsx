import { useEffect, useState } from "react";
import { FiTrendingUp, FiMapPin, FiPackage, FiTag, FiPercent, FiCalendar, FiList, FiBarChart2, FiUsers } from "react-icons/fi";
import { getInsights } from "../services/api";

const ICONS = {
  sales: <FiTrendingUp />,
  region: <FiMapPin />,
  product: <FiPackage />,
  category: <FiTag />,
  margin: <FiPercent />,
  trend: <FiCalendar />,
  rows: <FiList />,
  columns: <FiBarChart2 />,
};

const COLORS = [
  "bg-blue-50 text-blue-600",
  "bg-purple-50 text-purple-600",
  "bg-green-50 text-green-600",
  "bg-amber-50 text-amber-600",
  "bg-rose-50 text-rose-600",
  "bg-cyan-50 text-cyan-600",
];

export default function InsightCards({ refreshKey, selectedDataset }) {
  const [insights, setInsights] = useState([]);

  useEffect(() => {
    if (refreshKey === 0 || !selectedDataset) return;
    getInsights(selectedDataset)
      .then((res) => setInsights(res.data))
      .catch(() => {});
  }, [refreshKey, selectedDataset]);

  if (!insights.length) return null;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-8">
      <h2 className="text-base font-semibold text-gray-800 mb-5">Business Insights</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {insights.map((ins, i) => (
          <div key={i} className="bg-slate-50 rounded-xl p-4 border border-slate-100">
            <div className={`inline-flex p-2 rounded-lg mb-3 text-lg ${COLORS[i % COLORS.length]}`}>
              {ICONS[ins.icon] || <FiTrendingUp />}
            </div>
            <p className="text-xs font-medium text-gray-500 mb-1">{ins.title}</p>
            <p className="text-xl font-bold text-gray-900 mb-1 truncate">{ins.value}</p>
            <p className="text-xs text-gray-400 leading-relaxed">{ins.description}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
