"""Reconciled financial return, volatility, drawdown, and ranking engine."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from src.config import DB_PATH, RISK_FREE_RATE, TRADING_DAYS_PER_YEAR


@dataclass(frozen=True)
class FilterParams:
    """Interactive equity dashboard filter parameters."""

    tickers: tuple[str, ...] | None = None
    year: int | None = None
    quarter: int | None = None
    month: int | None = None
    weekday_num: int | None = None


def _connect() -> sqlite3.Connection:
    if not DB_PATH.exists():
        from src.pipeline import run_pipeline

        run_pipeline(refresh=False)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_filter_options() -> dict[str, Any]:
    """Return available ticker and calendar slicer values."""
    with _connect() as conn:
        tickers = [
            {"ticker": r[0], "company_name": r[1], "sector": r[2]}
            for r in conn.execute("SELECT ticker, company_name, sector FROM dim_ticker ORDER BY ticker")
        ]
        years = [r[0] for r in conn.execute("SELECT DISTINCT year FROM dim_date ORDER BY year")]
        months = [
            {"month_num": r[0], "month_name": r[1]}
            for r in conn.execute("SELECT DISTINCT month_num, month_name FROM dim_date ORDER BY month_num")
        ]
        weekdays = [
            {"weekday_num": r[0], "weekday_name": r[1]}
            for r in conn.execute("SELECT DISTINCT weekday_num, weekday_name FROM dim_date ORDER BY weekday_num")
        ]
        date_bounds = dict(
            conn.execute("SELECT MIN(trade_date) AS min_date, MAX(trade_date) AS max_date FROM dim_date").fetchone()
        )
    return {
        "tickers": tickers,
        "years": years,
        "quarters": [1, 2, 3, 4],
        "months": months,
        "weekdays": weekdays,
        "date_bounds": date_bounds,
    }


def _compute_ticker_metrics(df: pd.DataFrame) -> dict[str, Any]:
    """Compute exact reconciled return and risk metrics for a single ticker slice."""
    g = df.sort_values("trade_date").reset_index(drop=True)
    n_days = len(g)
    p_start = float(g["close_price"].iloc[0])
    p_end = float(g["close_price"].iloc[-1])

    total_ret = (p_end - p_start) / p_start if p_start > 0 else 0.0
    if n_days >= 2 and p_start > 0:
        cagr = (p_end / p_start) ** (TRADING_DAYS_PER_YEAR / max(n_days - 1, 1)) - 1.0
    else:
        cagr = 0.0

    rets = g["close_price"].pct_change().dropna()
    ann_vol = float(rets.std(ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR)) if len(rets) >= 2 else 0.0
    ann_mean = float(rets.mean() * TRADING_DAYS_PER_YEAR) if len(rets) >= 1 else 0.0
    sharpe = ((ann_mean - RISK_FREE_RATE) / ann_vol) if ann_vol > 0 else 0.0

    # Downside / Sortino ratio (annualized downside deviation below 0%)
    neg_rets = rets[rets < 0]
    downside_dev = float(np.sqrt(np.mean(neg_rets**2)) * np.sqrt(TRADING_DAYS_PER_YEAR)) if len(neg_rets) > 0 else 0.0
    sortino = ((ann_mean - RISK_FREE_RATE) / downside_dev) if downside_dev > 0 else 0.0

    # Historical 95% daily Value at Risk
    var_95_daily = float(np.percentile(rets, 5)) * 100.0 if len(rets) >= 5 else 0.0

    running_peak = g["close_price"].cummax()
    dd_series = (g["close_price"] - running_peak) / running_peak
    max_dd = float(dd_series.min()) * 100.0

    trail_252 = g.tail(252)
    high_52w = float(trail_252["close_price"].max())
    low_52w = float(trail_252["close_price"].min())

    total_vol = int(g["volume"].sum())
    avg_vol = float(g["volume"].mean())

    return {
        "ticker": str(g["ticker"].iloc[0]),
        "company_name": str(g["company_name"].iloc[0]),
        "trading_days": int(n_days),
        "beginning_price": round(p_start, 2),
        "ending_price": round(p_end, 2),
        "lowest_close": round(float(g["close_price"].min()), 2),
        "highest_close": round(float(g["close_price"].max()), 2),
        "low_52w": round(low_52w, 2),
        "high_52w": round(high_52w, 2),
        "running_peak": round(float(running_peak.iloc[-1]), 2),
        "total_return_pct": round(total_ret * 100.0, 2),
        "cagr_pct": round(cagr * 100.0, 2),
        "growth_10k_end": round(10000.0 * (1.0 + total_ret), 2),
        "annualized_volatility_pct": round(ann_vol * 100.0, 2),
        "max_drawdown_pct": round(max_dd, 2),
        "sharpe_ratio": round(sharpe, 2),
        "sortino_ratio": round(sortino, 2),
        "var_95_daily_pct": round(var_95_daily, 2),
        "total_volume": total_vol,
        "avg_daily_volume": round(avg_vol, 0),
    }


def get_dashboard_data(filters: FilterParams) -> dict[str, Any]:
    """Build reconciled multi-view Equity Analytics payload."""
    clauses: list[str] = []
    params: list[Any] = []
    if filters.tickers:
        placeholders = ",".join("?" for _ in filters.tickers)
        clauses.append(f"t.ticker IN ({placeholders})")
        params.extend(filters.tickers)
    if filters.year is not None:
        clauses.append("d.year = ?")
        params.append(filters.year)
    if filters.quarter is not None:
        clauses.append("d.quarter = ?")
        params.append(filters.quarter)
    if filters.month is not None:
        clauses.append("d.month_num = ?")
        params.append(filters.month)
    if filters.weekday_num is not None:
        clauses.append("d.weekday_num = ?")
        params.append(filters.weekday_num)

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    with _connect() as conn:
        df = pd.read_sql_query(
            f"""
            SELECT
                d.trade_date, d.year, d.quarter, d.month_num, d.month_name, d.year_month, d.weekday_num,
                t.ticker, t.company_name, t.sector,
                f.close_price, f.volume
            FROM fact_equity_daily f
            JOIN dim_date d ON f.date_key = d.date_key
            JOIN dim_ticker t ON f.ticker_id = t.ticker_id
            {where_sql}
            ORDER BY d.trade_date, t.ticker
            """,
            conn,
            params=params,
        )

    if df.empty:
        return {
            "empty": True,
            "kpis": {},
            "ranking": [],
            "time_series": [],
            "monthly_returns": [],
            "insights": [],
        }

    # Per-ticker reconciled stats and ranking
    per_ticker = [_compute_ticker_metrics(grp) for _, grp in df.groupby("ticker")]
    per_ticker.sort(key=lambda r: r["total_return_pct"], reverse=True)
    for idx, row in enumerate(per_ticker, start=1):
        row["rank"] = idx

    # Recompute filter-aligned growth_10k, drawdown, rolling volatility per ticker
    df = df.sort_values(["ticker", "trade_date"]).reset_index(drop=True)
    series_frames = []
    for sym, grp in df.groupby("ticker", sort=False):
        g = grp.copy()
        p0 = float(g["close_price"].iloc[0])
        g["growth_10k"] = np.round(10000.0 * (g["close_price"] / p0), 2)
        g["normalized_ret_pct"] = np.round((g["close_price"] / p0 - 1.0) * 100.0, 2)
        pk = g["close_price"].cummax()
        g["drawdown_pct"] = np.round((g["close_price"] - pk) / pk * 100.0, 2)
        rets = g["close_price"].pct_change()
        g["rolling_vol_20d_pct"] = np.round(
            rets.rolling(20, min_periods=5).std(ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR) * 100.0, 2
        )
        series_frames.append(g)
    ts_df = pd.concat(series_frames, ignore_index=True)

    # Monthly Total Return % per ticker (end close vs start close of month)
    monthly_rows = []
    for (ym, sym), grp in ts_df.groupby(["year_month", "ticker"]):
        g = grp.sort_values("trade_date")
        m_ret = (float(g["close_price"].iloc[-1]) / float(g["close_price"].iloc[0]) - 1.0) * 100.0
        monthly_rows.append({"year_month": ym, "ticker": sym, "monthly_return_pct": round(m_ret, 2)})

    # Portfolio-level aggregate across selected tickers (equal-weight composite)
    n_stocks = len(per_ticker)
    best = per_ticker[0]
    worst_dd_row = min(per_ticker, key=lambda r: r["max_drawdown_pct"])
    best_sharpe_row = max(per_ticker, key=lambda r: r["sharpe_ratio"])
    avg_close = float(df["close_price"].mean())
    avg_beg = float(np.mean([r["beginning_price"] for r in per_ticker]))
    avg_end = float(np.mean([r["ending_price"] for r in per_ticker]))
    eq_total_ret = float(np.mean([r["total_return_pct"] for r in per_ticker]))
    eq_cagr = float(np.mean([r["cagr_pct"] for r in per_ticker]))
    eq_growth_10k = float(np.mean([r["growth_10k_end"] for r in per_ticker]))
    avg_vol = float(np.mean([r["annualized_volatility_pct"] for r in per_ticker]))
    tot_volume = int(sum(r["total_volume"] for r in per_ticker))
    avg_daily_vol = float(df.groupby("trade_date")["volume"].sum().mean())
    trading_days = int(df["trade_date"].nunique())

    kpis = {
        "stocks_analyzed": n_stocks,
        "date_start": str(df["trade_date"].min()),
        "date_end": str(df["trade_date"].max()),
        "trading_days": trading_days,
        "avg_close_price": round(avg_close, 2),
        "lowest_closing_price": round(float(df["close_price"].min()), 2),
        "highest_closing_price": round(float(df["close_price"].max()), 2),
        "low_52w": round(min(r["low_52w"] for r in per_ticker), 2),
        "high_52w": round(max(r["high_52w"] for r in per_ticker), 2),
        "beginning_price": round(avg_beg, 2),
        "ending_price": round(avg_end, 2),
        "total_return_pct": round(eq_total_ret, 2),
        "cagr_pct": round(eq_cagr, 2),
        "growth_10k_end": round(eq_growth_10k, 2),
        "best_ticker": best["ticker"],
        "best_return_pct": best["total_return_pct"],
        "worst_drawdown_pct": worst_dd_row["max_drawdown_pct"],
        "avg_volatility_pct": round(avg_vol, 2),
        "best_sharpe_ticker": best_sharpe_row["ticker"],
        "best_sharpe_ratio": best_sharpe_row["sharpe_ratio"],
        "sum_of_volume": tot_volume,
        "avg_daily_volume": round(avg_daily_vol, 0),
        "running_peak": round(max(r["running_peak"] for r in per_ticker), 2),
    }

    insights = [
        {
            "ticker": r["ticker"],
            "company_name": r["company_name"],
            "headline": f"Rank #{r['rank']} · {r['total_return_pct']:+.2f}% Total Return ({r['cagr_pct']:+.2f}% CAGR)",
            "detail": (
                f"Annualized volatility {r['annualized_volatility_pct']:.2f}%, max drawdown {r['max_drawdown_pct']:.2f}%, "
                f"Sharpe {r['sharpe_ratio']:.2f}, $10K grew to ${r['growth_10k_end']:,.0f}."
            ),
        }
        for r in per_ticker
    ]

    return {
        "empty": False,
        "kpis": kpis,
        "ranking": per_ticker,
        "time_series": ts_df.where(pd.notnull(ts_df), None).to_dict(orient="records"),
        "monthly_returns": monthly_rows,
        "insights": insights,
    }
