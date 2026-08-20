"""
全域設定：色票、快取時間、字級常數、外部資料來源網址。
純常數與設定值，不含任何邏輯，方便日後調整不用動到其他模組。
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# 色票（紅漲綠跌，台股慣例，貫穿所有圖表與元件）
# ---------------------------------------------------------------------------
COLORS = {
    "text": "#2b2822",
    "subtext": "#6b6353",
    "grid": "#ece6d8",
    "accent": "#1d3557",       # 收盤價主線（深藏青，取代原本的科技藍，更有金融穩重感）
    "ma20": "#f59e0b",         # 月線
    "ma60": "#8b5cf6",         # 季線
    "up": "#e5484d",           # 漲／買超（台股慣例：紅漲）
    "down": "#12b76a",         # 跌／賣超（台股慣例：綠跌）
    "k_line": "#1d3557",
    "d_line": "#f59e0b",
    "overbought_zone": "rgba(229, 72, 77, 0.07)",
    "oversold_zone": "rgba(18, 183, 106, 0.07)",
    "foreign": "#1d3557",
    "trust": "#f59e0b",
    "dealer": "#8b5cf6",
    "green_light": "#12b76a",
    "yellow_light": "#f59e0b",
    "red_light": "#e5484d",
}

# ---------------------------------------------------------------------------
# 快取時間（全部走 st.cache_data，雲端友善，不寫本機檔案）
# ---------------------------------------------------------------------------
CACHE_TTL_PRICE = 3600            # 股價：1 小時
CACHE_TTL_STOCK_NAME = 3600       # 個股中英文名稱：1 小時
CACHE_TTL_TICKER_MAP = 7 * 24 * 3600   # 代號<->中文名對照表：7 天
CACHE_TTL_NEWS = 1800              # 新聞：30 分鐘
CACHE_TTL_CHIP_DAY = 24 * 3600     # 三大法人單日資料：1 天（同一天資料不會變）
CACHE_TTL_FUNDAMENTALS = 6 * 3600  # 獲利／股利基本面資料：6 小時（更新不頻繁）

# ---------------------------------------------------------------------------
# 高齡友善介面：字級／按鈕常數（供 styles.py 的 CSS 套用）
# ---------------------------------------------------------------------------
FONT_SIZE_TITLE = "30px"
FONT_SIZE_SUBTITLE = "22px"
FONT_SIZE_BODY = "19px"
FONT_SIZE_CAPTION = "16px"
BUTTON_MIN_HEIGHT = "56px"

# 「字體再放大」模式：使用者主動切換後套用的加大字級，約比預設大 25%
FONT_SIZE_TITLE_LARGE = "37px"
FONT_SIZE_SUBTITLE_LARGE = "27px"
FONT_SIZE_BODY_LARGE = "24px"
FONT_SIZE_CAPTION_LARGE = "20px"
BUTTON_MIN_HEIGHT_LARGE = "64px"

# ---------------------------------------------------------------------------
# 外部資料來源
# ---------------------------------------------------------------------------
TWSE_T86_URL = "https://www.twse.com.tw/rwd/zh/fund/T86"
TWSE_ISIN_URLS = {
    "上市": "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2",
    "上櫃": "https://isin.twse.com.tw/isin/C_public.jsp?strMode=4",
}
# 股價日 K：改用官方資料源（原本用 yfinance/Yahoo Finance，在 Streamlit Cloud
# 這類共用 IP 的雲端主機上常被 Yahoo 判定為異常流量而擋掉，改走證交所自家 API）。
TWSE_STOCK_DAY_URL = "https://www.twse.com.tw/exchangeReport/STOCK_DAY"
# 上櫃（TPEx）股票的補充來源：TPEx 官方的歷史區間查詢 API 已經下架（固定被導向錯誤頁），
# 新版 OpenAPI 只有當日快照、無法查歷史區間，所以上櫃股票改用 FinMind
# （台灣開發者社群長期使用的開放資料整合平台，非政府單位，但同時彙整證交所與櫃買中心資料，
# 免費額度供合理使用，不需要 API 金鑰）。
FINMIND_API_URL = "https://api.finmindtrade.com/api/v4/data"

# 近期查詢預設區間（天數）與可選的快速區間按鈕
DEFAULT_RANGE_DAYS = 182  # 近六個月
RANGE_PRESETS = {
    "近 1 個月": 30,
    "近 3 個月": 91,
    "近 6 個月": 182,
    "近 1 年": 365,
}
