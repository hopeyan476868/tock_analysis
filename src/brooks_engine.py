from __future__ import annotations
from dataclasses import dataclass, asdict
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple


# =========================
# 基础工具
# =========================
def _true_range(df: pd.DataFrame) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        (df["high"] - df["low"]),
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr

def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    return _true_range(df).rolling(period).mean()

def _body(df: pd.DataFrame) -> pd.Series:
    return (df["close"] - df["open"]).abs()

def _range(df: pd.DataFrame) -> pd.Series:
    return (df["high"] - df["low"]).replace(0, np.nan)

def _bull(df: pd.DataFrame) -> pd.Series:
    return df["close"] > df["open"]

def _bear(df: pd.DataFrame) -> pd.Series:
    return df["close"] < df["open"]

def _close_pos(df: pd.DataFrame) -> pd.Series:
    # close 在 bar range 中的位置 0~1
    return (df["close"] - df["low"]) / _range(df)

def _swing_points(series: pd.Series, left: int = 2, right: int = 2) -> Tuple[List[int], List[int]]:
    """
    简易 swing high/low：比左右窗口都高/低
    """
    highs, lows = [], []
    for i in range(left, len(series) - right):
        window_left = series[i-left:i]
        window_right = series[i+1:i+1+right]
        if series[i] > window_left.max() and series[i] > window_right.max():
            highs.append(i)
        if series[i] < window_left.min() and series[i] < window_right.min():
            lows.append(i)
    return highs, lows

