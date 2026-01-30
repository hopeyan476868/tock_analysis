# src/core/pipeline.py

from typing import List

from data_provider import DataFetcherManager
from src.analyzer import AnalysisResult
from src.stock_analyzer import StockAnalyzer


class StockAnalysisPipeline:
    def __init__(self):
        self.fetcher_manager = DataFetcherManager()
        self.analyzer = StockAnalyzer(self.fetcher_manager)

    def run(self, symbols: List[str]) -> List[AnalysisResult]:
        results: List[AnalysisResult] = []

        for symbol in symbols:
            try:
                result = self.analyzer.analyze(symbol)
                if result:
                    results.append(result)
            except Exception as e:
                print(f"[Pipeline] 分析失败 {symbol}: {e}")

        return results
