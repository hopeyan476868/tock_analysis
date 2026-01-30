# src/analyzer.py
from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class AnalysisResult:
    symbol: str
    market: str
    score: int
    trend: str
    decision: str
    summary: str
    data: Dict[str, Any]


class Analyzer:
    def analyze(self, symbol: str, market: str) -> AnalysisResult:
        raise NotImplementedError
