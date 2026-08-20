"""近期相關新聞（來源：Google 新聞 RSS，中文）。"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import quote
from zoneinfo import ZoneInfo

import requests
import streamlit as st

from config import CACHE_TTL_NEWS

_TAIPEI_TZ = ZoneInfo("Asia/Taipei")


def _format_pub_date(raw: str) -> str:
    """RSS 的 pubDate 是英文原始格式（例如 Wed, 20 Aug 2026 03:11:00 GMT），
    長輩看不懂，轉成台北時間的中文格式，太新的新聞改顯示「幾小時前」比較直覺。"""
    if not raw:
        return ""
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo("UTC"))
        dt_taipei = dt.astimezone(_TAIPEI_TZ)
    except (ValueError, TypeError):
        return raw

    now = datetime.now(_TAIPEI_TZ)
    delta = now - dt_taipei
    hours = delta.total_seconds() / 3600
    if 0 <= hours < 1:
        return f"{max(int(delta.total_seconds() // 60), 1)}分鐘前"
    if 1 <= hours < 24:
        return f"{int(hours)}小時前"
    return dt_taipei.strftime("%m月%d日 %H:%M")


@st.cache_data(ttl=CACHE_TTL_NEWS, show_spinner=False)
def fetch_news(stock_code: str, stock_name: str | None, max_items: int = 8):
    query = f"{stock_name} {stock_code}" if stock_name else stock_code
    url = f"https://news.google.com/rss/search?q={quote(query)}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    try:
        resp = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        root = ET.fromstring(resp.content)
    except Exception:
        return None

    items = []
    for item in root.findall(".//item")[:max_items]:
        title_el = item.find("title")
        link_el = item.find("link")
        date_el = item.find("pubDate")
        source_el = item.find("source")
        raw_pub_date = date_el.text if date_el is not None else ""
        items.append(
            {
                "title": title_el.text if title_el is not None else "",
                "link": link_el.text if link_el is not None else "",
                "pubDate": _format_pub_date(raw_pub_date),
                "source": source_el.text if source_el is not None else "",
            }
        )
    return items
