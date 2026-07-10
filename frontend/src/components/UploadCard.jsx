import { useRef, useState } from "react";
import { FiUploadCloud, FiFile, FiCheckCircle, FiX } from "react-icons/fi";
import { deleteFile, uploadFiles } from "../services/api";

export default function UploadCard({ onUploadSuccess }) {
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [error, setError] = useState("");
  const inputRef = useRef();

  const handleFiles = async (files) => {
    const csvFiles = Array.from(files).filter((f) => f.name.toLowerCase().endsWith(".csv"));
    if (!csvFiles.length) {
      setError("Only CSV files are supported. Please upload a .csv file.");
      return;
    }
    setError("");
    setUploading(true);
    try {
      const res = await uploadFiles(csvFiles);
      const uploaded = res.data.uploaded_files;
      setUploadedFiles((prev) => {
        const names = new Set(prev.map((f) => f.filename));
        const newFiles = uploaded.filter((f) => !names.has(f.filename));
        return [...prev, ...newFiles];
      });
      onUploadSuccess();
    } catch (e) {
      setError(e.response?.data?.detail || "Upload failed. Please try again.");
    } finally {
      setUploading(false);
    }
  };

  const removeFile = async (filename) => {
    try {
      await deleteFile(filename);
      setUploadedFiles((prev) => prev.filter((f) => f.filename !== filename));
      onUploadSuccess();
    } catch (e) {
      setError(e.response?.data?.detail || "Could not remove the file.");
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-8">
      <h2 className="text-base font-semibold text-gray-800 mb-5">Upload CSV Files</h2>

      {/* Drop Zone */}
      <div
        onClick={() => inputRef.current.click()}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => { e.preventDefault(); setDragging(false); handleFiles(e.dataTransfer.files); }}
        className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors
          ${dragging ? "border-primary bg-blue-50" : "border-slate-200 hover:border-primary hover:bg-slate-50"}`}
      >
        <FiUploadCloud className="mx-auto text-4xl text-primary mb-3" />
        <p className="font-medium text-gray-700">Drag & drop CSV files here</p>
        <p className="text-sm text-gray-400 mt-1">or click to browse — supports single & multiple files</p>
        <input
          ref={inputRef}
          type="file"
          accept=".csv"
          multiple
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>

      {error && (
        <p className="mt-3 text-sm text-red-500 bg-red-50 rounded-lg px-4 py-2">{error}</p>
      )}

      {uploading && (
        <p className="mt-3 text-sm text-primary animate-pulse">Uploading files...</p>
      )}

      {/* Uploaded File List */}
      {uploadedFiles.length > 0 && (
        <div className="mt-5 space-y-3">
          <p className="text-sm font-medium text-gray-600">Uploaded Files</p>
          {uploadedFiles.map((f) => (
            <div key={f.filename} className="flex items-center justify-between bg-slate-50 rounded-xl px-4 py-3">
              <div className="flex items-center gap-3">
                <FiFile className="text-primary text-lg" />
                <div>
                  <p className="text-sm font-medium text-gray-800">{f.filename}</p>
                  <p className="text-xs text-gray-400">{f.rows?.toLocaleString()} rows · {f.columns} columns</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-green-600 bg-green-50 px-2 py-1 rounded-full flex items-center gap-1">
                  <FiCheckCircle /> Uploaded
                </span>
                <button aria-label={`Remove ${f.filename}`} onClick={() => removeFile(f.filename)} className="text-gray-400 hover:text-red-400 transition-colors">
                  <FiX />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
