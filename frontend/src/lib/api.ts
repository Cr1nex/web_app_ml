/**
 * Fetch wrapper that survives access-token expiry.
 *
 * Why: the backend hands out HttpOnly cookies — `access_token` lives 15 min,
 * `refresh_token` lives 7 days, and the JS-readable `username` cookie lives
 * 7 days. After 15 min the API rightfully 401s, but `isAuthenticated()`
 * still returns true (because `username` is still set), so without this
 * wrapper the UI claims you're logged in while every call silently fails.
 *
 * Behaviour:
 *   1. Make the request with `credentials: "include"`.
 *   2. On 401 (or 419), call `/api/v1/auth/refresh` exactly once and retry.
 *   3. If refresh fails, drop the `username` cookie and bounce to `/login`.
 *
 * A single in-flight refresh is shared by concurrent callers so we don't
 * stampede the refresh endpoint.
 */

let refreshInFlight: Promise<boolean> | null = null;

/** Ask the backend to mint a fresh access_token cookie. The HttpOnly
 *  refresh_token cookie is sent automatically by the browser — no body
 *  needed. Shared across concurrent callers. */
export async function refreshTokens(): Promise<boolean> {
  if (!refreshInFlight) {
    refreshInFlight = fetch("/api/v1/auth/refresh", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    })
      .then(r => r.ok)
      .catch(() => false)
      .finally(() => { refreshInFlight = null; });
  }
  return refreshInFlight;
}

/** Clear the JS-visible "I am logged in" marker. Use before navigating to /login. */
export function clearLocalAuth() {
  document.cookie = "username=; Max-Age=0; path=/; SameSite=Lax";
}

function bounceToLogin() {
  clearLocalAuth();
  if (typeof window !== "undefined" && window.location.pathname !== "/login") {
    window.location.assign("/login");
  }
}

export async function apiFetch(input: RequestInfo, init: RequestInit = {}): Promise<Response> {
  const opts: RequestInit = { ...init, credentials: "include" };

  let r = await fetch(input, opts);
  if (r.status !== 401) return r;

  const refreshed = await refreshTokens();
  if (!refreshed) {
    bounceToLogin();
    return r;
  }

  r = await fetch(input, opts);
  if (r.status === 401) bounceToLogin();
  return r;
}
