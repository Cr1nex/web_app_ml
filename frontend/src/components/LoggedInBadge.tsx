import { useEffect, useState } from "react";

export default function LoggedInBadge({ username }: { username: string }) {
  const [visible, setVisible] = useState(true);

  // Auto-hide after 6 s, but keep it available on hover
  useEffect(() => {
    const t = setTimeout(() => setVisible(false), 6000);
    return () => clearTimeout(t);
  }, []);

  if (!visible) {
    return (
      <button
        onClick={() => setVisible(true)}
        className="fixed right-5 top-5 z-50 h-8 w-8 rounded-full bg-cyan-500 text-white text-xs font-bold shadow-lg animate-pulse-glow"
        title={`Logged in as ${username}`}
      >
        ✓
      </button>
    );
  }

  return (
    <div className="logged-in-badge fixed right-5 top-5 z-50 flex items-center gap-2 rounded-full border border-cyan-500/40 bg-slate-900/95 px-4 py-2.5 shadow-xl shadow-black/40 backdrop-blur">
      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-cyan-500 text-xs font-bold text-white animate-pulse-glow">
        ✓
      </span>
      <span className="text-sm text-slate-300">
        You are logged in as{" "}
        <span className="font-bold text-white">{username}</span>
      </span>
      <button
        onClick={() => setVisible(false)}
        className="ml-1 text-slate-500 hover:text-slate-300 transition"
      >
        ✕
      </button>
    </div>
  );
}
