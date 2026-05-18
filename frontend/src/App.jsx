import { useEffect, useMemo, useRef, useState } from "react";
import { createChart } from "lightweight-charts";
import { api } from "./api";

function Panel({ title, children }) {
  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">{title}</h2>
      {children}
    </section>
  );
}

export default function App() {
  const chartRef = useRef(null);
  const [candles, setCandles] = useState([]);
  const [signal, setSignal] = useState({ signal: "HOLD", confidence: 0, features: {} });
  const [news, setNews] = useState([]);
  const [logs, setLogs] = useState({ trades: [], predictions: [] });
  const [readiness, setReadiness] = useState(null);
  const [loading, setLoading] = useState(false);
  const brokerReady = readiness?.providers?.broker?.oanda_ready ?? false;
  const sentimentAvg = useMemo(() => {
    if (!news.length) return 0;
    return news.reduce((acc, item) => acc + (item.sentiment_score || 0), 0) / news.length;
  }, [news]);

  async function refresh() {
    setLoading(true);
    try {
      const [c, s, n, l] = await Promise.all([
        api.candles(),
        api.latestSignal(),
        api.latestNews(),
        api.tradeLogs(),
      ]);
      setCandles(c);
      setSignal(s);
      setNews(n);
      setLogs(l);
      try {
        setReadiness(await api.readiness());
      } catch {
        setReadiness(null);
      }
    } finally {
      setLoading(false);
    }
  }

  async function ingestAndRefresh() {
    await Promise.all([api.ingestCandles(), api.ingestNews()]);
    await refresh();
  }

  async function runAutoCycle() {
    await api.runCycle();
    await refresh();
  }

  async function manualTrade(direction) {
    await api.manualTrade({ instrument: "EUR_USD", direction, units: 1000, confidence: signal.confidence });
    await refresh();
  }

  useEffect(() => {
    refresh();
  }, []);

  useEffect(() => {
    if (!chartRef.current || candles.length === 0) return;
    chartRef.current.innerHTML = "";
    const chart = createChart(chartRef.current, {
      width: chartRef.current.clientWidth,
      height: 320,
      layout: { background: { color: "#020617" }, textColor: "#cbd5e1" },
      grid: { vertLines: { color: "#1e293b" }, horzLines: { color: "#1e293b" } },
      rightPriceScale: { borderColor: "#334155" },
      timeScale: { borderColor: "#334155" },
    });
    const series = chart.addCandlestickSeries();
    series.setData(
      candles.map((c) => ({
        time: Math.floor(new Date(c.time).getTime() / 1000),
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      }))
    );
    return () => chart.remove();
  }, [candles]);

  return (
    <main className="min-h-screen bg-slate-950 p-6 text-slate-100">
      <div className="mx-auto grid max-w-7xl gap-4">
        <header className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-2xl font-bold">Forex Prediction Dashboard</h1>
          <div className="flex gap-2">
            <button className="btn" onClick={refresh} disabled={loading}>
              Refresh
            </button>
            <button className="btn" onClick={ingestAndRefresh} disabled={loading}>
              Ingest
            </button>
            <button className="btn" onClick={runAutoCycle} disabled={loading}>
              Run Auto Cycle
            </button>
          </div>
        </header>

        <div className="grid gap-4 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <Panel title="Live Candles (EUR_USD H1)">
              <div ref={chartRef} className="w-full" />
            </Panel>
          </div>
          <Panel title="Current Signal">
            <p className="text-4xl font-extrabold">{signal.signal}</p>
            <p className="mt-2 text-slate-300">Confidence: {(signal.confidence * 100).toFixed(1)}%</p>
            <div className="mt-4 flex gap-2">
              <button className="btn" onClick={() => manualTrade("BUY")} disabled={!brokerReady}>
                Manual BUY
              </button>
              <button className="btn" onClick={() => manualTrade("SELL")} disabled={!brokerReady}>
                Manual SELL
              </button>
            </div>
            {!brokerReady && (
              <p className="mt-2 text-xs text-amber-300">
                Manual trading disabled until OANDA credentials are configured.
              </p>
            )}
          </Panel>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <Panel title="Sentiment Gauge">
            <p className="text-3xl font-semibold">{sentimentAvg.toFixed(3)}</p>
            <p className="text-sm text-slate-400">Average headline sentiment (last {news.length} headlines)</p>
          </Panel>
          <Panel title="Trade Log">
            <div className="max-h-64 space-y-2 overflow-auto">
              {logs.trades.map((trade) => (
                <div key={trade.id} className="rounded border border-slate-800 p-2 text-sm">
                  {trade.instrument} {trade.direction} {trade.units} @ {Math.round(trade.confidence * 100)}%
                </div>
              ))}
            </div>
          </Panel>
        </div>

        <Panel title="System Readiness">
          {!readiness ? (
            <p className="text-sm text-slate-400">Unable to load readiness.</p>
          ) : (
            <div className="space-y-2 text-sm">
              <p>
                Overall:{" "}
                <span className={readiness.overall_ready ? "text-emerald-400" : "text-amber-400"}>
                  {readiness.overall_ready ? "Ready" : "Needs setup"}
                </span>
              </p>
              <p>
                Forex source: {readiness.providers.forex.selected_provider} (
                {readiness.providers.forex.any_forex_source_ready ? "configured" : "missing keys"})
              </p>
              <p>
                News: RSS {readiness.providers.news.rss_enabled ? "on" : "off"}, API{" "}
                {readiness.providers.news.newsapi_ready ? "configured" : "missing"}
              </p>
              <p>
                Broker: OANDA {readiness.providers.broker.oanda_ready ? "configured" : "missing creds"} | Auto trade{" "}
                {readiness.providers.broker.auto_trade_enabled ? "on" : "off"}
              </p>
            </div>
          )}
        </Panel>

        <Panel title="Latest News">
          <div className="max-h-72 space-y-2 overflow-auto text-sm">
            {news.map((item, idx) => (
              <article key={`${item.published_at}-${idx}`} className="rounded border border-slate-800 p-2">
                <p>{item.title}</p>
                <p className="mt-1 text-xs text-slate-400">
                  {item.source} | sentiment {item.sentiment_score?.toFixed(3)}
                </p>
              </article>
            ))}
          </div>
        </Panel>
      </div>
    </main>
  );
}
