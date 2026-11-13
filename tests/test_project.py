"""Automated financial reconciliation and API test suite for Equity Analytics."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from src.analytics import FilterParams, get_dashboard_data
from src.ba_artifacts import generate_all_ba_artifacts
from src.config import DOCS_BA_DIR, TRADING_DAYS_PER_YEAR
from src.pipeline import run_pipeline

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_warehouse() -> None:
    run_pipeline(refresh=False)
    if not (DOCS_BA_DIR / "rtm_workbook.xlsx").exists():
        generate_all_ba_artifacts()


def test_etl_completeness() -> None:
    d = get_dashboard_data(FilterParams())
    assert not d["empty"]
    assert d["kpis"]["stocks_analyzed"] == 5
    assert d["kpis"]["trading_days"] == 370
    assert len(d["time_series"]) == 5 * 370


def test_financial_math_reconciliation() -> None:
    d = get_dashboard_data(FilterParams())
    for row in d["ranking"]:
        expected_ret = ((row["ending_price"] - row["beginning_price"]) / row["beginning_price"]) * 100.0
        assert pytest.approx(row["total_return_pct"], abs=0.15) == expected_ret
        expected_cagr = ((row["ending_price"] / row["beginning_price"]) ** (TRADING_DAYS_PER_YEAR / (row["trading_days"] - 1)) - 1.0) * 100.0
        assert pytest.approx(row["cagr_pct"], abs=0.15) == expected_cagr
        expected_10k = 10000.0 * (1.0 + row["total_return_pct"] / 100.0)
        assert pytest.approx(row["growth_10k_end"], abs=25.0) == expected_10k


def test_risk_invariants() -> None:
    d = get_dashboard_data(FilterParams())
    for row in d["ranking"]:
        assert row["annualized_volatility_pct"] > 0
        assert row["max_drawdown_pct"] <= 0
        assert row["var_95_daily_pct"] < 0
        assert row["low_52w"] <= row["high_52w"]


def test_ranking_order() -> None:
    d = get_dashboard_data(FilterParams())
    returns = [r["total_return_pct"] for r in d["ranking"]]
    assert returns == sorted(returns, reverse=True)


def test_api_and_validation() -> None:
    assert client.get("/api/health").status_code == 200
    assert client.get("/").status_code == 200

    res_sub = client.get("/api/dashboard?tickers=AAPL,NVDA")
    assert res_sub.status_code == 200
    assert res_sub.json()["kpis"]["stocks_analyzed"] == 2

    res_bad = client.get("/api/dashboard?tickers=INVALID")
    assert res_bad.status_code == 400

    res_csv = client.get("/api/export/ranking-csv")
    assert res_csv.status_code == 200
    assert "sharpe_ratio" in res_csv.text

    assert (DOCS_BA_DIR / "rtm_workbook.xlsx").exists()
    assert (DOCS_BA_DIR / "uat_test_log.xlsx").exists()
    assert (DOCS_BA_DIR / "executive_insights_report.pdf").exists()
