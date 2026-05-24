import { Link } from "react-router-dom";

export default function LandingPage() {
  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}>
      <header style={{
        position: "sticky",
        top: 0,
        zIndex: 40,
        borderBottom: "1px solid var(--border-color)",
        backgroundColor: "rgba(10, 10, 10, 0.8)",
        backdropFilter: "blur(12px)",
      }}>
        <div style={{
          margin: "0 auto",
          display: "flex",
          height: "60px",
          maxWidth: "1200px",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 24px"
        }}>
          <span style={{ fontFamily: "monospace", fontSize: "1.1rem", fontWeight: 600, letterSpacing: "-0.5px" }}>
            SlothOps <span style={{ color: "#888", fontSize: "0.85rem", fontWeight: "normal" }}>[Pre-Prod]</span>
          </span>
          <nav style={{ display: "flex", gap: "24px", alignItems: "center" }}>
            <Link to="/docs" style={{ fontFamily: "monospace", fontSize: "0.85rem", color: "var(--text-muted)", textDecoration: "none", transition: "color 0.2s" }} onMouseEnter={(e) => e.currentTarget.style.color = "var(--text-color)"} onMouseLeave={(e) => e.currentTarget.style.color = "var(--text-muted)"}>Documentation</Link>
            <Link to="/login" style={{
              backgroundColor: "var(--text-color)",
              color: "var(--bg-color)",
              padding: "6px 16px",
              borderRadius: "4px",
              fontFamily: "monospace",
              fontSize: "0.85rem",
              fontWeight: 600,
              textDecoration: "none",
              transition: "opacity 0.2s"
            }} onMouseEnter={(e) => e.currentTarget.style.opacity = "0.9"} onMouseLeave={(e) => e.currentTarget.style.opacity = "1"}>Sign In</Link>
          </nav>
        </div>
      </header>

      <main style={{ flex: 1 }}>
        <section style={{ padding: "100px 24px", borderBottom: "1px solid var(--border-color)", backgroundImage: "radial-gradient(circle at 50% 0%, rgba(147, 51, 234, 0.1), transparent 50%)" }}>
          <div style={{ maxWidth: "1200px", margin: "0 auto", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "64px", alignItems: "center" }}>
            <div>
              <h1 style={{ fontFamily: "monospace", fontSize: "3.5rem", fontWeight: 700, lineHeight: 1.1, margin: "0 0 24px 0", letterSpacing: "-2px" }}>
                Automate your <span style={{ color: "var(--accent)" }}>bug remediation</span> pipeline.
              </h1>
              <p style={{ color: "var(--text-muted)", fontSize: "1.1rem", lineHeight: 1.6, margin: "0 0 40px 0", maxWidth: "480px" }}>
                A closed-loop, production-aware pipeline that converts live application crashes into reviewed code fixes — automatically.
              </p>
              <Link to="/login" style={{
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
              }} onMouseEnter={(e) => e.currentTarget.style.backgroundColor = "var(--accent-hover)"} onMouseLeave={(e) => e.currentTarget.style.backgroundColor = "var(--accent)"}>
                Get Started →
              </Link>
            </div>
            
            <div style={{
              border: "1px solid var(--border-color)",
              backgroundColor: "var(--card-bg)",
              borderRadius: "8px",
              overflow: "hidden",
              boxShadow: "0 20px 40px rgba(0,0,0,0.4)"
            }}>
              <div style={{ display: "flex", alignItems: "center", borderBottom: "1px solid var(--border-color)", padding: "8px 16px", backgroundColor: "#1a1a1a" }}>
                <span style={{ fontFamily: "monospace", fontSize: "0.7rem", color: "var(--text-muted)" }}>~/slothops-engine — bash — 80×24</span>
              </div>
              <div style={{ padding: "20px", fontFamily: "monospace", fontSize: "0.8rem", color: "var(--text-muted)", lineHeight: 1.6 }}>
                <div><span style={{ color: "var(--text-color)" }}>$</span> docker compose up --build</div>
                <div style={{ marginLeft: "16px", color: "#737373", marginTop: "8px" }}>
                  <div>→ building web-builder...</div>
                  <div>→ building runtime...</div>
                  <div>→ starting postgres_db...</div>
                  <div style={{ color: "#4ade80" }}>→ slothops engine ready 🦥</div>
                </div>
                <div style={{ marginTop: "16px" }}><span style={{ color: "var(--text-color)" }}>$</span> <span style={{ animation: "blink 1s step-end infinite", borderRight: "8px solid var(--text-color)" }}></span></div>
              </div>
            </div>
          </div>
        </section>

        <section style={{ padding: "80px 24px", borderBottom: "1px solid var(--border-color)" }}>
          <div style={{ maxWidth: "1200px", margin: "0 auto" }}>
            <p style={{ fontFamily: "monospace", fontSize: "0.8rem", textTransform: "uppercase", letterSpacing: "2px", color: "var(--text-muted)", marginBottom: "40px" }}>Capabilities</p>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "24px" }}>
              <div style={{ padding: "32px", border: "1px solid var(--border-color)", backgroundColor: "var(--card-bg)", borderRadius: "8px" }}>
                <h3 style={{ fontFamily: "monospace", fontSize: "1.2rem", marginBottom: "16px" }}>Real-time Code Analysis</h3>
                <p style={{ color: "var(--text-muted)", lineHeight: 1.6, fontSize: "0.95rem" }}>Connects directly to Sentry and GitHub. When an exception occurs, SlothOps fetches the exact code context, dedupes it, and fingerprints the issue.</p>
              </div>
              <div style={{ padding: "32px", border: "1px solid var(--border-color)", backgroundColor: "var(--card-bg)", borderRadius: "8px" }}>
                <h3 style={{ fontFamily: "monospace", fontSize: "1.2rem", marginBottom: "16px" }}>Automated QA Suites</h3>
                <p style={{ color: "var(--text-muted)", lineHeight: 1.6, fontSize: "0.95rem" }}>Every generated PR is run through 6 distinct QA agents including regression, stress, performance, and functionality tests to ensure fix validity.</p>
              </div>
              <div style={{ padding: "32px", border: "1px solid var(--border-color)", backgroundColor: "var(--card-bg)", borderRadius: "8px" }}>
                <h3 style={{ fontFamily: "monospace", fontSize: "1.2rem", marginBottom: "16px" }}>Zero-Touch Rollbacks</h3>
                <p style={{ color: "var(--text-muted)", lineHeight: 1.6, fontSize: "0.95rem" }}>If a deployment fails, SlothOps plans a rollback to the last-known-good SHA and either auto-reverts or creates a governed rollback PR based on your policy.</p>
              </div>
            </div>
          </div>
        </section>

        <section style={{ padding: "100px 24px" }}>
          <div style={{ maxWidth: "800px", margin: "0 auto", textAlign: "center" }}>
            <h2 style={{ fontFamily: "monospace", fontSize: "2.5rem", fontWeight: 700, margin: "0 0 24px 0" }}>Slow is smooth. Smooth is fast.</h2>
            <p style={{ color: "var(--text-muted)", fontSize: "1.1rem", lineHeight: 1.6, marginBottom: "40px" }}>
              We don't ship half-baked features to hit a sprint deadline. We build things properly, test them obsessively, and release when they're actually ready. 
              SlothOps ensures your pipeline maintains quality without the developer toil.
            </p>
            <div style={{ display: "inline-flex", gap: "1px", backgroundColor: "var(--border-color)", border: "1px solid var(--border-color)", borderRadius: "8px", overflow: "hidden" }}>
              <div style={{ backgroundColor: "var(--card-bg)", padding: "24px 32px" }}>
                <div style={{ fontFamily: "monospace", fontSize: "2rem", fontWeight: 700, color: "var(--text-color)" }}>6</div>
                <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "4px" }}>QA Agents</div>
              </div>
              <div style={{ backgroundColor: "var(--card-bg)", padding: "24px 32px" }}>
                <div style={{ fontFamily: "monospace", fontSize: "2rem", fontWeight: 700, color: "var(--text-color)" }}>∞</div>
                <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "4px" }}>Hours Saved</div>
              </div>
              <div style={{ backgroundColor: "var(--card-bg)", padding: "24px 32px" }}>
                <div style={{ fontFamily: "monospace", fontSize: "2rem", fontWeight: 700, color: "var(--text-color)" }}>0</div>
                <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "4px" }}>Manual Reverts</div>
              </div>
            </div>
          </div>
        </section>
      </main>
      
      <footer style={{ borderTop: "1px solid var(--border-color)", padding: "40px 24px", textAlign: "center" }}>
        <div style={{ fontFamily: "monospace", fontSize: "2rem", fontWeight: 700, letterSpacing: "4px", marginBottom: "24px", color: "var(--border-color)" }}>ENHANCE</div>
        <p style={{ fontFamily: "monospace", fontSize: "0.8rem", color: "#737373" }}>© 2026 SlothOps. All rights reserved.</p>
      </footer>
      <style>
        {`
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
        `}
      </style>
    </div>
  );
}
