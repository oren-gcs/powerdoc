import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";

export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("oren@gcs-tech.org");
  const [password, setPassword] = useState("DocFlow!2026");
  const [err, setErr] = useState("");

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setErr("");
    try {
      await login(email, password);
      nav("/app");
    } catch (ex: any) {
      setErr(ex.message);
    }
  };

  return (
    <form className="auth-box card" onSubmit={onSubmit} autoComplete="off">
      <div className="eyebrow">DocFlow</div>
      <h1 className="mark">Sign in to the desk</h1>
      <div className="field" style={{ marginTop: 16 }}>
        <label htmlFor="login-email">Email</label>
        <input id="login-email" name="email" autoComplete="off" value={email} onChange={(e) => setEmail(e.target.value)} />
      </div>
      <div className="field" style={{ marginTop: 12 }}>
        <label htmlFor="login-password">Password</label>
        <input id="login-password" name="password" type="password" autoComplete="off" value={password} onChange={(e) => setPassword(e.target.value)} />
      </div>
      {err && <p className="pill bad">{err}</p>}
      <button className="btn primary" style={{ marginTop: 18, width: "100%" }}>
        Enter
      </button>
      <p className="muted" style={{ marginTop: 14 }}>
        New org? <Link to="/register">Register</Link>
      </p>
    </form>
  );
}
