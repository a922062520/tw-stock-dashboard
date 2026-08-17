"""
股票代號 <-> 中文名稱對照表（來源：證交所 ISIN 查詢頁）。

雷區（勿修改）：
- 直接用正規表示式解析原始 HTML，不要改用 pd.read_html / lxml——
  之前使用者環境沒裝到 lxml 時，pd.read_html 會悄悄回傳空結果，不會報錯，
  導致「代號對照表抓不到」的問題很難排查。
- 快取一律用 st.cache_data（雲端相容，重開就清空，不寫本機檔案）。
"""

from __future__ import annotations

import re

import requests
import streamlit as st

from config import CACHE_TTL_TICKER_MAP, TWSE_ISIN_URLS


def _parse_twse_isin_table(html_text: str) -> dict:
    """直接用正規表示式從原始 HTML 抓代號+名稱，不依賴 lxml/html5lib 等額外套件，
    避免使用者環境沒裝到對應套件時，整個對照表悄悄抓空。"""
    result = {}
    for m in re.finditer(r"<td[^>]*>\s*(\d{4,6})[\s　]+([^<]+?)\s*</td>", html_text):
        result[m.group(1)] = m.group(2).strip()
    return result


@st.cache_data(ttl=CACHE_TTL_TICKER_MAP, show_spinner=False)
def fetch_stock_name_map():
    """取得全市場股票代號<->名稱對照表，用 st.cache_data 快取 7 天（雲端相容，不寫本機檔案）。
    回傳 (mapping, error_detail)：error_detail 為 None 代表成功，否則附上除錯用的錯誤訊息。"""
    mapping = {}
    errors = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    for market, url in TWSE_ISIN_URLS.items():
        try:
            resp = requests.get(url, timeout=10, headers=headers)
            resp.encoding = "big5"
            part = _parse_twse_isin_table(resp.text)
            if not part:
                errors.append(f"{market}：HTTP {resp.status_code}，但解析不到任何股票資料（網站格式可能改變）")
            mapping.update(part)
        except Exception as e:
            errors.append(f"{market}：{type(e).__name__} - {e}")

    if mapping:
        return mapping, None
    return mapping, "；".join(errors) if errors else "未知原因"


def search_stock_by_name(query: str, name_map: dict):
    """回傳符合中文名稱的 (代號, 名稱) 清單，完全相符優先，其次為部分比對（模糊比對）。"""
    query = query.strip()
    exact = [(code, name) for code, name in name_map.items() if name == query]
    if exact:
        return exact
    return [(code, name) for code, name in name_map.items() if query in name]
