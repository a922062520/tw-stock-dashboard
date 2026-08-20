"""
三大法人籌碼資料（來源：FinMind TaiwanStockInstitutionalInvestorsBuySell，實驗性功能，
預設關閉，僅供參考）。改成單次區間請求，取代原本最多 60 次逐日呼叫 TWSE 的做法，
大幅降低查詢時間與被鎖 IP 的風險。快取用 st.cache_data（雲端相容，不寫本機檔案）；
同一天的歷史資料不會變，所以快取時間可以設長一點（見 config.CACHE_TTL_CHIP_DAY）。
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import requests
import streamlit as st

from config import CACHE_TTL_CHIP_DAY, FINMIND_API_URL

# FinMind 用英文代稱區分五個法人子類別，對應到畫面上習慣的三大分類：
# 外資買賣超＝外資及陸資（不含外資自營商）；自營商買賣超＝自行買賣＋避險合計。
_FOREIGN = "Foreign_Investor"
_FOREIGN_DEALER_SELF = "Foreign_Dealer_Self"
_TRUST = "Investment_Trust"
_DEALER_SELF = "Dealer_self"
_DEALER_HEDGING = "Dealer_Hedging"


@st.cache_data(ttl=CACHE_TTL_CHIP_DAY, show_spinner=False)
def _fetch_finmind_chip_raw(stock_code: str, start: date, end: date):
    try:
        resp = requests.get(
            FINMIND_API_URL,
            params={
                "dataset": "TaiwanStockInstitutionalInvestorsBuySell",
                "data_id": stock_code,
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
            },
            timeout=15,
        )
        payload = resp.json()
    except Exception:
        return None

    if payload.get("status") != 200 or not payload.get("data"):
        return None
    return payload["data"]


def fetch_chip_data(stock_code: str, start: date, end: date, max_days: int = 60):
    """抓取三大法人買賣超（FinMind 單次區間請求）。只取最近 max_days 個交易日方便畫圖，
    所以就算查詢區間選很長（例如近1年），實際要跟 FinMind 要的天數還是有上限。"""
    request_start = max(start, end - timedelta(days=int(max_days * 1.6) + 10))
    raw = _fetch_finmind_chip_raw(stock_code, request_start, end)
    if not raw:
        return None

    df = pd.DataFrame(raw)
    if df.empty or "name" not in df.columns:
        return None

    df["net"] = df["buy"] - df["sell"]
    pivot = df.pivot_table(index="date", columns="name", values="net", aggfunc="sum", fill_value=0)

    result = pd.DataFrame(index=pivot.index)
    result["外資買賣超"] = pivot.get(_FOREIGN, 0)
    result["投信買賣超"] = pivot.get(_TRUST, 0)
    result["自營商買賣超"] = pivot.get(_DEALER_SELF, 0) + pivot.get(_DEALER_HEDGING, 0)
    result["三大法人合計"] = (
        result["外資買賣超"] + result["投信買賣超"] + result["自營商買賣超"] + pivot.get(_FOREIGN_DEALER_SELF, 0)
    )
    # FinMind 回傳的 buy/sell 是原始股數，台灣人講買賣超一律講「張」（1張=1000股），
    # 這裡統一換算成張，畫面（圖表、白話文字）就不用各自處理單位。
    result = (result / 1000).round().astype(int)

    result.index = pd.to_datetime(result.index).date
    result = result.sort_index()
    if len(result) > max_days:
        result = result.iloc[-max_days:]

    if result.empty:
        return None
    return result
