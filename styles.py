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

from config import (
    BUTTON_MIN_HEIGHT,
    BUTTON_MIN_HEIGHT_LARGE,
    COLORS,
    FONT_SIZE_BODY,
    FONT_SIZE_BODY_LARGE,
    FONT_SIZE_CAPTION,
    FONT_SIZE_CAPTION_LARGE,
    FONT_SIZE_SUBTITLE,
    FONT_SIZE_SUBTITLE_LARGE,
    FONT_SIZE_TITLE,
    FONT_SIZE_TITLE_LARGE,
)


def oneline_html(html_str: str) -> str:
    """把多行、有縮排的 HTML 字串壓成單行，避免 CommonMark 把它誤判成程式碼區塊。"""
    lines = [line.strip() for line in html_str.strip().splitlines()]
    return "".join(lines)


def render_html(html_str: str) -> None:
    """統一的 HTML 輸出入口：一律先 oneline 化再交給 st.markdown。"""
    st.markdown(oneline_html(html_str), unsafe_allow_html=True)


def inject_css(large_font: bool = False) -> None:
    # 注意：<style> 必須緊接在三引號後面、完全不縮排，內層 CSS 規則的縮排不受影響。
    title_size = FONT_SIZE_TITLE_LARGE if large_font else FONT_SIZE_TITLE
    subtitle_size = FONT_SIZE_SUBTITLE_LARGE if large_font else FONT_SIZE_SUBTITLE
    body_size = FONT_SIZE_BODY_LARGE if large_font else FONT_SIZE_BODY
    caption_size = FONT_SIZE_CAPTION_LARGE if large_font else FONT_SIZE_CAPTION
    button_height = BUTTON_MIN_HEIGHT_LARGE if large_font else BUTTON_MIN_HEIGHT

    st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700;900&display=swap');

html, body, [class*="css"] {
    font-family: 'Noto Sans TC', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-size: """ + body_size + """;
}
.stApp { background-color: #f7f4ec; }
.block-container { max-width: 900px; padding-top: 1.2rem; }
h1 { font-size: """ + title_size + """ !important; font-weight: 900; color: #2b2822; letter-spacing: -0.01em; }
h2, h3 { font-size: """ + subtitle_size + """ !important; font-weight: 800; color: #2b2822; }
p, li, label, span { font-size: """ + body_size + """; }
.section-caption, small, .stCaption, div[data-testid="stCaptionContainer"] {
    font-size: """ + caption_size + """ !important;
    color: #6b6353 !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] {
    background-color: #ffffff;
    border: 1px solid #e6ddc8;
    border-radius: 16px;
    box-shadow: 0 1px 3px rgba(38, 33, 24, 0.06);
    padding: 10px 14px;
}
div[data-testid="stMetric"] {
    background-color: #faf8f2;
    border: 1px solid #e6ddc8;
    border-radius: 12px;
    padding: 14px 16px 10px 16px;
    overflow: visible;
}
div[data-testid="stMetricValue"] {
    font-size: 1.5rem;
    font-weight: 700;
    color: #2b2822;
    font-variant-numeric: tabular-nums;
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
div[data-testid="stMetricDelta"] { font-variant-numeric: tabular-nums; }
div[data-testid="stMetricLabel"] { font-size: """ + caption_size + """; color: #6b6353; }
div[data-testid="stMetricLabel"] p,
div[data-testid="stMetricLabel"] > div,
div[data-testid="stMain"] div[data-testid="stMetricLabel"] p,
div[data-testid="stMain"] div[data-testid="stMetricLabel"] > div {
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: unset !important;
}
hr { border-color: #e6ddc8; }
.badge {
    display: inline-block;
    padding: 5px 16px;
    border-radius: 999px;
    font-weight: 700;
    font-size: """ + body_size + """;
}
.traffic-light-card {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 6px 4px;
}
.traffic-light-emoji { font-size: 2.4rem; line-height: 1; }
.traffic-light-headline { font-size: 1.35rem; font-weight: 700; color: #2b2822; }
.stButton > button, .stDownloadButton > button {
    min-height: """ + button_height + """;
    font-size: """ + body_size + """;
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
div[data-baseweb="select"] { min-height: """ + button_height + """; font-size: """ + body_size + """; }
input[type="text"] { min-height: """ + button_height + """; font-size: """ + body_size + """ !important; }
div[data-testid="stTabs"] button[data-baseweb="tab"] {
    font-size: """ + body_size + """;
    font-weight: 700;
    min-height: """ + button_height + """;
    padding: 8px 16px;
    white-space: nowrap;
}
div[data-testid="stTabs"] [data-testid="stMarkdownContainer"] p { font-size: """ + body_size + """; font-weight: 700; }
div[data-testid="stTabs"] { overflow-x: auto; }
@media (max-width: 640px) {
    div[data-testid="stTabs"] div[data-baseweb="tab-list"] { gap: 2px; }
    div[data-testid="stTabs"] button[data-baseweb="tab"] { padding: 8px 10px; }
}
.explain-card {
    background: #faf8f2;
    border: 1px solid #e6ddc8;
    border-left: 5px solid """ + COLORS["accent"] + """;
    border-radius: 12px;
    padding: 14px 16px;
    margin-bottom: 12px;
}
.explain-card b { color: #2b2822; }
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


# 顏色以外還有形狀差異（打勾／警告三角／禁止），紅綠色盲的人也能一眼分辨，不是純靠顏色。
TRAFFIC_LIGHT_EMOJI = {"green": "✅", "yellow": "⚠️", "red": "⛔"}
