import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AgentAPI, AnalyticsAPI, DocsAPI } from "../api";
import { useAuth } from "../auth";

export default function Overview() {
  const { user } = useAuth();
  const [summary, setSummary] = useState<any>(null);
  const [docs, setDocs] = useState<any[]>([]);
  const [logs, setLogs] = useState<any[]>([]);

  useEffect(() => {
    AnalyticsAPI.summary().then(setSummary).catch(() => {});
    DocsAPI.list().then(setDocs).catch(() => {});
    AgentAPI.logs().then(setLogs).catch(() => {});
  }, []);

  const max = Math.max(1, ...(summary?.activity_daily || []).map((d: any) => d.count));

  return (
    <>
      <div className="topbar">
        <div>
          <div className="eyebrow">Good working session</div>
          <h1 className="mark" style={{ margin: "4px 0 0", fontSize: 36 }}>
            {user?.full_name.split(" ")[0]}, the desk is live.
          </h1>
        </div>
        <Link className="btn primary" to="/app/documents">
          Ingest a document
        </Link>
      </div>
      <div className="grid cards-4">
        {[
          ["In library", summary?.documents ?? "—"],
          ["Ready", summary?.ready ?? "—"],
          ["Flow runs", summary?.workflow_runs ?? "—"],
          ["Success", `${summary?.success_rate ?? "—"}%`],
        ].map(([k, v]) => (
          <div className="card stat" key={k}>
            <div className="eyebrow">{k}</div>
            <div className="n">{v}</div>
          </div>
        ))}
      </div>
      <div className="split" style={{ marginTop: 16 }}>
        <div className="card">
          <div className="eyebrow">Fourteen-day pulse</div>
          <div className="bars" style={{ marginTop: 16 }}>
            {(summary?.activity_daily || [{ count: 2 }, { count: 4 }, { count: 3 }]).map((d: any, i: number) => (
              <span key={i} style={{ height: `${(d.count / max) * 100}%` }} title={d.day} />
            ))}
          </div>
          <p className="muted" style={{ marginTop: 16 }}>
            {summary?.digest}
          </p>
        </div>
        <div className="card">
          <div className="eyebrow">Latest agent notes</div>
          <table className="table">
            <tbody>
              {logs.slice(0, 6).map((l) => (
                <tr key={l.id}>
                  <td className="mono">{l.agent_role}</td>
                  <td className="muted">{l.summary?.slice(0, 90)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div className="card" style={{ marginTop: 16 }}>
        <div className="eyebrow">Library</div>
        <table className="table">
          <thead>
            <tr>
              <th>File</th>
              <th>Class</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {docs.slice(0, 6).map((d) => (
              <tr key={d.id}>
                <td>
                  <Link to={`/app/documents/${d.id}`}>{d.filename}</Link>
                </td>
                <td>
                  <span className="pill">{d.classification || "—"}</span>
                </td>
                <td>
                  <span className={`pill ${d.status === "ready" ? "ok" : ""}`}>{d.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
