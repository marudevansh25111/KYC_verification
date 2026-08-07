function ConfidenceBar({ value }) {
  const pct = Math.round((value ?? 0) * 100);
  return (
    <div className="confidence-bar-track" title={`${pct}% confidence`}>
      <div
        className={`confidence-bar-fill ${value < 0.4 ? "low" : ""}`}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

function FieldsSection({ fields }) {
  if (!fields) return null;
  return (
    <>
      <div className="section-title">Extracted Fields</div>
      <div>
        {Object.entries(fields).map(([name, data]) => (
          <div className="field-row" key={name}>
            <div className="field-name">{name.replace("_", " ")}</div>
            <div className="field-value">
              {data.text || <em style={{ color: "var(--text-muted)" }}>(empty)</em>}
              {data.raw_ocr_text && data.raw_ocr_text !== data.text && (
                <span className="raw-diff">(raw OCR: {data.raw_ocr_text})</span>
              )}
              {data.reason && (
                <div style={{ color: "var(--red)", fontSize: 12.5, marginTop: 2 }}>{data.reason}</div>
              )}
            </div>
            <ConfidenceBar value={data.confidence} />
            <span className={`pill ${data.valid ? "pill-valid" : "pill-invalid"}`}>
              {data.valid ? "valid" : "invalid"}
            </span>
          </div>
        ))}
      </div>
    </>
  );
}

function QualitySection({ quality }) {
  if (!quality) return null;
  return (
    <>
      <div className="section-title">Quality Checks</div>
      <div className="check-grid">
        {Object.entries(quality.checks).map(([name, data]) => (
          <div className="check-item" key={name}>
            <div className="check-item-header">
              <span>{name}</span>
              <span className={`dot ${data.passed ? "dot-pass" : "dot-fail"}`} />
            </div>
            <div className="check-item-detail">
              {name === "blur" && `Laplacian variance: ${data.laplacian_variance}`}
              {name === "glare" && `Bright pixels: ${(data.bright_pixel_ratio * 100).toFixed(1)}%`}
              {name === "resolution" && `${data.width}x${data.height}px`}
              {name === "completeness" &&
                (data.missing_edges.length
                  ? `Missing edges: ${data.missing_edges.join(", ")}`
                  : "All edges present")}
            </div>
          </div>
        ))}
      </div>
    </>
  );
}

function TamperingSection({ tampering }) {
  if (!tampering) return null;
  return (
    <>
      <div className="section-title">Tampering Check (Error Level Analysis)</div>
      {tampering.tampering_detected ? (
        <p style={{ color: "var(--red)", fontSize: 14, margin: "0 0 12px" }}>
          Suspicious field(s): {tampering.suspicious_fields.join(", ")}
        </p>
      ) : (
        <p style={{ color: "var(--green)", fontSize: 14, margin: "0 0 12px" }}>
          No tampering signal detected
        </p>
      )}
      <div className="check-grid">
        {Object.entries(tampering.field_z_scores).map(([name, z]) => (
          <div className="check-item" key={name}>
            <div className="check-item-header">
              <span>{name.replace("_", " ")}</span>
              <span className={`dot ${z > 1.8 ? "dot-fail" : "dot-pass"}`} />
            </div>
            <div className="check-item-detail">z-score vs. baseline: {z}</div>
          </div>
        ))}
      </div>
    </>
  );
}

export default function ResultsDashboard({ result }) {
  const { decision, doc_type, quality, fields, tampering } = result;

  return (
    <div className="card">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <span className={`verdict-badge verdict-${decision.verdict}`}>{decision.verdict}</span>
          {doc_type?.doc_type && (
            <span style={{ marginLeft: 12, color: "var(--text-muted)", fontSize: 13 }}>
              Detected: {doc_type.doc_type}
              {doc_type.confidence != null && ` (${Math.round(doc_type.confidence * 100)}% confidence)`}
            </span>
          )}
        </div>
      </div>

      <ul className="reasons-list">
        {decision.reasons.map((r, i) => (
          <li key={i}>{r}</li>
        ))}
      </ul>

      <QualitySection quality={quality} />
      <FieldsSection fields={fields} />
      <TamperingSection tampering={tampering} />
    </div>
  );
}
