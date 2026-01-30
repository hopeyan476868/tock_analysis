# data_provider/akshare_fetcher.py
import akshare as ak
import pandas as pd


class AkshareFetcher:
    """
    统一行情获取器
    支持 A / US / HK
    """

    def fetch_daily(
        self,
        symbol: str,
        market: str,
        start_date: str = "20200101"
    ) -> pd.DataFrame:
        market = market.upper()

        if market == "CN":
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                start_date=start_date,
                adjust="qfq"
            )
            return df

        if market == "US":
            return ak.stock_us_daily(symbol=symbol)

        if market == "HK":
            return ak.stock_hk_daily(symbol=symbol)

        raise ValueError(f"Unsupported market: {market}")
