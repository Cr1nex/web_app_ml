import { useMemo, useState } from "react";
import { apiFetch } from "../lib/api";

// ── Domain values ──────────────────────────────────────────────────────────

const CT_TOWNS = [
  "Andover", "Ansonia", "Ashford", "Avon", "Barkhamsted", "Beacon Falls", "Berlin",
  "Bethany", "Bethel", "Bethlehem", "Bloomfield", "Bolton", "Bozrah", "Branford",
  "Bridgeport", "Bridgewater", "Bristol", "Brookfield", "Brooklyn", "Burlington",
  "Canaan", "Canterbury", "Canton", "Chaplin", "Cheshire", "Chester", "Clinton",
  "Colchester", "Colebrook", "Columbia", "Cornwall", "Coventry", "Cromwell",
  "Danbury", "Darien", "Deep River", "Derby", "Durham", "East Granby", "East Haddam",
  "East Hampton", "East Hartford", "East Haven", "East Lyme", "East Windsor",
  "Eastford", "Easton", "Ellington", "Enfield", "Essex", "Fairfield", "Farmington",
  "Franklin", "Glastonbury", "Goshen", "Granby", "Greenwich", "Griswold", "Groton",
  "Guilford", "Haddam", "Hamden", "Hampton", "Hartford", "Hartland", "Harwinton",
  "Hebron", "Kent", "Killingly", "Killingworth", "Lebanon", "Ledyard", "Lisbon",
  "Litchfield", "Lyme", "Madison", "Manchester", "Mansfield", "Marlborough",
  "Meriden", "Middlebury", "Middlefield", "Middletown", "Milford", "Monroe",
  "Montville", "Morris", "Naugatuck", "New Britain", "New Canaan", "New Fairfield",
  "New Hartford", "New Haven", "New London", "New Milford", "Newington", "Newtown",
  "Norfolk", "North Branford", "North Canaan", "North Haven", "North Stonington",
  "Norwalk", "Norwich", "Old Lyme", "Old Saybrook", "Orange", "Oxford", "Plainfield",
  "Plainville", "Plymouth", "Pomfret", "Portland", "Preston", "Prospect", "Putnam",
  "Redding", "Ridgefield", "Rocky Hill", "Roxbury", "Salem", "Salisbury", "Scotland",
  "Seymour", "Sharon", "Shelton", "Sherman", "Simsbury", "Somers", "South Windsor",
  "Southbury", "Southington", "Sprague", "Stafford", "Stamford", "Sterling",
  "Stonington", "Stratford", "Suffield", "Thomaston", "Thompson", "Tolland",
  "Torrington", "Trumbull", "Union", "Vernon", "Voluntown", "Wallingford", "Warren",
  "Washington", "Waterbury", "Waterford", "Watertown", "West Hartford", "West Haven",
  "Westbrook", "Weston", "Westport", "Wethersfield", "Willington", "Wilton",
  "Winchester", "Windham", "Windsor", "Windsor Locks", "Wolcott", "Woodbridge",
  "Woodbury", "Woodstock",
];

const PROPERTY_TYPES = [
  "Residential", "Condo", "Two Family", "Three Family", "Four Family",
  "Single Family", "Commercial", "Vacant Land", "Apartments", "Industrial",
  "Public Utility",
];

const RESIDENTIAL_TYPES = [
  "Single Family", "Condo", "Two Family", "Three Family", "Four Family", "Unknown",
];

// ── Form fields ────────────────────────────────────────────────────────────

type Transaction = {
  town: string;
  property_type: string;
  residential_type: string;
  assessed_value: string;
  list_year: string;
  month_recorded: string;
};

const EMPTY: Transaction = {
  town: "",
  property_type: "Residential",
  residential_type: "Single Family",
  assessed_value: "",
  list_year: "",
  month_recorded: "",
};

const EXAMPLE: Transaction = {
  town: "Avon",
  property_type: "Residential",
  residential_type: "Single Family",
  assessed_value: "217640",
  list_year: "2020",
  month_recorded: "9",
};

const REQUIRED_COLUMNS = [
  "town", "property_type", "residential_type",
  "assessed_value", "list_year", "month_recorded",
] as const;

// ── Styles ─────────────────────────────────────────────────────────────────

