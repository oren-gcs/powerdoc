import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { SearchAPI } from "../api";
import { t } from "../i18n";

type Hit = {
  kind: string;
  id: number;
  name: string;
  subtitle?: string;
  href: string;
};

const KIND_KEY: Record<string, string> = {
  form: "searchKindForm",
  workflow: "searchKindWorkflow",
  process: "searchKindProcess",
  document: "searchKindDocument",
  connector: "searchKindConnector",
};

export default function DeskSearch({ lang }: { lang: string }) {
  const nav = useNavigate();
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<Hit[]>([]);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  const timer = useRef<number | null>(null);

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (!box.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  useEffect(() => {
    if (timer.current) window.clearTimeout(timer.current);
    const needle = q.trim();
    if (needle.length < 1) {
      setHits([]);
      setBusy(false);
      return;
    }
    setBusy(true);
    timer.current = window.setTimeout(() => {
      SearchAPI.query(needle)
        .then((r) => {
          setHits(r.results || []);
          setOpen(true);
        })
        .catch(() => setHits([]))
        .finally(() => setBusy(false));
    }, 220);
    return () => {
      if (timer.current) window.clearTimeout(timer.current);
    };
  }, [q]);

  const go = (href: string) => {
    setOpen(false);
    setQ("");
    setHits([]);
    nav(href);
  };

  return (
    <div className="desk-search" ref={box}>
      <label className="desk-search-field">
        <span className="sr-only">{t(lang, "search")}</span>
        <svg className="desk-search-ico" viewBox="0 0 24 24" aria-hidden>
          <circle cx="11" cy="11" r="7" fill="none" stroke="currentColor" strokeWidth="1.6" />
          <path d="M16.5 16.5L21 21" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
        </svg>
        <input
          type="search"
          value={q}
          placeholder={t(lang, "searchPlaceholder")}
          autoComplete="off"
          onChange={(e) => setQ(e.target.value)}
          onFocus={() => hits.length && setOpen(true)}
          onKeyDown={(e) => {
            if (e.key === "Escape") {
              setOpen(false);
              (e.target as HTMLInputElement).blur();
            }
            if (e.key === "Enter" && hits[0]) {
              e.preventDefault();
              go(hits[0].href);
            }
          }}
        />
      </label>
      {open && q.trim() && (
        <div className="desk-search-drop" role="listbox">
          {busy && !hits.length && <div className="desk-search-empty muted">{t(lang, "searching")}</div>}
          {!busy && !hits.length && <div className="desk-search-empty muted">{t(lang, "searchEmpty")}</div>}
          {hits.map((h) => (
            <button
              key={`${h.kind}-${h.id}`}
              type="button"
              className="desk-search-hit"
              role="option"
              onClick={() => go(h.href)}
            >
              <span className="pill">{t(lang, KIND_KEY[h.kind] || "search")}</span>
              <span className="desk-search-hit-text">
                <span className="desk-search-name">{h.name}</span>
                {h.subtitle && <span className="muted desk-search-sub">{h.subtitle}</span>}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
