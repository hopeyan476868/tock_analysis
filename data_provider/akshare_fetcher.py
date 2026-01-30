import re
import pandas as pd
from datetime import datetime

# A股
import akshare as ak

# 港股 / 美股
import yfinance as yf


# =====================================================
# 1. 市场识别 & 代码规范
# =====================================================
def detect_market(symbol: str) -> str:
    """
    返回: CN / HK / US
    """
    s = symbol.upper().strip()

    if s.startswith(("SH", "SZ")) or re.fullmatch(r"\d{6}", s):
        return "CN"

    if s.endswith(".HK"):
        return "HK"

    return "US"


def normalize_symbol(symbol: str) -> str:
    """
    - A股: SH688012 / SZ002371 -> 688012
    - 港股: 0700.HK 保持
    - 美股: AAPL / MSFT 保持
    """
    s = symbol.upper().strip()

    if s.startswith(("SH", "SZ")):
        return re.sub(r"^(SH|SZ)", "", s)

    return s


# =====================================================
# 2. 技术指标（统一）
# =====================================================
def enrich_indicators(df: pd.DataFrame) -> pd.DataFrame:
    if len(df) < 20:
        raise RuntimeError("K线数量不足，无法计算 MA20")

    for w in (5, 10, 20):
        df[f"ma{w}"] = df["close"].rolling(w).mean()

    df["bias"] = (df["close"] / df["ma5"] - 1) * 100
    df["vol_ma5"] = df["volume"].rolling(5).mean()
    df["vol_ma20"] = df["volume"].rolling(20).mean()

    return df


# =====================================================
# 3. Fetcher 主类
# =====================================================
class MarketFetcher:
    def __init__(self):
        pass

    # -------------------------------------------------
    # A股
    # -------------------------------------------------
    def _fetch_cn(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        code = normalize_symbol(symbol)

        df = ak.stock_zh_a_hist(
            symbol=code,
            period="daily",
            start_date=start,
            end_date=end,
            adjust="qfq",
        )

        if df is None or df.empty:
            raise RuntimeError(f"A股无行情数据: {symbol}")

        df = df.rename(
            columns={
                "日期": "date",
                "开盘": "open",
                "收盘": "close",
                "最高": "high",
                "最低": "low",
                "成交量": "volume",
            }
        )

        df["date"] = pd.to_datetime(df["date"])
        return df[["date", "open", "high", "low", "close", "volume"]]

    # -------------------------------------------------
    # 港股 / 美股
    # -------------------------------------------------
    def _fetch_yf(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start, end=end, auto_adjust=True)

        if df is None or df.empty:
            raise RuntimeError(f"YFinance 无行情数据: {symbol}")

        df = df.reset_index()
        df = df.rename(
            columns={
                "Date": "date",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
            }
        )

        return df[["date", "open", "high", "low", "close", "volume"]]

    # -------------------------------------------------
    # 对外统一接口
    # -------------------------------------------------
    def get_stock_data(
        self,
        symbol: str,
        start_date: str = "2022-01-01",
        end_date: str = None,
    ) -> dict:

        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")

        market = detect_market(symbol)
        norm_symbol = normalize_symbol(symbol)

        if market == "CN":
            df = self._fetch_cn(norm_symbol, start_date.replace("-", ""), end_date.replace("-", ""))
        else:
            df = self._fetch_yf(norm_symbol, start_date, end_date)

        df = df.sort_values("date").reset_index(drop=True)
        df = enrich_indicators(df)

        latest = df.iloc[-1]

        return {
            "symbol": symbol,
            "market": market,
            "latest": {
                "date": str(latest["date"].date()),
                "close": float(latest["close"]),
                "ma5": float(latest["ma5"]),
                "ma10": float(latest["ma10"]),
                "ma20": float(latest["ma20"]),
                "bias": float(latest["bias"]),
                "volume": float(latest["volume"]),
            },
            "history": df,
        }
