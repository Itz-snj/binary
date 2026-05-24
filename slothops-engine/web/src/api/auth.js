import { apiFetch, setToken } from "../lib/api";
export async function login(email, password) {
    const form = new URLSearchParams();
    form.set("username", email);
    form.set("password", password);
    const res = await apiFetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: form.toString(),
    });
    setToken(res.access_token);
    return res;
}
export async function signup(email, password, workspaceName) {
    const res = await apiFetch("/api/signup", {
        method: "POST",
        body: JSON.stringify({
            email,
            password,
            workspace_name: workspaceName,
        }),
    });
    setToken(res.access_token);
    return res;
}
export function logout() {
    setToken(null);
}
