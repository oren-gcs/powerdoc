import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";

export default function Register() {
  const { register } = useAuth();
  const nav = useNavigate();
  const [form, setForm] = useState({ email: "", password: "", full_name: "", organization: "" });
  const [err, setErr] = useState("");
  const set = (k: string, v: string) => setForm({ ...form, [k]: v });

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setErr("");
    try {
      await register(form);
      nav("/app");
    } catch (ex: any) {
      setErr(ex.message);
    }
  };

  return (
    <form className="auth-box card" onSubmit={onSubmit}>
      <div className="eyebrow">New tenant</div>
      <h1 className="mark">Stand up an organization</h1>
      {["organization", "full_name", "email", "password"].map((k) => (
        <div className="field" style={{ marginTop: 12 }} key={k}>
          <label>{k.replace("_", " ")}</label>
          <input type={k === "password" ? "password" : "text"} value={(form as any)[k]} onChange={(e) => set(k, e.target.value)} />
        </div>
      ))}
      {err && <p className="pill bad">{err}</p>}
      <button className="btn primary" style={{ marginTop: 18, width: "100%" }}>
        Create and enter
      </button>
      <p className="muted">
        Already here? <Link to="/login">Sign in</Link>
      </p>
    </form>
  );
}
