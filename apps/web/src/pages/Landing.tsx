import { Link } from "react-router-dom";

export default function Landing() {
  return (
    <div className="hero">
      <div className="hero-copy">
        <div className="eyebrow">Doc-Power lineage · DocFlow 2.0</div>
        <h1 className="display">Documents should move. Not pile up.</h1>
        <p className="muted" style={{ fontSize: 18, maxWidth: 560, lineHeight: 1.5 }}>
          DocFlow is the production desk for ingest, OCR, classification, executable workflows,
          agents, and automations — built to run on your laptop and on AWS or GCP.
        </p>
        <div className="row-actions" style={{ marginTop: 28 }}>
          <Link className="btn primary" to="/login">
            Open the desk
          </Link>
          <Link className="btn" to="/register">
            Create an organization
          </Link>
        </div>
        <div className="grid cards-3" style={{ marginTop: 48, maxWidth: 720 }}>
          {[
            ["Executable flows", "Steps actually run: extract, classify, condition, notify — not a queue with no consumer."],
            ["Agents & skills", "Orchestrator, OCR, review, and MCP tools wired into the same platform."],
            ["Local + cloud", "SQLite on a laptop. Postgres, object storage, and Terraform for AWS and GCP."],
          ].map(([t, d]) => (
            <div key={t} className="card">
              <div className="eyebrow">{t}</div>
              <p className="muted" style={{ margin: "8px 0 0" }}>
                {d}
              </p>
            </div>
          ))}
        </div>
      </div>
      <aside className="hero-panel">
        <div className="eyebrow">live pipeline</div>
        <h2 className="mark" style={{ fontSize: 32, margin: "8px 0 18px" }}>
          ingest → read → decide → act
        </h2>
        <div className="flow">
          {["Upload", "OCR", "Classify", "Fields", "Workflow", "Notify"].map((s, i) => (
            <div className="step-chip" key={s}>
              <small>0{i + 1}</small>
              {s}
            </div>
          ))}
        </div>
        <p className="muted" style={{ marginTop: 28 }}>
          Demo account
          <br />
          <span className="mono">oren@gcs-tech.org / DocFlow!2026</span>
        </p>
      </aside>
    </div>
  );
}
