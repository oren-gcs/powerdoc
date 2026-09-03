import { FormEvent, useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { FormsAPI } from "../api";
import { dirFor } from "../i18n";

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

  useEffect(() => {
    if (!token) return;
    FormsAPI.publicGet(token).then((f) => {
      setForm(f);
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
      return { x: e.clientX - r.left, y: e.clientY - r.top };
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
      <div className="fill-wrap">
        <div className="paper fill-sheet">
          <h1 className="mark">Received</h1>
          <p>Logged as submission #{done.submission_id} and written into the desk database.</p>
        </div>
      </div>
    );
  }
  if (!form) return <p className="muted">{err || "Loading form…"}</p>;

  return (
    <div className="fill-wrap">
      <form className="paper fill-sheet" onSubmit={submit}>
        <div className="eyebrow">DocFlow</div>
        <h1 className="mark">{form.name}</h1>
        <p className="muted">{form.description}</p>
        <div className="field">
          <label>Your name</label>
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </div>
        <div className="field">
          <label>Email</label>
          <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required />
        </div>
        {form.fields.map((f: any, i: number) => (
          <div className="field" key={f.id}>
            {f.type === "heading" ? (
              <h3>{f.label}</h3>
            ) : (
              <>
                <label>
                  {i + 1}. {f.label} {f.required ? "*" : ""}
                </label>
                {f.type === "textarea" ? (
                  <textarea onChange={(e) => setAnswers({ ...answers, [f.id]: e.target.value })} required={f.required} />
                ) : f.type === "dropdown" || f.type === "radio" ? (
                  <select onChange={(e) => setAnswers({ ...answers, [f.id]: e.target.value })} required={f.required}>
                    <option value="">—</option>
                    {(f.options || []).map((o: string) => (
                      <option key={o}>{o}</option>
                    ))}
                  </select>
                ) : f.type === "yesno" ? (
                  <select onChange={(e) => setAnswers({ ...answers, [f.id]: e.target.value })} required={f.required}>
                    <option value="">—</option>
                    <option>yes</option>
                    <option>no</option>
                  </select>
                ) : f.type === "signature" ? (
                  <canvas ref={canvas} width={520} height={140} className="sign-pad" />
                ) : (
                  <input type={f.type === "number" ? "number" : f.type === "date" ? "date" : "text"} required={f.required} onChange={(e) => setAnswers({ ...answers, [f.id]: e.target.value })} />
                )}
              </>
            )}
          </div>
        ))}
        {err && <p className="pill bad">{err}</p>}
        <button className="btn primary" style={{ marginTop: 16 }}>
          Sign and send
        </button>
      </form>
    </div>
  );
}
