import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { FormsAPI } from "../api";
import { t, useDeskLang } from "../i18n";

export default function Forms() {
  const nav = useNavigate();
  const lang = useDeskLang();
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
      setMsg(`${t(lang, "copy")}: ${copy.name}`);
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
      setMsg(keep_answers ? `${t(lang, "archive")} · ${r.name}` : `${t(lang, "archiveFormOnly")} · ${r.name}`);
      load();
    } catch (e: any) {
      setMsg(e.message);
    }
  };

  const unarchiveForm = async (id: number) => {
    try {
      const r = await FormsAPI.unarchive(id);
      setMsg(`${t(lang, "unarchive")}: ${r.name}`);
      load();
    } catch (e: any) {
      setMsg(e.message);
    }
  };

  return (
    <>
      <div className="topbar">
        <div>
          <div className="eyebrow">{t(lang, "formsEyebrow")}</div>
          <h1 className="mark" style={{ fontSize: 32, margin: 0 }}>
            {t(lang, "forms")}
          </h1>
        </div>
        <Link className="btn primary" to="/app/forms/new">
          {t(lang, "newForm")}
        </Link>
      </div>
      {msg && <p className="pill ok">{msg}</p>}
      {archiveFor != null && (
        <div className="card archive-panel" data-demo="archive-panel">
          <h3 style={{ marginTop: 0 }}>{t(lang, "archiveForm")}</h3>
          <p className="muted">{t(lang, "archiveHint")}</p>
          <div className="row-actions">
            <button className="btn primary" data-demo="archive-keep" onClick={() => archiveForm(archiveFor, true)}>
              {t(lang, "keepAnswered")}
            </button>
            <button className="btn" data-demo="archive-form-only" onClick={() => archiveForm(archiveFor, false)}>
              {t(lang, "archiveFormOnly")}
            </button>
            <button className="btn ghost" onClick={() => setArchiveFor(null)}>
              {t(lang, "cancel")}
            </button>
          </div>
        </div>
      )}
      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>{t(lang, "name")}</th>
              <th>{t(lang, "language")}</th>
              <th>{t(lang, "status")}</th>
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
                      {t(lang, "locked")} · {f.submission_count}
                    </span>
                  )}
                  {f.archived && (
                    <span className="pill" style={{ marginInlineStart: 8 }} data-demo="archived-badge">
                      {t(lang, "archived")}
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
                      {t(lang, "answered")}
                    </Link>
                  )}
                  {f.status !== "live" && !f.locked && !f.archived && (
                    <button
                      className="btn"
                      onClick={async () => {
                        const r = await FormsAPI.publish(f.id);
                        setMsg(`${t(lang, "formAlive")}: ${r.share_url}`);
                        load();
                      }}
                    >
                      {t(lang, "makeAlive")}
                    </button>
                  )}
                  {f.share_url && !f.archived && (
                    <a className="btn" href={f.share_url} target="_blank" rel="noreferrer">
                      {t(lang, "openLink")}
                    </a>
                  )}
                  {!f.locked && !f.archived && (
                    <Link className="btn" to={`/app/forms/${f.id}`}>
                      {t(lang, "edit")}
                    </Link>
                  )}
                  <button className="btn" data-demo="copy-form" onClick={() => copyForm(f.id)}>
                    {t(lang, "copy")}
                  </button>
                  {f.archived ? (
                    <button className="btn" data-demo="unarchive-form" onClick={() => unarchiveForm(f.id)}>
                      {t(lang, "unarchive")}
                    </button>
                  ) : (
                    <button className="btn" data-demo="archive-form" onClick={() => setArchiveFor(f.id)}>
                      {t(lang, "archive")}
                    </button>
                  )}
                  {!f.locked && !f.archived && (
                    <button
                      className="btn"
                      onClick={async () => {
                        try {
                          await FormsAPI.remove(f.id);
                          setMsg(t(lang, "delete"));
                          load();
                        } catch (e: any) {
                          setMsg(e.message);
                        }
                      }}
                    >
                      {t(lang, "delete")}
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
