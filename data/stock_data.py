"""
股價資料抓取（yfinance）。

雷區（勿修改）：
- 台股要 auto_adjust=False，數字才會跟看盤軟體一致。
- yfinance 回傳欄位是 MultiIndex（帶 Ticker 層），要壓平：
  df.columns = df.columns.get_level_values(0)
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st
import yfinance as yf

from config import CACHE_TTL_PRICE, CACHE_TTL_STOCK_NAME


@st.cache_data(ttl=CACHE_TTL_PRICE, show_spinner=False)
def fetch_price(stock_code: str, start: date, end: date):
    """抓取台股日 K 資料。先試上市 .TW，抓不到再試上櫃 .TWO。"""
    for suffix in (".TW", ".TWO"):
        ticker = f"{stock_code}{suffix}"
        try:
            df = yf.download(
                ticker,
                start=start,
                end=end + timedelta(days=1),
                auto_adjust=False,  # 台股要設 False，數字才會跟看盤軟體一致
                progress=False,
            )
        except Exception:
            df = pd.DataFrame()

        if df is not None and not df.empty:
            # yfinance 回傳的欄位是 MultiIndex（帶 Ticker 層），這裡壓平，
            # 效果等同於使用者原本熟悉的 squeeze() 步驟，避免後續算報酬率全變 NaN。
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df = df.dropna(subset=["Close"])
            if not df.empty:
                return df, ticker
    return None, f"{stock_code}.TW"


@st.cache_data(ttl=CACHE_TTL_STOCK_NAME, show_spinner=False)
def fetch_stock_name(ticker: str):
    try:
        info = yf.Ticker(ticker).info
        return info.get("longName") or info.get("shortName")
    except Exception:
        return None
