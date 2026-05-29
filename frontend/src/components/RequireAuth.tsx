import { useEffect, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { isAuthenticated } from "../types";
import { clearLocalAuth, refreshTokens } from "../lib/api";

type Status = "checking" | "ok" | "denied";

const FRESH_FLAG = "session:fresh";

/**
 * Gate for authed routes.
 *
 * The JS-visible `username` cookie lives 7 days but the HttpOnly access_token
 * lives only 15 minutes, so a hard refresh on a stale session would otherwise
 * render the protected UI based on a cookie that's long outlasted the session.
 *
 * On mount:
 *   1. If no `username` cookie → denied.
 *   2. If we just landed from a fresh login (sessionStorage flag) → render.
 *   3. Otherwise probe `GET /api/v1/auth/check`. 200 means the access_token
 *      is still alive, render. 401 means it's expired — escalate to
 *      `/api/v1/auth/refresh`. Backend rotates and sets new HttpOnly cookies.
 *   4. If refresh also 401s → clear the `username` cookie and bounce.
 */
export default function RequireAuth({ children }: { children: JSX.Element }) {
  const location = useLocation();
  const [status, setStatus] = useState<Status>(() => {
    if (!isAuthenticated()) return "denied";
    if (sessionStorage.getItem(FRESH_FLAG)) {
      sessionStorage.removeItem(FRESH_FLAG);
      return "ok";
    }
    return "checking";
  });

  useEffect(() => {
    if (status !== "checking") return;
    let cancelled = false;

    (async () => {
      const check = await fetch("/api/v1/auth/check", {
        method: "GET",
        credentials: "include",
      }).catch(() => null);

      if (cancelled) return;
      if (check && check.ok) {
        setStatus("ok");
        return;
      }

      const refreshed = await refreshTokens();
      if (cancelled) return;
      if (refreshed) {
        setStatus("ok");
      } else {
        clearLocalAuth();
        setStatus("denied");
      }
    })();

    return () => { cancelled = true; };
  }, [status]);

  if (status === "denied") {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  if (status === "checking") {
    return null;
  }
  return children;
}
