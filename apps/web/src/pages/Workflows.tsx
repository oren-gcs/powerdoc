import { FormEvent, useEffect, useState } from "react";
import { WfAPI } from "../api";

const TYPES = ["extract_text", "classify", "extract_fields", "condition", "tag", "summarize", "notify", "agent", "webhook"];

export default function Workflows() {
  const [rows, setRows] = useState<any[]>([]);
  const [runs, setRuns] = useState<any[]>([]);
  const [name, setName] = useState("Custom intake");
  const [steps, setSteps] = useState("extract_text,classify,extract_fields,notify");

  const load = () => {
    WfAPI.list().then(setRows);
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

  return (
    <>
      <div className="topbar">
        <div>
          <div className="eyebrow">Executable engine</div>
          <h1 className="mark" style={{ fontSize: 32, margin: 0 }}>
            Flows
          </h1>
        </div>
      </div>
      <div className="split">
        <div className="card">
          {rows.map((w) => (
            <div key={w.id} style={{ padding: "12px 0", borderBottom: "1px solid var(--line)" }}>
              <strong>{w.name}</strong>
              <div className="muted">{w.description}</div>
              <div className="flow" style={{ marginTop: 8 }}>
                {(w.steps || []).map((s: any) => (
                  <div className="step-chip" key={s.key}>
                    <small>{s.type}</small>
                    {s.key}
                  </div>
                ))}
              </div>
            </div>
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
          {runs[0]?.steps && (
            <div style={{ marginTop: 12 }}>
              {runs[0].steps.map((s: any) => (
                <div key={s.key} className="muted">
                  {s.key}: {s.status}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
