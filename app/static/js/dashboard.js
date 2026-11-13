const charts = {};
Chart.defaults.animation = false;

const TICKER_COLORS = {
  AAPL: "#4ade80",
  AMZN: "#facc15",
  MSFT: "#38bdf8",
  NVDA: "#818cf8",
  TSLA: "#f87171",
};

function upsert(id, cfg) {
  if (charts[id]) charts[id].destroy();
  charts[id] = new Chart(document.getElementById(id).getContext("2d"), cfg);
}

function fmtVol(v) {
  if (v >= 1e9) return `${(v / 1e9).toFixed(2)}B`;
  if (v >= 1e6) return `${(v / 1e6).toFixed(1)}M`;
  return v.toLocaleString();
}

function getSelectedTickers() {
  return Array.from(document.querySelectorAll(".t-chip.active")).map(b => b.dataset.ticker);
}

function getQs() {
  const qs = new URLSearchParams();
  const ts = getSelectedTickers();
  if (ts.length > 0 && ts.length < 5) qs.set("tickers", ts.join(","));
  [["year", "fYear"], ["quarter", "fQuarter"], ["month", "fMonth"], ["weekday_num", "fWeekday"]].forEach(([k, id]) => {
    const v = document.getElementById(id).value;
    if (v) qs.set(k, v);
  });
  return qs;
}

