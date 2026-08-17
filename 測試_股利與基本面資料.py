"""
【第二階段前置測試，獨立腳本，不併入主程式 app.py】

目的：確認 yfinance 對台股「股利」與「公司基本面」資料的覆蓋率與品質，
作為之後要不要加股利／基本面功能、要不要換資料來源的判斷依據。

用法：
    在專案資料夾下，用跟 app.py 一樣的 Python 環境執行：
        python3 測試_股利與基本面資料.py
    （雙擊啟動器建立的 venv 裡就有 yfinance，可以先啟動一次儀表板讓 venv 建好，
    再用「終端機／命令提示字元」切到這個資料夾，啟用 venv 後執行這支腳本。）

    這支腳本需要連網（連 Yahoo Finance），執行結果會印在畫面上，
    請把整段輸出複製給我，我會依照結果決定第二階段的資料來源與做法。

測試對象：2330 台積電（權值股、現金股利為主）、2412 中華電（高股息、股利穩定）、
2327 國巨（曾經配過股票股利，適合測試「配股」資料）。
"""

from __future__ import annotations

import traceback
from datetime import date, timedelta

import yfinance as yf

TEST_CODES = ["2330", "2412", "2327"]


def resolve_ticker(code: str) -> str:
    """跟 app.py 的 fetch_price 一樣，先試 .TW 再試 .TWO。"""
    for suffix in (".TW", ".TWO"):
        ticker = f"{code}{suffix}"
        try:
            df = yf.Ticker(ticker).history(period="5d")
            if df is not None and not df.empty:
                return ticker
        except Exception:
            continue
    return f"{code}.TW"


def section(title: str) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def test_cash_dividends(t: yf.Ticker, ticker: str) -> None:
    section(f"[{ticker}] 1. 現金股利歷史紀錄 (.dividends)")
    try:
        div = t.dividends
        if div is None or div.empty:
            print("結果：抓不到任何現金股利紀錄（.dividends 是空的）")
            return
        years = sorted(set(div.index.year))
        print(f"結果：抓到 {len(div)} 筆紀錄，涵蓋年度：{years[0]} ~ {years[-1]}（共 {len(years)} 個年度）")
        print("最近 5 筆：")
        print(div.tail(5))
    except Exception:
        print("發生錯誤：")
        traceback.print_exc()


def test_stock_dividends(t: yf.Ticker, ticker: str) -> None:
    section(f"[{ticker}] 2. 股票股利／配股資料")
    try:
        actions = t.actions
        print("t.actions（包含 Dividends 與 Stock Splits 兩欄，yfinance 對台股配股通常會放在 Stock Splits 欄位）：")
        if actions is None or actions.empty:
            print("結果：t.actions 是空的")
        else:
            print(actions.tail(10))
            if "Stock Splits" in actions.columns:
                nonzero_splits = actions[actions["Stock Splits"] != 0]
                if nonzero_splits.empty:
                    print("觀察：Stock Splits 欄位裡沒有非零紀錄，代表這段期間 yfinance 沒有回報任何配股／分割事件。")
                else:
                    print("觀察：以下日期有非零的 Stock Splits 紀錄（需要人工確認這是不是真的配股）：")
                    print(nonzero_splits)
    except Exception:
        print("發生錯誤：")
        traceback.print_exc()

    try:
        splits = t.splits
        print("\nt.splits 原始資料：")
        print("（空）" if splits is None or splits.empty else splits.tail(10))
    except Exception:
        print("t.splits 發生錯誤：")
        traceback.print_exc()


def test_fundamentals(t: yf.Ticker, ticker: str) -> None:
    section(f"[{ticker}] 3. 基本面欄位 (.info)：EPS／營收／本益比")
    wanted_fields = [
        "trailingEps",
        "forwardEps",
        "totalRevenue",
        "revenueGrowth",
        "trailingPE",
        "forwardPE",
        "priceToBook",
        "dividendYield",
        "dividendRate",
        "payoutRatio",
        "trailingAnnualDividendYield",
        "trailingAnnualDividendRate",
    ]
    try:
        info = t.info
        if not info:
            print("結果：.info 抓不到任何資料（可能是這檔股票 Yahoo Finance 沒有基本面頁面，或當下被限流）")
            return
        available = {k: info.get(k) for k in wanted_fields if info.get(k) is not None}
        missing = [k for k in wanted_fields if info.get(k) is None]
        print(f"抓得到的欄位（共 {len(available)} / {len(wanted_fields)}）：")
        for k, v in available.items():
            print(f"  {k}: {v}")
        if missing:
            print(f"抓不到（值是 None 或欄位不存在）：{missing}")
    except Exception:
        print("發生錯誤：")
        traceback.print_exc()


def test_ex_dividend_gap(t: yf.Ticker, ticker: str) -> None:
    section(f"[{ticker}] 4. 除權息造成的股價跳空（auto_adjust=False vs True 對照）")
    try:
        div = t.dividends
        if div is None or div.empty:
            print("結果：這檔股票近期沒有股利紀錄，略過跳空測試。")
            return
        last_ex_date = div.index[-1].date()
        start = last_ex_date - timedelta(days=10)
        end = last_ex_date + timedelta(days=10)
        print(f"最近一次除息日：{last_ex_date}，抓取前後各 10 天做比較")

        df_raw = yf.download(ticker, start=start, end=end, auto_adjust=False, progress=False)
        df_adj = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
        for df in (df_raw, df_adj):
            if isinstance(df.columns, __import__("pandas").MultiIndex):
                df.columns = df.columns.get_level_values(0)

        print("\nauto_adjust=False（原始收盤價，除息當天會有明顯跳空）：")
        print(df_raw[["Close"]] if not df_raw.empty else "（抓不到資料）")
        print("\nauto_adjust=True（還原後收盤價，跳空會被平滑掉）：")
        print(df_adj[["Close"]] if not df_adj.empty else "（抓不到資料）")
        print(
            "\n判斷建議：若要用 auto_adjust=False 的原始股價算長期報酬率，"
            "除權息當天的跳空會讓報酬率被低估，需要額外用股利資料把報酬率補回來；"
            "若簡單起見，也可以只在「算報酬率」這件事上另外抓 auto_adjust=True 的還原股價，"
            "但 K 線圖顯示還是維持 auto_adjust=False（跟看盤軟體一致）。"
        )
    except Exception:
        print("發生錯誤：")
        traceback.print_exc()


def main() -> None:
    print(f"執行時間：{date.today().isoformat()}")
    print(f"測試對象：{', '.join(TEST_CODES)}")
    for code in TEST_CODES:
        ticker_str = resolve_ticker(code)
        print(f"\n\n######## {code} -> 使用代碼 {ticker_str} ########")
        t = yf.Ticker(ticker_str)
        test_cash_dividends(t, ticker_str)
        test_stock_dividends(t, ticker_str)
        test_fundamentals(t, ticker_str)
        test_ex_dividend_gap(t, ticker_str)

    print("\n\n測試結束，請把以上完整輸出複製回報，會用來決定第二階段的資料來源與做法。")


if __name__ == "__main__":
    main()