def _near(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol


# =========================
# 结构化输出
# =========================
@dataclass
class Setup:
    type: str                 # H1/H2/2EL/2ES/FailedBreakout/RangeFade etc.
    direction: str            # Bull/Bear
    trigger: str              # 触发条件描述
    entry: Optional[float]    # 入场价（建议）
    stop: Optional[float]     # 止损
    target_1: Optional[float] # 第一目标
    confidence: str           # low/medium/high
    notes: str                # 解释


@dataclass
class PriceActionResult:
    market_type: str          # Trend/TradingRange/SpikeChannel
    direction: str            # Bull/Bear/Neutral
    context: Dict[str, Any]
    key_levels: Dict[str, Any]
    setups: List[Dict[str, Any]]
    invalidations: List[str]


# =========================
# 核心判定：Trend / TR / Spike&Channel
# =========================
def classify_market(df: pd.DataFrame, lookback: int = 60) -> Dict[str, Any]:
    """
    返回 market_type, direction, 以及一些上下文特征
    """
    d = df.tail(lookback).copy()
    if len(d) < 30:
        raise ValueError("Not enough bars for price action classification (need >=30).")

    atr14 = _atr(d, 14)
    body = _body(d)
    rng = _range(d)
    close_pos = _close_pos(d)

    # 基本统计
    atr_now = float(atr14.iloc[-1]) if not np.isnan(atr14.iloc[-1]) else float(_true_range(d).iloc[-1])
    avg_body = float(body.tail(20).mean())
    avg_rng = float(rng.tail(20).mean())
    body_to_range = avg_body / (avg_rng + 1e-9)

    # 斜率/趋势：用回归估计近 N 日 close 的斜率
    n = min(40, len(d))
    y = d["close"].tail(n).values
    x = np.arange(n)
    slope = np.polyfit(x, y, 1)[0]
    # 用 ATR 标准化，避免不同价格量级影响
    slope_norm = slope / (atr_now + 1e-9)

    # 是否有 Spike：最近 5 根是否出现 “大实体 + 收在高位/低位” 且幅度显著
    big_body = body > (body.rolling(20).mean() * 1.6)
    spike_bull = big_body & _bull(d) & (close_pos > 0.75) & (rng > atr14 * 1.2)
    spike_bear = big_body & _bear(d) & (close_pos < 0.25) & (rng > atr14 * 1.2)
    has_spike = bool(spike_bull.tail(6).any() or spike_bear.tail(6).any())

    # Trading Range 特征：斜率小 + 多次穿越中轴 + 实体相对小
    # 用 close 与 20MA 的穿越次数来衡量“来回”
    ma20 = d["close"].rolling(20).mean()
    cross = ((d["close"] > ma20) != (d["close"].shift(1) > ma20.shift(1))).fillna(False)
    crosses = int(cross.tail(30).sum())

    # Trend 强度：close 连续创新高/新低的倾向（简化）
    hh = d["high"].diff()
    ll = d["low"].diff()
    up_pressure = float((hh.tail(20) > 0).mean() + (ll.tail(20) > 0).mean()) / 2
    down_pressure = float((hh.tail(20) < 0).mean() + (ll.tail(20) < 0).mean()) / 2

    # 判定阈值（工程经验值，后续可调）
    trend_like = abs(slope_norm) > 0.25 and body_to_range > 0.45
    range_like = abs(slope_norm) < 0.18 and crosses >= 8

    if has_spike and trend_like:
        market_type = "SpikeChannel"
    elif range_like:
        market_type = "TradingRange"
    else:
        market_type = "Trend"

    # 方向
    if market_type == "TradingRange":
        direction = "Neutral"
    else:
        direction = "Bull" if slope_norm >= 0 else "Bear"

    return {
        "market_type": market_type,
        "direction": direction,
        "metrics": {
            "atr14": atr_now,
            "slope_norm": float(slope_norm),
            "body_to_range": float(body_to_range),
            "crosses_30": crosses,
            "up_pressure": up_pressure,
            "down_pressure": down_pressure,
            "has_spike": has_spike,
        }
    }


# =========================
# Setup 识别：H1/H2/2EL（趋势）+ 失败突破（区间）
# =========================
def detect_setups(df: pd.DataFrame, market_info: Dict[str, Any], lookback: int = 80) -> List[Setup]:
    d = df.tail(lookback).copy()
    atr14 = _atr(d, 14)
    atr_now = float(atr14.iloc[-1]) if not np.isnan(atr14.iloc[-1]) else float(_true_range(d).iloc[-1])

    # swing levels
    highs, lows = _swing_points(d["high"], 2, 2)
    swing_high = float(d["high"].iloc[highs[-1]]) if highs else float(d["high"].max())
    swing_low = float(d["low"].iloc[lows[-1]]) if lows else float(d["low"].min())

    last = d.iloc[-1]
    prev = d.iloc[-2]

    setups: List[Setup] = []
    market_type = market_info["market_type"]
    direction = market_info["direction"]

    # 方便：信号棒质量
    rng = float(last["high"] - last["low"])
    body = float(abs(last["close"] - last["open"]))
    close_pos = float((last["close"] - last["low"]) / (rng + 1e-9))
    strong_bull_signal = (last["close"] > last["open"]) and close_pos > 0.7 and body > (rng * 0.45)
    strong_bear_signal = (last["close"] < last["open"]) and close_pos < 0.3 and body > (rng * 0.45)

    # ========= Trend / SpikeChannel：找 H1/H2、2EL/2ES =========
    if market_type in ("Trend", "SpikeChannel") and direction in ("Bull", "Bear"):
        # 简化的 pullback 定义：最近 10 根里出现与趋势相反的 2~4 根小回调，然后出现强信号棒
        recent = d.tail(12).copy()
        if direction == "Bull":
            pullback_bars = (recent["close"] < recent["open"]).sum()
            # H1：首次反转信号（简化）
            if pullback_bars >= 2 and strong_bull_signal:
                entry = float(last["high"])  # 突破信号棒高点
                stop = float(min(last["low"], prev["low"]))  # 结构止损
                target_1 = float(entry + 1.5 * atr_now)
                setups.append(Setup(
                    type="H1",
                    direction="Bull",
                    trigger="Buy stop above signal bar high (first pullback attempt)",
                    entry=entry,
                    stop=stop,
                    target_1=target_1,
                    confidence="medium",
                    notes="Trend context + pullback + strong bull signal bar. Prefer if breakout has follow-through."
                ))
            # H2：第二次尝试（简化：最近 20 根出现过一次类似信号但未走出）
            # 用“最近20根出现过强 bull signal 但未延续”当作第二次尝试的 proxy
            recent20 = d.tail(25).copy()
            prior_signals = ((_bull(recent20) & (_close_pos(recent20) > 0.7) & (_body(recent20) > _range(recent20)*0.45))).sum()
            if prior_signals >= 2 and strong_bull_signal:
                entry = float(last["high"])
                stop = float(last["low"])
                target_1 = float(entry + 2.0 * atr_now)
                setups.append(Setup(
                    type="H2",
                    direction="Bull",
                    trigger="Buy stop above signal bar high (second entry attempt)",
                    entry=entry,
                    stop=stop,
                    target_1=target_1,
                    confidence="medium",
                    notes="Second-entry proxy: multiple strong bull signals within last ~25 bars. Better RR but needs context check."
                ))

            # 2EL：第二次楔形/通道回调的入场（极简：两次更低的低点后出现强 bull 反转棒）
            lows_idx = np.argmin(d["low"].tail(10).values)
            if strong_bull_signal and pullback_bars >= 3:
                # 仅作为候选
                setups.append(Setup(
                    type="2EL",
                    direction="Bull",
                    trigger="Second entry after pullback lows (approx)",
                    entry=float(last["high"]),
                    stop=float(last["low"]),
                    target_1=float(last["high"] + 1.5 * atr_now),
                    confidence="low",
                    notes="Heuristic 2EL candidate. Improve by explicit wedge/legs counting later."
                ))

        else:  # Bear trend
            pullback_bars = (recent["close"] > recent["open"]).sum()
            if pullback_bars >= 2 and strong_bear_signal:
                entry = float(last["low"])   # 跌破信号棒低点
                stop = float(max(last["high"], prev["high"]))
                target_1 = float(entry - 1.5 * atr_now)
                setups.append(Setup(
                    type="L1",
                    direction="Bear",
                    trigger="Sell stop below signal bar low (first pullback attempt)",
                    entry=entry,
                    stop=stop,
                    target_1=target_1,
                    confidence="medium",
                    notes="Bear trend context + pullback + strong bear signal bar."
                ))

            recent20 = d.tail(25).copy()
            prior_signals = ((_bear(recent20) & (_close_pos(recent20) < 0.3) & (_body(recent20) > _range(recent20)*0.45))).sum()
            if prior_signals >= 2 and strong_bear_signal:
                entry = float(last["low"])
                stop = float(last["high"])
                target_1 = float(entry - 2.0 * atr_now)
                setups.append(Setup(
                    type="L2",
                    direction="Bear",
                    trigger="Sell stop below signal bar low (second entry attempt)",
                    entry=entry,
                    stop=stop,
                    target_1=target_1,
                    confidence="medium",
                    notes="Second-entry proxy in bear trend."
                ))

            if strong_bear_signal and pullback_bars >= 3:
                setups.append(Setup(
                    type="2ES",
                    direction="Bear",
                    trigger="Second entry after pullback highs (approx)",
                    entry=float(last["low"]),
                    stop=float(last["high"]),
                    target_1=float(last["low"] - 1.5 * atr_now),
                    confidence="low",
                    notes="Heuristic 2ES candidate."
                ))

    # ========= Trading Range：失败突破 / 区间边缘反转（Range Fade） =========
    if market_type == "TradingRange":
        # 估计区间上下沿：最近 lookback 的分位数
        hi = float(d["high"].quantile(0.9))
        lo = float(d["low"].quantile(0.1))
        mid = (hi + lo) / 2
        tol = max(atr_now * 0.3, (hi - lo) * 0.05)

        # 失败突破：突破后收回区间内（典型 TR 反向）
        # Bull failed breakout at top: high > hi and close < hi
        if last["high"] > hi and last["close"] < hi and strong_bear_signal:
            entry = float(last["low"])
            stop = float(last["high"] + tol)
            target_1 = float(mid)
            setups.append(Setup(
                type="FailedBreakout",
                direction="Bear",
                trigger="Sell below bear reversal bar after failed breakout above range",
                entry=entry,
                stop=stop,
                target_1=target_1,
                confidence="medium",
                notes="TR logic: failed breakout often reverses back to middle."
            ))

        # Bear failed breakout at bottom
        if last["low"] < lo and last["close"] > lo and strong_bull_signal:
            entry = float(last["high"])
            stop = float(last["low"] - tol)
            target_1 = float(mid)
            setups.append(Setup(
                type="FailedBreakout",
                direction="Bull",
                trigger="Buy above bull reversal bar after failed breakout below range",
                entry=entry,
                stop=stop,
                target_1=target_1,
                confidence="medium",
                notes="TR logic: failed downside breakout often reverses to middle."
            ))

        # Range Fade：靠近边缘做反转（更保守）
        if abs(float(last["close"]) - lo) <= tol and strong_bull_signal:
            setups.append(Setup(
                type="RangeFade",
                direction="Bull",
                trigger="Buy above bull reversal near range low",
                entry=float(last["high"]),
                stop=float(last["low"] - tol),
                target_1=float(mid),
                confidence="low",
                notes="Fade near range low; best when multiple prior reversals at similar level."
            ))

        if abs(float(last["close"]) - hi) <= tol and strong_bear_signal:
            setups.append(Setup(
                type="RangeFade",
                direction="Bear",
                trigger="Sell below bear reversal near range high",
                entry=float(last["low"]),
                stop=float(last["high"] + tol),
                target_1=float(mid),
                confidence="low",
                notes="Fade near range high."
            ))

    return setups


# =========================
# 关键价位：支撑/压力、MM目标
# =========================
def compute_key_levels(df: pd.DataFrame, lookback: int = 120) -> Dict[str, Any]:
    d = df.tail(lookback).copy()
    highs, lows = _swing_points(d["high"], 2, 2)
    sh = [float(d["high"].iloc[i]) for i in highs[-3:]] if highs else [float(d["high"].max())]
    sl = [float(d["low"].iloc[i]) for i in lows[-3:]] if lows else [float(d["low"].min())]

    # measured move：用最近一次摆动幅度近似
    if highs and lows:
        last_hi_i = highs[-1]
        last_lo_i = lows[-1]
        if last_hi_i > last_lo_i:
            leg = float(d["high"].iloc[last_hi_i] - d["low"].iloc[last_lo_i])
        else:
            leg = float(d["high"].iloc[last_hi_i] - d["low"].iloc[last_lo_i])
    else:
        leg = float(d["high"].max() - d["low"].min())

    last_close = float(d["close"].iloc[-1])
    mm_up = last_close + leg
    mm_dn = last_close - leg

    return {
        "swing_resistance": sh,
        "swing_support": sl,
        "measured_move": {
            "leg": leg,
            "target_up": mm_up,
            "target_down": mm_dn,
        }
    }


# =========================
# 总入口：给上层调用
# =========================
def brooks_price_action(df: pd.DataFrame) -> Dict[str, Any]:
    info = classify_market(df)
    setups = detect_setups(df, info)
    key_levels = compute_key_levels(df)

    invalidations = []
    mt = info["market_type"]
    direction = info["direction"]

    if mt == "Trend" and direction == "Bull":
        invalidations.append("Close below prior swing low invalidates bull trend setup.")
    if mt == "Trend" and direction == "Bear":
        invalidations.append("Close above prior swing high invalidates bear trend setup.")
    if mt == "TradingRange":
        invalidations.append("If breakout shows strong follow-through (2+ big trend bars), stop fading and switch bias.")

    result = PriceActionResult(
        market_type=info["market_type"],
        direction=info["direction"],
        context=info,
        key_levels=key_levels,
        setups=[asdict(s) for s in setups],
        invalidations=invalidations
    )
    return asdict(result)
