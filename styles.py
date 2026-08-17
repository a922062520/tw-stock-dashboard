"""
自訂 CSS 注入與共用的小型 HTML 元件（徽章、紅綠燈圖示等）。

【重要雷區，拆檔後更容易踩到，請勿修改以下寫法】
st.markdown 在套用 HTML 之前，底層會先跑一次 Markdown 解析。CommonMark 規則規定：
一行文字開頭如果有 4 個以上空白縮排，會被判定成「縮排程式碼區塊」，導致整段 HTML/CSS
原封不動被印在畫面上，而不是被套用生效（新聞卡片、CSS 區塊都曾經踩過這個雷）。
拆成模組後，函式內的縮排層次變深，更容易不小心讓字串前面帶出空白，所以：
  1. 任何要丟給 st.markdown(..., unsafe_allow_html=True) 的字串，一律先經過
     oneline_html() 處理（去除每行前後空白、合併成單行）再輸出。
  2. <style> 這種多行字串，開頭必須緊接在三引號後面、完全不縮排（見 inject_css）。
"""

from __future__ import annotations

import streamlit as st

from config import BUTTON_MIN_HEIGHT, COLORS, FONT_SIZE_BODY, FONT_SIZE_CAPTION, FONT_SIZE_SUBTITLE, FONT_SIZE_TITLE


def oneline_html(html_str: str) -> str:
    """把多行、有縮排的 HTML 字串壓成單行，避免 CommonMark 把它誤判成程式碼區塊。"""
    lines = [line.strip() for line in html_str.strip().splitlines()]
    return "".join(lines)


def render_html(html_str: str) -> None:
    """統一的 HTML 輸出入口：一律先 oneline 化再交給 st.markdown。"""
    st.markdown(oneline_html(html_str), unsafe_allow_html=True)


def inject_css() -> None:
    # 注意：<style> 必須緊接在三引號後面、完全不縮排，內層 CSS 規則的縮排不受影響。
    st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700;900&display=swap');

html, body, [class*="css"] {
    font-family: 'Noto Sans TC', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-size: """ + FONT_SIZE_BODY + """;
}
.stApp { background-color: #f7f9fc; }
.block-container { max-width: 900px; padding-top: 1.2rem; }
h1 { font-size: """ + FONT_SIZE_TITLE + """ !important; font-weight: 900; color: #1e293b; }
h2, h3 { font-size: """ + FONT_SIZE_SUBTITLE + """ !important; font-weight: 700; color: #1e293b; }
p, li, label, span { font-size: """ + FONT_SIZE_BODY + """; }
.section-caption, small, .stCaption, div[data-testid="stCaptionContainer"] {
    font-size: """ + FONT_SIZE_CAPTION + """ !important;
    color: #475569 !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] {
    background-color: #ffffff;
    border: 1px solid #e5e9f0;
    border-radius: 16px;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
    padding: 10px 14px;
}
div[data-testid="stMetric"] {
    background-color: #f8fafc;
    border: 1px solid #edf1f7;
    border-radius: 12px;
    padding: 14px 16px 10px 16px;
    overflow: visible;
}
div[data-testid="stMetricValue"] {
    font-size: 1.5rem;
    font-weight: 700;
    color: #1e293b;
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: unset !important;
    word-break: break-word;
    line-height: 1.25;
}
div[data-testid="stMetricValue"] > div {
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: unset !important;
}
div[data-testid="stMetricLabel"] { font-size: """ + FONT_SIZE_CAPTION + """; color: #64748b; }
hr { border-color: #e5e9f0; }
.badge {
    display: inline-block;
    padding: 5px 16px;
    border-radius: 999px;
    font-weight: 700;
    font-size: """ + FONT_SIZE_BODY + """;
}
.traffic-light-card {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 6px 4px;
}
.traffic-light-emoji { font-size: 2.4rem; line-height: 1; }
.traffic-light-headline { font-size: 1.35rem; font-weight: 700; color: #1e293b; }
.stButton > button, .stDownloadButton > button {
    min-height: """ + BUTTON_MIN_HEIGHT + """;
    font-size: """ + FONT_SIZE_BODY + """;
    font-weight: 600;
    border-radius: 12px;
    padding: 8px 18px;
    margin: 4px 6px 4px 0;
    white-space: nowrap;
}
/* 手機／窄螢幕：多欄按鈕（查詢區間快選、最近查看過的股票）在容器變窄時，
   原本文字會被壓到逐字換行變成直的（"近1個月"變成4行）。
   上面已經讓按鈕文字 nowrap，這裡讓外層欄位在容器不夠寬時改成自動換行成好幾排，
   而不是硬擠成又窄又高的欄位，觸控大小也不會被壓縮。*/
@media (max-width: 640px) {
    .block-container { padding-left: 1rem; padding-right: 1rem; }
    div[data-testid="stHorizontalBlock"] { row-gap: 8px; }
    div[data-testid="stColumn"] { min-width: fit-content !important; flex: 0 1 auto !important; }
    div[data-testid="stColumn"] .stButton { width: 100%; }
    div[data-testid="stColumn"] .stButton > button { width: 100%; }
}
.stApp { overflow-x: hidden; }
div[data-baseweb="select"] { min-height: """ + BUTTON_MIN_HEIGHT + """; font-size: """ + FONT_SIZE_BODY + """; }
input[type="text"] { min-height: """ + BUTTON_MIN_HEIGHT + """; font-size: """ + FONT_SIZE_BODY + """ !important; }
.explain-card {
    background: #f8fafc;
    border: 1px solid #edf1f7;
    border-left: 5px solid """ + COLORS["accent"] + """;
    border-radius: 12px;
    padding: 14px 16px;
    margin-bottom: 12px;
}
.explain-card b { color: #1e293b; }
</style>""", unsafe_allow_html=True)


def badge(text: str, bg: str, fg: str) -> str:
    return oneline_html(f'<span class="badge" style="background:{bg};color:{fg};">{text}</span>')


def risk_badge_html(label: str) -> str:
    palette = {
        "低風險": ("#ecfdf5", "#047857"),
        "中風險": ("#fffbeb", "#b45309"),
        "高風險": ("#fef2f2", "#b91c1c"),
    }
    bg, fg = palette.get(label, ("#f1f5f9", "#334155"))
    return badge(label, bg, fg)


def horizon_badge_html(label: str) -> str:
    palette = {
        "短期": ("#eff6ff", "#1d4ed8"),
        "中長期": ("#f5f3ff", "#6d28d9"),
    }
    bg, fg = palette.get(label, ("#f1f5f9", "#334155"))
    return badge(label, bg, fg)


TRAFFIC_LIGHT_EMOJI = {"green": "🟢", "yellow": "🟡", "red": "🔴"}
