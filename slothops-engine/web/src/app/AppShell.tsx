import { Link, Outlet, useLocation } from "react-router-dom";

const NAV = [
  { to: "/overview", label: "Overview" },
  { to: "/repos", label: "Repos" },
  { to: "/qa", label: "QA" },
  { to: "/rollbacks", label: "Rollbacks" },
  { to: "/audit", label: "Audit" },
  { to: "/settings", label: "Settings" },
];

export default function AppShell() {
  const location = useLocation();
  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <aside style={{ width: 240, borderRight: "1px solid var(--border-color)", padding: "24px 16px", backgroundColor: "#050505" }}>
        <h2 style={{ fontFamily: "monospace", fontSize: "1.2rem", fontWeight: 600, letterSpacing: "-0.5px", marginBottom: "32px", padding: "0 10px" }}>
          SlothOps <span style={{ color: "#888", fontSize: "0.85rem", fontWeight: "normal" }}>[Dashboard]</span>
        </h2>
        <nav style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {NAV.map((item) => {
            const isActive = location.pathname.startsWith(item.to);
            return (
              <Link
                key={item.to}
                to={item.to}
                style={{
                  padding: "8px 12px",
                  borderRadius: 6,
                  fontFamily: "monospace",
                  fontSize: "0.9rem",
                  background: isActive ? "var(--sidebar-active)" : "transparent",
                  color: isActive ? "var(--sidebar-active-text)" : "var(--text-muted)",
                  textDecoration: "none",
                  transition: "background 0.2s, color 0.2s",
                  borderLeft: isActive ? "2px solid var(--accent)" : "2px solid transparent",
                }}
                onMouseEnter={(e) => {
                  if (!isActive) e.currentTarget.style.color = "var(--text-color)";
                }}
                onMouseLeave={(e) => {
                  if (!isActive) e.currentTarget.style.color = "var(--text-muted)";
                }}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </aside>
      <main style={{ flex: 1, padding: "40px 48px", overflowY: "auto" }}>
        <Outlet />
      </main>
    </div>
  );
}
