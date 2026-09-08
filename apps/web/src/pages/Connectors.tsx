import { useEffect, useState } from "react";
import { AgentAPI, ConnectAPI } from "../api";
import { t, useDeskLang } from "../i18n";

const SOURCES = [
  {
    kind: "google_drive",
    title: "Google Drive",
    blurb: "Demo catalog — browse Source → Folder → Files (not live OAuth).",
    mark: "G",
  },
  {
    kind: "microsoft",
    title: "Microsoft 365",
    blurb: "Demo catalog — SharePoint / OneDrive sample tree for RAG.",
    mark: "365",
  },
  {
    kind: "local_db",
    title: "Local database",
    blurb: "Browse this tenant’s documents and OCR text as files.",
    mark: "DB",
  },
];

type BrowseNode = { id: string; name: string; path: string };
type BrowsePayload = {
  connector_id: number;
  kind: string;
  demo?: boolean;
  label?: string;
  path: string;
  breadcrumbs: BrowseNode[];
  sources: BrowseNode[];
  folders: BrowseNode[];
  files: BrowseNode[];
};

export default function Connectors() {
  const lang = useDeskLang();
  const [rows, setRows] = useState<any[]>([]);
  const [msg, setMsg] = useState("");
  const [ollama, setOllama] = useState<any>(null);
  const [pick, setPick] = useState("");
  const [panel, setPanel] = useState<{ id: number; kind: string; title: string } | null>(null);
  const [browse, setBrowse] = useState<BrowsePayload | null>(null);
  const [selected, setSelected] = useState<Record<string, boolean>>({});
  const [busy, setBusy] = useState(false);

  const load = () => {
    ConnectAPI.list().then(setRows);
    AgentAPI.ollama().then((o) => {
      setOllama(o);
      setPick(o.default || o.models?.[0] || "");
    });
  };
  useEffect(() => {
    load();
  }, []);

  const rowFor = (kind: string) => rows.find((r) => r.kind === kind);

  const connect = async (kind: string, title: string) => {
    await ConnectAPI.add({ kind, name: title });
    await load();
  };

  const openBrowse = async (id: number, kind: string, title: string, path = "") => {
    setPanel({ id, kind, title });
    setSelected({});
    setBusy(true);
    try {
      const data = await ConnectAPI.browse(id, path);
      setBrowse(data);
    } catch (e: any) {
      setMsg(e.message);
      setPanel(null);
      setBrowse(null);
    } finally {
      setBusy(false);
    }
  };

  const goPath = async (path: string) => {
    if (!panel) return;
    setBusy(true);
    try {
      const data = await ConnectAPI.browse(panel.id, path);
      setBrowse(data);
      if (!path) setSelected({});
    } catch (e: any) {
      setMsg(e.message);
    } finally {
      setBusy(false);
    }
  };

  const toggleFile = (path: string) => {
    setSelected((prev) => ({ ...prev, [path]: !prev[path] }));
  };

  const toggleAllFiles = () => {
    if (!browse?.files?.length) return;
    const allOn = browse.files.every((f) => selected[f.path]);
    const next: Record<string, boolean> = { ...selected };
    for (const f of browse.files) next[f.path] = !allOn;
    setSelected(next);
  };

  const syncSelected = async () => {
    if (!panel) return;
    const paths = Object.keys(selected).filter((p) => selected[p]);
    if (!paths.length) {
      setMsg(t(lang, "selectFilesFirst"));
      return;
    }
    setBusy(true);
    try {
      const r = await ConnectAPI.sync(panel.id, paths);
      setMsg(`${t(lang, "syncedIntoRag")} ${r.synced}`);
      await load();
      setPanel(null);
      setBrowse(null);
      setSelected({});
    } catch (e: any) {
      setMsg(e.message);
    } finally {
      setBusy(false);
    }
  };

  const closePanel = () => {
    setPanel(null);
    setBrowse(null);
    setSelected({});
  };

  const selectedCount = Object.values(selected).filter(Boolean).length;

  return (
    <>
      <div className="eyebrow">{t(lang, "connectorsEyebrow")}</div>
      <h1 className="mark" style={{ fontSize: 32 }}>
        {t(lang, "connectors")}
      </h1>
      <p className="muted">{t(lang, "connectorsBlurb")}</p>
      {msg && <p className="pill ok">{msg}</p>}
      <div className="grid cards-3" style={{ marginTop: 16 }}>
        {SOURCES.map((src) => {
          const row = rowFor(src.kind);
          return (
            <div className="card connector-card" key={src.kind} data-demo={`connector-${src.kind}`}>
              <div className="brand" style={{ padding: 0, marginBottom: 10 }}>
                <div className={`sigil src-${src.kind}`}>{src.mark}</div>
                <div>
                  <div className="mark">{src.title}</div>
                  <div className="eyebrow">{row?.status || t(lang, "notConnected")}</div>
                </div>
              </div>
              <p className="muted" style={{ minHeight: 48 }}>
                {src.blurb}
              </p>
              <ul className="file-list">
                {(row?.files || []).slice(0, 4).map((f: string) => (
                  <li key={f} className="mono">
                    {f}
                  </li>
                ))}
              </ul>
              <div className="row-actions">
                {!row && (
                  <button className="btn primary" data-demo={`connect-${src.kind}`} onClick={() => connect(src.kind, src.title)}>
                    {t(lang, "connect")}
                  </button>
                )}
                {row && (
                  <>
                    <button
                      className="btn primary"
                      data-demo={`browse-${src.kind}`}
                      onClick={() => openBrowse(row.id, src.kind, src.title)}
                    >
                      {t(lang, "browse")}
                    </button>
                    <button
                      className="btn"
                      data-demo={`sync-${src.kind}`}
                      title={t(lang, "browseFirstHint")}
                      onClick={() => openBrowse(row.id, src.kind, src.title)}
                    >
                      {t(lang, "syncIntoRag")}
                    </button>
                  </>
                )}
              </div>
            </div>
          );
        })}
        <div className="card connector-card" data-demo="connector-ollama">
          <div className="brand" style={{ padding: 0, marginBottom: 10 }}>
            <div className="sigil src-ollama">Ol</div>
            <div>
              <div className="mark">Ollama (local models)</div>
              <div className="eyebrow">{ollama?.up ? t(lang, "connected") : t(lang, "offline")}</div>
            </div>
          </div>
          <p className="muted" style={{ minHeight: 48 }}>
            {ollama?.up
              ? `Talking to ${ollama.url}. ${ollama.models?.length ? "Pulled: " + ollama.models.join(", ") : "No models yet — run ollama pull llama3.2"}`
              : `Not reachable at ${ollama?.url || "http://127.0.0.1:11434"}. Start with ollama serve, then bind a model.`}
          </p>
          {ollama?.up && (
            <div className="field" style={{ marginBottom: 10 }}>
              <select value={pick} onChange={(e) => setPick(e.target.value)}>
                {(ollama.models || []).map((m: string) => (
                  <option key={m}>{m}</option>
                ))}
              </select>
            </div>
          )}
          <div className="row-actions">
            <button className="btn" onClick={() => AgentAPI.ollama().then(setOllama)}>
              Refresh
            </button>
            {ollama?.up && (
              <button
                className="btn primary"
                data-demo="bind-ollama"
                onClick={async () => {
                  try {
                    const r = await AgentAPI.useOllama(pick);
                    setMsg(`Bound ${r.model} to form builder, agents, and flows`);
                    load();
                  } catch (e: any) {
                    setMsg(e.message);
                  }
                }}
              >
                Use this model
              </button>
            )}
          </div>
        </div>
      </div>

      {panel && (
        <div className="browse-mask" onClick={closePanel} data-demo="browse-mask">
          <div
            className="browse-panel"
            role="dialog"
            aria-modal="true"
            aria-label={t(lang, "browseSources")}
            data-demo={`browse-panel-${panel.kind}`}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="browse-head">
              <div>
                <div className="eyebrow">{panel.title}</div>
                <h2 className="mark" style={{ fontSize: 22, margin: 0 }}>
                  {t(lang, "browseSources")}
                </h2>
                {browse?.label && (
                  <p className={`pill ${browse.demo ? "warn" : "ok"}`} style={{ marginTop: 8 }}>
                    {browse.demo ? t(lang, "demoCatalog") : browse.label}
                  </p>
                )}
              </div>
              <button className="btn" type="button" onClick={closePanel}>
                {t(lang, "close")}
              </button>
            </div>

            <nav className="browse-crumbs" aria-label="Breadcrumb">
              <button type="button" className="crumb" onClick={() => goPath("")} disabled={busy}>
                {t(lang, "sources")}
              </button>
              {(browse?.breadcrumbs || []).map((c) => (
                <span key={c.path} className="crumb-wrap">
                  <span className="crumb-sep" aria-hidden>
                    ›
                  </span>
                  <button type="button" className="crumb" onClick={() => goPath(c.path)} disabled={busy}>
                    {c.name}
                  </button>
                </span>
              ))}
            </nav>

            <div className="browse-body">
              {busy && !browse && <p className="muted">{t(lang, "loading")}</p>}

              {browse && browse.sources.length > 0 && (
                <ul className="browse-list">
                  {browse.sources.map((s) => (
                    <li key={s.path}>
                      <button type="button" className="browse-row" data-demo="browse-source" onClick={() => goPath(s.path)}>
                        <span className="browse-kind">{t(lang, "source")}</span>
                        <span>{s.name}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}

              {browse && browse.folders.length > 0 && (
                <ul className="browse-list">
                  {browse.folders.map((f) => (
                    <li key={f.path}>
                      <button
                        type="button"
                        className="browse-row"
                        data-demo="browse-folder"
                        onClick={() => goPath(f.path)}
                      >
                        <span className="browse-kind">{t(lang, "folder")}</span>
                        <span>{f.name}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}

              {browse && browse.files.length > 0 && (
                <>
                  <div className="browse-files-toolbar">
                    <button type="button" className="btn" onClick={toggleAllFiles}>
                      {t(lang, "selectAll")}
                    </button>
                    <span className="muted">
                      {selectedCount} {t(lang, "selected")}
                    </span>
                  </div>
                  <ul className="browse-list files">
                    {browse.files.map((f) => (
                      <li key={f.path}>
                        <label className="browse-file" data-demo="browse-file">
                          <input type="checkbox" checked={!!selected[f.path]} onChange={() => toggleFile(f.path)} />
                          <span className="mono">{f.name}</span>
                        </label>
                      </li>
                    ))}
                  </ul>
                </>
              )}

              {browse && !browse.sources.length && !browse.folders.length && !browse.files.length && (
                <p className="muted">{t(lang, "emptyFolder")}</p>
              )}
            </div>

            <div className="browse-foot">
              <button className="btn" type="button" onClick={closePanel}>
                {t(lang, "cancel")}
              </button>
              <button
                className="btn primary"
                type="button"
                data-demo="sync-selected"
                disabled={busy || selectedCount === 0}
                onClick={syncSelected}
              >
                {t(lang, "syncSelected")} ({selectedCount})
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
