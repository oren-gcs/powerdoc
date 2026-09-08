import { useEffect, useState } from "react";
import { AnalyticsAPI } from "../api";

export default function Analytics() {
  const [s, setS] = useState<any>(null);
  const [act, setAct] = useState<any[]>([]);
  useEffect(() => {
    AnalyticsAPI.summary().then(setS);
    AnalyticsAPI.activity().then(setAct);
  }, []);
  return (
    <>
      <div className="eyebrow">Truth, not placeholders</div>
      <h1 className="mark" style={{ fontSize: 32 }}>
        Analytics
      </h1>
      <div className="grid cards-4">
        <div className="card stat">
          <div className="eyebrow">Documents</div>
          <div className="n">{s?.documents}</div>
        </div>
        <div className="card stat">
          <div className="eyebrow">Ready</div>
          <div className="n">{s?.ready}</div>
        </div>
        <div className="card stat">
          <div className="eyebrow">Runs</div>
          <div className="n">{s?.workflow_runs}</div>
        </div>
        <div className="card stat">
          <div className="eyebrow">Success</div>
          <div className="n">{s?.success_rate}%</div>
        </div>
      </div>
      <div className="split" style={{ marginTop: 16 }}>
        <div className="card">
          <div className="eyebrow">By class</div>
          {(s?.by_class || []).map((c: any) => (
            <div key={c.label} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0" }}>
              <span>{c.label}</span>
              <span className="mono">{c.count}</span>
            </div>
          ))}
          <p className="muted">{s?.digest}</p>
        </div>
        <div className="card">
          <div className="eyebrow">Activity</div>
          {act.slice(0, 12).map((a) => (
            <div key={a.id} className="muted" style={{ padding: "6px 0", borderBottom: "1px solid var(--line)" }}>
              {a.type}
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
