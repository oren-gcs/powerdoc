import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { FormsAPI } from "../api";

const TYPES = ["text", "textarea", "number", "date", "email", "phone", "dropdown", "radio", "yesno", "signature", "heading"];

function nid() {
  return Math.random().toString(16).slice(2, 10);
}

export default function FormBuilder() {
  const { id } = useParams();
  const nav = useNavigate();
  const [name, setName] = useState("Untitled form");
  const [language, setLanguage] = useState(localStorage.getItem("docflow.lang") || "en");
  const [prompt, setPrompt] = useState("Invoice approval with department dropdown and a required signature");
  const [fields, setFields] = useState<any[]>([]);
  const [sel, setSel] = useState(0);
  const [formId, setFormId] = useState<number | null>(id ? Number(id) : null);
  const [msg, setMsg] = useState("");
  const [share, setShare] = useState("");

  useEffect(() => {
    if (!id) return;
    FormsAPI.get(Number(id)).then((f) => {
      setName(f.name);
      setLanguage(f.language);
      setFields(f.fields || []);
      setFormId(f.id);
    });
  }, [id]);

  const move = (from: number, to: number) => {
    if (to < 0 || to >= fields.length) return;
    const next = fields.slice();
    const [item] = next.splice(from, 1);
    next.splice(to, 0, item);
    setFields(next);
    setSel(to);
  };

  const add = (type: string) => {
    setFields([...fields, { id: nid(), type, label: type === "heading" ? "Section" : "New field", required: type === "signature", options: type === "dropdown" ? ["A", "B"] : [] }]);
    setSel(fields.length);
  };

  const persist = async () => {
    const body = { name, topic: "", description: prompt, language, fields };
    const f = formId ? await FormsAPI.update(formId, body) : await FormsAPI.create(body);
    setFormId(f.id);
    setMsg("Saved draft");
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
    const r = await FormsAPI.compose({ prompt, language, use_rag: true });
    setName(r.name);
    setFields(r.fields);
    setMsg("Drafted from chat + context");
  };

  const selected = fields[sel];

  return (
    <div className="builder">
      <div className="topbar">
        <div>
          <div className="eyebrow">Anyone can build this</div>
          <input className="ghost-title" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="row-actions">
          <select value={language} onChange={(e) => setLanguage(e.target.value)}>
            <option value="en">English</option>
            <option value="he">עברית</option>
            <option value="ar">العربية</option>
            <option value="es">Español</option>
            <option value="fr">Français</option>
          </select>
          <button className="btn" onClick={save}>
            Save
          </button>
          <button
            className="btn primary"
            data-demo="publish"
            onClick={async () => {
              try {
                const saved = await persist();
                const live = await FormsAPI.publish(saved.id);
                setShare(live.share_url);
                setMsg("In the automation folder — form is alive");
              } catch (e: any) {
                setMsg(e.message);
              }
            }}
          >
            Make alive
          </button>
        </div>
      </div>
      <div className="chatbar">
        <input value={prompt} onChange={(e) => setPrompt(e.target.value)} placeholder="Tell the desk what this form is for…" />
        <button className="btn primary" data-demo="compose" onClick={compose}>
          Draft with chat
        </button>
      </div>
      {msg && <p className="pill ok">{msg} {share && <a href={share}> {share}</a>}</p>}
      <div className="builder-grid">
        <div className="card palette">
          <div className="eyebrow">Fields</div>
          {TYPES.map((ty) => (
            <button key={ty} className="btn" onClick={() => add(ty)}>
              {ty}
            </button>
          ))}
        </div>
        <div className="paper">
          {fields.map((f, i) => (
            <div
              key={f.id}
              className={`paper-row ${sel === i ? "on" : ""}`}
              draggable
              onDragStart={(e) => e.dataTransfer.setData("text/plain", String(i))}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                move(Number(e.dataTransfer.getData("text/plain")), i);
              }}
              onClick={() => setSel(i)}
            >
              <span className="line-no">{i + 1}</span>
              <div>
                <div className="mono dim">{f.type}</div>
                <strong>{f.label}</strong>
                {f.required && <span className="pill bad">required</span>}
              </div>
              <div>
                <button className="btn" onClick={() => move(i, i - 1)}>
                  ↑
                </button>
                <button className="btn" onClick={() => move(i, i + 1)}>
                  ↓
                </button>
              </div>
            </div>
          ))}
          {!fields.length && <p className="muted">Ask the chat, or tap a field type.</p>}
        </div>
        <div className="card">
          <div className="eyebrow">Line {sel + 1}</div>
          {selected && (
            <>
              <div className="field">
                <label>Label</label>
                <input
                  value={selected.label}
                  onChange={(e) => {
                    const next = fields.slice();
                    next[sel] = { ...selected, label: e.target.value };
                    setFields(next);
                  }}
                />
              </div>
              <label className="muted">
                <input
                  type="checkbox"
                  checked={!!selected.required}
                  onChange={(e) => {
                    const next = fields.slice();
                    next[sel] = { ...selected, required: e.target.checked };
                    setFields(next);
                  }}
                />{" "}
                Mandatory
              </label>
              {(selected.type === "dropdown" || selected.type === "radio") && (
                <div className="field">
                  <label>Choices (comma)</label>
                  <input
                    value={(selected.options || []).join(",")}
                    onChange={(e) => {
                      const next = fields.slice();
                      next[sel] = { ...selected, options: e.target.value.split(",").map((s) => s.trim()).filter(Boolean) };
                      setFields(next);
                    }}
                  />
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
