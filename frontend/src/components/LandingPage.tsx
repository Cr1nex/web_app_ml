import { Link } from "react-router-dom";

const SKILLS = [
  {
    icon: "🤖",
    title: "AI & Machine Learning",
    desc: "Building and deploying ML models — from training transformers to fine-tuning LLMs, feature engineering, and production inference pipelines.",
    tags: ["PyTorch", "HuggingFace", "Scikit-learn", "MLflow"],
    color: "from-violet-500/20 to-purple-500/10",
    border: "border-violet-500/30",
    glow: "hover:shadow-violet-500/20",
  },
  {
    icon: "🌐",
    title: "Fullstack Development",
    desc: "End-to-end web applications with modern React frontends and high-performance FastAPI/Node.js backends, backed by PostgreSQL and Redis.",
    tags: ["React", "FastAPI", "TypeScript", "PostgreSQL"],
    color: "from-cyan-500/20 to-sky-500/10",
    border: "border-cyan-500/30",
    glow: "hover:shadow-cyan-500/20",
  },
  {
    icon: "🔐",
    title: "Auth & Security",
    desc: "Designing secure authentication systems — JWT with RS256 key rotation, JWKS endpoints, refresh token families, rate limiting, and session management.",
    tags: ["JWT / JWKS", "OAuth2", "Redis sessions", "bcrypt"],
    color: "from-emerald-500/20 to-green-500/10",
    border: "border-emerald-500/30",
    glow: "hover:shadow-emerald-500/20",
  },
  {
    icon: "☸️",
    title: "MLOps & Infrastructure",
    desc: "Containerising ML workloads and deploying them on Kubernetes. CI/CD pipelines, service meshes, observability, and cloud-native architecture.",
    tags: ["Kubernetes", "Docker", "RabbitMQ", "Nginx"],
    color: "from-orange-500/20 to-amber-500/10",
    border: "border-orange-500/30",
    glow: "hover:shadow-orange-500/20",
  },
];

