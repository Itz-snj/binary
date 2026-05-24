// Thin fetch wrapper that attaches the JWT from localStorage and
// surfaces non-2xx as thrown errors. Endpoints live in src/api/*.
const TOKEN_KEY = "slothops.token";
export function getToken() {
    return localStorage.getItem(TOKEN_KEY);
}
export function setToken(token) {
    if (token === null)
        localStorage.removeItem(TOKEN_KEY);
    else
        localStorage.setItem(TOKEN_KEY, token);
}
export class ApiError extends Error {
    status;
    body;
    constructor(status, body) {
        super(`API ${status}`);
        this.status = status;
        this.body = body;
    }
}
export async function apiFetch(path, init = {}) {
    const headers = new Headers(init.headers);
    if (!headers.has("Content-Type") && init.body && typeof init.body === "string") {
        headers.set("Content-Type", "application/json");
    }
    const token = getToken();
    if (token)
        headers.set("Authorization", `Bearer ${token}`);
    const res = await fetch(path, { ...init, headers });
    const text = await res.text();
    const body = text ? JSON.parse(text) : null;
    if (!res.ok)
        throw new ApiError(res.status, body);
    return body;
}
