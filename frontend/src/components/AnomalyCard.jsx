import { useEffect, useState } from "react";
import { FiAlertTriangle, FiAlertCircle, FiInfo } from "react-icons/fi";
import { getAnomalies } from "../services/api";

const SEVERITY = {
  High:    { cls: "bg-red-50 border-red-100 text-red-700",    icon: <FiAlertTriangle className="text-red-500" /> },
  Warning: { cls: "bg-amber-50 border-amber-100 text-amber-700", icon: <FiAlertCircle className="text-amber-500" /> },
  Medium:  { cls: "bg-orange-50 border-orange-100 text-orange-700", icon: <FiAlertCircle className="text-orange-500" /> },
  Info:    { cls: "bg-blue-50 border-blue-100 text-blue-700",  icon: <FiInfo className="text-blue-500" /> },
};

export default function AnomalyCard({ refreshKey, selectedDataset }) {
  const [anomalies, setAnomalies] = useState([]);

  useEffect(() => {
    if (refreshKey === 0 || !selectedDataset) return;
    getAnomalies(selectedDataset)
      .then((res) => setAnomalies(res.data))
      .catch(() => {});
  }, [refreshKey, selectedDataset]);

  if (!anomalies.length) return null;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-8">
      <div className="flex items-center gap-2 mb-5">
        <h2 className="text-base font-semibold text-gray-800">Detected Anomalies</h2>
        <span className="bg-red-100 text-red-600 text-xs font-semibold px-2 py-0.5 rounded-full">
          {anomalies.length}
        </span>
      </div>
      <div className="space-y-3">
        {anomalies.map((a, i) => {
          const s = SEVERITY[a.severity] || SEVERITY.Info;
          return (
            <div key={i} className={`flex gap-3 items-start rounded-xl border px-4 py-3 ${s.cls}`}>
              <div className="mt-0.5 flex-shrink-0">{s.icon}</div>
              <div>
                <p className="text-sm font-semibold">{a.anomaly_type}</p>
                <p className="text-xs mt-0.5 opacity-80">{a.description}</p>
                <span className="text-xs opacity-60">Column: {a.column}</span>
              </div>
              <span className="ml-auto text-xs font-medium opacity-70 flex-shrink-0">{a.severity}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
