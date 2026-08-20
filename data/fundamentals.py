"""
公司基本面資料（獲利、股利）。原本只用 yfinance 的 .info 與 .dividends，
但台股在這兩個欄位上的覆蓋率不完整，常常查不到。改成優先用 FinMind
（TaiwanStockFinancialStatements、TaiwanStockDividend，見 config.py 說明），
查不到再退回 yfinance 當備援，兩邊都失敗才回傳空結果——呼叫端一律要能處理
「查不到」的情況。

yfinance 只在FinMind查不到時才會用到（備援），但這個套件本身依賴不少東西，
import 有實測得到的成本。故意不放在檔案最上面、改成在真的要用到的兩個函式
內部才 import——多數查詢FinMind就有資料，根本不會走到這條路，冷啟動時就不用
白白付這個成本。
"""

from __future__ import annotations

import pandas as pd
import requests
import streamlit as st

from config import CACHE_TTL_FUNDAMENTALS, FINMIND_API_URL
from data.finmind_auth import get_finmind_token


def _bare_code(ticker: str) -> str:
    return ticker.split(".")[0]


def _fetch_finmind_fundamentals(stock_code: str) -> dict:
    """用最近四季的財報資料算近似的 EPS／營收／淨利率（trailing 概念，非官方 TTM 精算）。"""
    params = {"dataset": "TaiwanStockFinancialStatements", "data_id": stock_code, "start_date": "2024-01-01"}
    token = get_finmind_token()
    if token:
        params["token"] = token
    try:
        resp = requests.get(FINMIND_API_URL, params=params, timeout=15)
        payload = resp.json()
    except Exception:
        return {}

    if payload.get("status") != 200 or not payload.get("data"):
        return {}

    df = pd.DataFrame(payload["data"])
    if df.empty or "type" not in df.columns:
        return {}

    dates = sorted(df["date"].unique())
    if not dates:
        return {}
    latest_date = dates[-1]
    recent_dates = dates[-4:]  # 近四季，湊近似的年度數字

    def value_at(date_, type_):
        row = df[(df["date"] == date_) & (df["type"] == type_)]
        return float(row["value"].iloc[0]) if not row.empty else None

    eps_latest = value_at(latest_date, "EPS")
    eps_ttm = None
    eps_rows = df[(df["date"].isin(recent_dates)) & (df["type"] == "EPS")]
    if len(eps_rows) == 4:
        eps_ttm = float(eps_rows["value"].sum())

    revenue = value_at(latest_date, "Revenue")
    income_after_tax = value_at(latest_date, "IncomeAfterTaxes")
    profit_margin = (income_after_tax / revenue) if (revenue and income_after_tax is not None and revenue != 0) else None

    if eps_latest is None and revenue is None:
        return {}

    return {
        "trailingEps": eps_ttm if eps_ttm is not None else eps_latest,
        "totalRevenue": revenue,
        "profitMargins": profit_margin,
        "_source": "finmind",
    }


def _fetch_finmind_dividends(stock_code: str) -> pd.Series | None:
    params = {"dataset": "TaiwanStockDividend", "data_id": stock_code, "start_date": "2010-01-01"}
    token = get_finmind_token()
    if token:
        params["token"] = token
    try:
        resp = requests.get(FINMIND_API_URL, params=params, timeout=15)
        payload = resp.json()
    except Exception:
        return None

    if payload.get("status") != 200 or not payload.get("data"):
        return None

    records = []
    for row in payload["data"]:
        ex_date = row.get("CashExDividendTradingDate")
        if not ex_date:
            continue
        cash = (row.get("CashEarningsDistribution") or 0) + (row.get("CashStatutorySurplus") or 0)
        if cash <= 0:
            continue
        records.append((ex_date, cash))

    if not records:
        return None

    series = pd.Series(
        data=[amount for _, amount in records],
        index=pd.to_datetime([d for d, _ in records]),
    ).sort_index()
    return series


@st.cache_data(ttl=CACHE_TTL_FUNDAMENTALS, show_spinner=False)
def fetch_fundamentals_info(ticker: str) -> dict:
    """公司基本面欄位（EPS、營收等）。先試 FinMind，查不到再退回 yfinance。"""
    stock_code = _bare_code(ticker)
    info = _fetch_finmind_fundamentals(stock_code)
    if info:
        return info

    try:
        import yfinance as yf

        info = yf.Ticker(ticker).info
        return info or {}
    except Exception:
        return {}


@st.cache_data(ttl=CACHE_TTL_FUNDAMENTALS, show_spinner=False)
def fetch_dividend_history(ticker: str):
    """現金股利歷史紀錄，回傳 pandas Series（index 是除息日）。先試 FinMind，查不到再退回 yfinance。"""
    stock_code = _bare_code(ticker)
    series = _fetch_finmind_dividends(stock_code)
    if series is not None and not series.empty:
        return series

    try:
        import yfinance as yf

        div = yf.Ticker(ticker).dividends
        if div is None or not isinstance(div, pd.Series) or div.empty:
            return None
        return div
    except Exception:
        return None
