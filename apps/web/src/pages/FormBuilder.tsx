import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { FormsAPI, OrgAPI } from "../api";
import FormExit from "../components/FormExit";
import { dirFor, t } from "../i18n";

const TYPES = [
  "text",
  "textarea",
  "number",
  "date",
  "email",
  "phone",
  "dropdown",
  "radio",
  "yesno",
  "signature",
  "file",
  "images",
  "heading",
] as const;

type FieldType = (typeof TYPES)[number];

const CHOICE_TYPES = new Set<FieldType>(["dropdown", "radio"]);
const PLACEHOLDER_TYPES = new Set<FieldType>(["text", "textarea", "number", "email", "phone", "date", "dropdown"]);
const DEFAULT_TYPES = new Set<FieldType>(["text", "textarea", "number", "email", "phone", "date", "dropdown", "radio", "yesno"]);
const UPLOAD_TYPES = new Set<FieldType>(["file", "images"]);
const DEFAULT_FILE_ACCEPT = ["pdf", "png", "jpg", "jpeg", "webp", "gif", "txt", "docx"];
const DEFAULT_IMAGE_ACCEPT = ["png", "jpg", "jpeg", "webp", "gif"];
const AUTO_BY_TYPE: Partial<Record<FieldType, { value: string; labelKey: string }[]>> = {
  date: [
    { value: "", labelKey: "none" },
    { value: "today", labelKey: "today" },
  ],
};

function nid() {
  return Math.random().toString(16).slice(2, 10);
}

/** Ensure every field has a unique id and stable shape for paper-row ↔ inspector sync. */
function normalizeFields(list: any[] | null | undefined): any[] {
  const seen = new Set<string>();
  return (list || []).map((raw) => {
    const f = raw && typeof raw === "object" ? raw : {};
    let id = String(f.id || "").trim() || nid();
    while (seen.has(id)) id = nid();
    seen.add(id);
    const type = (TYPES as readonly string[]).includes(String(f.type)) ? String(f.type) : "text";
    const options = Array.isArray(f.options)
      ? f.options.map((o: unknown) => String(o)).filter((o: string) => o.length > 0)
      : [];
    return normalizeField(
      {
        ...f,
        id,
        label: f.label == null ? "" : String(f.label),
        required: !!f.required,
        options,
        help: f.help == null ? "" : String(f.help),
        placeholder: f.placeholder == null ? "" : String(f.placeholder),
        auto: f.auto == null ? "" : String(f.auto),
        default: f.default == null ? "" : String(f.default),
      },
      type as FieldType
    );
  });
}

function parseRecipients(raw: string): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const part of raw.split(/[,;\s]+/)) {
    const email = part.trim().toLowerCase();
    if (!email || !email.includes("@") || seen.has(email)) continue;
    seen.add(email);
    out.push(email);
  }
  return out;
}

function fieldOptions(field: { options?: string[] }): string[] {
  return (field.options || []).map(String).map((s) => s.trim()).filter(Boolean);
}

function selectDisplayValue(
  field: { placeholder?: string; options?: string[]; default?: string },
  language: string
): string {
  const def = String(field.default || "").trim();
  if (def) return def;
  const ph = String(field.placeholder || "").trim();
  if (ph) return ph;
  const opts = fieldOptions(field);
  if (opts.length) return opts[0];
  return t(language, "noChoices");
}

const INPUT_LIKE = new Set<FieldType>(["text", "textarea", "number", "email", "phone", "date"]);
const SELECT_LIKE = new Set<FieldType>(["dropdown", "yesno"]);
const CONTROL_IMPLIED_TYPES = new Set<FieldType>(["email", "phone", "signature", "file", "images"]);

function isUselessDefaultLabel(label: string): boolean {
  const trimmed = String(label || "").trim();
  if (!trimmed) return true;
  for (const code of ["en", "he", "ar", "es", "fr"]) {
    if (trimmed === t(code, "newField")) return true;
  }
  return false;
}

function defaultInputPlaceholder(type: FieldType, language: string): string {
  if (type === "email") return t(language, "phEmail");
  if (type === "phone") return t(language, "phPhone");
  if (type === "number") return "0";
  if (type === "date") return "YYYY-MM-DD";
  return "";
}

function normalizeAccept(raw: unknown, nextType: FieldType): string[] {
  const fallback = nextType === "images" ? DEFAULT_IMAGE_ACCEPT : DEFAULT_FILE_ACCEPT;
  if (!Array.isArray(raw)) return [...fallback];
  const cleaned = raw
    .map((x) => String(x || "").trim().toLowerCase().replace(/^\./, ""))
    .filter(Boolean);
  return cleaned.length ? cleaned : [...fallback];
}

