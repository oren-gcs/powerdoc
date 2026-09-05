import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { FormsAPI, WfAPI } from "../api";
import FormExit from "../components/FormExit";

const ACTIONS: { key: string; label: string }[] = [
  { key: "ingest", label: "Ingest" },
  { key: "digest", label: "Digest" },
  { key: "extract", label: "Extract" },
  { key: "summarize", label: "Summarize" },
  { key: "insights", label: "Insights" },
  { key: "automate", label: "Create automation" },
];

export default function FormAnswered() {
  const { id } = useParams();
  const nav = useNavigate();
  const formId = Number(id);
  const [form, setForm] = useState<any>(null);
  const [folder, setFolder] = useState<any>(null);
  const [rows, setRows] = useState<any[]>([]);
  const [workflows, setWorkflows] = useState<any[]>([]);
  const [workflowId, setWorkflowId] = useState<number>(0);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState<string>("");
  const [open, setOpen] = useState<number | null>(null);
  const [archiveOpen, setArchiveOpen] = useState(false);

  const load = useCallback(() => {
    if (!formId) return;
    FormsAPI.answered(formId).then((r) => {
      setForm(r.form);
      setFolder(r.folder);
      setRows(r.submissions || []);
    });
  }, [formId]);

  useEffect(() => {
    load();
    WfAPI.list()
      .then((w) => {
        setWorkflows(w || []);
        if (w?.[0]) setWorkflowId(w[0].id);
      })
      .catch(() => setWorkflows([]));
  }, [load]);

  const run = async (submissionId: number, action: string) => {
    const key = `${submissionId}:${action}`;
    setBusy(key);
    setMsg("");
    try {
      const r = await FormsAPI.digest(formId, submissionId, {
        action,
        workflow_id: workflowId || undefined,
      });
      setMsg(r.entry?.summary || r.result?.summary || `${action} done`);
      load();
      setOpen(submissionId);
    } catch (e: any) {
      setMsg(e.message);
    } finally {
      setBusy("");
    }
  };

  if (!form) {
    return <div className="workspace muted">Opening answered folder…</div>;
  }

  return (
    <>
      <div className="topbar">
        <div>
          <FormExit fallback={`/app/forms/${formId}`} variant="on-dark" />
          <div className="eyebrow">Answered folder</div>
          <h1 className="mark" style={{ fontSize: 32, margin: 0 }} data-demo="answered-title">
            {form.name}
          </h1>
          <p className="muted" style={{ marginTop: 6 }}>
            {folder ? folder.name : "No answers yet"} · {rows.length} submission{rows.length === 1 ? "" : "s"}
            {form.locked ? (
              <>
                {" "}
                · <span className="pill warn" data-demo="locked-badge">Locked</span>
              </>
            ) : null}
            {form.archived ? (
              <>
                {" "}
                · <span className="pill" data-demo="archived-badge">Archived</span>
              </>
            ) : null}
          </p>
        </div>
        <div className="row-actions">
          <button
            className="btn"
            data-demo="copy-form"
            onClick={async () => {
              try {
                const copy = await FormsAPI.copy(formId);
                setMsg(`Copied to new unlocked form: ${copy.name}`);
                nav(`/app/forms/${copy.id}`);
              } catch (e: any) {
                setMsg(e.message);
              }
            }}
          >
            Copy to new form
          </button>
          {!form.archived && (
            <button className="btn" data-demo="archive-form" onClick={() => setArchiveOpen(true)}>
              Archive
            </button>
          )}
          {form.archived && (
            <button
              className="btn"
              data-demo="unarchive-form"
              onClick={async () => {
                try {
                  await FormsAPI.unarchive(formId);
                  setMsg("Unarchived as draft");
                  load();
                } catch (e: any) {
                  setMsg(e.message);
                }
              }}
            >
              Unarchive
            </button>
          )}
          <Link className="btn" to={`/app/forms/${formId}`}>
            Form definition
          </Link>
          {workflows.length > 0 && (
            <select
              value={workflowId}
              onChange={(e) => setWorkflowId(Number(e.target.value))}
              aria-label="Workflow for automate"
            >
              {workflows.map((w) => (
                <option key={w.id} value={w.id}>
                  {w.name}
                </option>
              ))}
            </select>
          )}
        </div>
      </div>
      {archiveOpen && (
        <div className="card archive-panel" data-demo="archive-panel">
          <h3 style={{ marginTop: 0 }}>Archive form</h3>
          <p className="muted">Definition stays frozen. Choose how answered data is packaged.</p>
          <div className="row-actions">
            <button
              className="btn primary"
              data-demo="archive-keep"
              onClick={async () => {
                try {
                  await FormsAPI.archive(formId, true);
                  setArchiveOpen(false);
                  setMsg("Archived with answered data");
                  load();
                } catch (e: any) {
                  setMsg(e.message);
                }
              }}
            >
              Keep answered data
            </button>
            <button
              className="btn"
              data-demo="archive-form-only"
              onClick={async () => {
                try {
                  await FormsAPI.archive(formId, false);
                  setArchiveOpen(false);
                  setMsg("Archived form only — answers stay in Answered folder / documents");
                  load();
                } catch (e: any) {
                  setMsg(e.message);
                }
              }}
            >
              Archive form only (answers stay in Answered folder / documents)
            </button>
            <button className="btn ghost" onClick={() => setArchiveOpen(false)}>
              Cancel
            </button>
          </div>
        </div>
      )}
      {msg && <p className="pill ok" data-demo="answered-msg">{msg}</p>}
      <div className="card" data-demo="answered-list">
        {!rows.length && <p className="muted">Answers will land here after someone fills the live form.</p>}
        <table className="table">
          <thead>
            <tr>
              <th>Submitter</th>
              <th>When</th>
              <th>Status</th>
              <th>Document</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((s) => (
              <tr key={s.id}>
                <td>
                  <strong>{s.submitter_name || "—"}</strong>
                  <div className="mono dim">{s.submitter_email}</div>
                </td>
                <td className="mono dim">{s.created_at ? new Date(s.created_at).toLocaleString() : "—"}</td>
                <td>
                  <span className={`pill ${s.status === "implemented" ? "ok" : ""}`}>{s.status}</span>
                </td>
                <td>
                  {s.document_id ? (
                    <Link to={`/app/documents/${s.document_id}`}>{s.document_filename || `#${s.document_id}`}</Link>
                  ) : (
                    "—"
                  )}
                </td>
                <td>
                  <div className="row-actions answered-actions">
                    {ACTIONS.map((a) => (
                      <button
                        key={a.key}
                        className="btn"
                        data-demo={`action-${a.key}`}
                        disabled={busy === `${s.id}:${a.key}`}
                        onClick={() => run(s.id, a.key)}
                      >
                        {busy === `${s.id}:${a.key}` ? "…" : a.label}
                      </button>
                    ))}
                    <button className="btn" onClick={() => setOpen(open === s.id ? null : s.id)}>
                      {open === s.id ? "Hide log" : "Log"}
                    </button>
                  </div>
                  {open === s.id && (
                    <div className="answered-log" data-demo="action-log">
                      {(s.actions || []).length === 0 && <p className="muted">No digest actions yet.</p>}
                      {(s.actions || [])
                        .slice()
                        .reverse()
                        .map((entry: any, i: number) => (
                          <div key={i} className="answered-log-row">
                            <span className="pill">{entry.action}</span>
                            <span className="mono dim">{entry.at}</span>
                            <p>{entry.summary}</p>
                          </div>
                        ))}
                    </div>
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
