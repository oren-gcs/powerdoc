import { useEffect, useState } from "react";
import { ConnectAPI } from "../api";

export default function Connectors() {
  const [rows, setRows] = useState<any[]>([]);
  const [msg, setMsg] = useState("");
  const load = () => ConnectAPI.list().then(setRows);
  useEffect(() => {
    load();
  }, []);
  return (
    <>
      <div className="eyebrow">Context sources</div>
      <h1 className="mark" style={{ fontSize: 32 }}>
        Connectors
      </h1>
      <p className="muted">Google Drive, Microsoft 365, and the local database feed RAG used by the form chatbot.</p>
      <div className="row-actions" style={{ marginBottom: 16 }}>
        {["google_drive", "microsoft", "local_db"].map((k) => (
          <button key={k} className="btn" onClick={() => ConnectAPI.add({ kind: k, name: k }).then(load)}>
            Connect {k}
          </button>
        ))}
      </div>
      {msg && <p className="pill ok">{msg}</p>}
      <div className="card">
        {rows.map((c) => (
          <div key={c.id} style={{ display: "flex", justifyContent: "space-between", padding: "10px 0", borderBottom: "1px solid var(--line)" }}>
            <div>
              <strong>{c.name}</strong>
              <div className="mono dim">
                {c.kind} · {c.status} · {c.file_count} files
              </div>
            </div>
            <button
              className="btn"
              onClick={async () => {
                const r = await ConnectAPI.sync(c.id);
                setMsg(`Synced ${r.synced} into unified context`);
                load();
              }}
            >
              Sync into RAG
            </button>
          </div>
        ))}
      </div>
    </>
  );
}
