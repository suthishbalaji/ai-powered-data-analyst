import { useEffect, useState } from "react";
import { FiGrid, FiAlertCircle, FiCopy, FiDatabase } from "react-icons/fi";
import { getSummary } from "../services/api";

const StatCard = ({ icon, label, value, color = "text-primary" }) => (
  <div className="bg-slate-50 rounded-xl p-4 flex items-center gap-3">
    <div className={`text-xl ${color}`}>{icon}</div>
    <div>
      <p className="text-xs text-gray-500">{label}</p>
      <p className="text-lg font-bold text-gray-800">{value}</p>
    </div>
  </div>
);

export default function DatasetSummary({ refreshKey, selected, onSelect, onSummaryLoaded }) {
  const [summaries, setSummaries] = useState({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (refreshKey === 0) return;
    setLoading(true);
    getSummary()
      .then((res) => {
        const data = res.data;
        let sums = {};
        let active = "";
        if (data.filename) {
          sums = { [data.filename]: data };
          active = data.filename;
        } else {
          sums = data;
          active = Object.keys(data)[0] || "";
        }
        setSummaries(sums);
        if (!selected || !sums[selected]) {
          onSelect(active);
        }
        if (onSummaryLoaded) {
          onSummaryLoaded(sums);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [refreshKey]);

  if (!Object.keys(summaries).length) return null;

  const s = summaries[selected];
  if (!s) return null;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-8">
      <div className="flex items-center justify-between mb-5">
        <h2 className="text-base font-semibold text-gray-800">Dataset Summary</h2>
        {Object.keys(summaries).length > 1 && (
          <select
            value={selected}
            onChange={(e) => onSelect(e.target.value)}
            className="text-sm border border-slate-200 rounded-lg px-3 py-1.5 text-gray-700 focus:outline-none focus:ring-2 focus:ring-primary"
          >
            {Object.keys(summaries).map((fn) => (
              <option key={fn} value={fn}>{fn}</option>
            ))}
          </select>
        )}
      </div>

      {loading ? (
        <p className="text-sm text-gray-400 animate-pulse">Loading summary...</p>
      ) : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <StatCard icon={<FiDatabase />} label="Total Rows" value={s.rows?.toLocaleString()} />
            <StatCard icon={<FiGrid />} label="Columns" value={s.columns} />
            <StatCard icon={<FiAlertCircle />} label="Missing Values" value={s.missing_values} color="text-amber-500" />
            <StatCard icon={<FiCopy />} label="Duplicate Rows" value={s.duplicate_rows} color="text-red-400" />
          </div>

          <div>
            <p className="text-sm font-medium text-gray-600 mb-3">Column Details</p>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-gray-400 border-b border-slate-100">
                    <th className="pb-2 font-medium">Column</th>
                    <th className="pb-2 font-medium">Type</th>
                    <th className="pb-2 font-medium">Missing</th>
                    <th className="pb-2 font-medium">Sample Values</th>
                  </tr>
                </thead>
                <tbody>
                  {s.columns_info?.map((col) => (
                    <tr key={col.name} className="border-b border-slate-50 hover:bg-slate-50 transition-colors">
                      <td className="py-2.5 font-medium text-gray-800">{col.name}</td>
                      <td className="py-2.5">
                        <span className="bg-blue-50 text-primary text-xs px-2 py-0.5 rounded-full">{col.type}</span>
                      </td>
                      <td className="py-2.5 text-gray-500">{col.missing}</td>
                      <td className="py-2.5 text-gray-400 text-xs">{col.samples?.join(", ")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
