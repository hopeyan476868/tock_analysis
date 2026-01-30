import re

def normalize_cn_stock(symbol: str) -> str:
    """
    SH688012 / SZ002371 / 688012 / 002371 -> 688012 / 002371
    """
    if not symbol:
        return symbol
    s = symbol.upper().strip()
    s = re.sub(r'^(SH|SZ)', '', s)
    s = re.sub(r'\D', '', s)
    return s