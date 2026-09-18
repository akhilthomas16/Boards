/**
 * API calls from server components. Public reads only — the auth cookie belongs to the API origin
 * and never reaches this server, so anything user-specific stays in a client island.
 */

// Inside Docker the browser's NEXT_PUBLIC_API_URL (localhost) is this container's own loopback.
export const SERVER_API_BASE =
  process.env.API_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

/**
 * `revalidate` seconds of caching; 0 (the default) means always fresh, which is what detail pages
 * need — a cached fetch would survive router.refresh() and hide a just-posted topic or reply.
 */
export async function fetchApi<T>(path: string, revalidate = 0): Promise<T> {
  const res = await fetch(`${SERVER_API_BASE}${path}`, { next: { revalidate } });
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail || `API ${res.status} for ${path}`);
  }
  return res.json();
}

/** For data a page can render without (similar topics, trending). */
export async function fetchApiOr<T>(path: string, fallback: T, revalidate = 0): Promise<T> {
  try {
    return await fetchApi<T>(path, revalidate);
  } catch {
    return fallback;
  }
}
