import axios from "axios";

const api = axios.create({ baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000" });

export const uploadFiles = (files) => {
  const form = new FormData();
  files.forEach((f) => form.append("files", f));
  return api.post("/upload", form);
};

export const getSummary = (filename) => api.get("/summary", { params: filename ? { filename } : {} });
export const getInsights = (filename) => api.get("/insights", { params: filename ? { filename } : {} });
export const getAnomalies = (filename) => api.get("/anomalies", { params: filename ? { filename } : {} });
export const getCharts = (filename) => api.get("/charts", { params: filename ? { filename } : {} });

export const askQuestion = (query, chatHistory, filename) =>
  api.post("/ask", { query, chat_history: chatHistory, filename: filename || null });

export const clearSession = () => api.post("/clear");
export const deleteFile = (filename) => api.delete(`/files/${encodeURIComponent(filename)}`);

export const getColumns = (filename) =>
  api.get("/columns", { params: filename ? { filename } : {} });

export const buildChart = (payload) => api.post("/build-chart", payload);

export const getDashboardData = (filename) =>
  api.get("/dashboard-data", { params: filename ? { filename } : {} });
