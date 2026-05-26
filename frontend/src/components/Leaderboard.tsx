import { useEffect, useState } from "react";

type Entry = { username: string; score: number; played_at: string };

export default function Leaderboard({ game = "snake", refreshKey = 0 }: { game?: string; refreshKey?: number }) {
  const [entries, setEntries] = useState<Entry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true); setError("");
    try {
      const r = await fetch(`/api/v1/game/scores/leaderboard?game=${game}&limit=10`);
      if (!r.ok) throw new Error("fetch_failed");
      const data = await r.json();
      setEntries(data.entries ?? []);
    } catch { setError("Could not load scores"); }
    finally { setLoading(false); }
  }

  useEffect(() => { load(); }, [game, refreshKey]);

  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-bold text-white" style={{ fontFamily: "'Space Grotesk',sans-serif" }}>
          🏆 Leaderboard
        </h3>
        <button onClick={load} className="text-xs text-slate-400 hover:text-white transition">
          Refresh
        </button>
      </div>

      {loading && <p className="text-sm text-slate-500">Loading…</p>}
      {error && <p className="text-sm text-rose-400">{error}</p>}
      {!loading && !error && entries.length === 0 && (
        <p className="text-sm text-slate-500">No scores yet — be the first!</p>
      )}
      {!loading && entries.length > 0 && (
        <ol className="space-y-2">
          {entries.map((e, i) => (
            <li
              key={i}
              className="flex items-center gap-3 rounded-xl border border-white/5 bg-white/5 px-4 py-2.5 transition hover:bg-white/10"
            >
              <span className={`w-6 text-center text-sm font-bold ${i === 0 ? "text-yellow-400" : i === 1 ? "text-slate-300" : i === 2 ? "text-amber-600" : "text-slate-500"}`}>
                {i + 1}
              </span>
              <span className="flex-1 text-sm font-semibold text-white">{e.username}</span>
              <span className="text-sm font-bold text-cyan-400">{e.score} pts</span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
