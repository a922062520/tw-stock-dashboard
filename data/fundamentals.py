"""
公司基本面資料（獲利、股利）。第一階段原本規劃放到第二階段再做，
但使用者確認需要提前加入，先用 yfinance 的 .info 與 .dividends 實作，
台股在這兩個欄位上的覆蓋率不一定完整，所以呼叫端一律要能處理「查不到」的情況。
"""

from __future__ import annotations

import pandas as pd
import streamlit as st
import yfinance as yf

from config import CACHE_TTL_FUNDAMENTALS


@st.cache_data(ttl=CACHE_TTL_FUNDAMENTALS, show_spinner=False)
def fetch_fundamentals_info(ticker: str) -> dict:
    """公司基本面欄位（EPS、營收等），可能因股票而異，缺欄位是正常情況。"""
    try:
        info = yf.Ticker(ticker).info
        return info or {}
    except Exception:
        return {}


@st.cache_data(ttl=CACHE_TTL_FUNDAMENTALS, show_spinner=False)
def fetch_dividend_history(ticker: str):
    """現金股利歷史紀錄，回傳 pandas Series（index 是除息日），查不到回傳 None。"""
    try:
        div = yf.Ticker(ticker).dividends
        if div is None or not isinstance(div, pd.Series) or div.empty:
            return None
        return div
    except Exception:
        return None
