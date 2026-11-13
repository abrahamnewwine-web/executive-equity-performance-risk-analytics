-- Executive Equity Performance & Risk Analytics - Production SQL Queries

-- 1. Latest Closing, High/Low, and Cumulative Volume by Equity
SELECT
    t.ticker,
    t.company_name,
    COUNT(*) AS trading_days,
    MIN(d.trade_date) AS first_date,
    MAX(d.trade_date) AS last_date,
    ROUND(MIN(f.close_price), 2) AS lowest_close,
    ROUND(MAX(f.close_price), 2) AS highest_close,
    ROUND(MAX(f.running_peak), 2) AS peak_close,
    ROUND(MIN(f.drawdown_pct) * 100.0, 2) AS max_drawdown_pct,
    SUM(f.volume) AS total_volume,
    ROUND(AVG(f.volume), 0) AS avg_daily_volume
FROM fact_equity_daily f
JOIN dim_ticker t ON f.ticker_id = t.ticker_id
JOIN dim_date d ON f.date_key = d.date_key
GROUP BY t.ticker_id, t.ticker, t.company_name
ORDER BY t.ticker;

-- 2. Monthly Average Return by Equity
SELECT
    d.year_month,
    t.ticker,
    COUNT(*) AS obs_days,
    ROUND(SUM(COALESCE(f.daily_return, 0.0)) * 100.0, 2) AS approx_monthly_return_pct
FROM fact_equity_daily f
JOIN dim_ticker t ON f.ticker_id = t.ticker_id
JOIN dim_date d ON f.date_key = d.date_key
GROUP BY d.year_month, t.ticker
ORDER BY d.year_month, t.ticker;
