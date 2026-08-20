"""
高齡友善版面元件：搜尋框（含模糊比對）、本次查看過的股票（大按鈕、session_state、
不寫檔）、查詢區間（大按鈕快選＋進階自訂）。拿掉側邊欄，全部放在畫面上方。
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import streamlit as st

from config import DEFAULT_RANGE_DAYS, RANGE_PRESETS
from data.ticker_map import search_stock_by_name
from explain.texts import ERROR_NAME_NOT_FOUND, ERROR_TICKER_MAP_UNAVAILABLE, RETRY_BUTTON_LABEL

TAIPEI_TZ = ZoneInfo("Asia/Taipei")


def today_taipei() -> date:
    """伺服器（Streamlit Cloud）跑在UTC，直接用date.today()在台灣時間凌晨0-8點會誤判成前一天，
    所有跟「今天」有關的判斷一律要走這個函式，不要用date.today()。"""
    return datetime.now(TAIPEI_TZ).date()


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


# ---------------------------------------------------------------------------
# 我的自選股：跟「本次查看過」不同，這個是使用者主動加入、存進網址參數（URL query
# params）而不是伺服器端資料庫，符合「不保存任何使用者資料」的設計原則——換瀏覽器
# 分頁或關掉重開就會消失，但用同一個網址（加進書籤／分享給家人）就能保留。
# ---------------------------------------------------------------------------
_WATCHLIST_PARAM = "watch"
_WATCHLIST_MAX = 10


def _load_watchlist_from_url() -> list[str]:
    raw = st.query_params.get(_WATCHLIST_PARAM, "")
    if not raw:
        return []
    return [code.strip() for code in raw.split(",") if code.strip()]


def _save_watchlist_to_url(codes: list[str]) -> None:
    if codes:
        st.query_params[_WATCHLIST_PARAM] = ",".join(codes)
    elif _WATCHLIST_PARAM in st.query_params:
        del st.query_params[_WATCHLIST_PARAM]


def get_watchlist() -> list[str]:
    if "watchlist" not in st.session_state:
        st.session_state["watchlist"] = _load_watchlist_from_url()
    return st.session_state["watchlist"]


def toggle_watchlist(code: str) -> None:
    codes = get_watchlist()
    if code in codes:
        codes = [c for c in codes if c != code]
    else:
        codes = [code] + codes
        codes = codes[:_WATCHLIST_MAX]
    st.session_state["watchlist"] = codes
    _save_watchlist_to_url(codes)


def render_watchlist_section(name_map: dict) -> None:
    """畫面上方的「我的自選股」快速按鈕列，點了直接查詢；網址列會記住這份清單。"""
    codes = get_watchlist()
    if not codes:
        return
    st.caption("⭐ 我的自選股（存在網址列，加進書籤或分享網址就能保留）：")
    cols = st.columns(len(codes))
    for col, code in zip(cols, codes):
        name = name_map.get(code, "")
        label = f"{code} {name}".strip()
        if col.button(label, key=f"watch_{code}", use_container_width=True):
            st.session_state["search_text"] = code
            st.rerun()


def render_watchlist_toggle_button(code: str) -> None:
    """在查到的股票旁邊放一顆「加入／移除自選」按鈕。"""
    codes = get_watchlist()
    is_in = code in codes
    label = "★ 已加入自選股" if is_in else "☆ 加入自選股"
    if st.button(label, key=f"watch_toggle_{code}"):
        toggle_watchlist(code)
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


def render_compare_input(main_code: str) -> list[str]:
    """讓使用者輸入另外1-2檔股票代號來比較（同一段查詢區間的累積漲跌幅疊圖）。
    只接受代號（不支援中文名稱模糊比對），保持這個功能單純好維護。"""
    with st.expander("📊 比較其他股票（最多加2檔，看同一段時間誰漲跌比較多）", expanded=False):
        raw = st.text_input(
            "輸入股票代號，用逗號分開，例如 2317,2454",
            key="compare_codes_input",
            placeholder="例如 2317,2454",
        ).strip()
        if not raw:
            return []
        codes = [c.strip() for c in raw.split("，" if "，" in raw else ",") if c.strip()]
        codes = [c for c in codes if c.isdigit() and c != main_code][:2]
        return codes


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

    end_date = today_taipei()
    start_date = end_date - timedelta(days=st.session_state["range_days"])

    with st.expander("自訂日期區間（進階，一般不需要調整）", expanded=False):
        custom = st.date_input(
            "自訂區間", value=(start_date, end_date), min_value=date(2000, 1, 1), max_value=end_date,
            label_visibility="collapsed",
        )
        if isinstance(custom, tuple) and len(custom) == 2:
            start_date, end_date = custom

    return start_date, end_date


def render_date_dropdown(price_df):
    """K 棒點選以外的另一個入口：日期下拉選單，平板手指不容易精準點中 K 棒時可以用這個。
    旁邊加「前一天／後一天」按鈕，看完一天想看隔壁那天不用重新展開選單找。"""
    options = list(price_df.index)
    labels = [d.date().isoformat() for d in options]

    current_label = st.session_state.get("date_dropdown", labels[-1])
    if current_label not in labels:
        current_label = labels[-1]
    current_idx = labels.index(current_label)

    prev_col, next_col, dropdown_col = st.columns([1, 1, 3])
    with prev_col:
        if st.button("◀ 前一天", key="date_prev", disabled=current_idx <= 0, use_container_width=True):
            st.session_state["date_dropdown"] = labels[current_idx - 1]
            st.rerun()
    with next_col:
        if st.button("後一天 ▶", key="date_next", disabled=current_idx >= len(labels) - 1, use_container_width=True):
            st.session_state["date_dropdown"] = labels[current_idx + 1]
            st.rerun()
    with dropdown_col:
        choice_label = st.selectbox("選擇日期查看單日行情", labels, index=len(labels) - 1, key="date_dropdown")

    idx = labels.index(choice_label)
    return options[idx]
