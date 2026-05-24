import { apiFetch } from "../lib/api";

// View models — kept in sync with app/schemas/dashboard.py on the backend.
export interface DashboardMetric {
  name: string;
  value: number;
  unit?: string | null;
}

export interface DashboardActivityItem {
  ts: string;
  actor?: string | null;
  action: string;
  target_type?: string | null;
  target_id?: string | null;
  metadata?: Record<string, unknown>;
}

export interface DashboardRepoCard {
  repo_name: string;
  active: boolean;
  sentry_project_slug?: string | null;
  last_qa_status?: string | null;
  last_rollback_status?: string | null;
  open_issues?: number;
}

export interface DashboardOverview {
  workspace_id: string;
  metrics: DashboardMetric[];
  repos: DashboardRepoCard[];
  recent_activity: DashboardActivityItem[];
  health: Record<string, string>;
}

export function getOverview(): Promise<DashboardOverview> {
  return apiFetch<DashboardOverview>("/api/dashboard/overview");
}
