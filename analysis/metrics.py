"""年化報酬率、年化波動度、風險等級分類。計算邏輯原樣保留，不重新發明。
白話說明文字統一放在 explain/texts.py，這裡只回傳分類標籤（低風險／中風險／高風險）。
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def compute_return_risk(close: pd.Series):
    daily_ret = close.pct_change(fill_method=None).dropna()
    if len(daily_ret) < 2:
        return None
    annual_return = daily_ret.mean() * 252
    annual_vol = daily_ret.std() * np.sqrt(252)
    return annual_return, annual_vol, daily_ret


def risk_label(vol: float) -> str:
    if vol < 0.20:
        return "低風險"
    elif vol < 0.40:
        return "中風險"
    else:
        return "高風險"


def classify_rsi(rsi_now: float | None) -> str:
    """回傳 RSI 現況分類代碼，白話文字交給 explain/texts.py。"""
    if rsi_now is None or pd.isna(rsi_now):
        return "unknown"
    if rsi_now > 70:
        return "overbought"
    if rsi_now < 30:
        return "oversold"
    if rsi_now >= 50:
        return "neutral_bullish"
    return "neutral_bearish"


def classify_kd(k_now: float | None, d_now: float | None) -> tuple[str, str]:
    """回傳 (區間代碼, 相對位置代碼)，例如 ("high", "up")。白話文字交給 explain/texts.py。"""
    if k_now is None or d_now is None or pd.isna(k_now) or pd.isna(d_now):
        return "unknown", "unknown"
    if k_now > 80:
        tier = "high"
    elif k_now < 20:
        tier = "low"
    else:
        tier = "mid"
    direction = "up" if k_now >= d_now else "down"
    return tier, direction


def analyze_chip_trend(chip_df: pd.DataFrame, days: int = 5) -> dict:
    """摘要近幾個交易日的三大法人買賣超趨勢，回傳結構化數值，白話文字交給 explain/texts.py。"""
    if chip_df is None or chip_df.empty:
        return {"available": False}

    recent = chip_df.tail(days)
    actual_days = len(recent)

    if "三大法人合計" in recent.columns and recent["三大法人合計"].notna().any():
        net_total = float(recent["三大法人合計"].fillna(0).sum())
    else:
        net_total = float(
            recent.get("外資買賣超", pd.Series(dtype=float)).fillna(0).sum()
            + recent.get("投信買賣超", pd.Series(dtype=float)).fillna(0).sum()
            + recent.get("自營商買賣超", pd.Series(dtype=float)).fillna(0).sum()
        )

    contributions = {}
    for label in ("外資買賣超", "投信買賣超", "自營商買賣超"):
        if label in recent.columns:
            contributions[label] = float(recent[label].fillna(0).sum())
    dominant_label = max(contributions, key=lambda k: abs(contributions[k])) if contributions else None

    if net_total > 0:
        direction = "buy"
    elif net_total < 0:
        direction = "sell"
    else:
        direction = "flat"

    return {
        "available": True,
        "days": actual_days,
        "net_total": net_total,
        "direction": direction,
        "dominant_label": dominant_label,
        "dominant_value": contributions.get(dominant_label) if dominant_label else None,
    }
