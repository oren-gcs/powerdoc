import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { FormsAPI, OrgAPI } from "../api";
import FormExit from "../components/FormExit";
import { t } from "../i18n";

const TYPES = ["text", "textarea", "number", "date", "email", "phone", "dropdown", "radio", "yesno", "signature", "heading"];

function nid() {
  return Math.random().toString(16).slice(2, 10);
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
      const name = byEmail.get(email) || "";
      return name ? `${name} · ${email}` : email;
    });
  }, [recipients, deskUsers]);

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
      setFields(f.fields || []);
      setRecipientsText((f.recipients || []).join(", "));
      setFormId(f.id);
      setLocked(!!f.locked);
      setArchived(!!f.archived);
      setSubmissionCount(f.submission_count || 0);
      if (f.share_url) setShare(f.share_url);
    });
  }, [id]);

  const frozen = locked || archived;

  const move = (from: number, to: number) => {
    if (frozen) return;
    if (to < 0 || to >= fields.length) return;
    const next = fields.slice();
    const [item] = next.splice(from, 1);
    next.splice(to, 0, item);
    setFields(next);
    setSel(to);
  };

  const remove = (index: number) => {
    if (frozen) return;
    const label = fields[index]?.label || `Line ${index + 1}`;
    if (!window.confirm(`Delete field “${label}”?`)) return;
    const next = fields.slice();
    next.splice(index, 1);
    setFields(next);
    setSel((prev) => {
      if (!next.length) return 0;
      if (prev > index) return prev - 1;
      if (prev === index) return Math.min(index, next.length - 1);
      return prev;
    });
  };

  const patchSelected = (patch: Record<string, unknown>) => {
    if (frozen) return;
    const current = fields[sel];
    if (!current) return;
    const next = fields.slice();
    next[sel] = { ...current, ...patch };
    setFields(next);
  };

  const add = (type: string) => {
    if (frozen) return;
    setFields([
      ...fields,
      {
        id: nid(),
        type,
        label: type === "heading" ? "Section" : "New field",
        required: type === "signature",
        options: type === "dropdown" || type === "radio" ? ["A", "B"] : [],
        help: "",
        placeholder: "",
        auto: "",
      },
    ]);
    setSel(fields.length);
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
    const body = { name, topic: "", description: prompt, language, fields, recipients };
    const f = formId ? await FormsAPI.update(formId, body) : await FormsAPI.create(body);
    setFormId(f.id);
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
    setThread((t) => [...t, { role: "user", text: asked }]);
    try {
      const r = await FormsAPI.compose({ prompt: asked, language, use_rag: true });
      setName(r.name);
      setFields(r.fields || []);
      setSel(0);
      setThread((t) => [
        ...t,
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
      setThread((t) => [
        ...t,
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

  const selected = fields[sel];

  return (
    <div className="builder">
      <div className="topbar">
        <div>
          <FormExit fallback="/app/forms" variant="on-dark" />
          <div>
            <div className="eyebrow">Anyone can build this</div>
            <input
              className="ghost-title"
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={frozen}
              readOnly={frozen}
            />
            {locked && (
              <p className="muted" style={{ marginTop: 4 }}>
                <span className="pill warn" data-demo="locked-badge">
                  Locked · {submissionCount} answer{submissionCount === 1 ? "" : "s"}
                </span>{" "}
                Definition frozen after the first submission.
                {archived && (
                  <>
                    {" "}
                    <span className="pill" data-demo="archived-badge">
                      Archived
                    </span>
                  </>
                )}
              </p>
            )}
            {!locked && archived && (
              <p className="muted" style={{ marginTop: 4 }}>
                <span className="pill" data-demo="archived-badge">
                  Archived
                </span>{" "}
                Copy to a new form or unarchive to edit.
              </p>
            )}
          </div>
        </div>
        <div className="row-actions">
          {locked && formId && (
            <button className="btn primary" data-demo="open-answered" onClick={() => nav(`/app/forms/${formId}/answered`)}>
              Answered folder
            </button>
          )}
          {formId && (
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
          )}
          {formId && !archived && (
            <button className="btn" data-demo="archive-form" onClick={() => setArchiveOpen(true)}>
              Archive
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
                  setMsg("Unarchived as draft");
                } catch (e: any) {
                  setMsg(e.message);
                }
              }}
            >
              Unarchive
            </button>
          )}
          <select value={language} onChange={(e) => setLanguage(e.target.value)} disabled={frozen}>
            <option value="en">English</option>
            <option value="he">עברית</option>
            <option value="ar">العربية</option>
            <option value="es">Español</option>
            <option value="fr">Français</option>
          </select>
          <button className="btn" onClick={save} disabled={frozen}>
            Save
          </button>
          <button
            className="btn primary"
            data-demo="publish"
            disabled={frozen}
            onClick={async () => {
              try {
                const saved = await persist();
                const live = await FormsAPI.publish(saved.id);
                setShare(live.share_url);
                const notified = live.notified || [];
                setMsg(
                  notified.length
                    ? `${t(language, "formAlive")} · ${t(language, "willBeSentTo")} ${notified.join(", ")}`
                    : t(language, "formAlive")
                );
              } catch (e: any) {
                setMsg(e.message);
              }
            }}
          >
            Make alive
          </button>
        </div>
      </div>
      {archiveOpen && formId && (
        <div className="card archive-panel" data-demo="archive-panel" style={{ marginBottom: 12 }}>
          <h3 style={{ marginTop: 0 }}>Archive form</h3>
          <p className="muted">Locked definitions cannot be edited or deleted — archive or copy instead.</p>
          <div className="row-actions">
            <button
              className="btn primary"
              data-demo="archive-keep"
              onClick={async () => {
                try {
                  const r = await FormsAPI.archive(formId, true);
                  setArchived(!!r.archived);
                  setArchiveOpen(false);
                  setMsg("Archived with answered data");
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
                  const r = await FormsAPI.archive(formId, false);
                  setArchived(!!r.archived);
                  setArchiveOpen(false);
                  setMsg("Archived form only — answers stay in Answered folder / documents");
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
      <div className="chatbar">
        <input
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && !frozen && compose()}
          placeholder="Tell the desk what this form is for…"
          disabled={frozen}
        />
        <button className="btn primary" data-demo="compose" onClick={compose} disabled={busy || frozen}>
          {busy ? "Listening…" : "Draft with chat"}
        </button>
      </div>
      {thread.length > 0 && (
        <div className="chat-thread" data-demo="chat-reply">
          {thread.map((m, i) => (
            <div key={i} className={`bubble ${m.role}`}>
              <div className="eyebrow">{m.role === "user" ? "You" : m.provider === "ollama" ? "Ollama" : "Desk"}</div>
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
          {msg} {share && <a href={share}> {share}</a>}
        </p>
      )}
      <div className="card form-options" data-demo="form-recipients">
        <div className="eyebrow">{t(language, "formOptions")}</div>
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
          <div className="eyebrow">Fields</div>
          {TYPES.map((ty) => (
            <button key={ty} className="btn" onClick={() => add(ty)} disabled={frozen}>
              {ty}
            </button>
          ))}
        </div>
        <div className="paper">
          {fields.map((f, i) => (
            <div
              key={f.id}
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
            >
              <span className="line-no">{i + 1}</span>
              <div className="paper-row-main">
                <div className="mono paper-row-type">{f.type}</div>
                <strong>{f.label}</strong>
                {f.required && <span className="pill bad">required</span>}
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
                  data-demo="delete-field"
                  aria-label="Delete field"
                  title={frozen ? "Form is locked" : "Delete field"}
                  onClick={() => remove(i)}
                  disabled={frozen}
                >
                  ×
                </button>
              </div>
            </div>
          ))}
          {!fields.length && <p className="muted">Ask the chat, or tap a field type.</p>}
        </div>
        <aside className={`card field-inspector ${selected ? "has-selection" : ""}`} data-demo="field-inspector">
          <div className="eyebrow">Line {selected ? sel + 1 : "—"}</div>
          <h3 className="inspector-title">{selected ? "Field configuration" : "Select a field"}</h3>
          {selected ? (
            <>
              <p className="muted inspector-hint">Editing “{selected.label || "Untitled"}”</p>
              <div className="field">
                <label>Type</label>
                <select
                  value={selected.type}
                  disabled={frozen}
                  aria-label="Field type"
                  onChange={(e) => {
                    const type = e.target.value;
                    const options =
                      type === "dropdown" || type === "radio"
                        ? selected.options?.length
                          ? selected.options
                          : ["A", "B"]
                        : [];
                    patchSelected({ type, options });
                  }}
                >
                  {TYPES.map((ty) => (
                    <option key={ty} value={ty}>
                      {ty}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label>Label</label>
                <input
                  value={selected.label}
                  disabled={frozen}
                  readOnly={frozen}
                  onChange={(e) => patchSelected({ label: e.target.value })}
                />
              </div>
              <label className="inspector-check muted">
                <input
                  type="checkbox"
                  checked={!!selected.required}
                  disabled={frozen}
                  onChange={(e) => patchSelected({ required: e.target.checked })}
                />{" "}
                Mandatory
              </label>
              {(selected.type === "dropdown" || selected.type === "radio") && (
                <div className="field">
                  <label>Choices (comma)</label>
                  <input
                    value={(selected.options || []).join(", ")}
                    disabled={frozen}
                    readOnly={frozen}
                    onChange={(e) =>
                      patchSelected({
                        options: e.target.value
                          .split(",")
                          .map((s) => s.trim())
                          .filter(Boolean),
                      })
                    }
                  />
                </div>
              )}
              <div className="field">
                <label>Help text</label>
                <input
                  value={selected.help || ""}
                  disabled={frozen}
                  readOnly={frozen}
                  placeholder="Shown under the label"
                  onChange={(e) => patchSelected({ help: e.target.value })}
                />
              </div>
              {selected.type !== "heading" && selected.type !== "signature" && selected.type !== "yesno" && (
                <div className="field">
                  <label>Placeholder</label>
                  <input
                    value={selected.placeholder || ""}
                    disabled={frozen}
                    readOnly={frozen}
                    placeholder="Hint inside the input"
                    onChange={(e) => patchSelected({ placeholder: e.target.value })}
                  />
                </div>
              )}
              {selected.auto ? (
                <p className="pill ok" style={{ marginTop: 8 }}>
                  Auto: {selected.auto}
                </p>
              ) : null}
            </>
          ) : (
            <p className="muted">Tap a row on the paper to configure label, type, and options.</p>
          )}
        </aside>
      </div>
    </div>
  );
}
