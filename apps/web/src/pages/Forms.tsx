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
                  <Link to={`/app/forms/${f.id}`}>{f.name}</Link>
                </td>
                <td className="mono">{f.language}</td>
                <td>
                  <span className={`pill ${f.status === "live" ? "ok" : ""}`}>{f.status}</span>
                </td>
                <td className="row-actions">
                  {f.status !== "live" && (
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
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
