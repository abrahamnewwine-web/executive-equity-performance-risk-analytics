"""CLI entry point for Executive Equity Performance & Risk Analytics."""

from __future__ import annotations

import argparse
import uvicorn

from src.ba_artifacts import generate_all_ba_artifacts
from src.pipeline import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Executive Equity Analytics Runner")
    parser.add_argument("--build-only", action="store_true")
    parser.add_argument("--refresh", action="store_true", help="Refresh live Yahoo Finance quotes")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8003)
    args = parser.parse_args()

    print("Equity ETL completed:", run_pipeline(refresh=args.refresh))
    generate_all_ba_artifacts()
    print("BA workbooks & PDF report generated.")
    if not args.build_only:
        uvicorn.run("app.main:app", host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
