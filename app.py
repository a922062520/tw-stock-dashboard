"""
台股互動式分析儀表板 —— 高齡友善版（第一階段）
--------------------------------------------
只負責頁面路由與版面組裝，實際邏輯都在各模組裡（見 data/ analysis/ explain/ ui/）。
純唯讀查詢工具，不保存任何使用者資料、不寫入任何本機檔案。
"""

from __future__ import annotations

import html as html_lib

import streamlit as st

from analysis.conclusion import build_analysis_conclusion, classify_traffic_light
from analysis.fundamentals import summarize_dividends, summarize_profit
from analysis.indicators import add_moving_averages, compute_atr, compute_kd, compute_rsi
from analysis.metrics import analyze_chip_trend, classify_kd, classify_rsi, compute_return_risk
from analysis.signals import detect_signals
from data.fundamentals import fetch_dividend_history, fetch_fundamentals_info
from data.institutional import fetch_chip_data
from data.news import fetch_news
from data.stock_data import fetch_price, fetch_stock_name
from data.ticker_map import fetch_stock_name_map
from explain.texts import (
    ERROR_CHIP_DATA_FAILED,
    ERROR_INSUFFICIENT_METRICS,
    ERROR_NO_CHIP_DATA,
    ERROR_NO_FUNDAMENTALS,
    ERROR_NO_NEWS,
    ERROR_NO_PRICE_DATA,
    LOADING_PRICE,
)
from styles import inject_css, render_html
from ui.cards import (
    build_summary_text,
    render_annual_metric_card,
    render_chip_analysis,
    render_daily_kpi_card,
    render_fundamentals_card,
    render_kd_analysis,
    render_reference_price_card,
    render_rsi_analysis,
    render_signal_cards,
    render_traffic_light_card,
    resolve_selected_date,
)
from ui.charts import (
    get_missing_dates,
    render_chip_chart,
    render_compare_chart,
    render_kd_chart,
    render_price_chart,
    render_rsi_chart,
)
from ui.layout import (
    remember_stock,
    render_compare_input,
    render_date_dropdown,
    render_date_range_controls,
    render_search_section,
    render_watchlist_section,
    render_watchlist_toggle_button,
    today_taipei,
)

st.set_page_config(page_title="台股分析儀表板", layout="wide")
if "large_font" not in st.session_state:
    st.session_state["large_font"] = False
inject_css(large_font=st.session_state["large_font"])

title_col, toggle_col = st.columns([5, 2])
with title_col:
    st.title("台股互動式分析儀表板")
    st.caption("查詢台股代號或中文名稱，馬上看到目前價格、一句話結論，以及走勢圖。")
with toggle_col:
    large_font = st.toggle("字體再放大", value=st.session_state["large_font"], key="large_font_toggle")
    if large_font != st.session_state["large_font"]:
        st.session_state["large_font"] = large_font
        st.rerun()

name_map, name_map_error = fetch_stock_name_map()
render_watchlist_section(name_map)
stock_code_input, matched_name, raw_input = render_search_section(name_map, name_map_error)
start_date, end_date = render_date_range_controls()

if not raw_input:
    st.info("請在上方輸入台股代號或中文名稱，例如 2330 或 台積電。")
    st.stop()
if not stock_code_input:
    st.stop()

with st.spinner(LOADING_PRICE):
    price_df, used_ticker = fetch_price(stock_code_input, start_date, end_date)

if price_df is None or price_df.empty:
    st.error(ERROR_NO_PRICE_DATA.format(code=stock_code_input))
    st.stop()

stock_name = matched_name or fetch_stock_name(used_ticker)
remember_stock(stock_code_input, stock_name)

header_col, watch_btn_col = st.columns([5, 2])
with header_col:
    header = stock_code_input + (f"　{stock_name}" if stock_name else "")
    st.subheader(header)
with watch_btn_col:
    render_watchlist_toggle_button(stock_code_input)

latest_date_full = price_df.index[-1].strftime("%Y/%m/%d")
latest_date_label = price_df.index[-1].strftime("%m/%d")
banner_col, refresh_col = st.columns([5, 2])
with banner_col:
    st.caption(f"📅 資料截至 {latest_date_full} 收盤，盤中不會即時更新（隔天約上午8點後更新前一交易日資料）")
with refresh_col:
    if st.button("🔄 重新整理最新資料", key="refresh_data", use_container_width=True):
        fetch_price.clear()
        fetch_fundamentals_info.clear()
        fetch_dividend_history.clear()
        st.rerun()

price_df = add_moving_averages(price_df)
price_df["RSI"] = compute_rsi(price_df["Close"])
price_df["K"], price_df["D"] = compute_kd(price_df)
price_df["ATR14"] = compute_atr(price_df)

metrics = compute_return_risk(price_df["Close"])
if metrics is None:
    st.warning(ERROR_INSUFFICIENT_METRICS)
    st.stop()

annual_return, annual_vol, daily_ret = metrics
concl = build_analysis_conclusion(price_df, annual_return, annual_vol, daily_ret)
light_info = classify_traffic_light(concl)
signal_keys = detect_signals(price_df)

prev_close = float(price_df["Close"].iloc[-2]) if len(price_df) >= 2 else None
day_change_pct = (concl["close_now"] - prev_close) / prev_close if prev_close else None

# ---- 第一層：現在多少錢、一句話結論＋燈號（打開就看到，不用捲動）----------------
render_traffic_light_card(concl, light_info, day_change_pct, latest_date_label)
render_signal_cards(signal_keys)

