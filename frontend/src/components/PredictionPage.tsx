import { useMemo, useState } from "react";

type FeatureGroup = {
  title: string;
  fields: { key: string; label: string; step?: string }[];
};

const FEATURE_GROUPS: FeatureGroup[] = [
  {
    title: "Time",
    fields: [
      { key: "year",              label: "Year",              step: "1"     },
      { key: "month",             label: "Month (1–12)",      step: "1"     },
      { key: "quarter",           label: "Quarter (1–4)",     step: "1"     },
      { key: "transaction_count", label: "Transaction count", step: "1"     },
      { key: "median_assessed_value", label: "Median assessed value", step: "1" },
      { key: "median_sales_ratio", label: "Median sales ratio", step: "0.01" },
    ],
  },
  {
    title: "Lag features",
    fields: [
      { key: "median_sale_price_lag_1",  label: "Sale price · lag 1",  step: "1" },
      { key: "median_sale_price_lag_3",  label: "Sale price · lag 3",  step: "1" },
      { key: "median_sale_price_lag_6",  label: "Sale price · lag 6",  step: "1" },
      { key: "median_sale_price_lag_12", label: "Sale price · lag 12", step: "1" },
      { key: "price_pct_change_1m",  label: "Pct change · 1m",  step: "0.001" },
      { key: "price_pct_change_3m",  label: "Pct change · 3m",  step: "0.001" },
      { key: "price_pct_change_12m", label: "Pct change · 12m", step: "0.001" },
    ],
  },
  {
    title: "Rolling features",
    fields: [
      { key: "median_sale_price_rolling_mean_3",  label: "Rolling mean · 3",  step: "1" },
      { key: "median_sale_price_rolling_std_3",   label: "Rolling std · 3",   step: "1" },
      { key: "median_sale_price_rolling_mean_6",  label: "Rolling mean · 6",  step: "1" },
      { key: "median_sale_price_rolling_std_6",   label: "Rolling std · 6",   step: "1" },
      { key: "median_sale_price_rolling_mean_12", label: "Rolling mean · 12", step: "1" },
      { key: "median_sale_price_rolling_std_12",  label: "Rolling std · 12",  step: "1" },
    ],
  },
];

const REQUIRED_FEATURES: readonly string[] = FEATURE_GROUPS.flatMap(g =>
  g.fields.map(f => f.key)
);

const EXAMPLE_VALUES: Record<string, number> = {
  year: 2020,
  month: 6,
  quarter: 2,
  transaction_count: 45,
  median_assessed_value: 150000,
  median_sale_price_lag_1: 250000,
  median_sale_price_lag_3: 245000,
  median_sale_price_lag_6: 240000,
  median_sale_price_lag_12: 230000,
  median_sale_price_rolling_mean_3: 248000,
  median_sale_price_rolling_std_3: 5000,
  median_sale_price_rolling_mean_6: 246000,
  median_sale_price_rolling_std_6: 6000,
  median_sale_price_rolling_mean_12: 242000,
  median_sale_price_rolling_std_12: 7000,
  price_pct_change_1m: 0.02,
  price_pct_change_3m: 0.05,
  price_pct_change_12m: 0.08,
  median_sales_ratio: 0.92,
};

type Mode = "single" | "batch";

const INPUT_CLASS =
  "w-full rounded-xl border border-white/10 bg-slate-950/60 px-3 py-2 text-sm text-white placeholder:text-slate-500 focus:border-cyan-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/40";

const BUTTON_CLASS =
  "rounded-xl bg-cyan-500 px-4 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:opacity-50";

const GHOST_BUTTON_CLASS =
  "rounded-xl border border-white/10 px-4 py-2.5 text-sm font-medium text-slate-300 transition hover:border-white/30 hover:bg-white/5";

