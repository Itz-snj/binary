import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { login, signup } from "../api/auth";
export default function LoginPage() {
    const navigate = useNavigate();
    const [mode, setMode] = useState("login");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [workspace, setWorkspace] = useState("");
    const [error, setError] = useState(null);
    const [busy, setBusy] = useState(false);
    async function onSubmit(e) {
        e.preventDefault();
        setBusy(true);
        setError(null);
        try {
            if (mode === "login")
                await login(email, password);
            else
                await signup(email, password, workspace);
            navigate("/");
        }
        catch (err) {
            setError(err instanceof Error ? err.message : String(err));
        }
        finally {
            setBusy(false);
        }
    }
    return (_jsx("div", { style: {
            minHeight: "100vh",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "24px",
            backgroundImage: "radial-gradient(circle at top, rgba(147, 51, 234, 0.05), transparent 40%)"
        }, children: _jsxs("div", { style: {
                width: "100%",
                maxWidth: "400px",
                backgroundColor: "var(--card-bg)",
                border: "1px solid var(--border-color)",
                borderRadius: "12px",
                padding: "40px 32px",
                boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.5)"
            }, children: [_jsx("h1", { style: { fontFamily: "monospace", fontSize: "1.75rem", textAlign: "center", marginBottom: "32px", letterSpacing: "-0.5px" }, children: "SlothOps" }), _jsxs("form", { onSubmit: onSubmit, style: { display: "flex", flexDirection: "column", gap: "16px" }, children: [_jsxs("div", { children: [_jsx("label", { style: { display: "block", fontFamily: "monospace", fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: "8px" }, children: "Email" }), _jsx("input", { type: "email", placeholder: "you@company.com", value: email, onChange: (e) => setEmail(e.target.value), required: true, style: { width: "100%", boxSizing: "border-box" } })] }), _jsxs("div", { children: [_jsx("label", { style: { display: "block", fontFamily: "monospace", fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: "8px" }, children: "Password" }), _jsx("input", { type: "password", placeholder: "\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022", value: password, onChange: (e) => setPassword(e.target.value), required: true, style: { width: "100%", boxSizing: "border-box" } })] }), mode === "signup" && (_jsxs("div", { children: [_jsx("label", { style: { display: "block", fontFamily: "monospace", fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: "8px" }, children: "Workspace Name" }), _jsx("input", { type: "text", placeholder: "acme-corp", value: workspace, onChange: (e) => setWorkspace(e.target.value), required: true, style: { width: "100%", boxSizing: "border-box" } })] })), error && _jsx("div", { style: { color: "#ef4444", fontSize: "0.85rem", padding: "10px", backgroundColor: "rgba(239, 68, 68, 0.1)", borderRadius: "6px", border: "1px solid rgba(239, 68, 68, 0.2)" }, children: error }), _jsx("button", { type: "submit", disabled: busy, style: { width: "100%", marginTop: "8px", padding: "12px" }, children: busy ? "Authenticating..." : mode === "login" ? "Sign In" : "Create Workspace" })] }), _jsx("div", { style: { marginTop: "24px", textAlign: "center" }, children: _jsx("button", { type: "button", className: "secondary", style: { fontSize: "0.8rem" }, onClick: () => setMode(mode === "login" ? "signup" : "login"), children: mode === "login" ? "Need an account? Sign up" : "Already have an account? Sign in" }) })] }) }));
}
