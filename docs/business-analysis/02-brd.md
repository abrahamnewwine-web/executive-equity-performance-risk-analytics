# Business Requirements Document (BRD) — Executive Equity Performance & Risk Analytics

| Req ID | Requirement Description | Priority |
| :--- | :--- | :--- |
| `BR-001` | Store 370 daily trading observations per ticker (`AAPL`, `AMZN`, `MSFT`, `NVDA`, `TSLA`) from Yahoo Finance with verified offline CSV snapshot fallback. | High |
| `BR-002` | Reconcile Total Return %, CAGR % (252-day trading convention), and Growth of `$10,000` across Python, SQL, and DAX. | High |
| `BR-003` | Compute Annualized Volatility %, Max Drawdown %, Daily 95% VaR, Sharpe Ratio, and Sortino Ratio. | High |
| `BR-004` | Provide 4 navigable analytical views (`Executive Dashboard`, `Performance Analysis`, `Risk Analysis`, `Executive Insight`). | High |
| `BR-005` | Support multi-ticker toggle chips, Year/Quarter/Month/Weekday filters, HTTP 400 validation, and CSV export. | Medium |
