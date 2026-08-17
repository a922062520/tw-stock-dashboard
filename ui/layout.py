"""
高齡友善版面元件：搜尋框（含模糊比對）、本次查看過的股票（大按鈕、session_state、
不寫檔）、查詢區間（大按鈕快選＋進階自訂）。拿掉側邊欄，全部放在畫面上方。
"""

from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from config import DEFAULT_RANGE_DAYS, RANGE_PRESETS
from data.ticker_map import search_stock_by_name
from explain.texts import ERROR_NAME_NOT_FOUND, ERROR_TICKER_MAP_UNAVAILABLE, RETRY_BUTTON_LABEL


def remember_stock(code: str, name: str | None) -> None:
    """把這次查詢的股票記到本次瀏覽的 session_state，關掉瀏覽器就清空，不寫入任何檔案。"""
    recents = [r for r in st.session_state.get("recent_stocks", []) if r["code"] != code]
    recents.insert(0, {"code": code, "name": name or ""})
    st.session_state["recent_stocks"] = recents[:8]


def render_recent_stocks() -> None:
    recents = st.session_state.get("recent_stocks", [])
    if not recents:
        return
    st.caption("本次查看過：")
    cols = st.columns(len(recents))
    for col, r in zip(cols, recents):
        label = f"{r['code']} {r['name']}".strip()
        if col.button(label, key=f"recent_{r['code']}", use_container_width=True):
            st.session_state["search_text"] = r["code"]
            st.rerun()


def render_search_section(name_map: dict, name_map_error: str | None):
    """回傳 (stock_code_input, matched_name, raw_input)。支援代號、中文全名、中文部分名稱模糊比對。"""
    st.markdown("### 查詢股票")
    render_recent_stocks()

    if "search_text" not in st.session_state:
        st.session_state["search_text"] = "2330"

    raw_input = st.text_input(
        "台股代號或中文名稱",
        key="search_text",
        placeholder="輸入代號或中文名稱，例如 2330、台積電、台積",
        label_visibility="collapsed",
    ).strip()

    stock_code_input = None
    matched_name = None

    if raw_input.isdigit():
        stock_code_input = raw_input
        matched_name = name_map.get(raw_input)
    elif raw_input:
        if not name_map:
            st.error(ERROR_TICKER_MAP_UNAVAILABLE)
            if name_map_error:
                with st.expander("查看錯誤細節（回報問題時可以複製這段）", expanded=True):
                    st.code(name_map_error)
            if st.button(RETRY_BUTTON_LABEL):
                from data.ticker_map import fetch_stock_name_map

                fetch_stock_name_map.clear()
                st.rerun()
        else:
            matches = search_stock_by_name(raw_input, name_map)
            if not matches:
                st.error(ERROR_NAME_NOT_FOUND.format(query=raw_input))
            elif len(matches) == 1:
                stock_code_input, matched_name = matches[0]
                st.caption(f"已比對到：{stock_code_input}　{matched_name}")
            else:
                options = [f"{c}　{n}" for c, n in matches[:20]]
                choice = st.selectbox("找到多筆符合的股票，請選擇", options)
                stock_code_input, matched_name = choice.split("　")

    return stock_code_input, matched_name, raw_input


def render_date_range_controls():
    """大按鈕快速選擇查詢區間，另外提供展開式的自訂區間，平板點選不容易誤觸。"""
    st.caption("查詢區間")
    if "range_days" not in st.session_state:
        st.session_state["range_days"] = DEFAULT_RANGE_DAYS

    labels = list(RANGE_PRESETS.keys())
    cols = st.columns(len(labels))
    for col, label in zip(cols, labels):
        days = RANGE_PRESETS[label]
        is_active = st.session_state["range_days"] == days
        btn_label = f"✅ {label}" if is_active else label
        if col.button(btn_label, key=f"range_{days}", use_container_width=True):
            st.session_state["range_days"] = days
            st.rerun()

    end_date = date.today()
    start_date = end_date - timedelta(days=st.session_state["range_days"])

    with st.expander("自訂日期區間（進階，一般不需要調整）", expanded=True):
        custom = st.date_input(
            "自訂區間", value=(start_date, end_date), min_value=date(2000, 1, 1), max_value=end_date,
            label_visibility="collapsed",
        )
        if isinstance(custom, tuple) and len(custom) == 2:
            start_date, end_date = custom

    return start_date, end_date


def render_date_dropdown(price_df):
    """K 棒點選以外的另一個入口：日期下拉選單，平板手指不容易精準點中 K 棒時可以用這個。"""
    options = list(price_df.index)
    labels = [d.date().isoformat() for d in options]
    choice_label = st.selectbox("選擇日期查看單日行情", labels, index=len(labels) - 1, key="date_dropdown")
    idx = labels.index(choice_label)
    return options[idx]
