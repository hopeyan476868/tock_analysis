# data_provider/__init__.py
from .akshare_fetcher import AkshareFetcher
from .manager import DataFetcherManager

__all__ = [
    "AkshareFetcher",
    "DataFetcherManager",
]