export default function PredictionPage() {
  const [mode, setMode] = useState<Mode>("single");

  return (
    <div>
      <div className="mb-8">
        <h2
          className="text-2xl font-bold text-white"
          style={{ fontFamily: "'Space Grotesk',sans-serif" }}
        >
          📈 Property valuation
        </h2>
        <p className="mt-1 text-sm text-slate-400">
          Predict Connecticut residential median sale prices using the trained
          XGBoost / LightGBM model registered in MLflow.
        </p>
      </div>

      <div className="mb-6 flex gap-2 rounded-xl border border-white/10 bg-slate-900/60 p-1 w-fit">
        <TabButton active={mode === "single"} onClick={() => setMode("single")}>
          Single
        </TabButton>
        <TabButton active={mode === "batch"} onClick={() => setMode("batch")}>
          Batch CSV
        </TabButton>
      </div>

      {mode === "single" ? <SinglePredict /> : <BatchPredict />}
    </div>
  );
}

function TabButton({
  active,
  children,
  onClick,
}: {
  active: boolean;
  children: React.ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={
        "rounded-lg px-4 py-2 text-sm font-medium transition " +
        (active
          ? "bg-cyan-500 text-slate-950"
          : "text-slate-300 hover:bg-white/5 hover:text-white")
      }
    >
      {children}
    </button>
  );
}

// ── Single prediction ──────────────────────────────────────────────────────

