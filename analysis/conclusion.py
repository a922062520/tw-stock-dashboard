"""
分析結論：短期／中長期判斷、參考進場價／停損價／停利價、紅黃綠燈分類。

【第一階段指令書規定：以下計算邏輯不要重新發明，只搬移位置】
進場價方法論（參考業界常見的技術面規則，不是市價，而是「合理的買點」）：
- 多頭（月線在季線之上）：採用「拉回月線進場法」——20 日均線常被當成動態支撐，
  等股價拉回月線附近再進場，比追高買在當下市價更有紀律。
- 盤整或空頭：採用布林通道下軌的均值回歸邏輯（中軌 20MA ± 2 倍標準差），
  在下軌附近才視為合理買點，而不是現在的市價。
- 兩種情況都取「目前價格」與「合理買點」兩者較低者，確保永遠不會建議追價買在市價之上。

停損／停利方法論：改用 ATR（Average True Range，平均真實區間）取代單純的收盤價報酬標準差，
這是 Van Tharp 等機構交易法常見的波動度量，公式為停損＝進場價－2×ATR，停利則抓風險報酬比 1:2。

本模組只回傳「代碼／數值」，不寫死任何白話文字——所有給使用者看的句子統一由
explain/texts.py 組裝，方便之後只改一個地方就能調整用詞。
"""

from __future__ import annotations

import pandas as pd

from analysis.metrics import risk_label


def build_analysis_conclusion(price_df: pd.DataFrame, annual_return: float, annual_vol: float, daily_ret: pd.Series) -> dict:
    close_now = float(price_df["Close"].iloc[-1])
    ma20_now = price_df["MA20"].iloc[-1]
    ma60_now = price_df["MA60"].iloc[-1]
    atr_now = price_df["ATR14"].iloc[-1] if "ATR14" in price_df.columns else None
    std20_now = price_df["Close"].rolling(20).std().iloc[-1]

    risk_lvl = risk_label(annual_vol)

    trend_strength = None
    if pd.notna(ma20_now) and pd.notna(ma60_now) and ma60_now:
        trend_strength = (ma20_now - ma60_now) / ma60_now

    # ---- 短期／中長期判斷 -> 回傳「代碼」，白話句子交給 texts.py ----
    if trend_strength is None:
        horizon = "資料不足以判斷"
        horizon_reason_kind = "insufficient"
        horizon_direction = None
    elif annual_vol >= 0.40 or abs(trend_strength) < 0.02:
        horizon = "短期"
        horizon_reason_kind = "high_vol" if annual_vol >= 0.40 else "sideways"
        horizon_direction = None
    else:
        horizon = "中長期"
        horizon_reason_kind = "trend"
        horizon_direction = "多頭（月線在季線之上）" if trend_strength > 0 else "空頭（月線在季線之下）"

    # ---- 進場價：不是市價，而是拉回支撐或均值回歸下軌，取較低者 ----
    if trend_strength is not None and trend_strength > 0 and pd.notna(ma20_now):
        candidate = float(ma20_now)
        entry_method_kind = "pullback_ma20"
    elif pd.notna(ma20_now) and pd.notna(std20_now):
        candidate = float(ma20_now) - 2 * float(std20_now)
        entry_method_kind = "bollinger_lower"
    else:
        candidate = close_now
        entry_method_kind = "insufficient"

    entry_ref = min(close_now, candidate) if candidate is not None else close_now
    entry_below_market = entry_ref < close_now - 1e-9
    entry_gap_pct = (entry_ref - close_now) / close_now if close_now else 0.0

    # ---- 停損／停利：改用 ATR（業界標準波動度量）取代單純日報酬標準差 ----
    if atr_now is not None and pd.notna(atr_now) and atr_now > 0 and entry_ref > 0:
        atr_pct = float(atr_now) / entry_ref
        stop_loss_pct = min(max(atr_pct * 2, 0.02), 0.15)  # 停損＝2倍ATR，限制在 2%~15% 之間
        risk_method_kind = "atr"
    else:
        daily_vol = float(daily_ret.std())
        stop_loss_pct = min(max(daily_vol * 2, 0.02), 0.15)  # ATR 資料不足時退回日報酬標準差估算
        risk_method_kind = "daily_std"
    take_profit_pct = stop_loss_pct * 2  # 風險報酬比抓 1:2

    return {
        "close_now": close_now,
        "risk_lvl": risk_lvl,
        "annual_vol": annual_vol,
        "horizon": horizon,
        "horizon_reason_kind": horizon_reason_kind,
        "horizon_direction": horizon_direction,
        "trend_strength": trend_strength,
        "entry_ref": entry_ref,
        "entry_method_kind": entry_method_kind,
        "entry_below_market": entry_below_market,
        "entry_gap_pct": entry_gap_pct,
        "risk_method_kind": risk_method_kind,
        "stop_loss_price": entry_ref * (1 - stop_loss_pct),
        "stop_loss_pct": stop_loss_pct,
        "take_profit_price": entry_ref * (1 + take_profit_pct),
        "take_profit_pct": take_profit_pct,
    }


def classify_traffic_light(concl: dict) -> dict:
    """把分析結論轉成紅黃綠燈分類。這是「參考規則」，不是投資訊號，措辭一律不用買賣字眼。

    規則（供日後調整參考）：
    - 紅燈：年化波動度屬高風險，或目前價格明顯高於參考進場價（entry_gap_pct <= -5%，代表偏熱）。
    - 綠燈：風險屬低風險、目前價格未明顯高於參考進場價（entry_gap_pct >= -1%），且趨勢判斷為中長期。
    - 其餘（含資料不足、盤整、中風險等中性情況）一律黃燈。
    """
    risk_lvl = concl["risk_lvl"]
    horizon = concl["horizon"]
    entry_gap_pct = concl["entry_gap_pct"]

    if risk_lvl == "高風險" or entry_gap_pct <= -0.05:
        reason_kind = "high_vol" if risk_lvl == "高風險" else "overheated"
        return {"light": "red", "reason_kind": reason_kind}

    if risk_lvl == "低風險" and entry_gap_pct >= -0.01 and horizon == "中長期":
        return {"light": "green", "reason_kind": "stable"}

    if horizon == "資料不足以判斷":
        return {"light": "yellow", "reason_kind": "insufficient"}

    return {"light": "yellow", "reason_kind": "neutral"}
