import { useEffect, useMemo, useState } from "react";
import "./App.css";

const CONTINENTS = [
  { value: "AFRICA", label: "Africa" },
  { value: "EUROPE", label: "Europe" },
  { value: "ASIA", label: "Asia" },
  { value: "NORTH_AMERICA", label: "North America" },
  { value: "SOUTH_AMERICA", label: "South America" },
  { value: "OCEANIA", label: "Oceania" },
];

const initialForm = {
  origin: "ICN",
  continent: "EUROPE",
  date_from: "",
  date_to: "",
  adults: 2,
  budget_total: "",
  currency: "KRW",
  max_stops: "",
  hotel_stars_min: "",
  max_price: "",
};

export default function App() {
  const [route, setRoute] = useState(window.location.pathname);

  useEffect(() => {
    const onPop = () => setRoute(window.location.pathname);
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  const navigate = (path) => {
    window.history.pushState({}, "", path);
    setRoute(path);
  };

  const resultsId = useMemo(() => {
    const match = /^\/results\/(\d+)$/.exec(route);
    return match ? match[1] : null;
  }, [route]);

  return (
    <div className="app">
      <header className="app-header">
        <div className="brand">
          <span className="brand-mark">VC</span>
          <div>
            <div className="brand-title">Vibecoder Travel</div>
            <div className="brand-subtitle">Smart destination preview</div>
          </div>
        </div>
        <nav className="nav">
          <button className="nav-link" onClick={() => navigate("/")}>
            Search
          </button>
          {resultsId && (
            <button
              className="nav-link"
              onClick={() => navigate(`/results/${resultsId}`)}
            >
              Results
            </button>
          )}
        </nav>
      </header>

      <main className="app-main">
        {resultsId ? (
          <ResultsPage searchId={resultsId} onNewSearch={() => navigate("/")} />
        ) : (
          <SearchForm onSuccess={(id) => navigate(`/results/${id}`)} />
        )}
      </main>
    </div>
  );
}

function SearchForm({ onSuccess }) {
  const [form, setForm] = useState(initialForm);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const update = (field) => (event) => {
    setForm((prev) => ({ ...prev, [field]: event.target.value }));
  };

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    setLoading(true);

    if (!form.date_from || !form.date_to || !form.budget_total) {
      setError("Please fill in all required fields.");
      setLoading(false);
      return;
    }
    if (!form.origin || !form.currency) {
      setError("Origin and currency are required.");
      setLoading(false);
      return;
    }
    if (Number(form.budget_total) <= 0) {
      setError("Budget total must be greater than zero.");
      setLoading(false);
      return;
    }

    const preferences = {};
    if (form.max_stops !== "") {
      const parsed = Number(form.max_stops);
      if (Number.isFinite(parsed)) preferences.max_stops = parsed;
    }
    if (form.hotel_stars_min !== "") {
      const parsed = Number(form.hotel_stars_min);
      if (Number.isFinite(parsed)) preferences.hotel_stars_min = parsed;
    }
    if (form.max_price !== "") {
      const parsed = Number(form.max_price);
      if (Number.isFinite(parsed)) preferences.max_price = parsed;
    }

    const payload = {
      origin: form.origin.trim().toUpperCase(),
      continent: form.continent,
      date_from: form.date_from,
      date_to: form.date_to,
      adults: Number(form.adults) || 1,
      budget_total: Number(form.budget_total),
      currency: form.currency.trim().toUpperCase(),
      ...(Object.keys(preferences).length > 0 ? { preferences } : {}),
    };

    try {
      const response = await fetch("/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        const detail = await safeJson(response);
        throw new Error(getErrorMessage(detail) || "Failed to create search.");
      }
      const data = await response.json();
      onSuccess(data.search_id);
    } catch (err) {
      setError(err?.message || "Unexpected error.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="panel">
      <div className="panel-header">
        <h1>Find your next destination</h1>
        <p>
          Compare a handful of city options with top flight + hotel offers. Results are
          cached for a short time.
        </p>
      </div>

      <form className="form-grid" onSubmit={submit}>
        <Field label="Origin" required>
          <input
            required
            value={form.origin}
            onChange={update("origin")}
            maxLength={3}
          />
        </Field>
        <Field label="Continent" required>
          <select required value={form.continent} onChange={update("continent")}>
            {CONTINENTS.map((continent) => (
              <option key={continent.value} value={continent.value}>
                {continent.label}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Departure date" required>
          <input
            required
            type="date"
            value={form.date_from}
            onChange={update("date_from")}
          />
        </Field>
        <Field label="Return date" required>
          <input
            required
            type="date"
            value={form.date_to}
            onChange={update("date_to")}
          />
        </Field>
        <Field label="Adults" required>
          <input
            required
            type="number"
            min="1"
            value={form.adults}
            onChange={update("adults")}
          />
        </Field>
        <Field label="Budget total" required>
          <input
            required
            type="number"
            min="0"
            step="0.01"
            value={form.budget_total}
            onChange={update("budget_total")}
          />
        </Field>
        <Field label="Currency" required>
          <input
            required
            value={form.currency}
            onChange={update("currency")}
            maxLength={3}
          />
        </Field>
        <Field label="Max stops">
          <input
            type="number"
            min="0"
            value={form.max_stops}
            onChange={update("max_stops")}
          />
        </Field>
        <Field label="Hotel stars min">
          <input
            type="number"
            min="1"
            max="5"
            value={form.hotel_stars_min}
            onChange={update("hotel_stars_min")}
          />
        </Field>
        <Field label="Max price (hotel total)">
          <input
            type="number"
            min="0"
            step="0.01"
            value={form.max_price}
            onChange={update("max_price")}
          />
        </Field>

        <div className="form-actions">
          <button className="primary" type="submit" disabled={loading}>
            {loading ? "Searching..." : "Search"}
          </button>
          {error && <div className="error">{error}</div>}
        </div>
      </form>
    </section>
  );
}

function ResultsPage({ searchId, onNewSearch }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [data, setData] = useState(null);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setError("");
    fetch(`/api/search/${searchId}`)
      .then(async (response) => {
        if (!response.ok) {
          const detail = await safeJson(response);
          throw new Error(getErrorMessage(detail) || "Failed to fetch results.");
        }
        return response.json();
      })
      .then((payload) => {
        if (isMounted) setData(payload);
      })
      .catch((err) => {
        if (isMounted) setError(err?.message || "Unexpected error.");
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [searchId]);

  return (
    <section className="panel">
      <div className="panel-header row">
        <div>
          <h1>Results</h1>
          <p>Search ID: {searchId}</p>
        </div>
        <button className="ghost" onClick={onNewSearch}>
          New search
        </button>
      </div>

      {loading && <div className="loading">Loading recommendations...</div>}
      {error && <div className="error">{error}</div>}

      {!loading && data && (
        <div className="results-grid">
          {data.recommendations?.length ? (
            data.recommendations.map((rec) => (
              <article key={rec.city_code} className="result-card">
                <div className="card-header">
                  <div>
                    <h2>
                      {rec.city} <span className="muted">({rec.city_code})</span>
                    </h2>
                    <p className="muted">{rec.country_code}</p>
                  </div>
                  <div className="score-pill">Score {formatScore(rec.score)}</div>
                </div>
                <div className="card-body">
                  <div className="stat">
                    <span>Total estimate</span>
                    <strong>{formatMoney(rec.total_estimate, rec.flight?.currency)}</strong>
                  </div>
                  <div className="stat">
                    <span>Flight min</span>
                    <strong>{formatMoney(rec.flight?.min_total, rec.flight?.currency)}</strong>
                  </div>
                  <div className="stat">
                    <span>Hotel min</span>
                    <strong>{formatMoney(rec.hotel?.min_total, rec.hotel?.currency)}</strong>
                  </div>
                </div>
                <div className="tag-row">
                  {(rec.reasons || []).map((reason, index) => (
                    <span key={`${rec.city_code}-${index}`} className="tag">
                      {reason}
                    </span>
                  ))}
                </div>
              </article>
            ))
          ) : (
            <div className="empty">No recommendations available.</div>
          )}
        </div>
      )}
    </section>
  );
}

function Field({ label, children, required }) {
  return (
    <label className="field">
      <span>
        {label}
        {required ? " *" : ""}
      </span>
      {children}
    </label>
  );
}

async function safeJson(response) {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

function formatMoney(value, currency) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "—";
  }
  if (!currency) {
    return value;
  }
  return `${value} ${currency}`;
}

function formatScore(value) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "0.0";
  }
  return Number(value).toFixed(2);
}

function getErrorMessage(payload) {
  if (!payload) return null;
  const detail = payload.detail ?? payload;
  if (typeof detail === "string") return detail;
  try {
    return JSON.stringify(detail);
  } catch {
    return "Request failed.";
  }
}
