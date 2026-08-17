"""近期相關新聞（來源：Google 新聞 RSS，中文）。"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from urllib.parse import quote

import requests
import streamlit as st

from config import CACHE_TTL_NEWS


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
        items.append(
            {
                "title": title_el.text if title_el is not None else "",
                "link": link_el.text if link_el is not None else "",
                "pubDate": date_el.text if date_el is not None else "",
                "source": source_el.text if source_el is not None else "",
            }
        )
    return items
