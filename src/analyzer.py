# src/analyzer.py
from market_fetcher import MarketFetcher
from brooks_engine import BrooksEngine
from report_builder import ReportBuilder

def analyze(symbol: str) -> str:
    profile = MarketFetcher.get_stock_profile(symbol)
    df = MarketFetcher.get_price_df(symbol)

    brooks = BrooksEngine(df)
    signal = brooks.signal()

    return ReportBuilder.build(profile, signal)