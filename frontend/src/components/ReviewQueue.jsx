import { useEffect, useState } from "react";
import { listVerifications, getVerification, reviewVerification } from "../api.js";
import ResultsDashboard from "./ResultsDashboard.jsx";

export default function ReviewQueue() {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selected, setSelected] = useState(null);
  const [selectedDetail, setSelectedDetail] = useState(null);

  async function refresh() {
    setLoading(true);
    try {
      const data = await listVerifications("REVIEW");
      setRecords(data.filter((r) => !r.reviewed));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function openRecord(id) {
    setSelected(id);
    const detail = await getVerification(id);
    setSelectedDetail(detail);
  }

  async function handleDecision(verdict) {
    await reviewVerification(selected, verdict);
    setSelected(null);
    setSelectedDetail(null);
    refresh();
  }

  return (
    <div className="card">
      <div className="section-title" style={{ marginTop: 0 }}>
        Documents flagged for review
      </div>

      {loading && <div className="empty-state">Loading…</div>}
      {error && <div className="error-banner">{error}</div>}

      {!loading && records.length === 0 && (
        <div className="empty-state">Nothing waiting on review right now.</div>
      )}

      {!loading && records.length > 0 && (
        <table className="queue-table">
          <thead>
            <tr>
              <th>Filename</th>
              <th>Doc Type</th>
              <th>Submitted</th>
              <th>Verdict</th>
            </tr>
          </thead>
          <tbody>
            {records.map((r) => (
              <tr key={r.id} onClick={() => openRecord(r.id)}>
                <td>{r.original_filename || "—"}</td>
                <td>{r.doc_type || "—"}</td>
                <td>{new Date(r.created_at).toLocaleString()}</td>
                <td>
                  <span className={`verdict-badge verdict-${r.verdict}`}>{r.verdict}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {selectedDetail && (
        <div className="modal-overlay" onClick={() => setSelected(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setSelected(null)}>
              ×
            </button>
            <ResultsDashboard result={selectedDetail} />
            <div style={{ display: "flex", gap: 10, marginTop: 20 }}>
              <button className="btn btn-accept" onClick={() => handleDecision("ACCEPT")}>
                Approve
              </button>
              <button className="btn btn-reject" onClick={() => handleDecision("REJECT")}>
                Reject
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
