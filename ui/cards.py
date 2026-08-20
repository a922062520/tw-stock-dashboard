"""
卡片元件：單日 KPI 卡、紅黃綠燈結論卡、參考價位卡、動態事件白話說明卡。
所有給使用者看的句子都從 explain/texts.py 取用，這裡只負責排版。
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from explain.texts import (
    ANNUAL_METRIC_EXPLAIN,
    DISCLAIMER_ANALYSIS,
    DISCLAIMER_ENTRY_PRICE,
    DIVIDEND_SUMMARY_TEXT_NONE,
    DIVIDEND_SUMMARY_TEXT_WITH_DATA,
    ENTRY_METHOD_TEXT,
    FUNDAMENTALS_DISCLAIMER,
    KD_STATUS_TEXT,
    PROFIT_STATUS_TEXT,
    RISK_EXPLAIN,
    RISK_METHOD_TEXT,
    SIGNAL_TEXTS,
    STOP_LOSS_EXPLAIN,
    TRAFFIC_LIGHT_TEXT,
    chip_trend_text,
    horizon_reason_text,
    rsi_status_text,
)
from styles import TRAFFIC_LIGHT_EMOJI, horizon_badge_html, render_html, risk_badge_html


# ---------------------------------------------------------------------------
# 單日 KPI 卡：點 K 棒或用日期下拉選單都能切換
# ---------------------------------------------------------------------------
def resolve_selected_date(chart_event, price_df: pd.DataFrame, dropdown_choice=None):
    """決定目前要顯示哪一天的 KPI 卡。K 棒點選與日期下拉選單都可以觸發，
    採「最後改動的那個生效」規則；平板上手指不容易精準點中 K 棒，
    所以下拉選單是同樣有效的入口，不是點選的附屬品。"""
    chart_date = None
    if chart_event:
        selection = chart_event.get("selection") if hasattr(chart_event, "get") else None
        points = selection.get("points", []) if selection else []
        if points:
            raw_x = points[0].get("x") if hasattr(points[0], "get") else None
            if raw_x:
                try:
                    candidate = pd.Timestamp(raw_x).normalize()
                    if candidate in price_df.index:
                        chart_date = candidate
                except Exception:
                    pass

    dropdown_date = None
    if dropdown_choice is not None:
        try:
            candidate = pd.Timestamp(dropdown_choice).normalize()
            if candidate in price_df.index:
                dropdown_date = candidate
        except Exception:
            pass

    prev_chart_date = st.session_state.get("_prev_chart_date")
    prev_dropdown_date = st.session_state.get("_prev_dropdown_date")
    changed_chart = chart_date is not None and chart_date != prev_chart_date
    changed_dropdown = dropdown_date is not None and dropdown_date != prev_dropdown_date

    if changed_dropdown and not changed_chart:
        result = dropdown_date
    elif changed_chart:
        result = chart_date
    elif dropdown_date is not None:
        result = dropdown_date
    elif chart_date is not None:
        result = chart_date
    else:
        result = price_df.index[-1]

    st.session_state["_prev_chart_date"] = chart_date
    st.session_state["_prev_dropdown_date"] = dropdown_date
    return result


def render_daily_kpi_card(price_df: pd.DataFrame, selected_date) -> None:
    row = price_df.loc[selected_date]
    pos = price_df.index.get_loc(selected_date)
    prev_row = price_df.iloc[pos - 1] if pos > 0 else None

    change = None
    change_pct = None
    if prev_row is not None and pd.notna(prev_row["Close"]) and prev_row["Close"]:
        change = float(row["Close"]) - float(prev_row["Close"])
        change_pct = change / float(prev_row["Close"])

    with st.container(border=True):
        st.markdown(f"#### 單日行情：{selected_date.date()}")
        # 分成兩列、每列 3 欄，避免 6 個指標擠在一列導致數字被截斷顯示不全。
        k1, k2, k3 = st.columns(3)
        k1.metric("開盤", f"{row['Open']:.2f}")
        k2.metric("最高", f"{row['High']:.2f}")
        k3.metric("最低", f"{row['Low']:.2f}")
        k4, k5, k6 = st.columns(3)
        k4.metric("收盤", f"{row['Close']:.2f}")
        k5.metric(
            "漲跌",
            f"{change:+.2f}" if change is not None else "—",
            f"{change_pct*100:+.2f}%" if change_pct is not None else None,
            delta_color="inverse",  # 台股慣例：紅漲綠跌
        )
        k6.metric("成交量", f"{row['Volume']:,.0f}")

        extra_bits = []
        for label, col in [("RSI", "RSI"), ("K", "K"), ("D", "D"), ("MA20", "MA20"), ("MA60", "MA60")]:
            val = row.get(col)
            if val is not None and pd.notna(val):
                extra_bits.append(f"{label} {val:.1f}" if label in ("RSI", "K", "D") else f"{label} {val:.2f}")
        if extra_bits:
            st.caption("　｜　".join(extra_bits))

        st.caption("點上方 K 線圖裡的任一根 K 棒，或用下方「選擇日期」都可以切換；預設顯示最新一個交易日。")


# ---------------------------------------------------------------------------
# 第一層：紅黃綠燈結論卡（一句話結論，打開就看到，不用捲動）
# ---------------------------------------------------------------------------
def render_traffic_light_card(concl: dict, light_info: dict, day_change_pct: float | None) -> None:
    emoji = TRAFFIC_LIGHT_EMOJI[light_info["light"]]
    headline = TRAFFIC_LIGHT_TEXT[(light_info["light"], light_info["reason_kind"])]

    with st.container(border=True):
        price_col, light_col = st.columns([1, 2])
        with price_col:
            st.metric(
                "目前價格",
                f"{concl['close_now']:.2f}",
                f"{day_change_pct*100:+.2f}%" if day_change_pct is not None else None,
                delta_color="inverse",  # 台股慣例：紅漲綠跌
            )
        with light_col:
            render_html(f"""
                <div class="traffic-light-card">
                    <div class="traffic-light-emoji">{emoji}</div>
                    <div class="traffic-light-headline">{headline}</div>
                </div>
            """)
        st.caption(DISCLAIMER_ANALYSIS)


# ---------------------------------------------------------------------------
# 第二層：走勢圖下方的風險等級與參考價位卡
# ---------------------------------------------------------------------------
def render_reference_price_card(concl: dict) -> None:
    with st.container(border=True):
        st.markdown("### 風險等級與參考價位")
        c1, c2 = st.columns(2)
        with c1:
            render_html(f"**建議操作時間框架** {horizon_badge_html(concl['horizon'])}")
            st.caption(
                horizon_reason_text(
                    concl["horizon_reason_kind"], concl["annual_vol"], concl["trend_strength"], concl["risk_lvl"], concl["horizon_direction"]
                )
            )
        with c2:
            render_html(f"**風險等級** {risk_badge_html(concl['risk_lvl'])}")
            st.caption(RISK_EXPLAIN.get(concl["risk_lvl"], ""))

        c3, c4, c5 = st.columns(3)
        entry_gap_pct = concl["entry_gap_pct"]
        c3.metric(
            "參考進場價",
            f"{concl['entry_ref']:.2f}",
            f"{entry_gap_pct*100:+.1f}% 距目前價" if abs(entry_gap_pct) > 1e-6 else "＝目前市價",
            delta_color="off",
        )
        c4.metric("參考停損價", f"{concl['stop_loss_price']:.2f}", f"-{concl['stop_loss_pct']*100:.1f}%")
        c5.metric("參考停利價", f"{concl['take_profit_price']:.2f}", f"+{concl['take_profit_pct']*100:.1f}%")

        st.caption(f"進場價方法論：{ENTRY_METHOD_TEXT.get(concl['entry_method_kind'], '')}。")
        st.caption(STOP_LOSS_EXPLAIN.format(risk_method=RISK_METHOD_TEXT.get(concl["risk_method_kind"], "")))
        st.caption(DISCLAIMER_ENTRY_PRICE)


def render_annual_metric_card(annual_return: float, annual_vol: float, risk_lvl: str) -> None:
    col1, col2, col3 = st.columns(3)
    col1.metric("年化平均報酬率", f"{annual_return * 100:.2f}%", f"{annual_return * 100:+.2f}%", delta_color="inverse")
    col2.metric("年化波動度", f"{annual_vol * 100:.2f}%")
    with col3:
        render_html(f"**風險等級** {risk_badge_html(risk_lvl)}")
    st.caption(ANNUAL_METRIC_EXPLAIN.format(explain=RISK_EXPLAIN.get(risk_lvl, "")))


# ---------------------------------------------------------------------------
# 動態事件白話說明卡（只在事件真的發生時顯示，固定三段式）
# ---------------------------------------------------------------------------
def render_signal_cards(signal_keys: list[str]) -> None:
    if not signal_keys:
        return
    st.markdown("### 這陣子值得留意的變化")
    for key in signal_keys:
        text = SIGNAL_TEXTS.get(key)
        if not text:
            continue
        render_html(f"""
            <div class="explain-card">
                <div style="margin-bottom:6px;"><b>{text['title']}</b></div>
                <div style="margin-bottom:4px;">{text['meaning']}</div>
                <div style="color:#64748b;">{text['caution']}</div>
            </div>
        """)


# ---------------------------------------------------------------------------
# RSI／KD 現況白話說明（每次查詢都固定顯示，不是事件觸發才出現）
# ---------------------------------------------------------------------------
def render_rsi_analysis(kind: str, rsi_now: float | None) -> None:
    st.caption(rsi_status_text(kind, rsi_now))


def render_kd_analysis(tier: str, direction: str) -> None:
    text = KD_STATUS_TEXT.get((tier, direction), KD_STATUS_TEXT[("unknown", "unknown")])
    st.caption(text)


# ---------------------------------------------------------------------------
# 三大法人籌碼趨勢白話說明
# ---------------------------------------------------------------------------
def render_chip_analysis(chip_summary: dict) -> None:
    st.caption(chip_trend_text(chip_summary))


# ---------------------------------------------------------------------------
# 分析結果文字摘要（給下載／分享用，純文字、不含任何 HTML）
# ---------------------------------------------------------------------------
def build_summary_text(
    stock_code: str,
    stock_name: str | None,
    concl: dict,
    light_info: dict,
    day_change_pct: float | None,
    annual_return: float,
    annual_vol: float,
    query_date: str,
) -> str:
    emoji = TRAFFIC_LIGHT_EMOJI[light_info["light"]]
    headline = TRAFFIC_LIGHT_TEXT[(light_info["light"], light_info["reason_kind"])]
    name_part = f"　{stock_name}" if stock_name else ""
    change_part = f"（{day_change_pct*100:+.2f}%）" if day_change_pct is not None else ""

    lines = [
        f"{stock_code}{name_part} 分析摘要",
        f"查詢時間：{query_date}",
        "",
        f"目前價格：{concl['close_now']:.2f}{change_part}",
        f"一句話結論：{emoji} {headline}",
        "",
        f"建議操作時間框架：{concl['horizon']}",
        f"風險等級：{concl['risk_lvl']}",
        f"參考進場價：{concl['entry_ref']:.2f}",
        f"參考停損價：{concl['stop_loss_price']:.2f}（-{concl['stop_loss_pct']*100:.1f}%）",
        f"參考停利價：{concl['take_profit_price']:.2f}（+{concl['take_profit_pct']*100:.1f}%）",
        "",
        f"年化平均報酬率：{annual_return*100:.2f}%",
        f"年化波動度：{annual_vol*100:.2f}%",
        "",
        "資料僅供參考，不構成投資建議。",
        "由「台股分析儀表板」產生：https://tw-stock-dashboard.streamlit.app/",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 獲利與股利卡片
# ---------------------------------------------------------------------------
def render_fundamentals_card(profit_summary: dict, dividend_summary: dict) -> None:
    st.markdown("#### 公司賺不賺錢")
    status = profit_summary.get("status", "unknown")
    template = PROFIT_STATUS_TEXT.get(status, PROFIT_STATUS_TEXT["unknown"])
    eps = profit_summary.get("eps")
    if status in ("profit", "loss", "breakeven") and eps is not None:
        st.write(template.format(eps=eps))
    else:
        st.write(PROFIT_STATUS_TEXT["unknown"])

    st.markdown("#### 股利發多少")
    if dividend_summary.get("has_dividend"):
        st.write(
            DIVIDEND_SUMMARY_TEXT_WITH_DATA.format(
                year=dividend_summary["latest_year"],
                amount=dividend_summary["recent_total"],
                years_covered=dividend_summary["years_covered"],
            )
        )
        rows = "".join(
            f"<div style='padding:3px 0;'>{year} 年：{amount:.2f} 元／股</div>"
            for year, amount in sorted(dividend_summary["by_year"].items(), reverse=True)
        )
        render_html(f'<div style="margin-top:4px;">{rows}</div>')
    else:
        st.write(DIVIDEND_SUMMARY_TEXT_NONE)

    st.caption(FUNDAMENTALS_DISCLAIMER)
