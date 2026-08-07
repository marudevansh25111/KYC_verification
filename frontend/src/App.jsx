import { useState } from "react";
import UploadPanel from "./components/UploadPanel.jsx";
import ReviewQueue from "./components/ReviewQueue.jsx";

export default function App() {
  const [tab, setTab] = useState("verify");

  return (
    <div className="app-shell">
      <div className="app-header">
        <div>
          <h1>Verifio</h1>
          <div className="subtitle">Automated KYC document verification — synthetic data only</div>
        </div>
      </div>

      <div className="tabs">
        <button className={`tab-button ${tab === "verify" ? "active" : ""}`} onClick={() => setTab("verify")}>
          Verify Document
        </button>
        <button className={`tab-button ${tab === "review" ? "active" : ""}`} onClick={() => setTab("review")}>
          Review Queue
        </button>
      </div>

      {tab === "verify" ? <UploadPanel /> : <ReviewQueue />}
    </div>
  );
}
