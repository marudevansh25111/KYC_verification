import { useState, useRef } from "react";
import { verifyDocument } from "../api.js";
import ResultsDashboard from "./ResultsDashboard.jsx";

export default function UploadPanel() {
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const inputRef = useRef(null);

  function selectFile(f) {
    if (!f) return;
    setFile(f);
    setPreviewUrl(URL.createObjectURL(f));
    setResult(null);
    setError(null);
  }

  function handleDrop(e) {
    e.preventDefault();
    setDragging(false);
    selectFile(e.dataTransfer.files?.[0]);
  }

  async function handleVerify() {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const data = await verifyDocument(file);
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <div className="card">
        <div
          className={`dropzone ${dragging ? "dragging" : ""}`}
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
        >
          {previewUrl ? (
            <img src={previewUrl} alt="preview" className="preview-thumb" />
          ) : (
            <div className="icon">📄</div>
          )}
          <p>
            {file ? file.name : "Drag & drop an ID document image here, or click to browse"}
          </p>
          <input
            ref={inputRef}
            type="file"
            accept="image/jpeg,image/png"
            style={{ display: "none" }}
            onChange={(e) => selectFile(e.target.files?.[0])}
          />
        </div>

        <div style={{ marginTop: 16, display: "flex", gap: 12, alignItems: "center" }}>
          <button className="btn btn-primary" disabled={!file || loading} onClick={handleVerify}>
            {loading && <span className="spinner" />}
            {loading ? "Verifying..." : "Verify Document"}
          </button>
          {file && !loading && (
            <button
              className="btn btn-secondary"
              onClick={() => {
                setFile(null);
                setPreviewUrl(null);
                setResult(null);
                setError(null);
              }}
            >
              Clear
            </button>
          )}
        </div>

        {error && <div className="error-banner">{error}</div>}
      </div>

      {result && <ResultsDashboard result={result} />}
    </>
  );
}
