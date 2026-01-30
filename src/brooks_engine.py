class BrooksEngine:
    def __init__(self, df):
        self.df = df

    def signal(self):
        if len(self.df) < 2:
            return {"type": "NONE", "reason": "Not enough data"}

        last = self.df.iloc[-1]
        prev = self.df.iloc[-2]

        if last["close"] > prev["high"]:
            return {"type": "BUY", "reason": "Bull breakout"}
        if last["close"] < prev["low"]:
            return {"type": "SELL", "reason": "Bear breakout"}

        return {"type": "NONE", "reason": "No clear price action signal"}

    def decision(self):
        sig = self.signal()
        allow_trade = sig["type"] in ("BUY", "SELL")

        return {
            "signal": sig,
            "allow_trade": allow_trade,
            "reason": (
                "存在明确价格行为交易结构"
                if allow_trade
                else "未识别到可靠的价格行为交易结构，仅供研究观察"
            ),
        }
