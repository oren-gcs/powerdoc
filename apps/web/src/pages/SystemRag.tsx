import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AdminAPI } from "../api";
import { useAuth } from "../auth";
import { t, useDeskLang } from "../i18n";

export default function SystemRag() {
  const lang = useDeskLang();
  const { user } = useAuth();
  const [sources, setSources] = useState<any[]>([]);
  const [chunks, setChunks] = useState<any[]>([]);
  const [settings, setSettings] = useState<any>(null);
  const [q, setQ] = useState("");
  const [tagFilter, setTagFilter] = useState("");
  const [tagDraft, setTagDraft] = useState<Record<number, string>>({});
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");

  const load = async () => {
    setErr("");
    try {
      const [src, ch, st] = await Promise.all([
        AdminAPI.ragSources(),
        AdminAPI.ragChunks({ q: q || undefined, tag: tagFilter || undefined }),
        AdminAPI.ragSettings(),
      ]);
      setSources(src.sources || []);
      setChunks(ch.chunks || []);
      setSettings(st);
    } catch (e: any) {
      setErr(e.message || "Failed to load");
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (user?.role !== "platform_admin") {
    return (
      <>
        <div className="eyebrow">{t(lang, "systemRagEyebrow")}</div>
        <h1 className="mark" style={{ fontSize: 32 }}>
          {t(lang, "systemRag")}
        </h1>
        <p className="pill bad">{t(lang, "systemRagForbidden")}</p>
        <p className="muted">
          <Link to="/app/connectors">{t(lang, "systemRagOpenConnectors")}</Link>
        </p>
      </>
    );
  }

  const search = async (e: FormEvent) => {
    e.preventDefault();
    await load();
  };

  const addTag = async (chunkId: number, existing: string[]) => {
    const raw = (tagDraft[chunkId] || "").trim();
    if (!raw) return;
    const next = Array.from(new Set([...existing, raw.toLowerCase()]));
    await AdminAPI.ragPatchTags(chunkId, next);
    setTagDraft((d) => ({ ...d, [chunkId]: "" }));
    setMsg(t(lang, "systemRagTagsSaved"));
    load();
  };

  const removeTag = async (chunkId: number, existing: string[], tag: string) => {
    const next = existing.filter((x) => x !== tag);
    await AdminAPI.ragPatchTags(chunkId, next);
    setMsg(t(lang, "systemRagTagsSaved"));
    load();
  };

  return (
    <>
      <div className="eyebrow">{t(lang, "systemRagEyebrow")}</div>
      <h1 className="mark" style={{ fontSize: 32 }}>
        {t(lang, "systemRag")}
      </h1>
      <p className="muted">{t(lang, "systemRagBlurb")}</p>
      <p className="muted">
        <Link to="/app/connectors">{t(lang, "systemRagOpenConnectors")}</Link>
        {" · "}
        <Link to="/app/admin">{t(lang, "admin")}</Link>
      </p>
      {err && <p className="pill bad">{err}</p>}
      {msg && <p className="pill ok">{msg}</p>}

      <div className="split" style={{ marginTop: 16 }}>
        <div className="card">
          <div className="eyebrow">{t(lang, "systemRagSources")}</div>
          <table className="table">
            <thead>
              <tr>
                <th>{t(lang, "name")}</th>
                <th>{t(lang, "systemRagTenant")}</th>
                <th>{t(lang, "status")}</th>
                <th>{t(lang, "systemRagChunks")}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {sources.map((s, i) => (
                <tr key={`${s.kind}-${s.id ?? "lib"}-${i}`}>
                  <td>
                    {s.name}
                    <div className="mono dim">{s.kind}</div>
                  </td>
                  <td className="muted">{s.tenant_name}</td>
                  <td>
                    <span className={`pill ${s.enabled && s.kind_enabled ? "ok" : ""}`}>
                      {s.enabled ? (s.kind_enabled ? t(lang, "connected") : t(lang, "systemRagKindOff")) : t(lang, "systemRagDisabled")}
                    </span>
                  </td>
                  <td className="mono">{s.chunk_count}</td>
                  <td>
                    {s.id != null && (
                      <button
                        className="btn"
                        type="button"
                        onClick={() => AdminAPI.ragToggleSource(s.id).then(load)}
                      >
                        {s.enabled ? t(lang, "systemRagDisable") : t(lang, "systemRagEnable")}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {!sources.length && (
                <tr>
                  <td colSpan={5} className="muted">
                    {t(lang, "systemRagNoSources")}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="card">
          <div className="eyebrow">{t(lang, "systemRagOptions")}</div>
          {settings?.min_score && (
            <div style={{ marginBottom: 12 }}>
              <div className="muted">{t(lang, "systemRagMinScore")}</div>
              <div className="mono">
                default={settings.min_score.default} · compose={settings.min_score.form_compose}
              </div>
              <p className="muted" style={{ marginTop: 6, fontSize: 13 }}>
                {settings.min_score.notes}
              </p>
            </div>
          )}
          {(settings?.flags || []).map((f: any) => (
            <div key={f.key} style={{ display: "flex", justifyContent: "space-between", gap: 12, padding: "8px 0", borderTop: "1px solid var(--line, #e8e4dc)" }}>
              <div>
                <div className="mono">{f.key}</div>
                <div className="muted" style={{ fontSize: 13 }}>
                  {f.description}
                </div>
              </div>
              <button
                className={`btn ${f.enabled ? "primary" : ""}`}
                type="button"
                onClick={() => AdminAPI.toggleFlag(f.key).then(load)}
              >
                {f.enabled ? t(lang, "systemRagOn") : t(lang, "systemRagOff")}
              </button>
            </div>
          ))}
        </div>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <div className="eyebrow">{t(lang, "systemRagLibrary")}</div>
        <form onSubmit={search} className="row-actions" style={{ marginBottom: 12, flexWrap: "wrap" }}>
          <input
            placeholder={t(lang, "search")}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            style={{ minWidth: 180 }}
          />
          <input
            placeholder={t(lang, "systemRagFilterTag")}
            value={tagFilter}
            onChange={(e) => setTagFilter(e.target.value)}
            style={{ minWidth: 140 }}
          />
          <button className="btn primary" type="submit">
            {t(lang, "search")}
          </button>
        </form>
        <table className="table">
          <thead>
            <tr>
              <th>{t(lang, "systemRagChunk")}</th>
              <th>{t(lang, "systemRagTenant")}</th>
              <th>{t(lang, "systemRagTags")}</th>
            </tr>
          </thead>
          <tbody>
            {chunks.map((c) => (
              <tr key={c.id}>
                <td>
                  <div>{c.title || c.source_id}</div>
                  <div className="mono dim">
                    {c.source_type} · #{c.id}
                  </div>
                  <div className="muted" style={{ fontSize: 13, marginTop: 4 }}>
                    {c.text_preview}
                  </div>
                </td>
                <td className="muted">{c.tenant_name}</td>
                <td>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 8 }}>
                    {(c.tags || []).map((tag: string) => (
                      <button
                        key={tag}
                        type="button"
                        className="pill ok"
                        style={{ cursor: "pointer" }}
                        title={t(lang, "removeChoice")}
                        onClick={() => removeTag(c.id, c.tags || [], tag)}
                      >
                        {tag} ×
                      </button>
                    ))}
                    {!(c.tags || []).length && <span className="muted">—</span>}
                  </div>
                  <div className="row-actions">
                    <input
                      placeholder={t(lang, "systemRagAddTag")}
                      value={tagDraft[c.id] || ""}
                      onChange={(e) => setTagDraft((d) => ({ ...d, [c.id]: e.target.value }))}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          e.preventDefault();
                          addTag(c.id, c.tags || []);
                        }
                      }}
                      style={{ minWidth: 120 }}
                    />
                    <button className="btn" type="button" onClick={() => addTag(c.id, c.tags || [])}>
                      {t(lang, "systemRagAddTag")}
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {!chunks.length && (
              <tr>
                <td colSpan={3} className="muted">
                  {t(lang, "systemRagNoChunks")}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}