function SinglePredict() {
  const [values, setValues] = useState<Record<string, string>>(() =>
    Object.fromEntries(REQUIRED_FEATURES.map(k => [k, ""]))
  );
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  function update(key: string, v: string) {
    setValues(prev => ({ ...prev, [key]: v }));
  }

  function loadExample() {
    setValues(
      Object.fromEntries(
        REQUIRED_FEATURES.map(k => [k, String(EXAMPLE_VALUES[k] ?? "")])
      )
    );
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setResult(null);

    const features: Record<string, number> = {};
    for (const key of REQUIRED_FEATURES) {
      const raw = values[key];
      const n = Number(raw);
      if (raw === "" || Number.isNaN(n)) {
        setError(`Missing or invalid value for "${key}".`);
        return;
      }
      features[key] = n;
    }

    setLoading(true);
    try {
      const r = await fetch("/api/v1/prediction/predict", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ features }),
      });
      if (!r.ok) {
        const body = await r.text();
        throw new Error(`${r.status} ${body}`);
      }
      const data = await r.json();
      setResult(data.predictions?.[0] ?? null);
    } catch (err: any) {
      setError(err.message ?? "Prediction failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-6">
      <div className="grid gap-4 lg:grid-cols-3">
        {FEATURE_GROUPS.map(group => (
          <div
            key={group.title}
            className="rounded-2xl border border-white/10 bg-white/5 p-5"
          >
            <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-cyan-400">
              {group.title}
            </h3>
            <div className="space-y-3">
              {group.fields.map(f => (
                <label key={f.key} className="block">
                  <span className="mb-1 block text-xs text-slate-400">
                    {f.label}
                  </span>
                  <input
                    type="number"
                    step={f.step ?? "any"}
                    value={values[f.key]}
                    onChange={e => update(f.key, e.target.value)}
                    className={INPUT_CLASS}
                    placeholder="0"
                  />
                </label>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="flex items-center gap-3">
        <button type="submit" className={BUTTON_CLASS} disabled={loading}>
          {loading ? "Predicting…" : "Predict"}
        </button>
        <button type="button" onClick={loadExample} className={GHOST_BUTTON_CLASS}>
          Load example
        </button>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-300">
          {error}
        </div>
      )}

      {result !== null && (
        <div className="rounded-2xl border border-cyan-500/40 bg-cyan-500/10 px-5 py-4">
          <p className="text-xs uppercase tracking-wider text-cyan-400">
            Predicted median sale price
          </p>
          <p className="mt-1 text-3xl font-bold text-white">
            ${result.toLocaleString(undefined, { maximumFractionDigits: 0 })}
          </p>
        </div>
      )}
    </form>
  );
}

// ── Batch prediction ───────────────────────────────────────────────────────

type ParsedCsv = {
  headers: string[];
  rows: Record<string, number>[];
};

function parseCsv(text: string): ParsedCsv {
  const lines = text
    .split(/\r?\n/)
    .map(l => l.trim())
    .filter(l => l.length > 0);
  if (lines.length < 2) {
    throw new Error("CSV must have a header row and at least one data row.");
  }
  const headers = lines[0].split(",").map(h => h.trim());

  const missing = REQUIRED_FEATURES.filter(k => !headers.includes(k));
  if (missing.length > 0) {
    throw new Error(`CSV is missing required columns: ${missing.join(", ")}`);
  }

  const rows: Record<string, number>[] = [];
  for (let i = 1; i < lines.length; i++) {
    const cells = lines[i].split(",").map(c => c.trim());
    if (cells.length !== headers.length) {
      throw new Error(`Row ${i + 1} has ${cells.length} cells, expected ${headers.length}.`);
    }
    const row: Record<string, number> = {};
    for (let j = 0; j < headers.length; j++) {
      if (!REQUIRED_FEATURES.includes(headers[j])) continue;
      const n = Number(cells[j]);
      if (Number.isNaN(n)) {
        throw new Error(`Row ${i + 1}, column "${headers[j]}" is not a number: ${cells[j]}`);
      }
      row[headers[j]] = n;
    }
    rows.push(row);
  }
  return { headers, rows };
}

function BatchPredict() {
  const [parsed, setParsed] = useState<ParsedCsv | null>(null);
  const [predictions, setPredictions] = useState<number[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const requiredColumns = useMemo(() => REQUIRED_FEATURES.join(", "), []);

  function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError(null);
    setPredictions(null);

    const reader = new FileReader();
    reader.onload = () => {
      try {
        const text = String(reader.result ?? "");
        setParsed(parseCsv(text));
      } catch (err: any) {
        setError(err.message ?? "Failed to parse CSV.");
        setParsed(null);
      }
    };
    reader.readAsText(file);
  }

  async function submit() {
    if (!parsed) return;
    setLoading(true);
    setError(null);
    setPredictions(null);
    try {
      const r = await fetch("/api/v1/prediction/predict/batch", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ instances: parsed.rows }),
      });
      if (!r.ok) {
        const body = await r.text();
        throw new Error(`${r.status} ${body}`);
      }
      const data = await r.json();
      setPredictions(data.predictions ?? []);
    } catch (err: any) {
      setError(err.message ?? "Batch prediction failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
        <p className="text-sm text-slate-300">
          Upload a CSV with one row per property. The header row must include
          these columns (extra columns are ignored):
        </p>
        <p className="mt-2 break-all rounded-lg bg-slate-950/60 px-3 py-2 font-mono text-xs text-cyan-300">
          {requiredColumns}
        </p>

        <div className="mt-4 flex items-center gap-3">
          <input
            type="file"
            accept=".csv,text/csv"
            onChange={handleFile}
            className="text-sm text-slate-300 file:mr-3 file:rounded-lg file:border-0 file:bg-cyan-500 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-slate-950 hover:file:bg-cyan-400"
          />
          <button
            type="button"
            onClick={submit}
            disabled={!parsed || loading}
            className={BUTTON_CLASS}
          >
            {loading ? "Predicting…" : "Run batch"}
          </button>
        </div>

        {parsed && (
          <p className="mt-3 text-xs text-slate-400">
            Parsed {parsed.rows.length} rows from CSV.
          </p>
        )}
      </div>

      {error && (
        <div className="rounded-xl border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-300">
          {error}
        </div>
      )}

      {predictions && parsed && (
        <div className="overflow-hidden rounded-2xl border border-white/10 bg-white/5">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-900/80 text-xs uppercase tracking-wider text-cyan-400">
              <tr>
                <th className="px-4 py-3">#</th>
                <th className="px-4 py-3">Year</th>
                <th className="px-4 py-3">Month</th>
                <th className="px-4 py-3 text-right">Predicted price</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {predictions.map((p, i) => (
                <tr key={i} className="text-slate-200">
                  <td className="px-4 py-2 text-slate-500">{i + 1}</td>
                  <td className="px-4 py-2">{parsed.rows[i]?.year ?? "—"}</td>
                  <td className="px-4 py-2">{parsed.rows[i]?.month ?? "—"}</td>
                  <td className="px-4 py-2 text-right font-semibold text-white">
                    ${p.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
