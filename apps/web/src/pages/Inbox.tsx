import { useEffect, useState } from "react";
import { AnalyticsAPI } from "../api";

export default function Inbox() {
  const [rows, setRows] = useState<any[]>([]);
  const load = () => AnalyticsAPI.notes().then(setRows);
  useEffect(() => {
    load();
  }, []);
  return (
    <>
      <div className="eyebrow">Notifications</div>
      <h1 className="mark" style={{ fontSize: 32 }}>
        Inbox
      </h1>
      <div className="card">
        {rows.map((n) => (
          <div key={n.id} style={{ padding: "12px 0", borderBottom: "1px solid var(--line)" }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <strong>{n.subject}</strong>
              <button className="btn" onClick={() => AnalyticsAPI.read(n.id).then(load)}>
                {n.status}
              </button>
            </div>
            <p className="muted">{n.body}</p>
          </div>
        ))}
        {!rows.length && <p className="muted">No notices yet — process a document.</p>}
      </div>
    </>
  );
}
