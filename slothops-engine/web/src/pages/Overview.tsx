import { useQuery } from "@tanstack/react-query";
import { getOverview } from "../api/dashboard";

export default function OverviewPage() {
  const { data, error, isLoading } = useQuery({
    queryKey: ["dashboard", "overview"],
    queryFn: getOverview,
  });

  if (isLoading) return <p>Loading…</p>;
  if (error) {
    // Backend endpoint isn't wired yet — show a placeholder.
    return (
      <div>
        <h1>Overview</h1>
        <p>
          Dashboard endpoint <code>/api/dashboard/overview</code> not yet
          implemented. Wire it up in <code>app/api/dashboard.py</code>.
        </p>
      </div>
    );
  }

  return (
    <div>
      <h1>Overview</h1>
      <p>Workspace: {data?.workspace_id}</p>
      <section>
        <h2>Repos</h2>
        <ul>
          {data?.repos.map((r) => (
            <li key={r.repo_name}>
              {r.repo_name} — {r.active ? "active" : "inactive"}
            </li>
          ))}
        </ul>
      </section>
      <section>
        <h2>Recent activity</h2>
        <ul>
          {data?.recent_activity.map((a, i) => (
            <li key={i}>
              {a.ts} — {a.action}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
