import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useQuery } from "@tanstack/react-query";
import { getOverview } from "../api/dashboard";
export default function OverviewPage() {
    const { data, error, isLoading } = useQuery({
        queryKey: ["dashboard", "overview"],
        queryFn: getOverview,
    });
    if (isLoading)
        return _jsx("p", { children: "Loading\u2026" });
    if (error) {
        // Backend endpoint isn't wired yet — show a placeholder.
        return (_jsxs("div", { children: [_jsx("h1", { children: "Overview" }), _jsxs("p", { children: ["Dashboard endpoint ", _jsx("code", { children: "/api/dashboard/overview" }), " not yet implemented. Wire it up in ", _jsx("code", { children: "app/api/dashboard.py" }), "."] })] }));
    }
    return (_jsxs("div", { children: [_jsx("h1", { children: "Overview" }), _jsxs("p", { children: ["Workspace: ", data?.workspace_id] }), _jsxs("section", { children: [_jsx("h2", { children: "Repos" }), _jsx("ul", { children: data?.repos.map((r) => (_jsxs("li", { children: [r.repo_name, " \u2014 ", r.active ? "active" : "inactive"] }, r.repo_name))) })] }), _jsxs("section", { children: [_jsx("h2", { children: "Recent activity" }), _jsx("ul", { children: data?.recent_activity.map((a, i) => (_jsxs("li", { children: [a.ts, " \u2014 ", a.action] }, i))) })] })] }));
}
