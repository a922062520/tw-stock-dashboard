"""技術指標計算：均線、RSI、KD、ATR。計算邏輯全部原樣保留，不重新發明。"""

from __future__ import annotations

import numpy as np
import pandas as pd


def add_moving_averages(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA60"] = df["Close"].rolling(60).mean()
    return df


def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.where(avg_loss != 0, 100)
    rsi = rsi.where(avg_gain != 0, 0).where((avg_gain != 0) | (avg_loss != 0), 50)
    return rsi


def compute_kd(df: pd.DataFrame, period: int = 9) -> tuple[pd.Series, pd.Series]:
    """台式 KD：RSV 9 日，K/D 以 1/3 平滑，初始值皆為 50。"""
    low_min = df["Low"].rolling(period).min()
    high_max = df["High"].rolling(period).max()
    denom = (high_max - low_min).replace(0, np.nan)
    rsv = (df["Close"] - low_min) / denom * 100
    rsv = rsv.fillna(50)

    k_values, d_values = [], []
    k_prev, d_prev = 50.0, 50.0
    for val in rsv:
        k_prev = (2 / 3) * k_prev + (1 / 3) * val
        d_prev = (2 / 3) * d_prev + (1 / 3) * k_prev
        k_values.append(k_prev)
        d_values.append(d_prev)
    return pd.Series(k_values, index=df.index), pd.Series(d_values, index=df.index)


def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """平均真實區間 ATR（Wilder 平滑法）。業界標準的波動度量，用來抓合理的進出場緩衝，
    比單純用收盤價漲跌幅的標準差更準確，因為它有把跳空缺口也算進去。"""
    prev_close = df["Close"].shift(1)
    true_range = pd.concat(
        [
            df["High"] - df["Low"],
            (df["High"] - prev_close).abs(),
            (df["Low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
