import { useCallback, useEffect, useRef, useState } from "react";
import { isAuthenticated } from "../types";

const GRID = 20, CELL = 20, SZ = GRID * CELL;
type Pt = { x: number; y: number };
type Dir = "UP" | "DOWN" | "LEFT" | "RIGHT";

function randFood(snake: Pt[]): Pt {
  let f: Pt;
  do { f = { x: Math.floor(Math.random() * GRID), y: Math.floor(Math.random() * GRID) }; }
  while (snake.some((s) => s.x === f.x && s.y === f.y));
  return f;
}

export default function SnakeGame({ onPlayAgain }: { onPlayAgain?: () => void } = {}) {
  const cvs = useRef<HTMLCanvasElement>(null);
  const gs = useRef({
    snake: [{ x: 10, y: 10 }, { x: 9, y: 10 }, { x: 8, y: 10 }] as Pt[],
    dir: "RIGHT" as Dir, next: "RIGHT" as Dir,
    food: { x: 15, y: 10 } as Pt,
    score: 0, running: false,
  });
  const raf = useRef<number>();
  const lastT = useRef(0);
  const [score, setScore] = useState(0);
  const [over, setOver] = useState(false);
  const [saved, setSaved] = useState(false);
  const [started, setStarted] = useState(false);

  const draw = useCallback(() => {
    const c = cvs.current; if (!c) return;
    const ctx = c.getContext("2d")!;
    const { snake, food } = gs.current;
    ctx.fillStyle = "#020617"; ctx.fillRect(0, 0, SZ, SZ);
    ctx.strokeStyle = "rgba(255,255,255,0.03)"; ctx.lineWidth = 0.5;
    for (let i = 0; i <= GRID; i++) {
      ctx.beginPath(); ctx.moveTo(i * CELL, 0); ctx.lineTo(i * CELL, SZ); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(0, i * CELL); ctx.lineTo(SZ, i * CELL); ctx.stroke();
    }
    ctx.fillStyle = "#f97316"; ctx.shadowColor = "#f97316"; ctx.shadowBlur = 14;
    ctx.beginPath();
    ctx.arc(food.x * CELL + CELL / 2, food.y * CELL + CELL / 2, CELL / 2 - 2, 0, Math.PI * 2);
    ctx.fill(); ctx.shadowBlur = 0;
    snake.forEach((s, i) => {
      const alpha = 1 - (i / snake.length) * 0.55;
      ctx.fillStyle = i === 0 ? "#22d3ee" : `rgba(34,211,238,${alpha})`;
      ctx.shadowColor = "#22d3ee"; ctx.shadowBlur = i === 0 ? 14 : 0;
      ctx.beginPath();
      ctx.roundRect(s.x * CELL + 1, s.y * CELL + 1, CELL - 2, CELL - 2, 3);
      ctx.fill(); ctx.shadowBlur = 0;
    });
  }, []);

  const endGame = useCallback(async (finalScore: number) => {
    gs.current.running = false;
    setOver(true);
    // Only POST if logged in — cookies sent automatically via credentials:"include"
    if (isAuthenticated() && finalScore > 0) {
      try {
        const r = await fetch("/api/v1/game/scores", {
          method: "POST",
          credentials: "include",           // ← HttpOnly cookie sent automatically
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ score: finalScore, game_name: "snake" }),
        });
        if (r.ok) setSaved(true);
      } catch { /* silently ignore */ }
    }
  }, []);

  const loop = useCallback((ts: number) => {
    const s = gs.current; if (!s.running) return;
    if (ts - lastT.current >= 140) {
      lastT.current = ts; s.dir = s.next;
      const h = s.snake[0];
      const nh: Pt = {
        x: h.x + (s.dir === "RIGHT" ? 1 : s.dir === "LEFT" ? -1 : 0),
        y: h.y + (s.dir === "DOWN" ? 1 : s.dir === "UP" ? -1 : 0),
      };
      if (nh.x < 0 || nh.x >= GRID || nh.y < 0 || nh.y >= GRID ||
          s.snake.some((p) => p.x === nh.x && p.y === nh.y)) {
        endGame(s.score); return;
      }
      const ate = nh.x === s.food.x && nh.y === s.food.y;
      s.snake = [nh, ...s.snake];
      if (!ate) s.snake.pop();
      else { s.score += 10; s.food = randFood(s.snake); setScore(s.score); }
    }
    draw();
    raf.current = requestAnimationFrame(loop);
  }, [draw, endGame]);

  const start = useCallback(() => {
    if (over && onPlayAgain) onPlayAgain();
    if (raf.current) cancelAnimationFrame(raf.current);
    const sn = [{ x: 10, y: 10 }, { x: 9, y: 10 }, { x: 8, y: 10 }];
    gs.current = { snake: sn, dir: "RIGHT", next: "RIGHT", food: randFood(sn), score: 0, running: true };
    setScore(0); setOver(false); setSaved(false); setStarted(true); lastT.current = 0;
    raf.current = requestAnimationFrame(loop);
  }, [loop, over, onPlayAgain]);

  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      const d = gs.current.dir;
      if      (e.key === "ArrowUp"    && d !== "DOWN")  gs.current.next = "UP";
      else if (e.key === "ArrowDown"  && d !== "UP")    gs.current.next = "DOWN";
      else if (e.key === "ArrowLeft"  && d !== "RIGHT") gs.current.next = "LEFT";
      else if (e.key === "ArrowRight" && d !== "LEFT")  gs.current.next = "RIGHT";
      if (e.key.startsWith("Arrow")) e.preventDefault();
    };
    window.addEventListener("keydown", h, { passive: false });
    return () => {
      window.removeEventListener("keydown", h);
      if (raf.current) cancelAnimationFrame(raf.current);
    };
  }, []);

  useEffect(() => { draw(); }, [draw]);

  return (
    <div className="flex flex-col items-center gap-5">
      <div className="flex w-full max-w-[400px] items-center justify-between">
        <span className="text-sm font-semibold text-slate-400">Score</span>
        <span className="text-3xl font-black text-white">{score}</span>
      </div>

      <div className="game-canvas-wrap">
        <canvas ref={cvs} width={SZ} height={SZ} className="block" />
      </div>

      {!started && !over && (
        <button onClick={start} className="rounded-xl bg-cyan-500 px-8 py-3 text-sm font-bold text-white transition hover:bg-cyan-400 hover:scale-105 active:scale-95">
          Start Game
        </button>
      )}

      {over && (
        <div className="text-center">
          <p className="text-xl font-bold text-white">
            Game Over — <span className="text-cyan-400">{score} pts</span>
          </p>
          {saved && <p className="mt-1 text-sm text-emerald-400">✓ Score saved to leaderboard!</p>}
          {!isAuthenticated() && score > 0 && (
            <p className="mt-1 text-sm text-slate-500">
              <a href="/login" className="text-cyan-400 underline">Log in</a> to save your scores
            </p>
          )}
          <button onClick={start} className="mt-4 rounded-xl bg-cyan-500 px-8 py-3 text-sm font-bold text-white transition hover:bg-cyan-400 hover:scale-105">
            Play Again
          </button>
        </div>
      )}

      <div className="mt-2 grid grid-cols-3 gap-1 sm:hidden">
        {[
          { label: "↑", cls: "col-start-2", fn: () => { if (gs.current.dir !== "DOWN")  gs.current.next = "UP";    } },
          { label: "←", cls: "",            fn: () => { if (gs.current.dir !== "RIGHT") gs.current.next = "LEFT";  } },
          { label: "↓", cls: "",            fn: () => { if (gs.current.dir !== "UP")    gs.current.next = "DOWN";  } },
          { label: "→", cls: "",            fn: () => { if (gs.current.dir !== "LEFT")  gs.current.next = "RIGHT"; } },
        ].map((b, i) => (
          <button key={i} onPointerDown={b.fn} className={`${b.cls} rounded-lg bg-white/10 px-4 py-3 text-white active:bg-white/20`}>
            {b.label}
          </button>
        ))}
      </div>

      <p className="text-xs text-slate-600">Use arrow keys · Each food = 10 pts</p>
    </div>
  );
}
