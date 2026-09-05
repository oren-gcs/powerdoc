import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { DocsAPI, WfAPI } from "../api";

export default function DocumentDetail() {
  const { id } = useParams();
  const [data, setData] = useState<any>(null);
  const [wfs, setWfs] = useState<any[]>([]);
  const [msg, setMsg] = useState("");

  const load = () => DocsAPI.detail(Number(id)).then(setData);

  useEffect(() => {
    load().catch((e) => setMsg(e.message));
    WfAPI.list().then(setWfs).catch(() => {});
  }, [id]);

  if (!data) return <p className="muted">{msg || "Loading…"}</p>;
  const d = data.document;

  return (
    <>
      <Link className="eyebrow" to="/app/documents">
        ← Library
      </Link>
      <div className="topbar">
        <h1 className="mark" style={{ fontSize: 32, margin: 0 }}>
          {d.filename}
        </h1>
        <a className="btn" href={DocsAPI.download(d.id)}>
          Download
        </a>
      </div>
      <div className="split">
        <div className="card">
          <div className="eyebrow">Extracted text · {data.ocr?.engine}</div>
          <pre className="ocr">{data.ocr?.text || "No OCR yet"}</pre>
        </div>
        <div>
          <div className="card">
            <div className="eyebrow">Identity</div>
            <p>
              <span className="pill ok">{d.status}</span> <span className="pill">{d.classification}</span>
            </p>
            <div className="muted">Confidence {Math.round((data.ocr?.confidence || 0) * 100)}%</div>
            <h3>Fields</h3>
            {data.fields?.map((f: any) => (
              <div key={f.name} style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
                <span className="mono dim">{f.name}</span>
                <span>{f.value}</span>
              </div>
            ))}
          </div>
          <div className="card" style={{ marginTop: 16 }}>
            <div className="eyebrow">Re-run a flow</div>
            {wfs.map((w) => (
              <button
                key={w.id}
                className="btn"
                style={{ margin: "6px 6px 0 0" }}
                onClick={async () => {
                  const r = await WfAPI.execute(w.id, d.id);
                  setMsg(`${w.name}: ${r.status}`);
                  load();
                }}
              >
                {w.name}
              </button>
            ))}
            {msg && <p className="muted">{msg}</p>}
          </div>
        </div>
      </div>
    </>
  );
}