function normalizeField(field: Record<string, unknown>, nextType: FieldType): Record<string, unknown> {
  const out: Record<string, unknown> = {
    ...field,
    type: nextType,
    help: field.help ?? "",
    placeholder: field.placeholder ?? "",
    auto: field.auto ?? "",
    default: field.default ?? "",
    options: Array.isArray(field.options) ? field.options : [],
  };
  if (CHOICE_TYPES.has(nextType)) {
    const opts = (out.options as string[]).filter(Boolean);
    out.options = opts.length ? opts : ["A", "B"];
  } else if (nextType === "yesno") {
    out.options = ["yes", "no"];
  } else {
    out.options = [];
  }
  if (nextType === "heading") {
    out.required = false;
    out.auto = "";
    out.placeholder = "";
    out.default = "";
  }
  if (nextType === "signature") {
    out.required = true;
    out.auto = "";
    out.placeholder = "";
    out.default = "";
  }
  if (UPLOAD_TYPES.has(nextType)) {
    out.auto = "";
    out.placeholder = "";
    out.default = "";
    out.accept = normalizeAccept(out.accept, nextType);
    const maxRaw = Number(out.max_count);
    if (nextType === "file") {
      out.max_count = 1;
    } else {
      out.max_count = Number.isFinite(maxRaw) && maxRaw >= 1 ? Math.min(Math.floor(maxRaw), 10) : 5;
    }
  } else {
    delete out.accept;
    delete out.max_count;
  }
  if (!AUTO_BY_TYPE[nextType]) out.auto = "";
  if (!PLACEHOLDER_TYPES.has(nextType)) out.placeholder = "";
  if (!DEFAULT_TYPES.has(nextType)) out.default = "";
  return out;
}

type ChatMsg = {
  role: "user" | "assistant";
  text: string;
  provider?: string;
  knowledge?: { applied?: boolean; href?: string; also?: string; reason?: string; action?: string };
  unclear?: string[];
};

type DeskUser = { id: number; email: string; full_name?: string; role?: string };

