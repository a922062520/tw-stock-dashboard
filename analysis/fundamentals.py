"""把 data/fundamentals.py 抓回來的原始資料，摘要成給 UI 用的結構化資訊。
只回傳代碼與數值，白話文字統一交給 explain/texts.py。"""

from __future__ import annotations

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
        return {"has_dividend": False, "by_year": {}, "recent_total": None, "latest_year": None, "years_covered": 0}

    by_year_full = dividends.groupby(dividends.index.year).sum()
    by_year_full = by_year_full.sort_index(ascending=False)
    recent = by_year_full.head(years)

    return {
        "has_dividend": True,
        "by_year": {int(year): float(amount) for year, amount in recent.items()},
        "recent_total": float(recent.iloc[0]) if len(recent) else None,
        "latest_year": int(recent.index[0]) if len(recent) else None,
        "years_covered": len(by_year_full),
    }