const INPUT_CLASS =
  "w-full rounded-xl border border-white/10 bg-slate-950/60 px-3 py-2 text-sm text-white placeholder:text-slate-500 focus:border-cyan-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/40";

const BUTTON_CLASS =
  "rounded-xl bg-cyan-500 px-4 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:opacity-50";

const GHOST_BUTTON_CLASS =
  "rounded-xl border border-white/10 px-4 py-2.5 text-sm font-medium text-slate-300 transition hover:border-white/30 hover:bg-white/5";

// ── Page shell ─────────────────────────────────────────────────────────────

type Mode = "single" | "batch";

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
          Estimate what a Connecticut property would sell for on a given month —
          including future months. Pick the town, describe the property, and
          point at the sale date you want the estimate for.
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
  const [tx, setTx] = useState<Transaction>(EMPTY);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  function update<K extends keyof Transaction>(key: K, v: string) {
    setTx(prev => ({ ...prev, [key]: v }));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setResult(null);

    if (!tx.town || !tx.property_type || !tx.residential_type) {
      setError("Town, property type and residential type are required.");
      return;
    }
    const assessed = Number(tx.assessed_value);
    const year = Number(tx.list_year);
    const month = Number(tx.month_recorded);
    if (!Number.isFinite(assessed) || assessed <= 0) {
      setError("Assessed value must be a positive number.");
      return;
    }
    if (!Number.isInteger(year) || year < 1900 || year > 2100) {
      setError("List year looks invalid.");
      return;
    }
    if (!Number.isInteger(month) || month < 1 || month > 12) {
      setError("Month must be 1–12.");
      return;
    }

    const features = {
      town: tx.town,
      property_type: tx.property_type,
      residential_type: tx.residential_type,
      assessed_value: assessed,
      list_year: year,
      month_recorded: month,
    };

    setLoading(true);
    try {
      const r = await apiFetch("/api/v1/prediction/predict", {
        method: "POST",
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
      <div className="grid gap-4 md:grid-cols-2">
        <Field label="Town">
          <input
            list="ct-towns"
            value={tx.town}
            onChange={e => update("town", e.target.value)}
            className={INPUT_CLASS}
            placeholder="e.g. Avon"
          />
          <datalist id="ct-towns">
            {CT_TOWNS.map(t => <option key={t} value={t} />)}
          </datalist>
        </Field>

        <Field label="Property type">
          <select
            value={tx.property_type}
            onChange={e => update("property_type", e.target.value)}
            className={INPUT_CLASS}
          >
            {PROPERTY_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        </Field>

        <Field label="Residential type">
          <select
            value={tx.residential_type}
            onChange={e => update("residential_type", e.target.value)}
            className={INPUT_CLASS}
          >
            {RESIDENTIAL_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        </Field>

        <Field
          label="Assessed value ($)"
          hint="The town tax assessor's official valuation of the property. In CT this is usually 70% of fair market value and is printed on the property tax bill / town's online assessor portal."
        >
          <input
            type="number"
            step="1000"
            min="0"
            value={tx.assessed_value}
            onChange={e => update("assessed_value", e.target.value)}
            className={INPUT_CLASS}
            placeholder="180000"
          />
        </Field>

        <Field label="Sale year" hint="Year you want the estimate for. Future years are allowed.">
          <input
            type="number"
            step="1"
            min="1900"
            max="2100"
            value={tx.list_year}
            onChange={e => update("list_year", e.target.value)}
            className={INPUT_CLASS}
            placeholder="2026"
          />
        </Field>

        <Field label="Sale month (1–12)" hint="Month you want the estimate for.">
          <input
            type="number"
            step="1"
            min="1"
            max="12"
            value={tx.month_recorded}
            onChange={e => update("month_recorded", e.target.value)}
            className={INPUT_CLASS}
            placeholder="6"
          />
        </Field>
      </div>

      <div className="flex items-center gap-3">
        <button type="submit" className={BUTTON_CLASS} disabled={loading}>
          {loading ? "Predicting…" : "Predict price"}
        </button>
        <button
          type="button"
          onClick={() => setTx(EXAMPLE)}
          className={GHOST_BUTTON_CLASS}
        >
          Load example
        </button>
        <button
          type="button"
          onClick={() => { setTx(EMPTY); setResult(null); setError(null); }}
          className={GHOST_BUTTON_CLASS}
        >
          Reset
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
            Predicted sale price
          </p>
          <p className="mt-1 text-3xl font-bold text-white">
            ${result.toLocaleString(undefined, { maximumFractionDigits: 0 })}
          </p>
        </div>
      )}
    </form>
  );
}

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs text-slate-400">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-[11px] leading-snug text-slate-500">{hint}</span>}
    </label>
  );
}

