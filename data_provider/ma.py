import pandas as pd

def calc_ma(df: pd.DataFrame, windows=(5,10,20)):
    for w in windows:
        df[f"ma{w}"] = df["close"].rolling(w).mean()
    return df

def calc_bias(df: pd.DataFrame, ma_col="ma5"):
    df["bias"] = (df["close"] / df[ma_col] - 1) * 100
    return df