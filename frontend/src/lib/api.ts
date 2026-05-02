import axios, { AxiosError } from "axios";

const TOKEN_KEY = "st.jwt";

// In dev we keep "/api" so Vite's proxy strips it and forwards to FastAPI on
// :8000 (see vite.config.ts). In Firebase Hosting deploys we set
// VITE_API_BASE_URL to the Cloud Run URL at build time so the SPA hits the
// backend cross-origin (CORS allow-list is on the FastAPI side).
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120_000,
});

api.interceptors.request.use((config) => {
  const token = loadToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

/** Redirect to /login on 401 so expired tokens boot the user out. */
let onUnauthorized: (() => void) | null = null;
export function setUnauthorizedHandler(fn: (() => void) | null) {
  onUnauthorized = fn;
}

api.interceptors.response.use(
  (r) => r,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      clearToken();
      onUnauthorized?.();
    }
    return Promise.reject(error);
  },
);

export function saveToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}
export function loadToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}
export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export function humanError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((d: { msg?: string; loc?: string[] }) => d.msg ?? JSON.stringify(d))
        .join("; ");
    }
    if (error.message) return error.message;
  }
  if (error instanceof Error) return error.message;
  return "Unexpected error";
}
