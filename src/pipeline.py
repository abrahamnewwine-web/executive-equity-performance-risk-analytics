"""ETL pipeline for Executive Equity Performance & Risk Analytics.

Fetches genuine historical daily OHLCV market data for AAPL, AMZN, MSFT, NVDA,
and TSLA from Yahoo Finance public chart API (with deterministic offline fallback
to the verified bundled CSV snapshot), computes daily returns, $10K growth,
running peaks, and drawdowns, and loads the SQLite warehouse.
"""

from __future__ import annotations

import json
import sqlite3
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import (
    DATA_PROCESSED_DIR,
    DATA_RAW_DIR,
    DB_PATH,
    DEFAULT_WINDOW_DAYS,
    SNAPSHOT_CSV,
    SQL_DIR,
    TICKERS,
)


def fetch_yahoo_ticker(ticker: str, range_str: str = "2y") -> pd.DataFrame:
    """Fetch daily OHLCV bars from Yahoo Finance public chart API."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range={range_str}&interval=1d"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    res = payload["chart"]["result"][0]
    timestamps = res["timestamp"]
    quote = res["indicators"]["quote"][0]
    adj_list = res["indicators"].get("adjclose", [{}])[0].get("adjclose", quote["close"])

    rows = []
    for ts, o, h, l, c, ac, v in zip(
        timestamps,
        quote["open"],
        quote["high"],
        quote["low"],
        quote["close"],
        adj_list,
        quote["volume"],
    ):
        if None in (o, h, l, c, v):
            continue
        dt = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
        rows.append(
            {
                "trade_date": dt,
                "ticker": ticker,
                "open_price": round(float(o), 4),
                "high_price": round(float(h), 4),
                "low_price": round(float(l), 4),
                "close_price": round(float(c), 4),
                "adj_close": round(float(ac if ac is not None else c), 4),
                "volume": int(v),
            }
        )
    df = pd.DataFrame(rows).drop_duplicates(subset=["trade_date", "ticker"])
    return df.sort_values("trade_date").reset_index(drop=True)


def acquire_market_data(refresh: bool = False) -> pd.DataFrame:
    """Load verified snapshot CSV or refresh live from Yahoo Finance."""
    if not refresh and SNAPSHOT_CSV.exists():
        df = pd.read_csv(SNAPSHOT_CSV)
        return df

    frames: list[pd.DataFrame] = []
    for _, symbol, _, _, _ in TICKERS:
        try:
            tdf = fetch_yahoo_ticker(symbol, range_str="2y")
            frames.append(tdf)
        except Exception:
            if SNAPSHOT_CSV.exists():
                return pd.read_csv(SNAPSHOT_CSV)
            raise

    combined = pd.concat(frames, ignore_index=True)
    # Align all 5 tickers on common trading dates and keep trailing 370 days
    common_dates = sorted(
        set.intersection(*(set(g["trade_date"]) for _, g in combined.groupby("ticker")))
    )
    if len(common_dates) > DEFAULT_WINDOW_DAYS:
        common_dates = common_dates[-DEFAULT_WINDOW_DAYS:]

    aligned = (
        combined[combined["trade_date"].isin(common_dates)]
        .sort_values(["ticker", "trade_date"])
        .reset_index(drop=True)
    )
    DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
    aligned.to_csv(SNAPSHOT_CSV, index=False)
    return aligned


def build_star_schema(raw_df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Transform daily OHLCV rows into dimension and fact tables."""
    df = raw_df.copy()
    df["trade_date_dt"] = pd.to_datetime(df["trade_date"])
    df = df.sort_values(["ticker", "trade_date_dt"]).reset_index(drop=True)

    unique_dates = pd.DataFrame({"trade_date_dt": sorted(df["trade_date_dt"].unique())})
    dim_date = pd.DataFrame(
        {
            "date_key": unique_dates["trade_date_dt"].dt.strftime("%Y%m%d").astype(int),
            "trade_date": unique_dates["trade_date_dt"].dt.strftime("%Y-%m-%d"),
            "year": unique_dates["trade_date_dt"].dt.year,
            "quarter": unique_dates["trade_date_dt"].dt.quarter,
            "month_num": unique_dates["trade_date_dt"].dt.month,
            "month_name": unique_dates["trade_date_dt"].dt.strftime("%B"),
            "year_month": unique_dates["trade_date_dt"].dt.strftime("%Y-%m"),
            "weekday_num": unique_dates["trade_date_dt"].dt.weekday + 1,
            "weekday_name": unique_dates["trade_date_dt"].dt.strftime("%A"),
        }
    )

    dim_ticker = pd.DataFrame(
        TICKERS, columns=["ticker_id", "ticker", "company_name", "sector", "exchange"]
    )
    ticker_map = dict(zip(dim_ticker["ticker"], dim_ticker["ticker_id"]))

    enriched_frames = []
    for sym, grp in df.groupby("ticker", sort=False):
        g = grp.sort_values("trade_date_dt").copy()
        first_close = float(g["close_price"].iloc[0])
        g["daily_return"] = g["close_price"].pct_change()
        g["growth_10k"] = np.round(10000.0 * (g["close_price"] / first_close), 2)
        g["running_peak"] = np.round(g["close_price"].cummax(), 4)
        g["drawdown_pct"] = np.round((g["close_price"] - g["running_peak"]) / g["running_peak"], 6)
        g["date_key"] = g["trade_date_dt"].dt.strftime("%Y%m%d").astype(int)
        g["ticker_id"] = ticker_map[sym]
        enriched_frames.append(g)

    fact_all = pd.concat(enriched_frames, ignore_index=True)
    fact_equity_daily = fact_all[
        [
            "date_key",
            "ticker_id",
            "open_price",
            "high_price",
            "low_price",
            "close_price",
            "adj_close",
            "volume",
            "daily_return",
            "growth_10k",
            "running_peak",
            "drawdown_pct",
        ]
    ].copy()

    return {
        "dim_date": dim_date,
        "dim_ticker": dim_ticker,
        "fact_equity_daily": fact_equity_daily,
    }


def export_csvs(tables: dict[str, pd.DataFrame]) -> None:
    DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.to_csv(DATA_PROCESSED_DIR / f"{name}.csv", index=False)


def load_sqlite(tables: dict[str, pd.DataFrame], db_path: Path = DB_PATH) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    schema_sql = (SQL_DIR / "schema.sql").read_text(encoding="utf-8")
    with sqlite3.connect(db_path) as conn:
        conn.executescript(schema_sql)
        for tbl in ["dim_date", "dim_ticker", "fact_equity_daily"]:
            tables[tbl].to_sql(tbl, conn, if_exists="append", index=False)
        conn.commit()


def run_pipeline(refresh: bool = False) -> dict[str, int]:
    """Run full Equity ETL pipeline."""
    raw_df = acquire_market_data(refresh=refresh)
    tables = build_star_schema(raw_df)
    export_csvs(tables)
    load_sqlite(tables)
    return {name: len(df) for name, df in tables.items()}


if __name__ == "__main__":
    print("Equity ETL completed:", run_pipeline(refresh=False))
