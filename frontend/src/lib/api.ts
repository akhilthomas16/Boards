/**
 * FastAPI client. Auth lives in httpOnly cookies set by the API; no token is ever readable from JS.
 * The API must be same-site with this app (e.g. localhost:3000 → localhost:8001) or the cookies aren't sent.
 */

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

interface FetchOptions extends RequestInit {
  skipRefresh?: boolean;
}

let refreshing: Promise<boolean> | null = null;

// One refresh at a time: each refresh token works once, so two parallel refreshes would end the session.
function refreshSession(): Promise<boolean> {
  refreshing ??= fetch(`${API_BASE}/api/auth/refresh`, { method: 'POST', credentials: 'include' })
    .then((res) => res.ok, () => false)
    .finally(() => { refreshing = null; });
  return refreshing;
}

export async function apiFetch<T = unknown>(
  endpoint: string,
  options: FetchOptions = {}
): Promise<T> {
  const { skipRefresh, ...fetchOptions } = options;
  const url = `${API_BASE}${endpoint}`;
  // JSON bodies are strings; FormData and URLSearchParams set their own Content-Type.
  const headers = typeof fetchOptions.body === 'string'
    ? { 'Content-Type': 'application/json', ...fetchOptions.headers }
    : fetchOptions.headers;
  const init: RequestInit = { ...fetchOptions, headers, credentials: 'include' };

  let res = await fetch(url, init);

  // Access cookie expired: rotate once and retry.
  if (res.status === 401 && !skipRefresh && await refreshSession()) {
    res = await fetch(url, init);
  }

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(typeof error.detail === 'string' ? error.detail : `API Error: ${res.status}`);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

// Convenience methods
export const api = {
  get: <T>(url: string) => apiFetch<T>(url),
  post: <T>(url: string, data: unknown) =>
    apiFetch<T>(url, { method: 'POST', body: JSON.stringify(data) }),
  patch: <T>(url: string, data: unknown) =>
    apiFetch<T>(url, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (url: string) => apiFetch(url, { method: 'DELETE' }),
  postForm: <T>(url: string, data: URLSearchParams, options: FetchOptions = {}) =>
    apiFetch<T>(url, { ...options, method: 'POST', body: data }),
  postMultipart: <T>(url: string, data: FormData) =>
    apiFetch<T>(url, { method: 'POST', body: data }),
};

export default api;
