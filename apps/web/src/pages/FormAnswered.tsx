import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { FormsAPI, WfAPI } from "../api";
import FormExit from "../components/FormExit";
import { t, useDeskLang } from "../i18n";

const ACTION_KEYS = ["ingest", "digest", "extract", "summarize", "insights", "automate"] as const;

export default function FormAnswered() {
  const { id } = useParams();
  const nav = useNavigate();
  const lang = useDeskLang();
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

  const actionLabel = (key: string) => {
    const map: Record<string, string> = {
      ingest: "actionIngest",
      digest: "actionDigest",
      extract: "actionExtract",
      summarize: "actionSummarize",
      insights: "actionInsights",
      automate: "actionAutomate",
    };
    return t(lang, map[key] || key);
  };

  if (!form) {
    return <div className="workspace muted">{t(lang, "openingAnswered")}</div>;
  }

  return (
    <>
      <div className="topbar">
        <div>
          <FormExit fallback={`/app/forms/${formId}`} variant="on-dark" />
          <div className="eyebrow">{t(lang, "answeredFolder")}</div>
          <h1 className="mark" style={{ fontSize: 32, margin: 0 }} data-demo="answered-title">
            {form.name}
          </h1>
          <p className="muted" style={{ marginTop: 6 }}>
            {folder ? folder.name : t(lang, "noAnswersYet")} · {rows.length}{" "}
            {rows.length === 1 ? t(lang, "submission") : t(lang, "submissions")}
            {form.locked ? (
              <>
                {" "}
                ·{" "}
                <span className="pill warn" data-demo="locked-badge">
                  {t(lang, "locked")}
                </span>
              </>
            ) : null}
            {form.archived ? (
              <>
                {" "}
                ·{" "}
                <span className="pill" data-demo="archived-badge">
                  {t(lang, "archived")}
                </span>
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
                setMsg(`${t(lang, "copy")}: ${copy.name}`);
                nav(`/app/forms/${copy.id}`);
              } catch (e: any) {
                setMsg(e.message);
              }
            }}
          >
            {t(lang, "copy")}
          </button>
          {!form.archived && (
            <button className="btn" data-demo="archive-form" onClick={() => setArchiveOpen(true)}>
              {t(lang, "archive")}
            </button>
          )}
          {form.archived && (
            <button
              className="btn"
              data-demo="unarchive-form"
              onClick={async () => {
                try {
                  await FormsAPI.unarchive(formId);
                  setMsg(t(lang, "unarchive"));
                  load();
                } catch (e: any) {
                  setMsg(e.message);
                }
              }}
            >
              {t(lang, "unarchive")}
            </button>
          )}
          <Link className="btn" to={`/app/forms/${formId}`}>
            {t(lang, "formDefinition")}
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
          <h3 style={{ marginTop: 0 }}>{t(lang, "archiveForm")}</h3>
          <p className="muted">{t(lang, "archiveHint")}</p>
          <div className="row-actions">
            <button
              className="btn primary"
              data-demo="archive-keep"
              onClick={async () => {
                try {
                  await FormsAPI.archive(formId, true);
                  setArchiveOpen(false);
                  setMsg(t(lang, "keepAnswered"));
                  load();
                } catch (e: any) {
                  setMsg(e.message);
                }
              }}
            >
              {t(lang, "keepAnswered")}
            </button>
            <button
              className="btn"
              data-demo="archive-form-only"
              onClick={async () => {
                try {
                  await FormsAPI.archive(formId, false);
                  setArchiveOpen(false);
                  setMsg(t(lang, "archiveFormOnly"));
                  load();
                } catch (e: any) {
                  setMsg(e.message);
                }
              }}
            >
              {t(lang, "archiveFormOnly")}
            </button>
            <button className="btn ghost" onClick={() => setArchiveOpen(false)}>
              {t(lang, "cancel")}
            </button>
          </div>
        </div>
      )}
      {msg && (
        <p className="pill ok" data-demo="answered-msg">
          {msg}
        </p>
      )}
      <div className="card" data-demo="answered-list">
        {!rows.length && <p className="muted">{t(lang, "answersWillLand")}</p>}
        <table className="table">
          <thead>
            <tr>
              <th>{t(lang, "submitter")}</th>
              <th>{t(lang, "when")}</th>
              <th>{t(lang, "status")}</th>
              <th>{t(lang, "document")}</th>
              <th>{t(lang, "actions")}</th>
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
                    {ACTION_KEYS.map((a) => (
                      <button
                        key={a}
                        className="btn"
                        data-demo={`action-${a}`}
                        disabled={busy === `${s.id}:${a}`}
                        onClick={() => run(s.id, a)}
                      >
                        {busy === `${s.id}:${a}` ? "…" : actionLabel(a)}
                      </button>
                    ))}
                    <button className="btn" onClick={() => setOpen(open === s.id ? null : s.id)}>
                      {open === s.id ? t(lang, "hideLog") : t(lang, "log")}
                    </button>
                  </div>
                  {open === s.id && (
                    <div className="answered-log" data-demo="action-log">
                      {(s.actions || []).length === 0 && <p className="muted">{t(lang, "noDigestYet")}</p>}
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
