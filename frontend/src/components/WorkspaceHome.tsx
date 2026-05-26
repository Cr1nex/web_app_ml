const CARDS = [
  { title: "Auth Sessions", value: "Secured ✓", body: "RS256 JWT with key rotation and Redis-backed revocation." },
  { title: "Token Health",  value: "99.98%",   body: "Refresh token rotation with parent-chain revocation." },
  { title: "Gateway",       value: "Active",   body: "NGINX rate-limited proxy routing frontend and API traffic." },
];

export default function WorkspaceHome() {
  return (
    <div>
      <h2
        className="mb-8 text-2xl font-bold text-white"
        style={{ fontFamily: "'Space Grotesk',sans-serif" }}
      >
        Overview
      </h2>
      <div className="grid gap-5 sm:grid-cols-3">
        {CARDS.map((c) => (
          <article
            key={c.title}
            className="rounded-2xl border border-white/10 bg-white/5 p-5 transition hover:-translate-y-1 hover:bg-white/10"
          >
            <p className="text-xs font-semibold uppercase tracking-widest text-cyan-400">
              {c.title}
            </p>
            <p className="mt-2 text-2xl font-bold text-white">{c.value}</p>
            <p className="mt-2 text-sm leading-relaxed text-slate-400">{c.body}</p>
          </article>
        ))}
      </div>
    </div>
  );
}