const PROJECTS = [
  {
    title: "Kubernetes Auth Microservice",
    desc: "Production-grade JWT auth stack running on Kind — RS256 key rotation, JWKS endpoint, Redis token store, RabbitMQ audit logging, NGINX rate-limited gateway, and Alembic-managed PostgreSQL.",
    tags: ["FastAPI", "Kind / K8s", "Redis", "PostgreSQL"],
    badge: "This project",
    badgeColor: "bg-cyan-500/20 text-cyan-300 border-cyan-500/30",
  },
  {
    title: "ML Model Serving Pipeline",
    desc: "End-to-end pipeline from data preprocessing to model serving: automated retraining, versioned artifact storage, A/B traffic splitting, and Prometheus metrics.",
    tags: ["MLflow", "FastAPI", "Docker", "Prometheus"],
    badge: "MLOps",
    badgeColor: "bg-violet-500/20 text-violet-300 border-violet-500/30",
  },
  {
    title: "LLM Fine-Tuning & RAG",
    desc: "Domain-specific fine-tuning of open-source LLMs combined with a retrieval-augmented generation layer for grounded, low-hallucination responses.",
    tags: ["HuggingFace", "PEFT / LoRA", "FAISS", "LangChain"],
    badge: "AI / NLP",
    badgeColor: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
  },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen">
      {/* ── Hero ─────────────────────────────────────────────── */}
      <section className="hero-bg relative">
        <div className="relative z-10 mx-auto max-w-6xl px-6 py-28 sm:py-36">
          <p className="animate-fade-in-up text-sm font-semibold uppercase tracking-widest text-cyan-400">
            AI Engineer · MLOps · Fullstack
          </p>
          <h1
            className="animate-fade-in-up delay-100 mt-4 text-5xl font-black leading-tight text-white sm:text-7xl"
            style={{ fontFamily: "'Space Grotesk',sans-serif" }}
          >
            I build{" "}
            <span className="bg-gradient-to-r from-cyan-400 to-emerald-400 bg-clip-text text-transparent">
              intelligent
            </span>
            <br />systems.
          </h1>
          <p className="animate-fade-in-up delay-200 mt-6 max-w-xl text-lg text-slate-300">
            From ML model training to Kubernetes-native deployments — I design
            and ship full-stack AI products end-to-end.
          </p>
          <div className="animate-fade-in-up delay-300 mt-10 flex flex-wrap gap-4">
            <Link
              to="/signup"
              className="rounded-full bg-cyan-500 px-7 py-3 text-sm font-bold text-white transition hover:bg-cyan-400 hover:scale-105 active:scale-95"
            >
              Get Started
            </Link>
            <Link
              to="/login"
              className="rounded-full border border-white/20 px-7 py-3 text-sm font-bold text-white transition hover:bg-white/10"
            >
              Sign In
            </Link>
            <Link
              to="/app/game"
              className="rounded-full border border-orange-500/40 px-7 py-3 text-sm font-bold text-orange-400 transition hover:bg-orange-500/10"
            >
              🎮 Play Snake
            </Link>
          </div>
        </div>

        {/* decorative blobs */}
        <div className="pointer-events-none absolute right-0 top-1/4 h-64 w-64 rounded-full bg-cyan-500/10 blur-3xl animate-float" />
        <div className="pointer-events-none absolute bottom-0 left-1/3 h-48 w-48 rounded-full bg-orange-500/10 blur-3xl animate-float delay-300" />
      </section>

      {/* ── Skills ───────────────────────────────────────────── */}
      <section className="landing-bg py-24">
        <div className="mx-auto max-w-6xl px-6">
          <p className="text-center text-sm font-semibold uppercase tracking-widest text-cyan-600">
            Core Expertise
          </p>
          <h2
            className="mt-3 text-center text-4xl font-bold text-slate-900"
            style={{ fontFamily: "'Space Grotesk',sans-serif" }}
          >
            What I do best
          </h2>
          <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {SKILLS.map((s) => (
              <div
                key={s.title}
                className={`skill-card rounded-2xl border bg-gradient-to-br p-6 hover:shadow-lg ${s.color} ${s.border} ${s.glow}`}
              >
                <span className="text-3xl">{s.icon}</span>
                <h3 className="mt-3 text-base font-bold text-slate-900">{s.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-600">{s.desc}</p>
                <div className="mt-4 flex flex-wrap gap-1.5">
                  {s.tags.map((t) => (
                    <span
                      key={t}
                      className="rounded-full border border-slate-300/60 bg-white/70 px-2.5 py-0.5 text-xs font-medium text-slate-700"
                    >
                      {t}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Projects ─────────────────────────────────────────── */}
      <section className="bg-slate-900 py-24">
        <div className="mx-auto max-w-6xl px-6">
          <p className="text-sm font-semibold uppercase tracking-widest text-cyan-400">
            Portfolio
          </p>
          <h2
            className="mt-3 text-4xl font-bold text-white"
            style={{ fontFamily: "'Space Grotesk',sans-serif" }}
          >
            Selected projects
          </h2>
          <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {PROJECTS.map((p) => (
              <div
                key={p.title}
                className="glass rounded-2xl p-6 transition hover:-translate-y-1 hover:shadow-xl hover:shadow-black/30"
              >
                <span
                  className={`inline-block rounded-full border px-2.5 py-0.5 text-xs font-semibold ${p.badgeColor}`}
                >
                  {p.badge}
                </span>
                <h3 className="mt-3 text-lg font-bold text-white">{p.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-400">{p.desc}</p>
                <div className="mt-4 flex flex-wrap gap-1.5">
                  {p.tags.map((t) => (
                    <span
                      key={t}
                      className="rounded-full bg-white/10 px-2.5 py-0.5 text-xs font-medium text-slate-300"
                    >
                      {t}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Game CTA ─────────────────────────────────────────── */}
      <section className="landing-bg py-20">
        <div className="mx-auto max-w-2xl px-6 text-center">
          <span className="text-4xl">🎮</span>
          <h2
            className="mt-4 text-3xl font-bold text-slate-900"
            style={{ fontFamily: "'Space Grotesk',sans-serif" }}
          >
            Take a break — play Snake
          </h2>
          <p className="mt-3 text-slate-600">
            A fully in-browser Snake game. Login to have your high scores saved to the
            leaderboard.
          </p>
          <div className="mt-8 flex justify-center gap-4">
            <Link
              to="/app/game"
              className="rounded-full bg-slate-900 px-7 py-3 text-sm font-bold text-white transition hover:bg-slate-700 hover:scale-105"
            >
              Play Now
            </Link>
            <Link
              to="/signup"
              className="rounded-full border border-slate-300 px-7 py-3 text-sm font-bold text-slate-700 transition hover:bg-slate-100"
            >
              Sign up to save scores
            </Link>
          </div>
        </div>
      </section>

      {/* ── Footer ───────────────────────────────────────────── */}
      <footer className="bg-slate-900 py-8 text-center text-sm text-slate-500">
        Built with FastAPI · React · PostgreSQL · Kubernetes
      </footer>
    </div>
  );
}
