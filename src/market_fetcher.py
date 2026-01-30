# src/market_fetcher.py
import akshare as ak
import yfinance as yf
import pandas as pd

class MarketFetcher:
    """
    统一行情入口：
    - A股：AkShare
    - 港股 / 美股：yfinance
    """

    @staticmethod
    def get_stock_profile(symbol: str) -> dict:
        """
        返回：{code, name, market}
        """
        if symbol.startswith(("SH", "SZ")):
            code = symbol[-6:]
            info = ak.stock_individual_info_em(symbol=code)
            name = info.loc[info["item"] == "股票简称", "value"].values[0]
            return {"code": symbol, "name": name, "market": "CN"}

        if symbol.endswith(".HK"):
            info = yf.Ticker(symbol).info
            return {"code": symbol, "name": info.get("shortName"), "market": "HK"}

        # 美股
        info = yf.Ticker(symbol).info
        return {"code": symbol, "name": info.get("shortName"), "market": "US"}

    @staticmethod
    def get_price_df(symbol: str, period="6mo") -> pd.DataFrame:
        """
        返回标准化 K 线：open high low close volume
        """
        if symbol.startswith(("SH", "SZ")):
            code = symbol[-6:]
            df = ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                adjust="qfq"
            )
            df = df.rename(columns={
                "开盘": "open",
                "最高": "high",
                "最低": "low",
                "收盘": "close",
                "成交量": "volume"
            })
            return df[["open", "high", "low", "close", "volume"]]

        df = yf.download(symbol, period=period)
        return df[["Open", "High", "Low", "Close", "Volume"]].rename(
            columns=str.lower
        )