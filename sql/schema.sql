-- Executive Equity Performance & Risk Analytics - Star Schema DDL (SQLite)

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS fact_equity_daily;
DROP TABLE IF EXISTS dim_ticker;
DROP TABLE IF EXISTS dim_date;

CREATE TABLE dim_date (
    date_key        INTEGER PRIMARY KEY,
    trade_date      TEXT NOT NULL UNIQUE,
    year            INTEGER NOT NULL,
    quarter         INTEGER NOT NULL,
    month_num       INTEGER NOT NULL,
    month_name      TEXT NOT NULL,
    year_month      TEXT NOT NULL,
    weekday_num     INTEGER NOT NULL,
    weekday_name    TEXT NOT NULL
);

CREATE TABLE dim_ticker (
    ticker_id       INTEGER PRIMARY KEY,
    ticker          TEXT NOT NULL UNIQUE,
    company_name    TEXT NOT NULL,
    sector          TEXT NOT NULL,
    exchange        TEXT NOT NULL
);

CREATE TABLE fact_equity_daily (
    price_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    date_key        INTEGER NOT NULL REFERENCES dim_date(date_key),
    ticker_id       INTEGER NOT NULL REFERENCES dim_ticker(ticker_id),
    open_price      REAL NOT NULL CHECK (open_price > 0),
    high_price      REAL NOT NULL CHECK (high_price > 0),
    low_price       REAL NOT NULL CHECK (low_price > 0),
    close_price     REAL NOT NULL CHECK (close_price > 0),
    adj_close       REAL NOT NULL CHECK (adj_close > 0),
    volume          INTEGER NOT NULL CHECK (volume >= 0),
    daily_return    REAL,
    growth_10k      REAL NOT NULL,
    running_peak    REAL NOT NULL,
    drawdown_pct    REAL NOT NULL,
    UNIQUE(date_key, ticker_id)
);

CREATE INDEX idx_equity_ticker_date ON fact_equity_daily(ticker_id, date_key);
CREATE INDEX idx_equity_date ON fact_equity_daily(date_key);