summary_text = build_summary_text(
    stock_code_input, stock_name, concl, light_info, day_change_pct,
    annual_return, annual_vol, today_taipei().isoformat(),
)
st.download_button(
    "⬇️ 下載本頁分析摘要（文字檔，可傳給家人）",
    data=summary_text,
    file_name=f"{stock_code_input}_分析摘要_{today_taipei().isoformat()}.txt",
    mime="text/plain",
)

st.divider()

# ---- 第二層：走勢圖、風險等級、參考價位 -------------------------------------
st.markdown("### 股價走勢")
st.caption("紅K＝收盤價高於開盤價，綠K＝收盤價低於開盤價；橘線／紫線為月線、季線；下方是成交量。")
price_chart_event = render_price_chart(price_df)
missing_dates = get_missing_dates(price_df.index)

selected_date_dropdown = render_date_dropdown(price_df)
selected_date = resolve_selected_date(price_chart_event, price_df, selected_date_dropdown)
render_daily_kpi_card(price_df, selected_date)

render_reference_price_card(concl)

compare_codes = render_compare_input(stock_code_input)
if compare_codes:
    compare_dfs = {stock_code_input: price_df}
    compare_names = {stock_code_input: stock_name or ""}
    for code in compare_codes:
        with st.spinner(f"查詢 {code} 中..."):
            cmp_df, cmp_ticker = fetch_price(code, start_date, end_date)
        if cmp_df is None or cmp_df.empty:
            st.warning(f"查不到 {code} 的股價資料，這檔先跳過比較。")
            continue
        compare_dfs[code] = cmp_df
        compare_names[code] = fetch_stock_name(cmp_ticker) or ""

    if len(compare_dfs) > 1:
        st.markdown("#### 走勢比較（換算成累積漲跌幅 %，方便不同價位的股票互相比較）")
        render_compare_chart(compare_dfs, compare_names)

        cols = st.columns(len(compare_dfs))
        for col, (code, df) in zip(cols, compare_dfs.items()):
            period_change_pct = (float(df["Close"].iloc[-1]) / float(df["Close"].iloc[0]) - 1) * 100
            label = f"{code} {compare_names.get(code, '')}".strip()
            col.metric(label, f"{df['Close'].iloc[-1]:.2f}", f"{period_change_pct:+.1f}% 區間累積")

st.divider()

# ---- 第三層：獲利股利、技術指標、法人籌碼、新聞（收在展開區內，想看才點開）--------
with st.expander("查看獲利與股利", expanded=True):
    try:
        fundamentals_info = fetch_fundamentals_info(used_ticker)
        dividend_history = fetch_dividend_history(used_ticker)
    except Exception:
        fundamentals_info = {}
        dividend_history = None

    if not fundamentals_info and dividend_history is None:
        st.info(ERROR_NO_FUNDAMENTALS)
    else:
        profit_summary = summarize_profit(fundamentals_info)
        dividend_summary = summarize_dividends(dividend_history)
        render_fundamentals_card(profit_summary, dividend_summary)

with st.expander("查看技術指標（RSI、KD、年化報酬與波動度）", expanded=True):
    st.markdown("#### RSI（相對強弱指標，14 日）")
    render_rsi_chart(price_df, missing_dates)
    rsi_now = price_df["RSI"].iloc[-1] if len(price_df) else None
    render_rsi_analysis(classify_rsi(rsi_now), rsi_now)

    st.markdown("#### KD 隨機指標（9,3,3）")
    render_kd_chart(price_df, missing_dates)
    kd_tier, kd_direction = classify_kd(price_df["K"].iloc[-1], price_df["D"].iloc[-1]) if len(price_df) else ("unknown", "unknown")
    render_kd_analysis(kd_tier, kd_direction)

    st.markdown("#### 年化報酬與波動度")
    render_annual_metric_card(annual_return, annual_vol, concl["risk_lvl"])

with st.expander("查看三大法人買賣超（實驗性功能，資料來源：FinMind）", expanded=True):
    show_chip = st.checkbox("顯示三大法人籌碼資料（近 60 個交易日，資料來源：FinMind）", value=True)
    if show_chip:
        try:
            chip_df = fetch_chip_data(stock_code_input, start_date, end_date, max_days=60)
        except Exception:
            chip_df = None
            st.warning(ERROR_CHIP_DATA_FAILED)
        if chip_df is None or chip_df.empty:
            st.info(ERROR_NO_CHIP_DATA)
        else:
            render_chip_chart(chip_df)
            st.caption("正值＝買超（買進多於賣出），負值＝賣超（賣出多於買進）。單位：股數。")
            render_chip_analysis(analyze_chip_trend(chip_df))

with st.expander("查看近期相關新聞", expanded=True):
    news_items = fetch_news(stock_code_input, stock_name)
    if not news_items:
        st.caption(ERROR_NO_NEWS)
    else:
        rows = "".join(
            f'<div style="padding:10px 14px;border-bottom:1px solid #e6ddc8;">'
            f'<a href="{html_lib.escape(n["link"])}" target="_blank" style="color:#2b2822;font-weight:600;text-decoration:none;">{html_lib.escape(n["title"])}</a>'
            f'<div style="color:#8b8266;font-size:16px;margin-top:2px;">{html_lib.escape(n["source"])}　{html_lib.escape(n["pubDate"])}</div>'
            "</div>"
            for n in news_items
        )
        render_html(f'<div style="background:#ffffff;border:1px solid #e6ddc8;border-radius:12px;overflow:hidden;">{rows}</div>')
        st.caption("新聞來源：Google 新聞，僅供參考，請自行判斷真實性與時效性，不代表本工具立場。")

st.divider()
st.caption("資料僅供參考，不構成投資建議。股價資料來源：上市個股為台灣證券交易所，上櫃個股為 FinMind 開放資料平台；籌碼資料來源：台灣證券交易所。")
