import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { FormsAPI } from "../api";

export default function Forms() {
  const nav = useNavigate();
  const [rows, setRows] = useState<any[]>([]);
  const [msg, setMsg] = useState("");
  const [archiveFor, setArchiveFor] = useState<number | null>(null);
  const load = () => FormsAPI.list().then(setRows);
  useEffect(() => {
    load();
  }, []);

  const copyForm = async (id: number) => {
    try {
      const copy = await FormsAPI.copy(id);
      setMsg(`Copied to new unlocked form: ${copy.name}`);
      load();
      nav(`/app/forms/${copy.id}`);
    } catch (e: any) {
      setMsg(e.message);
    }
  };

  const archiveForm = async (id: number, keep_answers: boolean) => {
    try {
      const r = await FormsAPI.archive(id, keep_answers);
      setArchiveFor(null);
      setMsg(
        keep_answers
          ? `Archived “${r.name}” with answered data under Archive.`
          : `Archived “${r.name}” — answers stay in Answered folder / documents.`
      );
      load();
    } catch (e: any) {
      setMsg(e.message);
    }
  };

  const unarchiveForm = async (id: number) => {
    try {
      const r = await FormsAPI.unarchive(id);
      setMsg(`Unarchived “${r.name}” as draft.`);
      load();
    } catch (e: any) {
      setMsg(e.message);
    }
  };

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
      {archiveFor != null && (
        <div className="card archive-panel" data-demo="archive-panel">
          <h3 style={{ marginTop: 0 }}>Archive form</h3>
          <p className="muted">Choose how answered data is handled. Definition stays frozen either way.</p>
          <div className="row-actions">
            <button className="btn primary" data-demo="archive-keep" onClick={() => archiveForm(archiveFor, true)}>
              Keep answered data
            </button>
            <button className="btn" data-demo="archive-form-only" onClick={() => archiveForm(archiveFor, false)}>
              Archive form only (answers stay in Answered folder / documents)
            </button>
            <button className="btn ghost" onClick={() => setArchiveFor(null)}>
              Cancel
            </button>
          </div>
        </div>
      )}
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
                  {f.archived && (
                    <span className="pill" style={{ marginInlineStart: 8 }} data-demo="archived-badge">
                      Archived
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
                  {f.status !== "live" && !f.locked && !f.archived && (
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
                  {f.share_url && !f.archived && (
                    <a className="btn" href={f.share_url} target="_blank" rel="noreferrer">
                      Open link
                    </a>
                  )}
                  {!f.locked && !f.archived && (
                    <Link className="btn" to={`/app/forms/${f.id}`}>
                      Edit
                    </Link>
                  )}
                  <button className="btn" data-demo="copy-form" onClick={() => copyForm(f.id)}>
                    Copy to new form
                  </button>
                  {f.archived ? (
                    <button className="btn" data-demo="unarchive-form" onClick={() => unarchiveForm(f.id)}>
                      Unarchive
                    </button>
                  ) : (
                    <button className="btn" data-demo="archive-form" onClick={() => setArchiveFor(f.id)}>
                      Archive
                    </button>
                  )}
                  {!f.locked && !f.archived && (
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
