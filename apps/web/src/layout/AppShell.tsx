import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";

const links = [
  ["Overview", "/app"],
  ["Documents", "/app/documents"],
  ["Flows", "/app/workflows"],
  ["Automations", "/app/automations"],
  ["Agents", "/app/agents"],
  ["Analytics", "/app/analytics"],
  ["Inbox", "/app/inbox"],
  ["Admin", "/app/admin"],
];

export default function AppShell() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  return (
    <div className="shell">
      <aside className="rail">
        <div className="brand" onClick={() => nav("/app")} style={{ cursor: "pointer" }}>
          <div className="sigil">Df</div>
          <div>
            <div className="mark">DocFlow</div>
            <div className="eyebrow">operations desk</div>
          </div>
        </div>
        <nav>
          {links.map(([label, to]) => (
            <NavLink key={to} to={to} end={to === "/app"} className={({ isActive }) => (isActive ? "active" : "")}>
              {label}
            </NavLink>
          ))}
        </nav>
        <div style={{ marginTop: "auto" }}>
          <div className="muted" style={{ fontSize: 13, marginBottom: 8 }}>
            {user?.full_name}
            <div className="mono dim">{user?.role}</div>
          </div>
          <button className="btn" onClick={logout}>
            Sign out
          </button>
        </div>
      </aside>
      <div className="workspace">
        <Outlet />
      </div>
    </div>
  );
}
