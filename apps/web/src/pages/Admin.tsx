import { FormEvent, useEffect, useState } from "react";
import { AdminAPI } from "../api";

export default function Admin() {
  const [stats, setStats] = useState<any>(null);
  const [users, setUsers] = useState<any[]>([]);
  const [flags, setFlags] = useState<any[]>([]);
  const [models, setModels] = useState<any[]>([]);
  const [health, setHealth] = useState<any>(null);
  const [form, setForm] = useState({ email: "", full_name: "", password: "DocFlow!2026", role: "operator" });
  const [err, setErr] = useState("");

  const load = () => {
    AdminAPI.stats().then(setStats).catch(() => {});
    AdminAPI.users().then(setUsers).catch(() => {});
    AdminAPI.flags().then(setFlags).catch(() => {});
    AdminAPI.models().then(setModels).catch(() => {});
    AdminAPI.health().then(setHealth).catch(() => {});
  };
  useEffect(() => {
    load();
  }, []);

  const add = async (e: FormEvent) => {
    e.preventDefault();
    setErr("");
    try {
      await AdminAPI.createUser(form);
      load();
    } catch (ex: any) {
      setErr(ex.message);
    }
  };

  return (
    <>
      <div className="eyebrow">Control plane</div>
      <h1 className="mark" style={{ fontSize: 32 }}>
        Admin
      </h1>
      <div className="grid cards-4">
        <div className="card stat">
          <div className="eyebrow">Users</div>
          <div className="n">{stats?.users}</div>
        </div>
        <div className="card stat">
          <div className="eyebrow">Documents</div>
          <div className="n">{stats?.documents}</div>
        </div>
        <div className="card stat">
          <div className="eyebrow">API</div>
          <div className="n" style={{ fontSize: 22 }}>
            {health?.api}
          </div>
        </div>
        <div className="card stat">
          <div className="eyebrow">DB</div>
          <div className="n" style={{ fontSize: 22 }}>
            {health?.database}
          </div>
        </div>
      </div>
      <div className="split" style={{ marginTop: 16 }}>
        <div className="card">
          <div className="eyebrow">People</div>
          <table className="table">
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td>
                    {u.full_name}
                    <div className="mono dim">{u.email}</div>
                  </td>
                  <td>{u.role}</td>
                  <td>
                    <button className="btn" onClick={() => AdminAPI.block(u.id).then(load)}>
                      {u.is_blocked ? "Unblock" : "Block"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <form onSubmit={add} style={{ marginTop: 12 }} className="grid">
            <input placeholder="name" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
            <input placeholder="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
            <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
              <option>operator</option>
              <option>admin</option>
              <option>viewer</option>
            </select>
            <button className="btn primary">Invite</button>
            {err && <span className="pill bad">{err}</span>}
          </form>
        </div>
        <div>
          <div className="card">
            <div className="eyebrow">Flags</div>
            {flags.map((f) => (
              <div key={f.key} style={{ display: "flex", justifyContent: "space-between", padding: "6px 0" }}>
                <span>{f.key}</span>
                <span className={`pill ${f.enabled ? "ok" : ""}`}>{f.enabled ? "on" : "off"}</span>
              </div>
            ))}
          </div>
          <div className="card" style={{ marginTop: 16 }}>
            <div className="eyebrow">Model bindings</div>
            {models.map((m) => (
              <div key={m.role} className="muted">
                {m.role} → {m.model} ({m.provider})
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}
