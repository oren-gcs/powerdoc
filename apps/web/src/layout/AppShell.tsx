import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { LANGS, dirFor, t } from "../i18n";

const groups = [
  {
    key: "work",
    items: [
      ["overview", "/app"],
      ["documents", "/app/documents"],
      ["forms", "/app/forms"],
      ["builder", "/app/forms/new"],
      ["flows", "/app/workflows"],
      ["automations", "/app/automations"],
    ],
  },
  {
    key: "people",
    items: [
      ["manage", "/app/manage"],
      ["inbox", "/app/inbox"],
      ["agents", "/app/agents"],
    ],
  },
  {
    key: "control",
    items: [
      ["connectors", "/app/connectors"],
      ["analytics", "/app/analytics"],
      ["admin", "/app/admin"],
    ],
  },
];

const ICON: Record<string, string> = {
  overview: "M3 3h8v8H3zM13 3h8v5h-8zM13 10h8v11h-8zM3 13h8v8H3z",
  documents: "M6 2h9l5 5v15H6zM15 2v5h5",
  forms: "M5 3h14v18H5zM8 8h8M8 12h8M8 16h5",
  builder: "M11 4h2v16h-2zM4 11h16v2H4z",
  flows: "M4 6h10v3H4zM10 15h10v3H10zM14 9v6",
  automations: "M13 2L4 14h7l-1 8 10-14h-7z",
  manage: "M4 6h16v3H4zM4 11h16v3H4zM4 16h16v3H4z",
  inbox: "M3 6h18v12H3zM3 6l9 7 9-7",
  agents: "M12 3l2.4 6.6L21 12l-6.6 2.4L12 21l-2.4-6.6L3 12l6.6-2.4z",
  connectors: "M7 7h4v4H7zM13 13h4v4h-4zM11 9l4 4",
  analytics: "M5 19V9h3v10zM10.5 19V5h3v14zM16 19v-7h3v7z",
  admin: "M12 2l8 4v6c0 5-3.4 8.4-8 10-4.6-1.6-8-5-8-10V6z",
};

function Icon({ name }: { name: string }) {
  return (
    <svg className="nav-ico" viewBox="0 0 24 24" aria-hidden>
      <path d={ICON[name] || ICON.overview} />
    </svg>
  );
}

export default function AppShell() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const [lang, setLang] = useState(localStorage.getItem("docflow.lang") || user?.locale || "en");
  const [open, setOpen] = useState(() => localStorage.getItem("docflow.rail") !== "collapsed");
  const [narrow, setNarrow] = useState(false);
  const [drawer, setDrawer] = useState(false);

  useEffect(() => {
    document.documentElement.lang = lang;
    document.documentElement.dir = dirFor(lang);
    localStorage.setItem("docflow.lang", lang);
  }, [lang]);

  useEffect(() => {
    localStorage.setItem("docflow.rail", open ? "open" : "collapsed");
  }, [open]);

  useEffect(() => {
    const mq = window.matchMedia("(max-width: 980px)");
    const apply = () => setNarrow(mq.matches);
    apply();
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, []);

  const expanded = narrow ? true : open;

  const changeLang = async (code: string) => {
    setLang(code);
    try {
      await api(`/api/v1/auth/me?locale=${code}`, { method: "PATCH" });
    } catch {
      /* locale still applies locally */
    }
  };

  return (
    <div className={`shell ${expanded ? "" : "collapsed"} ${drawer ? "nav-open" : ""}`}>
      <header className="mobile-bar">
        <button className="nav-fab" type="button" aria-label={t(lang, "menu")} onClick={() => setDrawer(true)}>
          <span />
          <span />
          <span />
        </button>
        <div className="brand" onClick={() => nav("/app")}>
          <div className="sigil">Df</div>
          <div className="mark">DocFlow</div>
        </div>
      </header>
      {drawer && <div className="nav-mask" onClick={() => setDrawer(false)} />}
      <aside className="rail" aria-label={t(lang, "nav")}>
        <div className="brand" onClick={() => nav("/app")} role="button" tabIndex={0}>
          <div className="sigil">Df</div>
          {expanded && (
            <div>
              <div className="mark">DocFlow</div>
              <div className="eyebrow">{t(lang, "desk")}</div>
            </div>
          )}
        </div>
        {!narrow && (
          <button className="rail-toggle" type="button" onClick={() => setOpen((v) => !v)} aria-label="Collapse navigation">
            {open ? "⟨" : "⟩"}
          </button>
        )}
        <nav>
          {groups.map((g) => (
            <div key={g.key} className="nav-group">
              {expanded && <div className="nav-label">{t(lang, g.key)}</div>}
              {g.items.map(([key, to]) => (
                <NavLink
                  key={to}
                  to={to}
                  end={to === "/app"}
                  title={t(lang, key)}
                  onClick={() => setDrawer(false)}
                  className={({ isActive }) => (isActive ? "active" : "")}
                >
                  <Icon name={key} />
                  {expanded && <span>{t(lang, key)}</span>}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
        <div className="rail-foot">
          <label className="field">
            {expanded && <span className="eyebrow">{t(lang, "language")}</span>}
            <select value={lang} onChange={(e) => changeLang(e.target.value)} aria-label={t(lang, "language")}>
              {LANGS.map((l) => (
                <option key={l.code} value={l.code}>
                  {l.native}
                </option>
              ))}
            </select>
          </label>
          <div className="who">
            <div className="who-avatar">{user?.full_name?.slice(0, 1)}</div>
            {expanded && (
              <div>
                <div>{user?.full_name}</div>
                <div className="mono dim">{user?.role}</div>
              </div>
            )}
          </div>
          <button className="btn" type="button" onClick={logout}>
            {expanded ? t(lang, "signOut") : "×"}
          </button>
        </div>
      </aside>
      <div className="workspace">
        <Outlet />
      </div>
    </div>
  );
}
