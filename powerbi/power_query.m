// Executive Equity Performance & Risk Analytics - Power Query (M) Script
let
    BasePath = "C:\path\to\executive-equity-performance-risk-analytics\data\processed\",
    Source = Csv.Document(File.Contents(BasePath & "fact_equity_daily.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.None]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"date_key", Int64.Type}, {"ticker_id", Int64.Type},
        {"open_price", type number}, {"high_price", type number}, {"low_price", type number},
        {"close_price", type number}, {"adj_close", type number}, {"volume", Int64.Type},
        {"daily_return", type number}, {"growth_10k", type number},
        {"running_peak", type number}, {"drawdown_pct", type number}
    })
in
    Typed
