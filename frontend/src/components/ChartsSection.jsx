import { useEffect, useState } from "react";
import { getCharts } from "../services/api";
import ChartCard from "./ChartCard";

export default function ChartsSection({ refreshKey, selectedDataset }) {
  const [charts, setCharts] = useState([]);

  useEffect(() => {
    if (refreshKey === 0 || !selectedDataset) return;
    getCharts(selectedDataset)
      .then((res) => setCharts(res.data))
      .catch(() => {});
  }, [refreshKey, selectedDataset]);

  if (!charts.length) return null;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-8">
      <h2 className="text-base font-semibold text-gray-800 mb-5">Charts</h2>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {charts.map((chart, i) => (
          <div key={i} className="bg-slate-50 rounded-xl p-4 border border-slate-100">
            <p className="text-sm font-semibold text-gray-700 mb-4">{chart.title}</p>
            <ChartCard chart={chart} />
          </div>
        ))}
      </div>
    </div>
  );
}
