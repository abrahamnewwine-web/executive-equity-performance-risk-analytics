"""FastAPI application for Executive Equity Performance & Risk Analytics."""

from __future__ import annotations

import csv
import io
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.analytics import FilterParams, get_dashboard_data, get_filter_options

APP_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="Executive Equity Performance & Risk Analytics",
    description="Four-view interactive equity performance, volatility, drawdown, and Sharpe analytics platform.",
    version="1.0.0",
)

app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
templates = Jinja2Templates(directory=APP_DIR / "templates")


@app.get("/", response_class=HTMLResponse)
def dashboard_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "index.html", {"options": get_filter_options()})


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "executive-equity-performance-risk-analytics"}


@app.get("/api/filters")
def api_filters() -> dict[str, object]:
    return get_filter_options()


@app.get("/api/dashboard")
def api_dashboard(
    tickers: str | None = Query(default=None, description="Comma-separated equity tickers"),
    year: int | None = Query(default=None, ge=2020, le=2030),
    quarter: int | None = Query(default=None, ge=1, le=4),
    month: int | None = Query(default=None, ge=1, le=12),
    weekday_num: int | None = Query(default=None, ge=1, le=5),
) -> dict[str, object]:
    opts = get_filter_options()
    valid_tickers = {t["ticker"] for t in opts["tickers"]}
    parsed_tickers: tuple[str, ...] | None = None
    if tickers and tickers.strip() and tickers.strip() != "All":
        tlist = tuple(t.strip().upper() for t in tickers.split(",") if t.strip())
        invalid = [t for t in tlist if t not in valid_tickers]
        if invalid:
            raise HTTPException(status_code=400, detail=f"Unknown equity ticker(s): {','.join(invalid)}")
        parsed_tickers = tlist

    params = FilterParams(
        tickers=parsed_tickers,
        year=year,
        quarter=quarter,
        month=month,
        weekday_num=weekday_num,
    )
    return get_dashboard_data(params)


@app.get("/api/export/ranking-csv")
def export_ranking_csv(
    tickers: str | None = Query(default=None),
    year: int | None = Query(default=None, ge=2020, le=2030),
    quarter: int | None = Query(default=None, ge=1, le=4),
    month: int | None = Query(default=None, ge=1, le=12),
    weekday_num: int | None = Query(default=None, ge=1, le=5),
) -> StreamingResponse:
    data = api_dashboard(tickers=tickers, year=year, quarter=quarter, month=month, weekday_num=weekday_num)
    rows = data["ranking"]
    buf = io.StringIO()
    if rows:
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    else:
        buf.write("rank,ticker,company_name,total_return_pct,cagr_pct,annualized_volatility_pct,max_drawdown_pct,sharpe_ratio\n")
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=equity_performance_ranking.csv"},
    )
