"""Configuration and equity universe metadata."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_RAW_DIR = BASE_DIR / "data" / "raw"
DATA_PROCESSED_DIR = BASE_DIR / "data" / "processed"
SQL_DIR = BASE_DIR / "sql"
DOCS_BA_DIR = BASE_DIR / "docs" / "business-analysis"
SCREENSHOTS_DIR = BASE_DIR / "assets" / "screenshots"
DB_PATH = DATA_PROCESSED_DIR / "equity_analytics.db"
SNAPSHOT_CSV = DATA_RAW_DIR / "equity_prices_snapshot.csv"

RISK_FREE_RATE = 0.04  # Annualized 4.0% Treasury benchmark for Sharpe ratio
TRADING_DAYS_PER_YEAR = 252
DEFAULT_WINDOW_DAYS = 370

TICKERS = [
    (1, "AAPL", "Apple Inc.", "Consumer Technology", "NASDAQ"),
    (2, "AMZN", "Amazon.com Inc.", "Cloud & E-Commerce", "NASDAQ"),
    (3, "MSFT", "Microsoft Corporation", "Enterprise Software & Cloud", "NASDAQ"),
    (4, "NVDA", "NVIDIA Corporation", "Semiconductors & AI", "NASDAQ"),
    (5, "TSLA", "Tesla, Inc.", "Automotive & Clean Energy", "NASDAQ"),
]
