import { useEffect, useState } from "react";
import { AgentAPI, ConnectAPI } from "../api";

const SOURCES = [
  {
    kind: "google_drive",
    title: "Google Drive",
    blurb: "Shared drives, My Drive, PDFs and Docs into unified context.",
    mark: "G",
  },
  {
    kind: "microsoft",
    title: "Microsoft 365",
    blurb: "SharePoint libraries and OneDrive files for AP and legal.",
    mark: "365",
  },
  {
    kind: "local_db",
    title: "Local database",
    blurb: "DocFlow SQLite / Postgres — OCR text and extracted fields.",
    mark: "DB",
  },
];

export default function Connectors() {
  const [rows, setRows] = useState<any[]>([]);
  const [msg, setMsg] = useState("");
  const [ollama, setOllama] = useState<any>(null);
  const [pick, setPick] = useState("");
  const load = () => {
    ConnectAPI.list().then(setRows);
    AgentAPI.ollama().then((o) => {
      setOllama(o);
      setPick(o.default || o.models?.[0] || "");
    });
  };
  useEffect(() => {
    load();
  }, []);

  const rowFor = (kind: string) => rows.find((r) => r.kind === kind);

  const connect = async (kind: string, title: string) => {
    await ConnectAPI.add({ kind, name: title });
    await load();
  };

  const sync = async (id: number) => {
    const r = await ConnectAPI.sync(id);
    setMsg(`Synced ${r.synced} files into RAG`);
    load();
  };

  return (
    <>
      <div className="eyebrow">Cloud + local context</div>
      <h1 className="mark" style={{ fontSize: 32 }}>
        Connectors
      </h1>
      <p className="muted">Google Drive, Microsoft 365, the desk database, and local Ollama models feed the form chatbot and n8n flows.</p>
      {msg && <p className="pill ok">{msg}</p>}
      <div className="grid cards-3" style={{ marginTop: 16 }}>
        {SOURCES.map((src) => {
          const row = rowFor(src.kind);
          return (
            <div className="card connector-card" key={src.kind} data-demo={`connector-${src.kind}`}>
              <div className="brand" style={{ padding: 0, marginBottom: 10 }}>
                <div className={`sigil src-${src.kind}`}>{src.mark}</div>
                <div>
                  <div className="mark">{src.title}</div>
                  <div className="eyebrow">{row?.status || "not connected"}</div>
                </div>
              </div>
              <p className="muted" style={{ minHeight: 48 }}>
                {src.blurb}
              </p>
              <ul className="file-list">
                {(row?.files || []).slice(0, 4).map((f: string) => (
                  <li key={f} className="mono">
                    {f}
                  </li>
                ))}
              </ul>
              <div className="row-actions">
                {!row && (
                  <button className="btn primary" data-demo={`connect-${src.kind}`} onClick={() => connect(src.kind, src.title)}>
                    Connect
                  </button>
                )}
                {row && (
                  <button className="btn primary" data-demo={`sync-${src.kind}`} onClick={() => sync(row.id)}>
                    Sync into RAG
                  </button>
                )}
              </div>
            </div>
          );
        })}
        <div className="card connector-card" data-demo="connector-ollama">
          <div className="brand" style={{ padding: 0, marginBottom: 10 }}>
            <div className="sigil src-ollama">Ol</div>
            <div>
              <div className="mark">Ollama (local models)</div>
              <div className="eyebrow">{ollama?.up ? "connected" : "offline"}</div>
            </div>
          </div>
          <p className="muted" style={{ minHeight: 48 }}>
            {ollama?.up
              ? `Talking to ${ollama.url}. ${ollama.models?.length ? "Pulled: " + ollama.models.join(", ") : "No models yet — run ollama pull llama3.2"}`
              : `Not reachable at ${ollama?.url || "http://127.0.0.1:11434"}. Start with ollama serve, then bind a model.`}
          </p>
          {ollama?.up && (
            <div className="field" style={{ marginBottom: 10 }}>
              <select value={pick} onChange={(e) => setPick(e.target.value)}>
                {(ollama.models || []).map((m: string) => (
                  <option key={m}>{m}</option>
                ))}
              </select>
            </div>
          )}
          <div className="row-actions">
            <button className="btn" onClick={() => AgentAPI.ollama().then(setOllama)}>
              Refresh
            </button>
            {ollama?.up && (
              <button
                className="btn primary"
                data-demo="bind-ollama"
                onClick={async () => {
                  try {
                    const r = await AgentAPI.useOllama(pick);
                    setMsg(`Bound ${r.model} to form builder, agents, and flows`);
                    load();
                  } catch (e: any) {
                    setMsg(e.message);
                  }
                }}
              >
                Use this model
              </button>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
