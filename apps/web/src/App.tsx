import React from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import AppShell from "./layout/AppShell";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Overview from "./pages/Overview";
import Documents from "./pages/Documents";
import DocumentDetail from "./pages/DocumentDetail";
import Workflows from "./pages/Workflows";
import Automations from "./pages/Automations";
import Agents from "./pages/Agents";
import Analytics from "./pages/Analytics";
import Inbox from "./pages/Inbox";
import Admin from "./pages/Admin";

function Guard({ children }: { children: React.ReactElement }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="workspace muted">Opening the desk…</div>;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route
        path="/app"
        element={
          <Guard>
            <AppShell />
          </Guard>
        }
      >
        <Route index element={<Overview />} />
        <Route path="documents" element={<Documents />} />
        <Route path="documents/:id" element={<DocumentDetail />} />
        <Route path="workflows" element={<Workflows />} />
        <Route path="automations" element={<Automations />} />
        <Route path="agents" element={<Agents />} />
        <Route path="analytics" element={<Analytics />} />
        <Route path="inbox" element={<Inbox />} />
        <Route path="admin" element={<Admin />} />
      </Route>
      <Route path="*" element={<Navigate to="/" />} />
    </Routes>
  );
}
