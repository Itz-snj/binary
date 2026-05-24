import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { Link } from "react-router-dom";
export default function LandingPage() {
    return (_jsxs("div", { style: { display: "flex", flexDirection: "column", minHeight: "100vh" }, children: [_jsx("header", { style: {
                    position: "sticky",
                    top: 0,
                    zIndex: 40,
                    borderBottom: "1px solid var(--border-color)",
                    backgroundColor: "rgba(10, 10, 10, 0.8)",
                    backdropFilter: "blur(12px)",
                }, children: _jsxs("div", { style: {
                        margin: "0 auto",
                        display: "flex",
                        height: "60px",
                        maxWidth: "1200px",
                        alignItems: "center",
                        justifyContent: "space-between",
                        padding: "0 24px"
                    }, children: [_jsxs("span", { style: { fontFamily: "monospace", fontSize: "1.1rem", fontWeight: 600, letterSpacing: "-0.5px" }, children: ["SlothOps ", _jsx("span", { style: { color: "#888", fontSize: "0.85rem", fontWeight: "normal" }, children: "[Pre-Prod]" })] }), _jsxs("nav", { style: { display: "flex", gap: "24px", alignItems: "center" }, children: [_jsx(Link, { to: "/docs", style: { fontFamily: "monospace", fontSize: "0.85rem", color: "var(--text-muted)", textDecoration: "none", transition: "color 0.2s" }, onMouseEnter: (e) => e.currentTarget.style.color = "var(--text-color)", onMouseLeave: (e) => e.currentTarget.style.color = "var(--text-muted)", children: "Documentation" }), _jsx(Link, { to: "/login", style: {
                                        backgroundColor: "var(--text-color)",
                                        color: "var(--bg-color)",
                                        padding: "6px 16px",
                                        borderRadius: "4px",
                                        fontFamily: "monospace",
                                        fontSize: "0.85rem",
                                        fontWeight: 600,
                                        textDecoration: "none",
                                        transition: "opacity 0.2s"
                                    }, onMouseEnter: (e) => e.currentTarget.style.opacity = "0.9", onMouseLeave: (e) => e.currentTarget.style.opacity = "1", children: "Sign In" })] })] }) }), _jsxs("main", { style: { flex: 1 }, children: [_jsx("section", { style: { padding: "100px 24px", borderBottom: "1px solid var(--border-color)", backgroundImage: "radial-gradient(circle at 50% 0%, rgba(147, 51, 234, 0.1), transparent 50%)" }, children: _jsxs("div", { style: { maxWidth: "1200px", margin: "0 auto", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "64px", alignItems: "center" }, children: [_jsxs("div", { children: [_jsxs("h1", { style: { fontFamily: "monospace", fontSize: "3.5rem", fontWeight: 700, lineHeight: 1.1, margin: "0 0 24px 0", letterSpacing: "-2px" }, children: ["Automate your ", _jsx("span", { style: { color: "var(--accent)" }, children: "bug remediation" }), " pipeline."] }), _jsx("p", { style: { color: "var(--text-muted)", fontSize: "1.1rem", lineHeight: 1.6, margin: "0 0 40px 0", maxWidth: "480px" }, children: "A closed-loop, production-aware pipeline that converts live application crashes into reviewed code fixes \u2014 automatically." }), _jsx(Link, { to: "/login", style: {
                                                display: "inline-block",
                                                border: "1px solid var(--border-color)",
                                                backgroundColor: "var(--accent)",
                                                color: "#fff",
                                                padding: "12px 24px",
                                                fontFamily: "monospace",
                                                fontSize: "0.9rem",
                                                fontWeight: 600,
                                                textDecoration: "none",
                                                borderRadius: "4px",
                                                transition: "background-color 0.2s"
                                            }, onMouseEnter: (e) => e.currentTarget.style.backgroundColor = "var(--accent-hover)", onMouseLeave: (e) => e.currentTarget.style.backgroundColor = "var(--accent)", children: "Get Started \u2192" })] }), _jsxs("div", { style: {
                                        border: "1px solid var(--border-color)",
                                        backgroundColor: "var(--card-bg)",
                                        borderRadius: "8px",
                                        overflow: "hidden",
                                        boxShadow: "0 20px 40px rgba(0,0,0,0.4)"
                                    }, children: [_jsx("div", { style: { display: "flex", alignItems: "center", borderBottom: "1px solid var(--border-color)", padding: "8px 16px", backgroundColor: "#1a1a1a" }, children: _jsx("span", { style: { fontFamily: "monospace", fontSize: "0.7rem", color: "var(--text-muted)" }, children: "~/slothops-engine \u2014 bash \u2014 80\u00D724" }) }), _jsxs("div", { style: { padding: "20px", fontFamily: "monospace", fontSize: "0.8rem", color: "var(--text-muted)", lineHeight: 1.6 }, children: [_jsxs("div", { children: [_jsx("span", { style: { color: "var(--text-color)" }, children: "$" }), " docker compose up --build"] }), _jsxs("div", { style: { marginLeft: "16px", color: "#737373", marginTop: "8px" }, children: [_jsx("div", { children: "\u2192 building web-builder..." }), _jsx("div", { children: "\u2192 building runtime..." }), _jsx("div", { children: "\u2192 starting postgres_db..." }), _jsx("div", { style: { color: "#4ade80" }, children: "\u2192 slothops engine ready \uD83E\uDDA5" })] }), _jsxs("div", { style: { marginTop: "16px" }, children: [_jsx("span", { style: { color: "var(--text-color)" }, children: "$" }), " ", _jsx("span", { style: { animation: "blink 1s step-end infinite", borderRight: "8px solid var(--text-color)" } })] })] })] })] }) }), _jsx("section", { style: { padding: "80px 24px", borderBottom: "1px solid var(--border-color)" }, children: _jsxs("div", { style: { maxWidth: "1200px", margin: "0 auto" }, children: [_jsx("p", { style: { fontFamily: "monospace", fontSize: "0.8rem", textTransform: "uppercase", letterSpacing: "2px", color: "var(--text-muted)", marginBottom: "40px" }, children: "Capabilities" }), _jsxs("div", { style: { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "24px" }, children: [_jsxs("div", { style: { padding: "32px", border: "1px solid var(--border-color)", backgroundColor: "var(--card-bg)", borderRadius: "8px" }, children: [_jsx("h3", { style: { fontFamily: "monospace", fontSize: "1.2rem", marginBottom: "16px" }, children: "Real-time Code Analysis" }), _jsx("p", { style: { color: "var(--text-muted)", lineHeight: 1.6, fontSize: "0.95rem" }, children: "Connects directly to Sentry and GitHub. When an exception occurs, SlothOps fetches the exact code context, dedupes it, and fingerprints the issue." })] }), _jsxs("div", { style: { padding: "32px", border: "1px solid var(--border-color)", backgroundColor: "var(--card-bg)", borderRadius: "8px" }, children: [_jsx("h3", { style: { fontFamily: "monospace", fontSize: "1.2rem", marginBottom: "16px" }, children: "Automated QA Suites" }), _jsx("p", { style: { color: "var(--text-muted)", lineHeight: 1.6, fontSize: "0.95rem" }, children: "Every generated PR is run through 6 distinct QA agents including regression, stress, performance, and functionality tests to ensure fix validity." })] }), _jsxs("div", { style: { padding: "32px", border: "1px solid var(--border-color)", backgroundColor: "var(--card-bg)", borderRadius: "8px" }, children: [_jsx("h3", { style: { fontFamily: "monospace", fontSize: "1.2rem", marginBottom: "16px" }, children: "Zero-Touch Rollbacks" }), _jsx("p", { style: { color: "var(--text-muted)", lineHeight: 1.6, fontSize: "0.95rem" }, children: "If a deployment fails, SlothOps plans a rollback to the last-known-good SHA and either auto-reverts or creates a governed rollback PR based on your policy." })] })] })] }) }), _jsx("section", { style: { padding: "100px 24px" }, children: _jsxs("div", { style: { maxWidth: "800px", margin: "0 auto", textAlign: "center" }, children: [_jsx("h2", { style: { fontFamily: "monospace", fontSize: "2.5rem", fontWeight: 700, margin: "0 0 24px 0" }, children: "Slow is smooth. Smooth is fast." }), _jsx("p", { style: { color: "var(--text-muted)", fontSize: "1.1rem", lineHeight: 1.6, marginBottom: "40px" }, children: "We don't ship half-baked features to hit a sprint deadline. We build things properly, test them obsessively, and release when they're actually ready. SlothOps ensures your pipeline maintains quality without the developer toil." }), _jsxs("div", { style: { display: "inline-flex", gap: "1px", backgroundColor: "var(--border-color)", border: "1px solid var(--border-color)", borderRadius: "8px", overflow: "hidden" }, children: [_jsxs("div", { style: { backgroundColor: "var(--card-bg)", padding: "24px 32px" }, children: [_jsx("div", { style: { fontFamily: "monospace", fontSize: "2rem", fontWeight: 700, color: "var(--text-color)" }, children: "6" }), _jsx("div", { style: { fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "4px" }, children: "QA Agents" })] }), _jsxs("div", { style: { backgroundColor: "var(--card-bg)", padding: "24px 32px" }, children: [_jsx("div", { style: { fontFamily: "monospace", fontSize: "2rem", fontWeight: 700, color: "var(--text-color)" }, children: "\u221E" }), _jsx("div", { style: { fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "4px" }, children: "Hours Saved" })] }), _jsxs("div", { style: { backgroundColor: "var(--card-bg)", padding: "24px 32px" }, children: [_jsx("div", { style: { fontFamily: "monospace", fontSize: "2rem", fontWeight: 700, color: "var(--text-color)" }, children: "0" }), _jsx("div", { style: { fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "4px" }, children: "Manual Reverts" })] })] })] }) })] }), _jsxs("footer", { style: { borderTop: "1px solid var(--border-color)", padding: "40px 24px", textAlign: "center" }, children: [_jsx("div", { style: { fontFamily: "monospace", fontSize: "2rem", fontWeight: 700, letterSpacing: "4px", marginBottom: "24px", color: "var(--border-color)" }, children: "ENHANCE" }), _jsx("p", { style: { fontFamily: "monospace", fontSize: "0.8rem", color: "#737373" }, children: "\u00A9 2026 SlothOps. All rights reserved." })] }), _jsx("style", { children: `
          @keyframes blink {
            0%, 100% { border-color: transparent }
            50% { border-color: var(--text-color) }
          }
          @media (max-width: 768px) {
            main section:first-of-type > div {
              grid-template-columns: 1fr !important;
            }
            h1 {
              font-size: 2.5rem !important;
            }
          }
        ` })] }));
}
