"""
股價資料抓取——改用台灣證交所（TWSE）官方 API，不再透過 Yahoo Finance / yfinance。

背景：原本用 yfinance 抓 Yahoo Finance 的資料，部署到 Streamlit Community Cloud 後，
Yahoo 會把雲端主機的共用 IP 判定為異常流量而擋掉（YFRateLimitError），導致查詢在雲端上
必定失敗，但在本機測試時因為是家用 IP，反而看不出問題。改用證交所官方 API 後就不會再被擋。

雷區（勿修改）：
- 回傳的 DataFrame 欄位固定是 Open/High/Low/Close/Volume（大寫開頭），
  索引是遞增排序的 DatetimeIndex——這是 analysis/、ui/ 模組共同依賴的格式，不可更動。
- 台股原始成交資料本來就沒有還原權息調整，天生等同於原本 yfinance auto_adjust=False 的效果，
  數字會跟看盤軟體一致，這點不用額外處理。
- TWSE STOCK_DAY 一次只能查一個月，要抓的區間橫跨好幾個月時得逐月呼叫再合併，
  呼叫之間加一點 sleep 是刻意的，避免短時間內大量請求又被官方 API 限流。

上市（TWSE）股票先試證交所 STOCK_DAY；查不到（代表可能是上櫃股票）再試 FinMind
（見 config.py 對 FINMIND_API_URL 的說明：TPEx 官方的歷史行情 API 已經下架，
FinMind 是替代來源，非政府單位但長期被台灣開發者社群使用）。
"""

from __future__ import annotations

import time
from datetime import date

import pandas as pd
import requests
import streamlit as st

from config import CACHE_TTL_PRICE, CACHE_TTL_STOCK_NAME, FINMIND_API_URL, TWSE_STOCK_DAY_URL

_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def _month_starts(start: date, end: date):
    """列出 start~end 涵蓋的每個月第一天，TWSE STOCK_DAY 是以月為單位查詢。"""
    cursor = start.replace(day=1)
    while cursor <= end:
        yield cursor
        cursor = date(cursor.year + 1, 1, 1) if cursor.month == 12 else date(cursor.year, cursor.month + 1, 1)


def _to_float(text: str) -> float:
    return float(str(text).replace(",", ""))


def _fetch_twse_month(stock_code: str, month_start: date) -> pd.DataFrame:
    """跟證交所 STOCK_DAY 拿一個月的上市股票日 K，抓不到／格式跑掉一律回傳空 DataFrame。"""
    try:
        resp = requests.get(
            TWSE_STOCK_DAY_URL,
            params={"response": "json", "date": month_start.strftime("%Y%m01"), "stockNo": stock_code},
            headers=_HEADERS,
            timeout=10,
        )
        payload = resp.json()
    except Exception:
        return pd.DataFrame()

    if payload.get("stat") != "OK" or not payload.get("data"):
        return pd.DataFrame()

    rows = []
    for row in payload["data"]:
        try:
            roc_date, _volume, _amount, open_, high, low, close, *_rest = row
            y, m, d = roc_date.split("/")
            dt = date(int(y) + 1911, int(m), int(d))
            rows.append(
                {
                    "Date": dt,
                    "Open": _to_float(open_),
                    "High": _to_float(high),
                    "Low": _to_float(low),
                    "Close": _to_float(close),
                    "Volume": int(str(_volume).replace(",", "")),
                }
            )
        except (ValueError, AttributeError, IndexError):
            continue

    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows).set_index("Date")
    df.index = pd.to_datetime(df.index)
    return df


def _fetch_finmind_range(stock_code: str, start: date, end: date) -> pd.DataFrame:
    """上櫃股票的補充來源：FinMind（見檔頭說明）。一次可以查整個區間，不用像 TWSE 那樣逐月呼叫。"""
    try:
        resp = requests.get(
            FINMIND_API_URL,
            params={
                "dataset": "TaiwanStockPrice",
                "data_id": stock_code,
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
            },
            timeout=15,
        )
        payload = resp.json()
    except Exception:
        return pd.DataFrame()

    if payload.get("status") != 200 or not payload.get("data"):
        return pd.DataFrame()

    rows = []
    for row in payload["data"]:
        try:
            rows.append(
                {
                    "Date": row["date"],
                    "Open": float(row["open"]),
                    "High": float(row["max"]),
                    "Low": float(row["min"]),
                    "Close": float(row["close"]),
                    "Volume": int(row["Trading_Volume"]),
                }
            )
        except (KeyError, ValueError, TypeError):
            continue

    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows).set_index("Date")
    df.index = pd.to_datetime(df.index)
    return df


@st.cache_data(ttl=CACHE_TTL_PRICE, show_spinner=False)
def fetch_price(stock_code: str, start: date, end: date):
    """抓取台股日 K 資料。先試上市（證交所 STOCK_DAY），查不到再試上櫃（FinMind）。"""
    frames = []
    for month_start in _month_starts(start, end):
        frame = _fetch_twse_month(stock_code, month_start)
        if not frame.empty:
            frames.append(frame)
        time.sleep(0.15)  # 對官方 API 客氣一點，避免短時間內大量請求又被限流

    if frames:
        df = pd.concat(frames).sort_index()
        df = df[~df.index.duplicated(keep="last")]
        df = df.loc[(df.index.date >= start) & (df.index.date <= end)]
        df = df.dropna(subset=["Close"])
        if not df.empty:
            return df, f"{stock_code}.TW"

    # TWSE 查不到，可能是上櫃股票，改試 FinMind
    df = _fetch_finmind_range(stock_code, start, end)
    df = df.dropna(subset=["Close"]) if not df.empty else df
    if not df.empty:
        return df, f"{stock_code}.TWO"

    return None, f"{stock_code}.TW"


@st.cache_data(ttl=CACHE_TTL_STOCK_NAME, show_spinner=False)
def fetch_stock_name(ticker: str):
    """公司名稱改查現有的代號<->名稱對照表（data/ticker_map.py，一樣是證交所來源），
    不再另外呼叫一次 yfinance——原本這裡打 Yahoo 只是為了拿名稱，多打一次一樣會被限流。"""
    from data.ticker_map import fetch_stock_name_map

    stock_code = ticker.split(".")[0]
    try:
        name_map, _error = fetch_stock_name_map()
        return name_map.get(stock_code)
    except Exception:
        return None