async function refresh() {
  const res = await fetch(`/api/dashboard?${getQs().toString()}`);
  const d = await res.json();
  if (d.empty) return;
  const k = d.kpis;

  document.getElementById("kStocksCount").textContent = k.stocks_analyzed;
  document.getElementById("kDateSpan").textContent = `${k.date_start} → ${k.date_end}`;
  document.getElementById("headerSub").textContent =
    `Comparative Analysis of ${d.ranking.map(r => r.ticker).join(", ")} (${k.date_start} to ${k.date_end})`;

  document.getElementById("kAvgClose").textContent = `$${k.avg_close_price.toFixed(2)}`;
  document.getElementById("kLowClose").textContent = `$${k.lowest_closing_price.toFixed(2)}`;
  document.getElementById("kHighClose").textContent = `$${k.highest_closing_price.toFixed(2)}`;
  document.getElementById("kTotalRet").textContent = `${k.total_return_pct.toFixed(2)}%`;
  document.getElementById("kCagr").textContent = `${k.cagr_pct.toFixed(2)}%`;
  document.getElementById("kGrowth10k").textContent = `$${Math.round(k.growth_10k_end).toLocaleString()}`;

  document.getElementById("k52Low").textContent = `$${k.low_52w.toFixed(2)}`;
  document.getElementById("k52High").textContent = `$${k.high_52w.toFixed(2)}`;
  document.getElementById("kBegPrice").textContent = `$${k.beginning_price.toFixed(2)}`;
  document.getElementById("kEndPrice").textContent = `$${k.ending_price.toFixed(2)}`;
  document.getElementById("kBestRet").textContent = `${k.best_return_pct.toFixed(2)}%`;
  document.getElementById("kMaxDD").textContent = `${k.worst_drawdown_pct.toFixed(2)}%`;

  document.getElementById("kSumVol").textContent = fmtVol(k.sum_of_volume);
  document.getElementById("kDays").textContent = k.trading_days;
  document.getElementById("kAvgVol").textContent = fmtVol(k.avg_daily_volume);
  document.getElementById("kPeak").textContent = `$${k.running_peak.toFixed(2)}`;
  document.getElementById("kSharpe").textContent = `${k.best_sharpe_ratio.toFixed(2)} (${k.best_sharpe_ticker})`;
  document.getElementById("kBestTicker").textContent = k.best_ticker;

  // Group time series by ticker
  const dates = [...new Set(d.time_series.map(r => r.trade_date))].sort();
  const byTicker = {};
  d.time_series.forEach(r => {
    if (!byTicker[r.ticker]) byTicker[r.ticker] = {};
    byTicker[r.ticker][r.trade_date] = r;
  });

  const makeDatasets = (field) => Object.keys(byTicker).sort().map(t => ({
    label: t,
    data: dates.map(dt => byTicker[t][dt] ? byTicker[t][dt][field] : null),
    borderColor: TICKER_COLORS[t] || "#38bdf8",
    borderWidth: 2,
    pointRadius: 0,
    tension: 0.2,
  }));

  const lineOpts = (yFmt) => ({
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { labels: { color: "#e2e8f0", boxWidth: 10, font: { size: 10.5 } } } },
    scales: {
      x: { ticks: { color: "#94a3b8", maxTicksLimit: 8, font: { size: 9.5 } }, grid: { display: false } },
      y: { ticks: { color: "#94a3b8", callback: yFmt }, grid: { color: "rgba(148,163,184,0.12)" } },
    },
  });

  upsert("cCloseTrend", { type: "line", data: { labels: dates, datasets: makeDatasets("close_price") }, options: lineOpts(v => `$${v}`) });
  upsert("cGrowth10k", { type: "line", data: { labels: dates, datasets: makeDatasets("growth_10k") }, options: lineOpts(v => `$${(v / 1000).toFixed(0)}K`) });
  upsert("cNormPerf", { type: "line", data: { labels: dates, datasets: makeDatasets("normalized_ret_pct") }, options: lineOpts(v => `${v}%`) });
  upsert("cDrawdown", { type: "line", data: { labels: dates, datasets: makeDatasets("drawdown_pct") }, options: lineOpts(v => `${v}%`) });
  upsert("cRollingVol", { type: "line", data: { labels: dates, datasets: makeDatasets("rolling_vol_20d_pct") }, options: lineOpts(v => `${v}%`) });

  // Risk vs Return scatter
  upsert("cRiskReturn", {
    type: "bubble",
    data: {
      datasets: d.ranking.map(r => ({
        label: r.ticker,
        data: [{ x: r.annualized_volatility_pct, y: r.total_return_pct, r: Math.max(7, Math.min(18, r.total_volume / 2.5e9)) }],
        backgroundColor: TICKER_COLORS[r.ticker] || "#38bdf8",
      })),
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { labels: { color: "#e2e8f0", boxWidth: 9, font: { size: 10 } } } },
      scales: {
        x: { title: { display: true, text: "Annualized Volatility %", color: "#94a3b8", font: { size: 10 } }, ticks: { color: "#94a3b8", callback: v => `${v}%` }, grid: { color: "rgba(148,163,184,0.12)" } },
        y: { title: { display: true, text: "Total Return %", color: "#94a3b8", font: { size: 10 } }, ticks: { color: "#94a3b8", callback: v => `${v}%` }, grid: { color: "rgba(148,163,184,0.12)" } },
      },
    },
  });

  // Total Volume by Stock
  const byVol = [...d.ranking].sort((a, b) => b.total_volume - a.total_volume);
  upsert("cVolStock", {
    type: "bar",
    data: {
      labels: byVol.map(r => r.ticker),
      datasets: [{ data: byVol.map(r => r.total_volume / 1e9), backgroundColor: byVol.map(r => TICKER_COLORS[r.ticker] || "#38bdf8") }],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { x: { ticks: { color: "#94a3b8", callback: v => `${v}B` }, grid: { color: "rgba(148,163,184,0.12)" } }, y: { ticks: { color: "#f8fafc" }, grid: { display: false } } },
    },
  });

  // Monthly Returns (recent 6 months)
  const months = [...new Set(d.monthly_returns.map(r => r.year_month))].sort().slice(-6);
  const mrMap = {};
  d.monthly_returns.forEach(r => { mrMap[`${r.year_month}_${r.ticker}`] = r.monthly_return_pct; });
  upsert("cMonthlyRet", {
    type: "bar",
    data: {
      labels: months,
      datasets: Object.keys(byTicker).sort().map(t => ({
        label: t,
        data: months.map(m => mrMap[`${m}_${t}`] ?? 0),
        backgroundColor: TICKER_COLORS[t] || "#38bdf8",
      })),
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { labels: { color: "#e2e8f0", boxWidth: 9, font: { size: 9.5 } } } },
      scales: { x: { ticks: { color: "#94a3b8", font: { size: 9.5 } }, grid: { display: false } }, y: { ticks: { color: "#94a3b8", callback: v => `${v}%` }, grid: { color: "rgba(148,163,184,0.12)" } } },
    },
  });

  // Ret vs CAGR bar
  upsert("cRetVsCagr", {
    type: "bar",
    data: {
      labels: d.ranking.map(r => r.ticker),
      datasets: [
        { label: "Total Return %", data: d.ranking.map(r => r.total_return_pct), backgroundColor: "#38bdf8" },
        { label: "CAGR %", data: d.ranking.map(r => r.cagr_pct), backgroundColor: "#4ade80" },
      ],
    },
    options: lineOpts(v => `${v}%`),
  });

  // Tables
  document.getElementById("rankingBody").innerHTML = d.ranking.map(r => `
    <tr><td>${r.rank}</td><td><strong>${r.ticker}</strong></td><td>${r.total_return_pct.toFixed(2)}%</td><td>${r.cagr_pct.toFixed(2)}%</td><td>${r.annualized_volatility_pct.toFixed(1)}%</td><td>${r.max_drawdown_pct.toFixed(1)}%</td></tr>
  `).join("");

  document.getElementById("perfScorecardBody").innerHTML = d.ranking.map(r => `
    <tr><td>${r.rank}</td><td><strong>${r.ticker}</strong></td><td style="text-align:left">${r.company_name}</td><td>$${r.beginning_price.toFixed(2)}</td><td>$${r.ending_price.toFixed(2)}</td><td>$${Math.round(r.growth_10k_end).toLocaleString()}</td><td>${r.total_return_pct.toFixed(2)}%</td><td>${r.cagr_pct.toFixed(2)}%</td><td>${fmtVol(r.total_volume)}</td></tr>
  `).join("");

  document.getElementById("riskTableBody").innerHTML = d.ranking.map(r => `
    <tr><td><strong>${r.ticker}</strong></td><td>${r.annualized_volatility_pct.toFixed(2)}%</td><td>${r.max_drawdown_pct.toFixed(2)}%</td><td>${r.var_95_daily_pct.toFixed(2)}%</td><td>${r.sharpe_ratio.toFixed(2)}</td><td>${r.sortino_ratio.toFixed(2)}</td></tr>
  `).join("");

  document.getElementById("insightsContainer").innerHTML = d.insights.map(ins => `
    <div class="ins-card"><h3>${ins.ticker} — ${ins.company_name}</h3><div class="hl">${ins.headline}</div><p>${ins.detail}</p></div>
  `).join("");
}

document.querySelectorAll(".t-chip").forEach(btn => {
  btn.addEventListener("click", () => {
    const activeCount = document.querySelectorAll(".t-chip.active").length;
    if (btn.classList.contains("active") && activeCount === 1) return;
    btn.classList.toggle("active");
    refresh();
  });
});

document.querySelectorAll(".tab-btn").forEach(tab => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".view-pane").forEach(v => v.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById(`view-${tab.dataset.view}`).classList.add("active");
  });
});

["fYear", "fQuarter", "fMonth", "fWeekday"].forEach(id => {
  document.getElementById(id).addEventListener("change", refresh);
});

document.getElementById("btnReset").addEventListener("click", () => {
  document.querySelectorAll(".t-chip").forEach(b => b.classList.add("active"));
  ["fYear", "fQuarter", "fMonth", "fWeekday"].forEach(id => document.getElementById(id).value = "");
  refresh();
});

document.getElementById("btnExport").addEventListener("click", () => {
  window.location.href = `/api/export/ranking-csv?${getQs().toString()}`;
});

window.addEventListener("DOMContentLoaded", refresh);
