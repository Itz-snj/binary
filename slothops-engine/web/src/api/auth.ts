import { apiFetch, setToken } from "../lib/api";

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export async function login(email: string, password: string): Promise<LoginResponse> {
  const form = new URLSearchParams();
  form.set("username", email);
  form.set("password", password);
  const res = await apiFetch<LoginResponse>("/api/login", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form.toString(),
  });
  setToken(res.access_token);
  return res;
}

export async function signup(
  email: string,
  password: string,
  workspaceName: string,
): Promise<LoginResponse> {
  const res = await apiFetch<LoginResponse>("/api/signup", {
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

export function logout(): void {
  setToken(null);
}
