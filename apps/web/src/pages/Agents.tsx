import { useEffect, useState } from "react";
import { AgentAPI } from "../api";

export default function Agents() {
  const [status, setStatus] = useState<any>(null);
  const [logs, setLogs] = useState<any[]>([]);
  const [skills, setSkills] = useState<any[]>([]);
  const [out, setOut] = useState("");
  const [prompt, setPrompt] = useState("Review the latest invoice intake and say what finance should do next.");

  useEffect(() => {
    AgentAPI.status().then(setStatus);
    AgentAPI.logs().then(setLogs);
    AgentAPI.skills().then(setSkills);
  }, []);

  return (
    <>
      <div className="eyebrow">Skills · MCP · orchestrator</div>
      <h1 className="mark" style={{ fontSize: 32 }}>
        Agents
      </h1>
      <div className="grid cards-3">
        <div className="card">
          <div className="eyebrow">Orchestrator</div>
          <p className="n mark" style={{ fontSize: 28 }}>
            {status?.orchestrator}
          </p>
          <div className="muted">{status?.skills} skills loaded</div>
        </div>
        <div className="card" data-demo="agent-ollama">
          <div className="eyebrow">Ollama</div>
          <p className="n mark" style={{ fontSize: 28 }}>
            {status?.ollama?.up ? "local" : "offline"}
          </p>
          <div className="muted">
            {status?.ollama?.up
              ? status.ollama.models?.length
                ? status.ollama.models.join(", ")
                : "Up — pull llama3.2"
              : `Start ollama serve at ${status?.ollama?.url || "http://127.0.0.1:11434"}`}
          </div>
        </div>
        {(status?.bindings || []).slice(0, 1).map((b: any) => (
          <div className="card" key={b.role}>
            <div className="eyebrow">{b.role}</div>
            <div className="mono">{b.model}</div>
            <div className="dim">{b.provider}</div>
          </div>
        ))}
      </div>
      <div className="split" style={{ marginTop: 16 }}>
        <div className="card">
          <div className="eyebrow">Run a skill</div>
          {skills.map((s) => (
            <button
              key={s.id}
              className="btn"
              style={{ margin: "6px 6px 0 0" }}
              onClick={async () => {
                const r = await AgentAPI.runSkill(s.id, prompt);
                setOut(`${s.name}\n\n${r.result}`);
              }}
            >
              {s.name}
            </button>
          ))}
          <textarea style={{ width: "100%", marginTop: 12, minHeight: 90 }} value={prompt} onChange={(e) => setPrompt(e.target.value)} />
          {out && <pre className="ocr">{out}</pre>}
        </div>
        <div className="card">
          <div className="eyebrow">Agent log</div>
          <table className="table">
            <tbody>
              {logs.map((l) => (
                <tr key={l.id}>
                  <td className="mono">{l.agent_role}</td>
                  <td className="muted">{l.summary?.slice(0, 100)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
