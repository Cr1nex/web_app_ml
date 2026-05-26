import { useState } from "react";
import SnakeGame from "./SnakeGame";
import Leaderboard from "./Leaderboard";
import { isAuthenticated } from "../types";

export default function GamePage() {
  const [refreshKey, setRefreshKey] = useState(0);

  return (
    <div>
      <div className="mb-8">
        <h2
          className="text-2xl font-bold text-white"
          style={{ fontFamily: "'Space Grotesk',sans-serif" }}
        >
          🎮 Snake
        </h2>
        <p className="mt-1 text-sm text-slate-400">
          {isAuthenticated()
            ? "You're logged in — your scores will be saved automatically."
            : "Playing as guest — scores won't be saved. Log in to compete!"}
        </p>
      </div>

      <div className="grid gap-8 lg:grid-cols-[auto_1fr]">
        <SnakeGame onPlayAgain={() => setRefreshKey(k => k + 1)} />
        <Leaderboard refreshKey={refreshKey} />
      </div>
    </div>
  );
}
