import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { DocsAPI } from "../api";

export default function Documents() {
  const [docs, setDocs] = useState<any[]>([]);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  const load = () => DocsAPI.list().then(setDocs);

  useEffect(() => {
    load().catch((e) => setMsg(e.message));
  }, []);

  const onFile = async (file?: File) => {
    if (!file) return;
    setBusy(true);
    setMsg("");
    try {
      await DocsAPI.upload(file, true);
      await load();
      setMsg(`${file.name} processed through the pipeline.`);
    } catch (e: any) {
      setMsg(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <div className="topbar">
        <div>
          <div className="eyebrow">Library</div>
          <h1 className="mark" style={{ fontSize: 32, margin: 0 }}>
            Documents
          </h1>
        </div>
      </div>
      <label className="drop" style={{ display: "block", cursor: "pointer" }}>
        <div className="eyebrow">Drop or choose a file</div>
        <p className="muted">{busy ? "Running OCR → classify → workflow…" : "TXT, PDF, images. Pipeline runs immediately."}</p>
        <input type="file" hidden onChange={(e) => onFile(e.target.files?.[0])} />
      </label>
      {msg && <p className="pill ok" style={{ marginTop: 12 }}>{msg}</p>}
      <div className="card" style={{ marginTop: 16 }}>
        <table className="table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Class</th>
              <th>Status</th>
              <th>Size</th>
            </tr>
          </thead>
          <tbody>
            {docs.map((d) => (
              <tr key={d.id}>
                <td>
                  <Link to={`/app/documents/${d.id}`}>{d.filename}</Link>
                </td>
                <td>
                  <span className="pill">{d.classification || "pending"}</span>
                </td>
                <td>
                  <span className={`pill ${d.status === "ready" ? "ok" : d.status === "failed" ? "bad" : ""}`}>{d.status}</span>
                </td>
                <td className="mono dim">{d.size_bytes} B</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
