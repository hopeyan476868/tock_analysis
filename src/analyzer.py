# src/analyzer.py

from src.market_fetcher import MarketFetcher
from src.brooks_engine import BrooksEngine
from src.report_builder import ReportBuilder


def analyze(symbol: str) -> str:
    profile = MarketFetcher.get_stock_profile(symbol)
    df = MarketFetcher.get_price_df(symbol)

    brooks = BrooksEngine(df)
    pa_decision = brooks.decision()

    analysis_context = {
        "price_action": {
            "signal": pa_decision["signal"],
            "allow_trade": pa_decision["allow_trade"],
            "reason": pa_decision["reason"],
        }
    }

    return ReportBuilder.build(profile, analysis_context)
