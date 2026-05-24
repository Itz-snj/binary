import { apiFetch } from "../lib/api";
export function getOverview() {
    return apiFetch("/api/dashboard/overview");
}
