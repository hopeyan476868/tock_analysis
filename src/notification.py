# src/notification.py

from typing import List
from src.analyzer import AnalysisResult


class NotificationService:
    def __init__(self):
        pass

    def send(self, results: List[AnalysisResult]):
        for r in results:
            print(
                f"[通知] {r.symbol} | {r.decision} | 评分 {r.score} | 趋势 {r.trend}"
            )
