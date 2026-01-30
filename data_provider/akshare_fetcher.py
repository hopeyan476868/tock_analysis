# data_provider/akshare_fetcher.py
import akshare as ak
import pandas as pd


class AkshareFetcher:
    def fetch_daily(
        self,
        symbol: str,
        market: str,
        start_date: str = "20200101"
    ) -> pd.DataFrame:
        """
        market: CN / US / HK
        """
        if market == "CN":
            return ak.stock_zh_a_hist(
                symbol=symbol,
                start_date=start_date,
                adjust="qfq"
            )

        if market == "US":
            return ak.stock_us_daily(symbol=symbol)

        if market == "HK":
            return ak.stock_hk_daily(symbol=symbol)

        raise ValueError(f"Unsupported market: {market}")
