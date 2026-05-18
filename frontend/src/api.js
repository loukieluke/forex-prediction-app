const BASE_URL = "http://localhost:8000";

async function getJson(path, init = {}) {
  const response = await fetch(`${BASE_URL}${path}`, init);
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || "Request failed");
  }
  return response.json();
}

export const api = {
  candles: (instrument = "EUR_USD", granularity = "H1") =>
    getJson(`/api/data/candles?instrument=${instrument}&granularity=${granularity}&limit=250`),
  latestSignal: (instrument = "EUR_USD", granularity = "H1") =>
    getJson(`/api/signal/latest?instrument=${instrument}&granularity=${granularity}`),
  latestNews: () => getJson("/api/data/news/latest?limit=20"),
  tradeLogs: () => getJson("/api/trade/logs?limit=50"),
  readiness: () => getJson("/api/system/readiness"),
  manualTrade: (payload) =>
    getJson("/api/trade/manual", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  runCycle: () => getJson("/api/trade/auto/run", { method: "POST" }),
  ingestCandles: () => getJson("/api/data/ingest/candles", { method: "POST" }),
  ingestNews: () => getJson("/api/data/ingest/news", { method: "POST" }),
};
