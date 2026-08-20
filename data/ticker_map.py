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
    避免使用者環境沒裝到對應套件時，整個對照表悄悄抓空。

    證交所這份表格裡認購/認售權證佔了六成以上的筆數（實測：上市表30977筆裡
    18688筆是這種），代號一律是6碼、名稱一定帶「購」或「售」（例如「南亞統一
    59購01」），混進來會蓋掉搜尋結果裡真正的股票。ETF代號雖然也是6碼（例如
    006208、009800），但名稱不會有「購」「售」，這條規則不會誤殺到；唯一
    一檔4碼股票名稱剛好帶「購」字的（2945 三商家購）也因為長度不是6碼而保留。"""
    result = {}
    for m in re.finditer(r"<td[^>]*>\s*(\d{4,6})[\s　]+([^<]+?)\s*</td>", html_text):
        code, name = m.group(1), m.group(2).strip()
        if len(code) == 6 and ("購" in name or "售" in name):
            continue
        result[code] = name
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
            # 上市那份表格實測約8MB、下載要10秒左右（權證佔了六成以上筆數），
            # 原本10秒逾時常常卡在臨界點，稍微變慢就整批失敗，改成25秒給足緩衝。
            resp = requests.get(url, timeout=25, headers=headers)
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
    """回傳符合中文名稱的 (代號, 名稱) 清單。完全相符優先；其次是名稱開頭就符合的
    （例如查「台積」，「台積電」會排在只是名稱中間帶到這兩個字的公司前面）；
    其餘部分比對排最後——不然原本按字典序排，最相關的結果不一定排在前面。"""
    query = query.strip()
    exact = [(code, name) for code, name in name_map.items() if name == query]
    if exact:
        return exact
    starts_with = [(code, name) for code, name in name_map.items() if name.startswith(query)]
    contains = [(code, name) for code, name in name_map.items() if query in name and not name.startswith(query)]
    return starts_with + contains
