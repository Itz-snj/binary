import { Route, Routes } from "react-router-dom";
import AppShell from "./AppShell";
import LandingPage from "../pages/Landing";
import DocsPage from "../pages/Docs";
import OverviewPage from "../pages/Overview";
import LoginPage from "../pages/Login";
import ReposPage from "../pages/Repos";
import QAPage from "../pages/QA";
import RollbacksPage from "../pages/Rollbacks";
import AuditPage from "../pages/Audit";
import SettingsPage from "../pages/Settings";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/docs" element={<DocsPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route element={<AppShell />}>
        <Route path="/overview" element={<OverviewPage />} />
        <Route path="/repos" element={<ReposPage />} />
        <Route path="/qa" element={<QAPage />} />
        <Route path="/rollbacks" element={<RollbacksPage />} />
        <Route path="/audit" element={<AuditPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}
