import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { FormsAPI } from "../api";
import FormExit from "../components/FormExit";
import { dirFor, t } from "../i18n";

type SendTo = { email: string; name?: string | null };

function formatSendsTo(entries: SendTo[]): string {
  return entries
    .map((r) => {
      const name = (r.name || "").trim();
      const email = (r.email || "").trim();
      if (name && email) return `${name} · ${email}`;
      return name || email;
    })
    .filter(Boolean)
    .join(", ");
}

export default function FillForm() {
  const { token } = useParams();
  const [form, setForm] = useState<any>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [err, setErr] = useState("");
  const [done, setDone] = useState<any>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const drawing = useRef(false);

  const lang = form?.language || "en";
  const sendsToLabel = useMemo(() => formatSendsTo(form?.sends_to || []), [form]);

  useEffect(() => {
    if (!token) return;
    FormsAPI.publicGet(token).then((f) => {
      setForm(f);
      const today = new Date().toISOString().slice(0, 10);
      const seed: Record<string, string> = {};
      for (const field of f.fields || []) {
        if (field.type === "date" && field.auto === "today") seed[field.id] = today;
        else if (field.default != null && field.default !== "") seed[field.id] = String(field.default);
      }
      setAnswers(seed);
      document.documentElement.lang = f.language;
      document.documentElement.dir = dirFor(f.language);
    }).catch((e) => setErr(e.message));
  }, [token]);

  useEffect(() => {
    const c = canvas.current;
    if (!c) return;
    const ctx = c.getContext("2d");
    if (!ctx) return;
    ctx.strokeStyle = "#1a1408";
    ctx.lineWidth = 2;
    const pos = (e: PointerEvent) => {
      const r = c.getBoundingClientRect();
      const sx = c.width / r.width;
      const sy = c.height / r.height;
      return { x: (e.clientX - r.left) * sx, y: (e.clientY - r.top) * sy };
    };
    const down = (e: PointerEvent) => {
      drawing.current = true;
      const p = pos(e);
      ctx.beginPath();
      ctx.moveTo(p.x, p.y);
    };
    const move = (e: PointerEvent) => {
      if (!drawing.current) return;
      const p = pos(e);
      ctx.lineTo(p.x, p.y);
      ctx.stroke();
    };
    const up = () => {
      drawing.current = false;
    };
    c.addEventListener("pointerdown", down);
    c.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
    return () => {
      c.removeEventListener("pointerdown", down);
      c.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
    };
  }, [form]);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setErr("");
    try {
      const signature = canvas.current?.toDataURL() || null;
      const r = await FormsAPI.publicSubmit(token!, { name, email, answers, signature, locale: form.language });
      setDone(r);
    } catch (ex: any) {
      setErr(ex.message);
    }
  };

  if (done) {
    return (
      <div className="fill-wrap" dir={dirFor(lang)} lang={lang}>
        <div className="paper fill-sheet">
          <FormExit fallback="/" variant="on-paper" />
          <h1 className="mark">{t(lang, "received")}</h1>
          <p>{t(lang, "receivedBody", { id: done.submission_id })}</p>
        </div>
      </div>
    );
  }
  if (!form) return <p className="muted">{err || t("en", "loadingForm")}</p>;

  return (
    <div className="fill-wrap" dir={dirFor(lang)} lang={lang}>
      <form className="paper fill-sheet" onSubmit={submit}>
        <FormExit fallback="/" variant="on-paper" />
        <div className="eyebrow">DocFlow</div>
        <h1 className="mark">{form.name}</h1>
        <p className="muted">{form.description}</p>
        <div className="field">
          <label>{t(lang, "yourName")}</label>
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </div>
        <div className="field">
          <label>{t(lang, "email")}</label>
          <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required />
        </div>
        {form.fields.map((f: any, i: number) => {
          const rawLabel = String(f.label || "").trim();
          const impliedControl = f.type === "email" || f.type === "phone" || f.type === "signature";
          const uselessDefault =
            !rawLabel ||
            rawLabel === t("en", "newField") ||
            rawLabel === t("he", "newField") ||
            rawLabel === t("ar", "newField") ||
            rawLabel === t("es", "newField") ||
            rawLabel === t("fr", "newField");
          const hideLabel = impliedControl && uselessDefault;
          const labelText = hideLabel ? "" : rawLabel;
          return (
          <div className="field" key={f.id}>
            {f.type === "heading" ? (
              <h3>{labelText || rawLabel}</h3>
            ) : (
              <>
                {!hideLabel || f.required ? (
                  <label>
                    {labelText ? (
                      <>
                        {i + 1}. {labelText}
                      </>
                    ) : null}{" "}
                    {f.required ? "*" : ""}
                  </label>
                ) : null}
                {f.help ? <p className="muted" style={{ margin: "0 0 6px", fontSize: 13 }}>{f.help}</p> : null}
                {f.type === "textarea" ? (
                  <textarea
                    value={answers[f.id] || ""}
                    placeholder={f.placeholder || undefined}
                    onChange={(e) => setAnswers({ ...answers, [f.id]: e.target.value })}
                    required={f.required}
                  />
                ) : f.type === "dropdown" || f.type === "radio" ? (
                  <select value={answers[f.id] || ""} onChange={(e) => setAnswers({ ...answers, [f.id]: e.target.value })} required={f.required}>
                    <option value="">{f.placeholder || "—"}</option>
                    {(f.options || []).map((o: string) => (
                      <option key={o}>{o}</option>
                    ))}
                  </select>
                ) : f.type === "yesno" ? (
                  <select value={answers[f.id] || ""} onChange={(e) => setAnswers({ ...answers, [f.id]: e.target.value })} required={f.required}>
                    <option value="">—</option>
                    <option value="yes">{t(lang, "yes")}</option>
                    <option value="no">{t(lang, "no")}</option>
                  </select>
                ) : f.type === "signature" ? (
                  <canvas ref={canvas} width={364} height={98} className="sign-pad" />
                ) : (
                  <input
                    type={f.type === "number" ? "number" : f.type === "date" ? "date" : f.type === "email" ? "email" : "text"}
                    required={f.required}
                    placeholder={f.placeholder || undefined}
                    value={answers[f.id] || ""}
                    onChange={(e) => setAnswers({ ...answers, [f.id]: e.target.value })}
                  />
                )}
              </>
            )}
          </div>
          );
        })}
        {err && <p className="pill bad">{err}</p>}
        <div className="fill-submit-row">
          <button className="btn primary" type="submit">
            {t(lang, "signAndSend")}
          </button>
          {sendsToLabel ? (
            <span className="sends-to-note muted" data-demo="sends-to">
              {t(lang, "sendsTo")} {sendsToLabel}
            </span>
          ) : null}
        </div>
      </form>
    </div>
  );
}
