export type AuthMode = "login" | "signup";

export type User = {
  user_id: string;
  username: string;
  email: string;
};

export type TokenPair = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
};

export type AuthResponse = {
  user: User;
  tokens: TokenPair;
};

// ── Cookie helpers ──────────────────────────────────────────────────────────

/** Read a cookie value by name (works for non-HttpOnly cookies only). */
export function getCookie(name: string): string | null {
  const match = document.cookie.match(
    new RegExp("(?:^|;\\s*)" + name + "=([^;]*)")
  );
  return match ? decodeURIComponent(match[1]) : null;
}

/**
 * Returns true when the browser holds an auth session.
 * We check the readable `username` cookie set by the backend on login/register.
 * The actual access_token is HttpOnly and invisible to JS — that's intentional.
 */
export function isAuthenticated(): boolean {
  return !!getCookie("username");
}

/** Return the current username from the readable cookie. */
export function getUsername(): string | null {
  return getCookie("username");
}

/**
 * Log out: call the backend logout endpoint to clear HttpOnly cookies,
 * then wipe any remaining client-side state.
 */
export async function clearAuth(): Promise<void> {
  try {
    await fetch("/api/v1/auth/logout", {
      method: "POST",
      credentials: "include",
    });
  } catch {
    // ignore network errors — cookies may still expire on their own
  }
  // Manually expire the readable username cookie
  document.cookie = "username=; Max-Age=0; path=/; SameSite=Lax";
}

/**
 * @deprecated Tokens live in HttpOnly cookies — JS can't read them.
 * Use isAuthenticated() to gate UI; rely on credentials:"include" for API calls.
 */
export function getToken(): null {
  return null;
}
