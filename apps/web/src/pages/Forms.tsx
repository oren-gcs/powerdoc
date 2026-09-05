import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { FormsAPI } from "../api";

export default function Forms() {
  const [rows, setRows] = useState<any[]>([]);
  const [msg, setMsg] = useState("");
  const load = () => FormsAPI.list().then(setRows);
  useEffect(() => {
    load();
  }, []);
  return (
    <>
      <div className="topbar">
        <div>
          <div className="eyebrow">Paper that can move</div>
          <h1 className="mark" style={{ fontSize: 32, margin: 0 }}>
            Forms
          </h1>
        </div>
        <Link className="btn primary" to="/app/forms/new">
          New form
        </Link>
      </div>
      {msg && <p className="pill ok">{msg}</p>}
      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Language</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((f) => (
              <tr key={f.id}>
                <td>
                  <Link to={f.locked ? `/app/forms/${f.id}/answered` : `/app/forms/${f.id}`}>{f.name}</Link>
                  {f.locked && (
                    <span className="pill warn" style={{ marginInlineStart: 8 }} data-demo="locked-badge">
                      Locked · {f.submission_count}
                    </span>
                  )}
                </td>
                <td className="mono">{f.language}</td>
                <td>
                  <span className={`pill ${f.status === "live" ? "ok" : ""}`}>{f.status}</span>
                </td>
                <td className="row-actions">
                  {f.locked && (
                    <Link className="btn primary" to={`/app/forms/${f.id}/answered`} data-demo="open-answered">
                      Answered
                    </Link>
                  )}
                  {f.status !== "live" && !f.locked && (
                    <button
                      className="btn"
                      onClick={async () => {
                        const r = await FormsAPI.publish(f.id);
                        setMsg(`Alive: ${r.share_url}`);
                        load();
                      }}
                    >
                      Make alive
                    </button>
                  )}
                  {f.share_url && (
                    <a className="btn" href={f.share_url} target="_blank" rel="noreferrer">
                      Open link
                    </a>
                  )}
                  {!f.locked && (
                    <Link className="btn" to={`/app/forms/${f.id}`}>
                      Edit
                    </Link>
                  )}
                  {!f.locked && (
                    <button
                      className="btn"
                      onClick={async () => {
                        try {
                          await FormsAPI.remove(f.id);
                          setMsg("Deleted");
                          load();
                        } catch (e: any) {
                          setMsg(e.message);
                        }
                      }}
                    >
                      Delete
                    </button>
                  )}
                  {(f.recipients || []).length > 0 && (
                    <span className="muted" title={(f.recipients || []).join(", ")}>
                      → {(f.recipients || []).slice(0, 2).join(", ")}
                      {(f.recipients || []).length > 2 ? "…" : ""}
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
