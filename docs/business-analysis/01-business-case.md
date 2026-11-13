# Business Case & Problem Statement — Executive Equity Performance & Risk Analytics

**Document ID:** EEPR-BC-001 | **Author:** Abraham Adetola, PMP®, PMI-PBA®, CSM®, CSPO®

## Business Problem
Evaluating competing mega-cap technology and growth equities (`AAPL`, `AMZN`, `MSFT`, `NVDA`, `TSLA`) across shifting market regimes requires consistent return, CAGR, volatility, drawdown, and risk-adjusted Sharpe comparisons. Manual spreadsheet workflows introduce return-basis inconsistencies, weak data lineage, and isolated risk views.

## Objectives
- **BO-01:** Consolidate 370 aligned daily trading observations into a governed SQLite star schema.
- **BO-02:** Reconcile Total Return %, CAGR %, and standardized `$10,000` investment growth trajectories.
- **BO-03:** Quantify downside risk via Annualized Volatility %, Maximum Drawdown %, Daily 95% VaR, Sharpe, and Sortino ratios.
- **BO-04:** Deliver 4 integrated analytical views (`Executive Dashboard`, `Performance Analysis`, `Risk Analysis`, `Executive Insight`).
- **BO-05:** Enable multi-ticker and calendar slicing with automated reconciliation tests.
