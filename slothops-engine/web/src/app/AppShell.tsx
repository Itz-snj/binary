import { Link, Outlet, useLocation } from "react-router-dom";

const NAV = [
  { to: "/", label: "Overview" },
  { to: "/repos", label: "Repos" },
  { to: "/qa", label: "QA" },
  { to: "/rollbacks", label: "Rollbacks" },
  { to: "/audit", label: "Audit" },
  { to: "/settings", label: "Settings" },
];

export default function AppShell() {
  const location = useLocation();
  return (
    <div style={{ display: "flex", minHeight: "100vh", fontFamily: "system-ui" }}>
      <aside style={{ width: 220, borderRight: "1px solid #2a2a2a", padding: 16 }}>
        <h2 style={{ marginTop: 0 }}>SlothOps</h2>
        <nav style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          {NAV.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              style={{
                padding: "6px 10px",
                borderRadius: 6,
                background:
                  location.pathname === item.to ? "#2a2a2a" : "transparent",
                color: "inherit",
                textDecoration: "none",
              }}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </aside>
      <main style={{ flex: 1, padding: 24 }}>
        <Outlet />
      </main>
    </div>
  );
}
