import { useState } from "react";
import { FiGrid } from "react-icons/fi";
import Navbar from "./components/Navbar";
import UploadCard from "./components/UploadCard";
import DatasetSummary from "./components/DatasetSummary";
import ChatBox from "./components/ChatBox";
import InsightCards from "./components/InsightCards";
import ChartsSection from "./components/ChartsSection";
import AnomalyCard from "./components/AnomalyCard";
import ChartBuilder from "./components/ChartBuilder";
import Footer from "./components/Footer";
import DashboardView from "./components/DashboardView";

export default function App() {
  const [refreshKey, setRefreshKey] = useState(0);
  const [showDashboard, setShowDashboard] = useState(false);
  const [selectedDataset, setSelectedDataset] = useState("");
  const [suggestedQuestions, setSuggestedQuestions] = useState([]);
  const hasData = refreshKey > 0;

  const handleUploadSuccess = () => setRefreshKey((k) => k + 1);

  // Store all summaries so we can look up questions when switching dataset
  const [allSummaries, setAllSummaries] = useState({});

  // Called when DatasetSummary fetches all summaries — extract suggested questions for active file
  const handleSummaryLoaded = (summaries) => {
    setAllSummaries(summaries);
    const active = selectedDataset || Object.keys(summaries)[0] || "";
    if (active && summaries[active]?.suggested_questions) {
      setSuggestedQuestions(summaries[active].suggested_questions);
    }
  };

  // Called when the user picks a different dataset from the dropdown
  const handleSelectDataset = (filename) => {
    setSelectedDataset(filename);
    // Update suggestions immediately from stored summaries
    if (allSummaries[filename]?.suggested_questions) {
      setSuggestedQuestions(allSummaries[filename].suggested_questions);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <Navbar />

      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-10 space-y-6">
        {/* Upload */}
        <UploadCard onUploadSuccess={handleUploadSuccess} />

        {/* Dataset Summary — appears after upload */}
        <DatasetSummary
          refreshKey={refreshKey}
          selected={selectedDataset}
          onSelect={handleSelectDataset}
          onSummaryLoaded={handleSummaryLoaded}
        />

        {/* Ask AI / Chat — dynamic questions from active dataset */}
        <ChatBox hasData={hasData} suggestedQuestions={suggestedQuestions} selectedDataset={selectedDataset} />

        {/* Auto-generated insights for active dataset */}
        <InsightCards refreshKey={refreshKey} selectedDataset={selectedDataset} />

        {/* Auto-generated charts for active dataset */}
        <ChartsSection refreshKey={refreshKey} selectedDataset={selectedDataset} />

        {/* Custom Chart Builder */}
        <ChartBuilder hasData={hasData} uploadedFile={refreshKey} selectedDataset={selectedDataset} />

        {/* Anomaly detection for active dataset */}
        <AnomalyCard refreshKey={refreshKey} selectedDataset={selectedDataset} />

        {/* Generate Dashboard Button at the final */}
        {hasData && (
          <div className="flex justify-center pt-8 pb-4">
            <button
              onClick={() => setShowDashboard(true)}
              className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white font-extrabold px-8 py-4 rounded-2xl shadow-xl shadow-blue-500/20 active:scale-95 transition-all text-base flex items-center gap-3 hover:scale-105 transform cursor-pointer"
            >
              <FiGrid className="text-xl" />
              Generate Business Dashboard
            </button>
          </div>
        )}
      </main>

      {showDashboard && (
        <DashboardView onClose={() => setShowDashboard(false)} selectedDataset={selectedDataset} />
      )}

      <Footer />
    </div>
  );
}
