"""
動態事件偵測（第一階段核心新功能）。

只回傳「現在（依查詢區間最新一天）真的發生」的事件 key 清單，
沒發生的事件不會出現在清單裡——白話說明只在事件真的發生時才顯示，
不放固定的教學文章。

事件 key 對應的白話說明文字統一放在 explain/texts.py（SIGNAL_TEXTS），
新增一種事件只要「這裡加偵測邏輯」＋「texts.py 加一筆說明」兩邊各改一次。

至少涵蓋指令書第 5.5 節列出的 12 種事件（部分「站上／跌破」「黃金/死亡交叉」
拆成正反兩個獨立 key，涵蓋範圍更細，但不脫離指令書要求）：
  ma_golden_cross / ma_death_cross
  price_above_ma20 / price_below_ma20
  price_above_ma60 / price_below_ma60
  kd_golden_cross / kd_death_cross
  kd_high_blunt / kd_low_blunt
  rsi_overbought / rsi_oversold
  volume_spike
  new_high / new_low
  volatility_rising
"""

from __future__ import annotations

import pandas as pd

KD_BLUNT_DAYS = 3          # KD 高檔／低檔鈍化：連續幾天算「鈍化」
VOLUME_SPIKE_MULTIPLE = 2  # 爆量：今日量 > 近 20 日均量的幾倍
VOLATILITY_RISING_MULTIPLE = 1.5  # 波動放大：近 20 日波動 > 前 20 日波動的幾倍


def _crossed_up(a: pd.Series, b: pd.Series) -> bool:
    if len(a) < 2 or len(b) < 2:
        return False
    a_prev, a_now, b_prev, b_now = a.iloc[-2], a.iloc[-1], b.iloc[-2], b.iloc[-1]
    if pd.isna(a_prev) or pd.isna(a_now) or pd.isna(b_prev) or pd.isna(b_now):
        return False
    return a_prev <= b_prev and a_now > b_now


def _crossed_down(a: pd.Series, b: pd.Series) -> bool:
    if len(a) < 2 or len(b) < 2:
        return False
    a_prev, a_now, b_prev, b_now = a.iloc[-2], a.iloc[-1], b.iloc[-2], b.iloc[-1]
    if pd.isna(a_prev) or pd.isna(a_now) or pd.isna(b_prev) or pd.isna(b_now):
        return False
    return a_prev >= b_prev and a_now < b_now


def detect_signals(df: pd.DataFrame) -> list[str]:
    """df 需已經算好 MA20/MA60/RSI/K/D 欄位。回傳目前偵測到的事件 key 清單。"""
    keys: list[str] = []
    if len(df) < 2:
        return keys

    close = df["Close"]
    ma20 = df.get("MA20")
    ma60 = df.get("MA60")
    k = df.get("K")
    d = df.get("D")
    rsi = df.get("RSI")
    volume = df.get("Volume")

    if ma20 is not None and ma60 is not None:
        if _crossed_up(ma20, ma60):
            keys.append("ma_golden_cross")
        if _crossed_down(ma20, ma60):
            keys.append("ma_death_cross")
        if _crossed_up(close, ma20):
            keys.append("price_above_ma20")
        if _crossed_down(close, ma20):
            keys.append("price_below_ma20")
        if _crossed_up(close, ma60):
            keys.append("price_above_ma60")
        if _crossed_down(close, ma60):
            keys.append("price_below_ma60")

    if k is not None and d is not None:
        if _crossed_up(k, d):
            keys.append("kd_golden_cross")
        if _crossed_down(k, d):
            keys.append("kd_death_cross")
        k_clean = k.dropna()
        if len(k_clean) >= KD_BLUNT_DAYS:
            recent_k = k_clean.iloc[-KD_BLUNT_DAYS:]
            if (recent_k > 80).all():
                keys.append("kd_high_blunt")
            if (recent_k < 20).all():
                keys.append("kd_low_blunt")

    if rsi is not None and len(rsi.dropna()) >= 1:
        rsi_now = rsi.iloc[-1]
        if pd.notna(rsi_now):
            if rsi_now > 70:
                keys.append("rsi_overbought")
            elif rsi_now < 30:
                keys.append("rsi_oversold")

    if volume is not None and len(volume.dropna()) >= 21:
        avg20 = volume.iloc[-21:-1].mean()
        if avg20 and pd.notna(avg20) and volume.iloc[-1] > avg20 * VOLUME_SPIKE_MULTIPLE:
            keys.append("volume_spike")

    close_clean = close.dropna()
    if len(close_clean) >= 5:
        if close_clean.iloc[-1] >= close_clean.max() - 1e-9:
            keys.append("new_high")
        if close_clean.iloc[-1] <= close_clean.min() + 1e-9:
            keys.append("new_low")

    daily_ret = close.pct_change(fill_method=None)
    daily_ret_clean = daily_ret.dropna()
    if len(daily_ret_clean) >= 40:
        recent_vol = daily_ret_clean.iloc[-20:].std()
        prior_vol = daily_ret_clean.iloc[-40:-20].std()
        if prior_vol and pd.notna(prior_vol) and recent_vol > prior_vol * VOLATILITY_RISING_MULTIPLE:
            keys.append("volatility_rising")

    return keys
