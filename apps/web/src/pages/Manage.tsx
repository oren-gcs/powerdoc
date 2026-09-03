import { useEffect, useState } from "react";
import { OrgAPI } from "../api";

export default function Manage() {
  const [tree, setTree] = useState<any>(null);
  const [layerName, setLayerName] = useState("New team");
  const [email, setEmail] = useState("");
  const [sel, setSel] = useState<number | null>(null);
  const [perm, setPerm] = useState({ resource_type: "form", resource_id: 1, permission: "fill" });
  const load = () => OrgAPI.tree().then(setTree);
  useEffect(() => {
    load();
  }, []);
  if (!tree) return <p className="muted">Loading layers…</p>;
  return (
    <>
      <div className="eyebrow">Organization layers</div>
      <h1 className="mark" style={{ fontSize: 32 }}>
        Manage
      </h1>
      <p className="muted">Add in-domain users to a layer and grant view / fill / edit / manage on folders, files, or forms.</p>
      <div className="split">
        <div className="card">
          {tree.layers.map((l: any) => (
            <div key={l.id} className={`layer-row ${sel === l.id ? "on" : ""}`} onClick={() => setSel(l.id)}>
              <strong>{l.parent_id ? "↳ " : ""}{l.name}</strong>
              <span className="pill">{l.kind}</span>
              <span className="mono dim">{l.locale}</span>
              <div className="muted">
                {l.members.map((m: any) => (
                  <div key={m.user_id}>
                    {m.full_name} · {m.email} · {m.title}
                  </div>
                ))}
              </div>
            </div>
          ))}
          <div className="row-actions" style={{ marginTop: 12 }}>
            <input value={layerName} onChange={(e) => setLayerName(e.target.value)} />
            <button className="btn" onClick={() => OrgAPI.layer({ name: layerName, parent_id: sel }).then(load)}>
              Add layer
            </button>
          </div>
        </div>
        <div className="card">
          <div className="eyebrow">Invite into selected layer</div>
          <input placeholder="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          <button
            className="btn primary"
            style={{ marginTop: 8 }}
            disabled={!sel}
            onClick={() => sel && OrgAPI.member(sel, { email, role: "viewer", title: "member" }).then(load)}
          >
            Add user
          </button>
          <div className="eyebrow" style={{ marginTop: 18 }}>
            Permission
          </div>
          <select value={perm.permission} onChange={(e) => setPerm({ ...perm, permission: e.target.value })}>
            <option>view</option>
            <option>fill</option>
            <option>edit</option>
            <option>manage</option>
          </select>
          <button
            className="btn"
            style={{ marginTop: 8 }}
            disabled={!sel}
            onClick={() =>
              sel &&
              OrgAPI.grant({
                principal_type: "layer",
                principal_id: sel,
                ...perm,
                resource_id: Number(perm.resource_id),
              }).then(load)
            }
          >
            Grant to layer
          </button>
          <table className="table">
            <tbody>
              {tree.grants.map((g: any) => (
                <tr key={g.id}>
                  <td className="mono">
                    {g.principal_type}:{g.principal_id}
                  </td>
                  <td>
                    {g.resource_type} {g.resource_id}
                  </td>
                  <td>{g.permission}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
