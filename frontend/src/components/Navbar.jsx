import { FiBarChart2 } from "react-icons/fi";

export default function Navbar() {
  return (
    <nav className="bg-white border-b border-slate-100 sticky top-0 z-50 shadow-sm">
      <div className="max-w-6xl mx-auto px-6 py-4 flex items-center gap-3">
        <div className="bg-primary p-2 rounded-xl">
          <FiBarChart2 className="text-white text-xl" />
        </div>
        <div>
          <h1 className="text-lg font-bold text-gray-900 leading-tight">AI Data Analyst</h1>
          <p className="text-xs text-gray-500">Analyze your CSV files using Natural Language</p>
        </div>
      </div>
    </nav>
  );
}
