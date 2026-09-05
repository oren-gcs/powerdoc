import { FormEvent, useEffect, useState } from "react";
import { AutoAPI, WfAPI } from "../api";

export default function Automations() {
  const [rows, setRows] = useState<any[]>([]);
  const [wfs, setWfs] = useState<any[]>([]);
  const [form, setForm] = useState({ name: "On invoice", trigger_type: "on_classify", classification: "invoice", workflow_id: 0 });

  const load = () => AutoAPI.list().then(setRows);
  useEffect(() => {
    load();
    WfAPI.list().then((w) => {
      setWfs(w);
      if (w[0]) setForm((f) => ({ ...f, workflow_id: w[0].id }));
    });
  }, []);

  const create = async (e: FormEvent) => {
    e.preventDefault();
    await AutoAPI.create({
      name: form.name,
      trigger_type: form.trigger_type,
      trigger_config: form.classification ? { classification: form.classification } : {},
      workflow_id: Number(form.workflow_id),
    });
    load();
  };

  return (
    <>
      <div className="eyebrow">Triggers</div>
      <h1 className="mark" style={{ fontSize: 32 }}>
        Automations
      </h1>
      <div className="split">
        <div className="card">
          {rows.map((a) => (
            <div key={a.id} style={{ display: "flex", justifyContent: "space-between", padding: "10px 0", borderBottom: "1px solid var(--line)" }}>
              <div>
                <strong>{a.name}</strong>
                <div className="mono dim">
                  {a.trigger_type} · fired {a.fire_count}×
                </div>
              </div>
              <button className="btn" onClick={() => AutoAPI.toggle(a.id).then(load)}>
                {a.is_active ? "On" : "Off"}
              </button>
            </div>
          ))}
        </div>
        <form className="card" onSubmit={create}>
          <div className="eyebrow">New trigger</div>
          <div className="field" style={{ marginTop: 10 }}>
            <label>Name</label>
            <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </div>
          <div className="field" style={{ marginTop: 10 }}>
            <label>When</label>
            <select value={form.trigger_type} onChange={(e) => setForm({ ...form, trigger_type: e.target.value })}>
              <option value="on_upload">On upload</option>
              <option value="on_classify">On classify</option>
              <option value="webhook">Webhook</option>
            </select>
          </div>
          <div className="field" style={{ marginTop: 10 }}>
            <label>Class filter</label>
            <input value={form.classification} onChange={(e) => setForm({ ...form, classification: e.target.value })} />
          </div>
          <div className="field" style={{ marginTop: 10 }}>
            <label>Workflow</label>
            <select value={form.workflow_id} onChange={(e) => setForm({ ...form, workflow_id: Number(e.target.value) })}>
              {wfs.map((w) => (
                <option key={w.id} value={w.id}>
                  {w.name}
                </option>
              ))}
            </select>
          </div>
          <button className="btn primary" style={{ marginTop: 14 }}>
            Save automation
          </button>
        </form>
      </div>
    </>
  );
}
