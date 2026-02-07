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

const ITINERARY_STYLES = [
  { value: "activity", label: "Activity" },
  { value: "history", label: "History" },
  { value: "photo", label: "Photo" },
  { value: "mixed", label: "Mixed" },
];

const ITINERARY_PACES = [
  { value: "relaxed", label: "Relaxed" },
  { value: "normal", label: "Normal" },
  { value: "packed", label: "Packed" },
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
  const [itineraryForm, setItineraryForm] = useState({
    city_code: "",
    style: "activity",
    pace: "normal",
  });
  const [itineraryLoading, setItineraryLoading] = useState(false);
  const [itineraryError, setItineraryError] = useState("");
  const [itineraryData, setItineraryData] = useState(null);
  const [expandedDays, setExpandedDays] = useState({});

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

  useEffect(() => {
    if (!data?.recommendations?.length) return;
    setItineraryForm((prev) => {
      if (prev.city_code) return prev;
      return { ...prev, city_code: data.recommendations[0].city_code };
    });
  }, [data]);

  const updateItineraryForm = (field) => (event) => {
    const value = event.target.value;
    setItineraryForm((prev) => ({ ...prev, [field]: value }));
  };

  const generateItinerary = async () => {
    setItineraryError("");
    setItineraryData(null);
    setExpandedDays({});
    if (!data?.search_input?.date_from || !data?.search_input?.date_to) {
      setItineraryError("Search dates are required to create an itinerary.");
      return;
    }
    if (!itineraryForm.city_code) {
      setItineraryError("Choose a city first.");
      return;
    }

    const payload = {
      city_code: itineraryForm.city_code,
      date_from: data.search_input.date_from,
      date_to: data.search_input.date_to,
      adults: Number(data.search_input.adults) || 1,
      style: itineraryForm.style,
      pace: itineraryForm.pace,
    };

    setItineraryLoading(true);
    try {
      const response = await fetch("/api/itinerary", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        const detail = await safeJson(response);
        throw new Error(getErrorMessage(detail) || "Failed to generate itinerary.");
      }
      const itinerary = await response.json();
      setItineraryData(itinerary);
    } catch (err) {
      setItineraryError(err?.message || "Unexpected itinerary error.");
    } finally {
      setItineraryLoading(false);
    }
  };

  useEffect(() => {
    if (!itineraryData?.variants?.length) return;
    setExpandedDays((prev) => {
      const next = { ...prev };
      itineraryData.variants.forEach((variant, variantIndex) => {
        const firstDay = variant.days?.[0];
        if (!firstDay) return;
        const key = `${variant.variant_style}-${variantIndex}-${firstDay.date}`;
        if (next[key] === undefined) {
          next[key] = true;
        }
      });
      return next;
    });
  }, [itineraryData]);

  const toggleDay = (key) => {
    setExpandedDays((prev) => ({ ...prev, [key]: !prev[key] }));
  };

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
        <>
          {data.search_input && (
            <div className="search-summary">
              <div className="summary-item">
                <span>Region</span>
                <strong>{formatContinent(data.search_input.continent)}</strong>
              </div>
              <div className="summary-item">
                <span>Budget</span>
                <strong>
                  {formatMoney(
                    data.search_input.budget_total,
                    data.search_input.currency,
                  )}
                </strong>
              </div>
              <div className="summary-item">
                <span>Origin</span>
                <strong>{data.search_input.origin || "-"}</strong>
              </div>
              <div className="summary-item">
                <span>Dates</span>
                <strong>
                  {formatDateRange(
                    data.search_input.date_from,
                    data.search_input.date_to,
                  )}
                </strong>
              </div>
              <div className="summary-item">
                <span>Adults</span>
                <strong>{data.search_input.adults ?? "-"}</strong>
              </div>
            </div>
          )}

          {data.search_input && (
            <section className="itinerary-panel">
              <div className="itinerary-header">
                <h2>Build Itinerary</h2>
                <p>Generate day-by-day plans with alternatives per slot.</p>
              </div>
              <div className="itinerary-form-row">
                <Field label="City">
                  <select
                    value={itineraryForm.city_code}
                    onChange={updateItineraryForm("city_code")}
                  >
                    {data.recommendations?.map((rec) => (
                      <option key={`city-${rec.city_code}`} value={rec.city_code}>
                        {rec.city} ({rec.city_code})
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label="Style">
                  <select value={itineraryForm.style} onChange={updateItineraryForm("style")}>
                    {ITINERARY_STYLES.map((style) => (
                      <option key={style.value} value={style.value}>
                        {style.label}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label="Pace">
                  <select value={itineraryForm.pace} onChange={updateItineraryForm("pace")}>
                    {ITINERARY_PACES.map((pace) => (
                      <option key={pace.value} value={pace.value}>
                        {pace.label}
                      </option>
                    ))}
                  </select>
                </Field>
                <div className="itinerary-actions">
                  <button
                    className="primary"
                    type="button"
                    disabled={itineraryLoading}
                    onClick={generateItinerary}
                  >
                    {itineraryLoading ? "Generating..." : "Generate itinerary"}
                  </button>
                </div>
              </div>
              {itineraryError && <div className="error">{itineraryError}</div>}

              {itineraryData?.variants?.length ? (
                <div className="itinerary-variants">
                  {itineraryData.variants.map((variant) => (
                    <article
                      key={`${variant.variant_style}-${variant.variant_label}`}
                      className="itinerary-variant"
                    >
                      <h3>{variant.variant_label}</h3>
                      {(variant.days || []).map((day, dayIndex) => {
                        const dayKey = `${variant.variant_style}-${dayIndex}-${day.date}`;
                        const isExpanded = Boolean(expandedDays[dayKey]);
                        return (
                          <div key={`${variant.variant_style}-${day.date}`} className="itinerary-day">
                            <button
                              type="button"
                              className="day-toggle"
                              onClick={() => toggleDay(dayKey)}
                            >
                              <span>
                                Day {day.day_index} ({day.date})
                              </span>
                              <span>{isExpanded ? "Hide" : "Show"}</span>
                            </button>
                            {isExpanded && (day.slots || []).map((slot) => (
                              <div key={`${day.date}-${slot.slot}`} className="itinerary-slot">
                                <div className="slot-title">{slot.slot}</div>
                                <div className="slot-alternatives">
                                  {(slot.alternatives || []).map((item, index) => (
                                    <div
                                      key={`${day.date}-${slot.slot}-${item.poi_id || index}`}
                                      className="alternative-item"
                                    >
                                      <strong>{item.poi_name}</strong>
                                      <span>
                                        Visit {item.estimated_visit_minutes}m / Travel{" "}
                                        {item.estimated_travel_minutes}m
                                      </span>
                                      <span className="muted">
                                        {(item.reasons || []).join(" | ")}
                                      </span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            ))}
                          </div>
                        );
                      })}
                    </article>
                  ))}
                </div>
              ) : null}
            </section>
          )}

          <div className="results-grid">
            {data.recommendations?.length ? (
              data.recommendations.map((rec) => {
                const flightOfferName = resolveOfferName(rec.flight);
                const hotelOfferName = resolveOfferName(rec.hotel);

                return (
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
                      <div className="stat stat-name">
                        <span>Flight offer</span>
                        <strong className="name-value">{flightOfferName || "-"}</strong>
                      </div>
                      <div className="stat">
                        <span>Hotel min</span>
                        <strong>{formatMoney(rec.hotel?.min_total, rec.hotel?.currency)}</strong>
                      </div>
                      <div className="stat stat-name">
                        <span>Hotel</span>
                        <strong className="name-value">{hotelOfferName || "-"}</strong>
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
                );
              })
            ) : (
              <div className="empty">No recommendations available.</div>
            )}
          </div>
        </>
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
    return "-";
  }
  if (!currency) {
    return value;
  }
  return `${value} ${currency}`;
}

function resolveOfferName(section) {
  if (!section) return null;
  if (section.min_offer_name) return section.min_offer_name;
  if (!Array.isArray(section.top_offers) || !section.top_offers.length) return null;
  return section.top_offers[0]?.name ?? null;
}

function formatContinent(continent) {
  if (!continent) return "-";
  return CONTINENTS.find((item) => item.value === continent)?.label || continent;
}

function formatDateRange(dateFrom, dateTo) {
  if (!dateFrom || !dateTo) return "-";
  return `${dateFrom} - ${dateTo}`;
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

