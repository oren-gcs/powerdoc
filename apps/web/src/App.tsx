import React from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import AppShell from "./layout/AppShell";
import HomePage from "./pages/Landing";
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
import Manage from "./pages/Manage";
import Forms from "./pages/Forms";
import FormBuilder from "./pages/FormBuilder";
import FormAnswered from "./pages/FormAnswered";
import FillForm from "./pages/FillForm";
import Connectors from "./pages/Connectors";

function Guard({ children }: { children: React.ReactElement }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="workspace muted">Opening the desk…</div>;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/f/:token" element={<FillForm />} />
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
        <Route path="forms" element={<Forms />} />
        <Route path="forms/new" element={<FormBuilder />} />
        <Route path="forms/:id/answered" element={<FormAnswered />} />
        <Route path="forms/:id" element={<FormBuilder />} />
        <Route path="workflows" element={<Workflows />} />
        <Route path="automations" element={<Automations />} />
        <Route path="agents" element={<Agents />} />
        <Route path="analytics" element={<Analytics />} />
        <Route path="inbox" element={<Inbox />} />
        <Route path="manage" element={<Manage />} />
        <Route path="connectors" element={<Connectors />} />
        <Route path="admin" element={<Admin />} />
      </Route>
      <Route path="*" element={<Navigate to="/" />} />
    </Routes>
  );
}