export default function FormBuilder() {
  const { id } = useParams();
  const nav = useNavigate();
  const [name, setName] = useState("Untitled form");
  const [language, setLanguage] = useState(localStorage.getItem("docflow.lang") || "en");
  const [topic, setTopic] = useState("");
  const [description, setDescription] = useState("");
  const [prompt, setPrompt] = useState(
    "day summery to students , date automatic , rate today class, signature mandatory, email by user , did the student was in class, which topic was best explained"
  );
  const [fields, setFields] = useState<any[]>([]);
  const [recipientsText, setRecipientsText] = useState("");
  const [deskUsers, setDeskUsers] = useState<DeskUser[]>([]);
  const [sel, setSel] = useState(0);
  const [formId, setFormId] = useState<number | null>(id ? Number(id) : null);
  const [msg, setMsg] = useState("");
  const [share, setShare] = useState("");
  const [recipientLinks, setRecipientLinks] = useState<
    { email: string; url?: string | null; token?: string | null; status?: string }[]
  >([]);
  const [busy, setBusy] = useState(false);
  const [thread, setThread] = useState<ChatMsg[]>([]);
  const [locked, setLocked] = useState(false);
  const [archived, setArchived] = useState(false);
  const [submissionCount, setSubmissionCount] = useState(0);
  const [archiveOpen, setArchiveOpen] = useState(false);

  const recipients = useMemo(() => parseRecipients(recipientsText), [recipientsText]);

  const recipientLabels = useMemo(() => {
    const byEmail = new Map(
      deskUsers.map((u) => [(u.email || "").toLowerCase(), (u.full_name || "").trim()])
    );
    return recipients.map((email) => {
      const fullName = byEmail.get(email) || "";
      return fullName ? `${fullName} · ${email}` : email;
    });
  }, [recipients, deskUsers]);

  const selected = fields[sel];

  useEffect(() => {
    OrgAPI.tree()
      .then((tree) => setDeskUsers(tree.users || []))
      .catch(() => setDeskUsers([]));
  }, []);

  useEffect(() => {
    if (!id) return;
    FormsAPI.get(Number(id)).then((f) => {
      setName(f.name);
      setLanguage(f.language);
      setTopic(f.topic || "");
      setDescription(f.description || "");
      setPrompt(f.description || "");
      const next = normalizeFields(f.fields || []);
      setFields(next);
      setRecipientsText((f.recipients || []).join(", "));
      setFormId(f.id);
      setLocked(!!f.locked);
      setArchived(!!f.archived);
      setSubmissionCount(f.submission_count || 0);
      setSel(0);
      if (f.share_url) setShare(f.share_url);
      else setShare("");
      setRecipientLinks(f.recipient_links || []);
    });
  }, [id]);

  const frozen = locked || archived;

  const move = (from: number, to: number) => {
    if (frozen) return;
    setFields((prev) => {
      if (to < 0 || to >= prev.length) return prev;
      const next = prev.slice();
      const [item] = next.splice(from, 1);
      next.splice(to, 0, item);
      return next;
    });
    setSel(to);
  };

  const remove = (index: number) => {
    if (frozen) return;
    const label = fields[index]?.label || t(language, "lineN", { n: index + 1 });
    if (!window.confirm(t(language, "deleteFieldConfirm", { label }))) return;
    setFields((prev) => {
      const next = prev.slice();
      next.splice(index, 1);
      return next;
    });
    setSel((prev) => {
      const remaining = fields.length - 1;
      if (remaining <= 0) return 0;
      if (prev > index) return prev - 1;
      if (prev === index) return Math.min(index, remaining - 1);
      return prev;
    });
  };

  const patchSelected = (patch: Record<string, unknown>) => {
    if (frozen) return;
    setFields((prev) => {
      if (sel < 0 || sel >= prev.length) return prev;
      const next = prev.slice();
      next[sel] = { ...next[sel], ...patch };
      return next;
    });
  };

  const setSelectedOptions = (options: string[]) => {
    if (frozen) return;
    setFields((prev) => {
      if (sel < 0 || sel >= prev.length) return prev;
      const next = prev.slice();
      const cur = next[sel];
      const defaultValue = String(cur.default || "");
      const keepDefault = defaultValue && options.includes(defaultValue) ? defaultValue : "";
      next[sel] = { ...cur, options, default: keepDefault };
      return next;
    });
  };

  const updateChoiceAt = (index: number, value: string) => {
    const opts = Array.isArray(selected?.options) ? [...selected.options] : [];
    opts[index] = value;
    setSelectedOptions(opts);
  };

  const removeChoiceAt = (index: number) => {
    const opts = Array.isArray(selected?.options) ? selected.options.slice() : [];
    opts.splice(index, 1);
    setSelectedOptions(opts);
  };

  const addChoice = () => {
    const opts = Array.isArray(selected?.options) ? [...selected.options] : [];
    opts.push("");
    setSelectedOptions(opts);
  };

  const changeSelectedType = (type: FieldType) => {
    if (frozen) return;
    setFields((prev) => {
      if (sel < 0 || sel >= prev.length) return prev;
      const next = prev.slice();
      next[sel] = normalizeField(next[sel], type);
      return next;
    });
  };

  const add = (type: string) => {
    if (frozen) return;
    const ty = type as FieldType;
    const implied = CONTROL_IMPLIED_TYPES.has(ty);
    const field = normalizeField(
      {
        id: nid(),
        label: ty === "heading" ? t(language, "section") : implied ? "" : t(language, "newField"),
        required: ty === "signature",
        placeholder: ty === "email" || ty === "phone" ? defaultInputPlaceholder(ty, language) : "",
      },
      ty
    );
    setFields((prev) => {
      const next = [...prev, field];
      setSel(next.length - 1);
      return next;
    });
  };

  const toggleDeskUser = (email: string) => {
    if (frozen) return;
    const current = new Set(recipients);
    const key = email.toLowerCase();
    if (current.has(key)) current.delete(key);
    else current.add(key);
    setRecipientsText([...current].join(", "));
  };

  const persist = async () => {
    if (frozen) {
      throw new Error(archived ? "Form is archived" : "Form is locked after the first answer");
    }
    const body = { name, topic, description, language, fields, recipients };
    const f = formId ? await FormsAPI.update(formId, body) : await FormsAPI.create(body);
    setFormId(f.id);
    setTopic(f.topic || "");
    setDescription(f.description || "");
    setRecipientsText((f.recipients || []).join(", "));
    setLocked(!!f.locked);
    setSubmissionCount(f.submission_count || 0);
    setMsg(t(language, "formSaved"));
    if (!id) nav(`/app/forms/${f.id}`, { replace: true });
    return f;
  };

  const save = async () => {
    try {
      await persist();
    } catch (e: any) {
      setMsg(e.message);
    }
  };

  const compose = async () => {
    const asked = prompt.trim();
    if (!asked || busy) return;
    setBusy(true);
    setThread((prev) => [...prev, { role: "user", text: asked }]);
    try {
      const r = await FormsAPI.compose({ prompt: asked, language, use_rag: true });
      setName(r.name);
      if (r.topic) setTopic(r.topic);
      if (r.description) setDescription(r.description);
      else setDescription(asked.slice(0, 400));
      setFields(normalizeFields(r.fields || []));
      setSel(0);
      setThread((prev) => [
        ...prev,
        {
          role: "assistant",
          text: r.reply || "I drafted the form from your chat.",
          provider: r.provider,
          knowledge: r.knowledge,
          unclear: r.unclear,
        },
      ]);
      setMsg(r.provider === "ollama" ? `Drafted with Ollama (${r.model})` : "Drafted from chat");
    } catch (e: any) {
      setThread((prev) => [
        ...prev,
        {
          role: "assistant",
          text: `I could not draft that: ${e.message}. Rephrase, or pick a field type on the left.`,
        },
      ]);
      setMsg(e.message);
    } finally {
      setBusy(false);
    }
  };

  const autoChoices = selected ? AUTO_BY_TYPE[selected.type as FieldType] : undefined;
  const showPlaceholder = selected && PLACEHOLDER_TYPES.has(selected.type as FieldType);
  const showDefault = selected && DEFAULT_TYPES.has(selected.type as FieldType);
  const showChoices = selected && CHOICE_TYPES.has(selected.type as FieldType);
  const showUploadOpts = selected && UPLOAD_TYPES.has(selected.type as FieldType);
  const showRequired = selected && selected.type !== "heading";

  return (
    <div className="builder">
      <div className="topbar">
        <div>
          <FormExit fallback="/app/forms" variant="on-dark" />
          <div>
            <div className="eyebrow">{t(language, "builderEyebrow")}</div>
            <input
              className="ghost-title"
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={frozen}
              readOnly={frozen}
              aria-label={t(language, "formName")}
            />
            {locked && (
              <p className="muted" style={{ marginTop: 4 }}>
                <span className="pill warn" data-demo="locked-badge">
                  {t(language, "locked")} · {submissionCount} {submissionCount === 1 ? t(language, "submission") : t(language, "submissions")}
                </span>{" "}
                {t(language, "lockedFrozen")}
                {archived && (
                  <>
                    {" "}
                    <span className="pill" data-demo="archived-badge">
                      {t(language, "archived")}
                    </span>
                  </>
                )}
              </p>
            )}
            {!locked && archived && (
              <p className="muted" style={{ marginTop: 4 }}>
                <span className="pill" data-demo="archived-badge">
                  {t(language, "archived")}
                </span>{" "}
                {t(language, "archivedHint")}
              </p>
            )}
          </div>
        </div>
        <div className="row-actions">
          {locked && formId && (
            <button className="btn primary" data-demo="open-answered" onClick={() => nav(`/app/forms/${formId}/answered`)}>
              {t(language, "answeredFolder")}
            </button>
          )}
          {formId && (
            <button
              className="btn"
              data-demo="copy-form"
              onClick={async () => {
                try {
                  const copy = await FormsAPI.copy(formId);
                  setMsg(`${t(language, "copy")}: ${copy.name}`);
                  nav(`/app/forms/${copy.id}`);
                } catch (e: any) {
                  setMsg(e.message);
                }
              }}
            >
              {t(language, "copy")}
            </button>
          )}
          {formId && !archived && (
            <button className="btn" data-demo="archive-form" onClick={() => setArchiveOpen(true)}>
              {t(language, "archive")}
            </button>
          )}
          {formId && archived && (
            <button
              className="btn"
              data-demo="unarchive-form"
              onClick={async () => {
                try {
                  const r = await FormsAPI.unarchive(formId);
                  setArchived(!!r.archived);
                  setMsg(t(language, "unarchive"));
                } catch (e: any) {
                  setMsg(e.message);
                }
              }}
            >
              {t(language, "unarchive")}
            </button>
          )}
          <select value={language} onChange={(e) => setLanguage(e.target.value)} disabled={frozen} aria-label={t(language, "language")}>
            <option value="en">English</option>
            <option value="he">עברית</option>
            <option value="ar">العربية</option>
            <option value="es">Español</option>
            <option value="fr">Français</option>
          </select>
          <button className="btn" onClick={save} disabled={frozen}>
            {t(language, "save")}
          </button>
          <button
            className="btn primary"
            data-demo="publish"
            disabled={frozen}
            onClick={async () => {
              try {
                const saved = await persist();
                const live = await FormsAPI.publish(saved.id);
                setShare(live.share_url || "");
                setRecipientLinks(live.recipient_links || []);
                const notified = live.notified || [];
                setMsg(
                  notified.length
                    ? `${t(language, "formAlive")} · ${t(language, "personalLinksReady")}`
                    : `${t(language, "formAlive")} · ${t(language, "openLinkOnlyNoRecipients")}`
                );
              } catch (e: any) {
                setMsg(e.message);
              }
            }}
          >
            {t(language, "makeAlive")}
          </button>
        </div>
      </div>
      {archiveOpen && formId && (
        <div className="card archive-panel" data-demo="archive-panel" style={{ marginBottom: 12 }}>
          <h3 style={{ marginTop: 0 }}>{t(language, "archiveForm")}</h3>
          <p className="muted">{t(language, "archiveHint")}</p>
          <div className="row-actions">
            <button
              className="btn primary"
              data-demo="archive-keep"
              onClick={async () => {
                try {
                  const r = await FormsAPI.archive(formId, true);
                  setArchived(!!r.archived);
                  setArchiveOpen(false);
                  setMsg(t(language, "keepAnswered"));
                } catch (e: any) {
                  setMsg(e.message);
                }
              }}
            >
              {t(language, "keepAnswered")}
            </button>
            <button
              className="btn"
              data-demo="archive-form-only"
              onClick={async () => {
                try {
                  const r = await FormsAPI.archive(formId, false);
                  setArchived(!!r.archived);
                  setArchiveOpen(false);
                  setMsg(t(language, "archiveFormOnly"));
                } catch (e: any) {
                  setMsg(e.message);
                }
              }}
            >
              {t(language, "archiveFormOnly")}
            </button>
            <button className="btn ghost" onClick={() => setArchiveOpen(false)}>
              {t(language, "cancel")}
            </button>
          </div>
        </div>
      )}
      <div className="chatbar">
        <input
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && !frozen && compose()}
          placeholder={t(language, "chatPlaceholder")}
          disabled={frozen}
        />
        <button className="btn primary" data-demo="compose" onClick={compose} disabled={busy || frozen}>
          {busy ? t(language, "listening") : t(language, "draftWithChat")}
        </button>
      </div>
      {thread.length > 0 && (
        <div className="chat-thread" data-demo="chat-reply">
          {thread.map((m, i) => (
            <div key={i} className={`bubble ${m.role}`}>
              <div className="eyebrow">{m.role === "user" ? t(language, "you") : m.provider === "ollama" ? "Ollama" : t(language, "deskChat")}</div>
              <p>{m.text}</p>
              {m.role === "assistant" && m.knowledge && !m.knowledge.applied && (
                <p className="pill warn">
                  {m.knowledge.reason || "No knowledge source applied."}{" "}
                  <a href={m.knowledge.href || "/app/connectors"}>Open Connectors</a>
                  {m.knowledge.also && (
                    <>
                      {" "}
                      · <a href={m.knowledge.also}>Manage folders</a>
                    </>
                  )}
                </p>
              )}
              {m.unclear && m.unclear.length > 0 && (
                <p className="pill">I did not fully understand: {m.unclear.join("; ")}</p>
              )}
            </div>
          ))}
        </div>
      )}
      {msg && (
        <p className="pill ok">
          {msg}{" "}
          {share && !recipientLinks.length ? (
            <a href={share}> {share}</a>
          ) : null}
        </p>
      )}
      {recipientLinks.length > 0 && (
        <div className="card" data-demo="recipient-links" style={{ marginBottom: 12 }}>
          <div className="eyebrow">{t(language, "personalLinks")}</div>
          <p className="muted" style={{ marginTop: 0 }}>
            {t(language, "personalLinksHint")}
          </p>
          <ul className="recipient-link-list" style={{ listStyle: "none", padding: 0, margin: 0 }}>
            {recipientLinks.map((link) => (
              <li
                key={link.email}
                style={{
                  display: "flex",
                  flexWrap: "wrap",
                  gap: 8,
                  alignItems: "center",
                  marginBottom: 8,
                }}
              >
                <span className="mono">{link.email}</span>
                <span className={`pill ${link.status === "submitted" ? "ok" : ""}`}>{link.status || "pending"}</span>
                {link.url ? (
                  <>
                    <a className="btn" href={link.url} target="_blank" rel="noreferrer">
                      {link.url}
                    </a>
                    <button
                      type="button"
                      className="btn"
                      onClick={async () => {
                        try {
                          await navigator.clipboard.writeText(
                            `${window.location.origin}${link.url}${link.email ? `?email=${encodeURIComponent(link.email)}` : ""}`
                          );
                          setMsg(t(language, "linkCopied"));
                        } catch {
                          setMsg(link.url || "");
                        }
                      }}
                    >
                      {t(language, "copyLink")}
                    </button>
                  </>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      )}
      {!recipientLinks.length && share ? (
        <p className="muted" data-demo="open-share-hint">
          {t(language, "openLinkOnlyNoRecipients")}: <a href={share}>{share}</a>
        </p>
      ) : null}
      <div className="card form-options" data-demo="form-recipients">
        <div className="eyebrow">{t(language, "formOptions")}</div>
        <div className="form-options-grid">
          <div className="field">
            <label>{t(language, "topic")}</label>
            <input
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder={t(language, "topicPlaceholder")}
              disabled={frozen}
              readOnly={frozen}
              data-demo="form-topic"
            />
          </div>
          <div className="field">
            <label>{t(language, "description")}</label>
            <input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={t(language, "descriptionPlaceholder")}
              disabled={frozen}
              readOnly={frozen}
              data-demo="form-description"
            />
          </div>
        </div>
        <div className="field">
          <label>{t(language, "sendTo")}</label>
          <input
            value={recipientsText}
            onChange={(e) => setRecipientsText(e.target.value)}
            placeholder={t(language, "recipientsPlaceholder")}
            aria-label={t(language, "sendTo")}
            disabled={frozen}
            readOnly={frozen}
          />
        </div>
        {deskUsers.length > 0 && !frozen && (
          <div className="recipient-picks">
            <div className="muted">{t(language, "deskPeople")}</div>
            <div className="recipient-chips">
              {deskUsers.map((u) => {
                const on = recipients.includes((u.email || "").toLowerCase());
                return (
                  <button
                    key={u.id}
                    type="button"
                    className={`btn recipient-chip ${on ? "on" : ""}`}
                    onClick={() => toggleDeskUser(u.email)}
                  >
                    {u.full_name || u.email}
                    {u.role ? ` · ${u.role}` : ""}
                  </button>
                );
              })}
            </div>
          </div>
        )}
        <p className={`recipients-preview ${recipients.length ? "ready" : ""}`}>
          {recipients.length
            ? `${t(language, "sendsTo")} ${recipientLabels.join(", ")}`
            : t(language, "recipientNotSet")}
        </p>
      </div>
      <div className="builder-grid">
        <div className="card palette">
          <div className="eyebrow">{t(language, "fields")}</div>
          {TYPES.map((ty) => (
            <button key={ty} className="btn" onClick={() => add(ty)} disabled={frozen} data-demo={`add-${ty}`}>
              {t(language, `type_${ty}`)}
            </button>
          ))}
        </div>
        <div className="paper" data-demo="form-paper" dir={dirFor(language)} lang={language}>
          {fields.map((f, i) => {
            const type = f.type as FieldType;
            const opts = fieldOptions(f);
            const rawLabel = String(f.label || "").trim();
            const hideDefaultTitle = CONTROL_IMPLIED_TYPES.has(type) && isUselessDefaultLabel(rawLabel);
            const labelText = hideDefaultTitle ? "" : rawLabel || t(language, "newField");
            const showLabelRow = type === "heading" || !hideDefaultTitle || !!f.required;
            return (
              <div
                key={f.id || `field-${i}`}
                className={`paper-row ${sel === i ? "on" : ""}`}
                draggable={!frozen}
                onDragStart={(e) => !frozen && e.dataTransfer.setData("text/plain", String(i))}
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault();
                  if (frozen) return;
                  move(Number(e.dataTransfer.getData("text/plain")), i);
                }}
                onClick={() => setSel(i)}
                data-demo="paper-row"
              >
                <span className="line-no">{i + 1}</span>
                <div className="paper-row-main">
                  {type === "heading" ? (
                    <h3 className="paper-heading" dir="auto" data-demo="paper-label">
                      {labelText}
                    </h3>
                  ) : (
                    <>
                      {showLabelRow ? (
                        <div className="paper-label-row">
                          {!hideDefaultTitle ? (
                            <strong className="paper-label" dir="auto" data-demo="paper-label">
                              {labelText}
                            </strong>
                          ) : null}
                          {f.required ? <span className="pill bad">{t(language, "required")}</span> : null}
                        </div>
                      ) : null}
                      {SELECT_LIKE.has(type) ? (
                        <div className="paper-select-preview" data-demo="paper-options" aria-hidden="true">
                          <span className="paper-select-value" dir="auto">
                            {type === "yesno"
                              ? f.default === "no"
                                ? t(language, "no")
                                : f.default === "yes"
                                  ? t(language, "yes")
                                  : "—"
                              : selectDisplayValue(f, language)}
                          </span>
                          <span className="paper-select-chevron" aria-hidden="true">
                            ▼
                          </span>
                        </div>
                      ) : null}
                      {type === "radio" ? (
                        <div className="paper-radio-preview" data-demo="paper-options" aria-hidden="true">
                          {(opts.length ? opts : ["A", "B"]).map((o) => (
                            <span key={o} className="paper-radio-option">
                              <span className="paper-radio-dot" />
                              <span dir="auto">{o}</span>
                            </span>
                          ))}
                        </div>
                      ) : null}
                      {INPUT_LIKE.has(type) ? (
                        <div
                          className={`paper-input-preview ${type === "textarea" ? "tall" : ""}`}
                          aria-hidden="true"
                        >
                          <span className="paper-input-placeholder" dir="auto">
                            {String(f.placeholder || "").trim() || defaultInputPlaceholder(type, language)}
                          </span>
                        </div>
                      ) : null}
                      {type === "signature" ? (
                        <div className="paper-sign-preview" aria-hidden="true">
                          <span>{t(language, "type_signature")}</span>
                        </div>
                      ) : null}
                      {type === "file" ? (
                        <div className="paper-upload-preview" aria-hidden="true" data-demo="paper-file">
                          <span className="paper-upload-btn">{t(language, "chooseFile")}</span>
                          <span className="paper-upload-hint muted">
                            {(Array.isArray(f.accept) && f.accept.length ? f.accept : DEFAULT_FILE_ACCEPT).join(", ")}
                          </span>
                        </div>
                      ) : null}
                      {type === "images" ? (
                        <div className="paper-upload-preview images" aria-hidden="true" data-demo="paper-images">
                          <span className="paper-upload-btn">{t(language, "chooseImages")}</span>
                          <span className="paper-upload-hint muted">
                            {t(language, "maxFiles", { n: Number(f.max_count) || 5 })} ·{" "}
                            {(Array.isArray(f.accept) && f.accept.length ? f.accept : DEFAULT_IMAGE_ACCEPT).join(", ")}
                          </span>
                        </div>
                      ) : null}
                      {type === "dropdown" && opts.length > 1 ? (
                        <div className="paper-options-hint" dir="auto">
                          {opts.length <= 4 ? opts.join(", ") : `${opts.slice(0, 4).join(", ")}…`}
                        </div>
                      ) : null}
                    </>
                  )}
                </div>
                <div className="paper-row-actions" onClick={(e) => e.stopPropagation()}>
                  <button
                    type="button"
                    className="btn paper-icon-btn"
                    aria-label="Move up"
                    title="Move up"
                    onClick={() => move(i, i - 1)}
                    disabled={frozen || i === 0}
                  >
                    ↑
                  </button>
                  <button
                    type="button"
                    className="btn paper-icon-btn"
                    aria-label="Move down"
                    title="Move down"
                    onClick={() => move(i, i + 1)}
                    disabled={frozen || i === fields.length - 1}
                  >
                    ↓
                  </button>
                  <button
                    type="button"
                    className="btn paper-icon-btn danger"
                    data-demo="delete-field-row"
                    aria-label={`${t(language, "deleteField")} ${f.label || i + 1}`}
                    title={frozen ? t(language, "locked") : t(language, "deleteField")}
                    onClick={() => remove(i)}
                    disabled={frozen}
                  >
                    ×
                  </button>
                </div>
              </div>
            );
          })}
          {!fields.length && <p className="muted">{t(language, "emptyPaper")}</p>}
        </div>
        <aside className={`card field-inspector ${selected ? "has-selection" : ""}`} data-demo="field-inspector">
          <div className="eyebrow">{selected ? t(language, "lineN", { n: sel + 1 }) : t(language, "fieldDetails")}</div>
          <h3 className="inspector-title">{selected ? t(language, "fieldDetails") : t(language, "selectFieldHint")}</h3>
          {selected ? (
            <>
              <p className="muted inspector-hint">
                {selected.label ||
                  (CONTROL_IMPLIED_TYPES.has(selected.type as FieldType)
                    ? t(language, `type_${selected.type}`)
                    : t(language, "newField"))}
              </p>
              <div className="field">
                <label>{t(language, "type")}</label>
                <select
                  value={selected.type}
                  disabled={frozen}
                  aria-label={t(language, "type")}
                  data-demo="field-type"
                  onChange={(e) => changeSelectedType(e.target.value as FieldType)}
                >
                  {TYPES.map((ty) => (
                    <option key={ty} value={ty}>
                      {t(language, `type_${ty}`)}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label>{t(language, "label")}</label>
                <input
                  value={selected.label || ""}
                  disabled={frozen}
                  readOnly={frozen}
                  dir="auto"
                  data-demo="field-label"
                  onChange={(e) => patchSelected({ label: e.target.value })}
                />
              </div>
              {showRequired && (
                <label className="inspector-check muted">
                  <input
                    type="checkbox"
                    checked={!!selected.required}
                    disabled={frozen}
                    data-demo="field-required"
                    onChange={(e) => patchSelected({ required: e.target.checked })}
                  />{" "}
                  {t(language, "mandatory")}
                </label>
              )}
              {showUploadOpts && (
                <>
                  <div className="field">
                    <label>{t(language, "acceptTypes")}</label>
                    <input
                      value={(Array.isArray(selected.accept) ? selected.accept : []).join(", ")}
                      disabled={frozen}
                      readOnly={frozen}
                      placeholder={
                        selected.type === "images"
                          ? DEFAULT_IMAGE_ACCEPT.join(", ")
                          : DEFAULT_FILE_ACCEPT.join(", ")
                      }
                      data-demo="field-accept"
                      onChange={(e) =>
                        patchSelected({
                          accept: e.target.value
                            .split(/[,;\s]+/)
                            .map((s) => s.trim().toLowerCase().replace(/^\./, ""))
                            .filter(Boolean),
                        })
                      }
                    />
                  </div>
                  {selected.type === "images" ? (
                    <div className="field">
                      <label>{t(language, "maxCount")}</label>
                      <input
                        type="number"
                        min={1}
                        max={10}
                        value={Number(selected.max_count) || 5}
                        disabled={frozen}
                        readOnly={frozen}
                        data-demo="field-max-count"
                        onChange={(e) => {
                          const n = Number(e.target.value);
                          patchSelected({
                            max_count: Number.isFinite(n) ? Math.max(1, Math.min(10, Math.floor(n))) : 5,
                          });
                        }}
                      />
                    </div>
                  ) : null}
                </>
              )}
              <div className="field">
                <label>{t(language, "helpText")}</label>
                <input
                  value={selected.help || ""}
                  disabled={frozen}
                  readOnly={frozen}
                  placeholder={t(language, "helpPlaceholder")}
                  data-demo="field-help"
                  onChange={(e) => patchSelected({ help: e.target.value })}
                />
              </div>
              {showPlaceholder && (
                <div className="field">
                  <label>{t(language, "placeholder")}</label>
                  <input
                    value={selected.placeholder || ""}
                    disabled={frozen}
                    readOnly={frozen}
                    placeholder={t(language, "placeholder")}
                    data-demo="field-placeholder"
                    onChange={(e) => patchSelected({ placeholder: e.target.value })}
                  />
                </div>
              )}
              {showChoices && (
                <div className="field" data-demo="field-choices">
                  <label>{t(language, "choices")}</label>
                  <div className="choice-list">
                    {(selected.options || []).length === 0 ? (
                      <div className="choice-empty">
                        <p className="muted field-help" data-demo="choices-preview">
                          {t(language, "noChoices")}
                        </p>
                        <button
                          type="button"
                          className="btn"
                          disabled={frozen}
                          data-demo="add-choice"
                          onClick={addChoice}
                        >
                          {t(language, "addChoice")}
                        </button>
                      </div>
                    ) : (
                      <>
                        {(selected.options || []).map((opt: string, oi: number) => (
                          <div className="choice-row" key={`choice-${oi}`}>
                            <input
                              value={opt}
                              disabled={frozen}
                              readOnly={frozen}
                              dir="auto"
                              aria-label={`${t(language, "choices")} ${oi + 1}`}
                              data-demo="choice-input"
                              onChange={(e) => updateChoiceAt(oi, e.target.value)}
                            />
                            <button
                              type="button"
                              className="btn"
                              disabled={frozen}
                              data-demo="remove-choice"
                              aria-label={t(language, "removeChoice")}
                              onClick={() => removeChoiceAt(oi)}
                            >
                              {t(language, "removeChoice")}
                            </button>
                          </div>
                        ))}
                        <button
                          type="button"
                          className="btn"
                          disabled={frozen}
                          data-demo="add-choice"
                          onClick={addChoice}
                        >
                          {t(language, "addChoice")}
                        </button>
                      </>
                    )}
                  </div>
                </div>
              )}
              {autoChoices && (
                <div className="field">
                  <label>{t(language, "autoFill")}</label>
                  <select
                    value={selected.auto || ""}
                    disabled={frozen}
                    data-demo="field-auto"
                    onChange={(e) => patchSelected({ auto: e.target.value })}
                  >
                    {autoChoices.map((opt) => (
                      <option key={opt.value || "none"} value={opt.value}>
                        {t(language, opt.labelKey)}
                      </option>
                    ))}
                  </select>
                </div>
              )}
              {showDefault && (
                <div className="field">
                  <label>{t(language, "defaultValue")}</label>
                  {selected.type === "yesno" ? (
                    <select
                      value={selected.default || ""}
                      disabled={frozen}
                      data-demo="field-default"
                      onChange={(e) => patchSelected({ default: e.target.value })}
                    >
                      <option value="">—</option>
                      <option value="yes">{t(language, "yes")}</option>
                      <option value="no">{t(language, "no")}</option>
                    </select>
                  ) : showChoices ? (
                    <select
                      value={selected.default || ""}
                      disabled={frozen}
                      data-demo="field-default"
                      onChange={(e) => patchSelected({ default: e.target.value })}
                    >
                      <option value="">—</option>
                      {(selected.options || [])
                        .map((o: string) => String(o).trim())
                        .filter(Boolean)
                        .map((o: string) => (
                          <option key={o} value={o}>
                            {o}
                          </option>
                        ))}
                    </select>
                  ) : (
                    <input
                      type={selected.type === "number" ? "number" : selected.type === "date" ? "date" : "text"}
                      value={selected.default || ""}
                      disabled={frozen}
                      readOnly={frozen}
                      data-demo="field-default"
                      onChange={(e) => patchSelected({ default: e.target.value })}
                    />
                  )}
                </div>
              )}
              <div className="row-actions" style={{ marginTop: 12 }}>
                <button
                  className="btn"
                  type="button"
                  data-demo="delete-field"
                  disabled={frozen}
                  onClick={() => remove(sel)}
                >
                  {t(language, "deleteField")}
                </button>
              </div>
            </>
          ) : (
            <p className="muted" data-demo="field-inspector-empty">
              {t(language, "selectFieldHint")}
            </p>
          )}
        </aside>
      </div>
    </div>
  );
}
