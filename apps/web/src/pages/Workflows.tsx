import { FormEvent, useEffect, useState } from "react";
import { WfAPI } from "../api";

const TYPES = ["extract_text", "classify", "extract_fields", "condition", "tag", "summarize", "notify", "agent", "webhook"];

function FlowBoard({ nodes }: { nodes: any[] }) {
  const items = nodes || [];
  return (
    <div className="n8n-board" data-demo="n8n-board">
      {items.map((n, i) => (
        <div key={n.key || i} className="n8n-col">
          <div className={`n8n-node type-${n.type}`}>
            <div className="n8n-port" />
            <div className="eyebrow">{n.n8n?.replace("n8n-nodes-base.", "") || n.type}</div>
            <strong>{n.label}</strong>
          </div>
          {i < items.length - 1 && <div className="n8n-wire" aria-hidden />}
        </div>
      ))}
    </div>
  );
}

export default function Workflows() {
  const [rows, setRows] = useState<any[]>([]);
  const [runs, setRuns] = useState<any[]>([]);
  const [sel, setSel] = useState<any>(null);
  const [n8n, setN8n] = useState<any>(null);
  const [name, setName] = useState("Custom intake");
  const [steps, setSteps] = useState("extract_text,classify,extract_fields,notify");

  const load = () => {
    WfAPI.list().then((w) => {
      setRows(w);
      setSel((cur: any) => cur || w[0] || null);
    });
    WfAPI.runs().then(setRuns);
  };
  useEffect(() => {
    load();
  }, []);

  const create = async (e: FormEvent) => {
    e.preventDefault();
    await WfAPI.create({
      name,
      description: "Created from the desk",
      trigger: "manual",
      steps: steps.split(",").map((t, i) => ({ key: `${t.trim()}-${i}`, type: t.trim(), config: {} })),
    });
    setName("");
    load();
  };

  const openN8n = async (wf: any) => {
    setSel(wf);
    const graph = await WfAPI.n8n(wf.id);
    setN8n(graph);
  };

  return (
    <>
      <div className="topbar">
        <div>
          <div className="eyebrow">n8n-compatible · executable here</div>
          <h1 className="mark" style={{ fontSize: 32, margin: 0 }}>
            n8n flows
          </h1>
        </div>
        {sel && (
          <button className="btn" data-demo="n8n-json" onClick={() => openN8n(sel)}>
            Open n8n JSON
          </button>
        )}
      </div>
      {sel && <FlowBoard nodes={sel.canvas || sel.steps} />}
      {n8n && (
        <pre className="ocr" data-demo="n8n-json-view">
          {JSON.stringify({ name: n8n.name, nodes: (n8n.nodes || []).map((n: any) => n.name), webhook: n8n.webhook }, null, 2)}
        </pre>
      )}
      <div className="split" style={{ marginTop: 16 }}>
        <div className="card">
          {rows.map((w) => (
            <button
              type="button"
              key={w.id}
              className={`flow-pick ${sel?.id === w.id ? "on" : ""}`}
              data-demo={`flow-${w.id}`}
              onClick={() => {
                setSel(w);
                setN8n(null);
              }}
            >
              <div>
                <strong>{w.name}</strong>
                <span className="pill">n8n</span>
              </div>
              <div className="muted">{w.description}</div>
            </button>
          ))}
          <form onSubmit={create} style={{ marginTop: 16 }}>
            <div className="field">
              <label>New flow name</label>
              <input value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div className="field" style={{ marginTop: 8 }}>
              <label>Steps ({TYPES.join(", ")})</label>
              <input value={steps} onChange={(e) => setSteps(e.target.value)} />
            </div>
            <button className="btn primary" style={{ marginTop: 12 }}>
              Save flow
            </button>
          </form>
        </div>
        <div className="card">
          <div className="eyebrow">Recent runs</div>
          <table className="table">
            <tbody>
              {runs.map((r) => (
                <tr key={r.id}>
                  <td>
                    {r.workflow_name}
                    <div className="mono dim">doc #{r.document_id}</div>
                  </td>
                  <td>
                    <span className={`pill ${r.status === "completed" ? "ok" : "bad"}`}>{r.status}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
