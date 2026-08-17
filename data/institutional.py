"""
三大法人籌碼資料（來源：TWSE T86，實驗性功能，預設關閉，僅供參考）。
逐日快取用 st.cache_data（雲端相容，不寫本機檔案）；同一天的歷史資料不會變，
所以快取時間可以設長一點（見 config.CACHE_TTL_CHIP_DAY）。
"""

from __future__ import annotations

import time
from datetime import date

import pandas as pd
import requests
import streamlit as st

from config import CACHE_TTL_CHIP_DAY, TWSE_T86_URL


@st.cache_data(ttl=CACHE_TTL_CHIP_DAY, show_spinner=False)
def _fetch_chip_single_day(day: date):
    date_str = day.strftime("%Y%m%d")
    try:
        resp = requests.get(
            TWSE_T86_URL,
            params={"date": date_str, "selectType": "ALL", "response": "json"},
            timeout=8,
        )
        return resp.json()
    except Exception:
        return None


def _parse_chip_row(row, fields):
    wanted = {
        "外資買賣超": ["外陸資買賣超股數(不含外資自營商)", "外資買賣超股數"],
        "投信買賣超": ["投信買賣超股數"],
        "自營商買賣超": ["自營商買賣超股數"],
        "三大法人合計": ["三大法人買賣超股數"],
    }
    result = {}
    for label, candidates in wanted.items():
        val = None
        for col_name in candidates:
            if col_name in fields:
                idx = fields.index(col_name)
                try:
                    val = int(row[idx].replace(",", ""))
                except (ValueError, IndexError, AttributeError):
                    val = None
                break
        result[label] = val
    return result


def fetch_chip_data(stock_code: str, start: date, end: date, max_days: int = 60):
    """抓取近 max_days 個交易日的三大法人買賣超（逐日呼叫 TWSE，量大時只取最近區間）。"""
    all_days = pd.bdate_range(start, end)
    target_days = list(all_days[-max_days:])

    records = []
    progress = st.progress(0.0, text="正在抓取籌碼資料（來源：證交所），請稍等一下…")
    ok_any = False
    for i, d in enumerate(target_days):
        day = d.date()
        data = _fetch_chip_single_day(day)
        progress.progress((i + 1) / len(target_days))
        if not data or data.get("stat") != "OK":
            time.sleep(0.05)
            continue
        fields = data.get("fields", [])
        for row in data.get("data", []):
            if row and row[0].strip() == stock_code:
                parsed = _parse_chip_row(row, fields)
                parsed["date"] = day
                records.append(parsed)
                ok_any = True
                break
        time.sleep(0.05)
    progress.empty()

    if not ok_any:
        return None
    chip_df = pd.DataFrame(records).set_index("date").sort_index()
    return chip_df
