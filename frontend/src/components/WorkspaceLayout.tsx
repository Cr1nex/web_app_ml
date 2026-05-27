import { Link, Outlet, useNavigate } from "react-router-dom";
import { clearAuth, getUsername } from "../types";
import LoggedInBadge from "./LoggedInBadge";

const NAV = [
  { to: "/app",         label: "Overview" },
  { to: "/app/game",    label: "🎮 Game"  },
  { to: "/app/predict", label: "📈 Predict" },
];

export default function WorkspaceLayout() {
  const navigate = useNavigate();
  const username = getUsername();

  async function handleLogout() {
    await clearAuth();   // calls POST /api/v1/auth/logout → clears HttpOnly cookies
    navigate("/");
  }

  return (
    <div className="min-h-screen bg-slate-950">
      {username && <LoggedInBadge username={username} />}

      <header className="border-b border-white/10 bg-slate-900/80 backdrop-blur-sm">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest text-cyan-400">
              Dashboard
            </p>
            <h1
              className="mt-0.5 text-xl font-bold text-white"
              style={{ fontFamily: "'Space Grotesk',sans-serif" }}
            >
              My Workspace
            </h1>
          </div>

          <div className="flex items-center gap-3">
            {username && (
              <span className="hidden text-sm text-slate-400 sm:block">
                Hi,{" "}
                <span className="font-semibold text-white">{username}</span>
              </span>
            )}
            <button
              onClick={handleLogout}
              className="rounded-full border border-rose-500/40 px-4 py-2 text-sm font-semibold text-rose-400 transition hover:bg-rose-500/10 hover:border-rose-400"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      <nav className="border-b border-white/10 bg-slate-900/60">
        <div className="mx-auto flex max-w-6xl gap-1 px-6 py-2">
          {NAV.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              className="rounded-lg px-4 py-2 text-sm font-medium text-slate-300 transition hover:bg-white/10 hover:text-white"
            >
              {item.label}
            </Link>
          ))}
        </div>
      </nav>

      <main className="mx-auto max-w-6xl px-6 py-10">
        <Outlet />
      </main>
    </div>
  );
}