// ── Batch prediction ───────────────────────────────────────────────────────

type ParsedRow = {
  town: string;
  property_type: string;
  residential_type: string;
  assessed_value: number;
  list_year: number;
  month_recorded: number;
};

function parseCsv(text: string): ParsedRow[] {
  const lines = text.split(/\r?\n/).map(l => l.trim()).filter(l => l.length > 0);
  if (lines.length < 2) {
    throw new Error("CSV must have a header row and at least one data row.");
  }
  const headers = lines[0].split(",").map(h => h.trim());

  const missing = REQUIRED_COLUMNS.filter(k => !headers.includes(k));
  if (missing.length > 0) {
    throw new Error(`CSV is missing required columns: ${missing.join(", ")}`);
  }

  const idx: Record<string, number> = {};
  REQUIRED_COLUMNS.forEach(c => { idx[c] = headers.indexOf(c); });

  const rows: ParsedRow[] = [];
  for (let i = 1; i < lines.length; i++) {
    const cells = lines[i].split(",").map(c => c.trim());
    const assessed = Number(cells[idx.assessed_value]);
    const year = Number(cells[idx.list_year]);
    const month = Number(cells[idx.month_recorded]);
    if (!Number.isFinite(assessed) || !Number.isFinite(year) || !Number.isFinite(month)) {
      throw new Error(`Row ${i + 1}: assessed_value / list_year / month_recorded must be numeric.`);
    }
    rows.push({
      town: cells[idx.town],
      property_type: cells[idx.property_type],
      residential_type: cells[idx.residential_type],
      assessed_value: assessed,
      list_year: year,
      month_recorded: month,
    });
  }
  return rows;
}

function BatchPredict() {
  const [rows, setRows] = useState<ParsedRow[] | null>(null);
  const [predictions, setPredictions] = useState<number[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const requiredColumns = useMemo(() => REQUIRED_COLUMNS.join(", "), []);

  function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError(null);
    setPredictions(null);

    const reader = new FileReader();
    reader.onload = () => {
      try {
        const text = String(reader.result ?? "");
        setRows(parseCsv(text));
      } catch (err: any) {
        setError(err.message ?? "Failed to parse CSV.");
        setRows(null);
      }
    };
    reader.readAsText(file);
  }

  async function submit() {
    if (!rows) return;
    setLoading(true);
    setError(null);
    setPredictions(null);
    try {
      const r = await apiFetch("/api/v1/prediction/predict/batch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ instances: rows }),
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
          Upload a CSV with one row per transaction. The header row must include
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
            disabled={!rows || loading}
            className={BUTTON_CLASS}
          >
            {loading ? "Predicting…" : "Run batch"}
          </button>
        </div>

        {rows && (
          <p className="mt-3 text-xs text-slate-400">
            Parsed {rows.length} rows from CSV.
          </p>
        )}
      </div>

      {error && (
        <div className="rounded-xl border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-300">
          {error}
        </div>
      )}

      {predictions && rows && (
        <div className="overflow-hidden rounded-2xl border border-white/10 bg-white/5">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-900/80 text-xs uppercase tracking-wider text-cyan-400">
              <tr>
                <th className="px-4 py-3">#</th>
                <th className="px-4 py-3">Town</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3 text-right">Assessed</th>
                <th className="px-4 py-3 text-right">Predicted price</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {predictions.map((p, i) => (
                <tr key={i} className="text-slate-200">
                  <td className="px-4 py-2 text-slate-500">{i + 1}</td>
                  <td className="px-4 py-2">{rows[i]?.town ?? "—"}</td>
                  <td className="px-4 py-2">{rows[i]?.residential_type ?? "—"}</td>
                  <td className="px-4 py-2 text-right text-slate-300">
                    ${rows[i]?.assessed_value.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                  </td>
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
