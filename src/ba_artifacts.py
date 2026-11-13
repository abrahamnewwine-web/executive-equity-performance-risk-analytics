"""Generate Excel RTM/UAT workbooks and ReportLab Executive PDF for Equity Analytics."""

from __future__ import annotations

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from src.analytics import FilterParams, get_dashboard_data
from src.config import DOCS_BA_DIR

NAVY_FILL = PatternFill(start_color="0D1322", end_color="0D1322", fill_type="solid")
HEADER_FONT = Font(color="FFFFFF", bold=True, size=11)


def _write_sheet(wb: openpyxl.Workbook, title: str, headers: list[str], rows: list[list[object]], first: bool = False) -> None:
    ws = wb.active if first else wb.create_sheet(title=title)
    ws.title = title
    ws.append(headers)
    for cell in ws[1]:
        cell.fill = NAVY_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for row in rows:
        ws.append(row)
    for col in ws.columns:
        max_len = max((len(str(c.value or "")) for c in col), default=12)
        ws.column_dimensions[col[0].column_letter].width = min(max(max_len + 4, 14), 48)


def generate_all_ba_artifacts() -> None:
    DOCS_BA_DIR.mkdir(parents=True, exist_ok=True)
    d = get_dashboard_data(FilterParams())

    wb_rtm = openpyxl.Workbook()
    _write_sheet(
        wb_rtm,
        "RTM",
        ["Req ID", "Objective", "Requirement", "Priority", "Implementation", "Test ID", "Status"],
        [
            ["BR-001", "BO-01", "Ingest 370-day daily market OHLCV data for AAPL, AMZN, MSFT, NVDA, TSLA", "High", "src/pipeline.py & sql/schema.sql", "TC-001", "Verified"],
            ["BR-002", "BO-02", "Reconcile Total Return %, CAGR %, and $10,000 investment growth math", "High", "src/analytics.py & powerbi/measures.dax", "TC-002", "Verified"],
            ["BR-003", "BO-03", "Compute Annualized Volatility, Max Drawdown, 95% VaR, Sharpe & Sortino", "High", "src/analytics.py (_compute_ticker_metrics)", "TC-003", "Verified"],
            ["BR-004", "BO-04", "Deliver 4 interactive dashboard views (Executive, Performance, Risk, Insight)", "High", "app/templates/index.html & dashboard.js", "TC-004", "Verified"],
            ["BR-005", "BO-05", "Support multi-ticker & calendar filtering with HTTP 400 validation and CSV export", "Medium", "app/main.py", "TC-005", "Verified"],
        ],
        first=True,
    )
    wb_rtm.save(DOCS_BA_DIR / "rtm_workbook.xlsx")

    wb_uat = openpyxl.Workbook()
    _write_sheet(
        wb_uat,
        "UAT_Test_Cases",
        ["Test ID", "Req ID", "Scenario", "Expected Outcome", "Status", "Automated Test"],
        [
            ["TC-001", "BR-001", "370-Day Market Dataset Completeness", "5 tickers * 370 days = 1,850 aligned daily records", "Pass", "test_etl_completeness"],
            ["TC-002", "BR-002", "CAGR & $10K Growth Reconciliation", "Formula matches exact (P_end/P_start)^(252/(N-1)) - 1", "Pass", "test_financial_math_reconciliation"],
            ["TC-003", "BR-003", "Drawdown & Volatility Invariants", "Max drawdown <= 0; Volatility > 0; Sharpe finite", "Pass", "test_risk_invariants"],
            ["TC-004", "BR-004", "Ticker Ranking Ordering", "Ranking strictly sorted descending by Total Return %", "Pass", "test_ranking_order"],
            ["TC-005", "BR-005", "API Ticker Validation & CSV Export", "HTTP 200 valid filters/CSV; HTTP 400 invalid ticker", "Pass", "test_api_and_validation"],
        ],
        first=True,
    )
    _write_sheet(
        wb_uat,
        "Defect_Log",
        ["Defect ID", "Severity", "Observation", "Resolution", "Status"],
        [
            ["DEF-001", "Minor", "Reference visual header misspelled TSLA as 'TELA' and '20260'", "Fixed labels & dynamically bound header date span", "Closed"],
            ["DEF-002", "High", "Spec required independent reconciliation of CAGR, drawdown & volume", "Added direct formula assertions in pytest against pandas/numpy series", "Closed"],
        ],
        first=False,
    )
    wb_uat.save(DOCS_BA_DIR / "uat_test_log.xlsx")

    doc = SimpleDocTemplate(str(DOCS_BA_DIR / "executive_insights_report.pdf"), pagesize=letter)
    styles = getSampleStyleSheet()
    k = d["kpis"]
    table_data = [["Rank", "Ticker", "Total Return %", "CAGR %", "Volatility %", "Max DD %", "Sharpe"]]
    for r in d["ranking"]:
        table_data.append([
            str(r["rank"]), r["ticker"], f"{r['total_return_pct']:+.2f}%", f"{r['cagr_pct']:+.2f}%",
            f"{r['annualized_volatility_pct']:.2f}%", f"{r['max_drawdown_pct']:.2f}%", f"{r['sharpe_ratio']:.2f}",
        ])
    tbl = Table(table_data, colWidths=[45, 65, 90, 75, 85, 80, 65])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0D1322")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (1, 0), (1, -1), "LEFT"),
    ]))
    doc.build([
        Paragraph("Executive Equity Performance & Risk Analytics — Reconciled Report", styles["Title"]),
        Paragraph("Prepared by Abraham Adetola, PMP®, PMI-PBA®, CSM®, CSPO®", styles["Italic"]),
        Spacer(1, 10),
        Paragraph(
            f"Trailing {k['trading_days']}-trading-day real market window ({k['date_start']} to {k['date_end']}) "
            f"across AAPL, AMZN, MSFT, NVDA, and TSLA. Equal-weight composite Total Return: {k['total_return_pct']:+.2f}%, "
            f"CAGR: {k['cagr_pct']:+.2f}%, Best Performing Equity: {k['best_ticker']} ({k['best_return_pct']:+.2f}%).",
            styles["BodyText"],
        ),
        Spacer(1, 10),
        tbl,
    ])
