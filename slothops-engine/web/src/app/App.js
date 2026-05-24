import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
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
    return (_jsxs(Routes, { children: [_jsx(Route, { path: "/", element: _jsx(LandingPage, {}) }), _jsx(Route, { path: "/docs", element: _jsx(DocsPage, {}) }), _jsx(Route, { path: "/login", element: _jsx(LoginPage, {}) }), _jsxs(Route, { element: _jsx(AppShell, {}), children: [_jsx(Route, { path: "/overview", element: _jsx(OverviewPage, {}) }), _jsx(Route, { path: "/repos", element: _jsx(ReposPage, {}) }), _jsx(Route, { path: "/qa", element: _jsx(QAPage, {}) }), _jsx(Route, { path: "/rollbacks", element: _jsx(RollbacksPage, {}) }), _jsx(Route, { path: "/audit", element: _jsx(AuditPage, {}) }), _jsx(Route, { path: "/settings", element: _jsx(SettingsPage, {}) })] })] }));
}
