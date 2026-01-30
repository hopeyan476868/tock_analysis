# src/analyzer.py

from dataclasses import dataclass
from typing import Optional, Dict, Any

from src.market_fetcher import MarketFetcher
from src.brooks_engine import BrooksEngine
from src.report_builder import ReportBuilder


# =======【关键：必须存在】=======
@dataclass
class AnalysisResult:
    symbol: str
    report: str
    allow_trade: bool
    extra: Optional[Dict[str, Any]] = None


# ======= 主分析入口 =======
def analyze(symbol: str) -> AnalysisResult:
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

    report = ReportBuilder.build(profile, analysis_context)

    return AnalysisResult(
        symbol=symbol,
        report=report,
        allow_trade=pa_decision["allow_trade"],
        extra=analysis_context,
    )
