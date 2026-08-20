"""把 data/fundamentals.py 抓回來的原始資料，摘要成給 UI 用的結構化資訊。
只回傳代碼與數值，白話文字統一交給 explain/texts.py。"""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd


def summarize_profit(info: dict) -> dict:
    eps = info.get("trailingEps")
    if eps is None:
        status = "unknown"
    elif eps > 0:
        status = "profit"
    elif eps < 0:
        status = "loss"
    else:
        status = "breakeven"
    return {
        "status": status,
        "eps": eps,
        "revenue": info.get("totalRevenue"),
        "profit_margin": info.get("profitMargins"),
    }


def summarize_dividends(dividends: pd.Series | None, years: int = 5) -> dict:
    if dividends is None or dividends.empty:
        return {
            "has_dividend": False,
            "by_year": {},
            "recent_total": None,
            "latest_year": None,
            "years_covered": 0,
            "ttm_total": None,
            "consecutive_years": 0,
        }

    by_year_full = dividends.groupby(dividends.index.year).sum()
    by_year_full = by_year_full.sort_index(ascending=False)
    recent = by_year_full.head(years)

    # 近一年殖利率用「近12個月」滾動加總，比單看今年（可能還沒發完）或去年（可能已經過時）準確。
    cutoff = pd.Timestamp(datetime.now() - timedelta(days=365))
    ttm_total = float(dividends[dividends.index >= cutoff].sum())

    # 連續配息年數：從資料裡最新的年度往前數，中間只要斷過一年（該年度加總為0或缺資料）就停止。
    consecutive_years = 0
    expected_year = None
    for year, amount in by_year_full.items():
        year = int(year)
        if amount <= 0 or (expected_year is not None and year != expected_year):
            break
        consecutive_years += 1
        expected_year = year - 1

    return {
        "has_dividend": True,
        "by_year": {int(year): float(amount) for year, amount in recent.items()},
        "recent_total": float(recent.iloc[0]) if len(recent) else None,
        "latest_year": int(recent.index[0]) if len(recent) else None,
        "years_covered": len(by_year_full),
        "ttm_total": ttm_total,
        "consecutive_years": consecutive_years,
    }


def summarize_valuation(close_now: float, profit_summary: dict, dividend_summary: dict) -> dict:
    """殖利率／本益比／連續配息年數——存股族最常用的三個數字，資料都已經抓回來了，
    只是沒有相乘。全部用「目前股價」當分母，不是嚴謹的財報估值，僅供參考。"""
    eps = profit_summary.get("eps")
    pe_ratio = (close_now / eps) if (eps and eps > 0 and close_now) else None

    ttm_total = dividend_summary.get("ttm_total")
    dividend_yield = (ttm_total / close_now) if (ttm_total and close_now) else None

    by_year = dividend_summary.get("by_year") or {}
    avg_yield_5y = (sum(by_year.values()) / len(by_year) / close_now) if (by_year and close_now) else None

    return {
        "available": pe_ratio is not None or dividend_yield is not None,
        "pe_ratio": pe_ratio,
        "dividend_yield": dividend_yield,
        "avg_yield_5y": avg_yield_5y,
        "avg_yield_years": len(by_year),
        "consecutive_years": dividend_summary.get("consecutive_years", 0),
    }
