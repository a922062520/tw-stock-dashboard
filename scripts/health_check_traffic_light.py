"""
燈號健檢腳本（離線診斷用，不是 app 的一部分，app.py 不會 import 這裡）。

目的：實際跑一遍 analysis/conclusion.py 的紅黃綠燈邏輯，套用在一批常見台股上，
看看：
1. 綠燈實際上多常會亮（懷疑條件太嚴，幾乎不會出現）
2. 紅燈是不是常常出現在盤整／下跌股（懷疑「追高風險大」的措辭套用在明明沒有在漲的股票上）

只做觀察與統計，不會改動任何邏輯或程式碼。用法：
    python scripts/health_check_traffic_light.py
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analysis.conclusion import build_analysis_conclusion, classify_traffic_light  # noqa: E402
from analysis.indicators import add_moving_averages, compute_atr  # noqa: E402
from analysis.metrics import compute_return_risk  # noqa: E402
from data.stock_data import fetch_price  # noqa: E402

# 涵蓋範圍盡量廣：權值科技股、金融股、傳產、內需、航運、營建，以及幾檔上櫃股，
# 好壞股（漲多的、盤整的、跌深的）都要有，才能看出燈號邏輯在不同情境下的表現。
STOCK_CODES = [
    # 科技權值
    "2330", "2317", "2454", "2382", "2308", "3711", "2379", "2357", "3034",
    "2303", "3037", "2377", "6669", "3231", "2356", "2327", "2408", "2409",
    # 金融
    "2881", "2882", "2884", "2885", "2886", "2887", "2891", "2892", "2880",
    "2801", "5880", "2883", "2890", "2812",
    # 傳產／原物料
    "1301", "1303", "1326", "2002", "1101", "1102", "2105", "9910", "1216",
    "1210", "2912", "2201", "2207", "9904",
    # 電信
    "4904", "3045",
    # 內需消費
    "2915", "9945", "8454", "2731",
    # 航運
    "2603", "2609", "2615",
    # 營建
    "2542", "5522",
    # 上櫃（測試 FinMind 價格 fallback 路徑）
    "6488", "5347", "8299", "3324", "4966", "3661", "6547",
    # 生技
    "1789", "6446",
]


def evaluate(stock_code: str, start: date, end: date) -> dict | None:
    price_df, _ = fetch_price(stock_code, start, end)
    if price_df is None or price_df.empty or len(price_df) < 60:
        return None

    price_df = add_moving_averages(price_df)
    price_df["ATR14"] = compute_atr(price_df)

    metrics = compute_return_risk(price_df["Close"])
    if metrics is None:
        return None
    annual_return, annual_vol, daily_ret = metrics

    concl = build_analysis_conclusion(price_df, annual_return, annual_vol, daily_ret)
    light_info = classify_traffic_light(concl)

    return {
        "code": stock_code,
        "light": light_info["light"],
        "reason_kind": light_info["reason_kind"],
        "risk_lvl": concl["risk_lvl"],
        "horizon": concl["horizon"],
        "trend_strength": concl["trend_strength"],
        "entry_gap_pct": concl["entry_gap_pct"],
        "annual_vol": annual_vol,
    }


def main():
    end = date.today()
    start = end - timedelta(days=210)  # 約7個月，確保 MA60 有足夠資料熱機

    results = []
    failed = []
    for i, code in enumerate(STOCK_CODES, 1):
        print(f"[{i}/{len(STOCK_CODES)}] {code} ...", flush=True)
        try:
            r = evaluate(code, start, end)
        except Exception as e:
            r = None
            print(f"    錯誤：{type(e).__name__} - {e}")
        if r is None:
            failed.append(code)
        else:
            results.append(r)

    print("\n" + "=" * 60)
    print(f"樣本數：{len(STOCK_CODES)}　成功：{len(results)}　失敗（查無資料）：{len(failed)}")
    if failed:
        print(f"失敗清單：{', '.join(failed)}")

    counts = {"red": 0, "yellow": 0, "green": 0}
    for r in results:
        counts[r["light"]] += 1
    total = len(results) or 1
    print("\n【燈號分布】")
    for light, label in [("red", "紅燈"), ("yellow", "黃燈"), ("green", "綠燈")]:
        n = counts[light]
        print(f"  {label}：{n} 檔（{n/total*100:.1f}%）")

    print("\n【紅燈原因細分】")
    red_reasons = {}
    for r in results:
        if r["light"] == "red":
            red_reasons.setdefault(r["reason_kind"], []).append(r)
    for reason, items in red_reasons.items():
        print(f"  {reason}：{len(items)} 檔")

    overheated = red_reasons.get("overheated", [])
    if overheated:
        declining_or_flat = [r for r in overheated if r["trend_strength"] is not None and r["trend_strength"] <= 0]
        print(
            f"\n【紅燈細查】reason=overheated（措辭是「追高風險大」）共 {len(overheated)} 檔，"
            f"其中月線在季線之下或持平（並非真的在漲）有 {len(declining_or_flat)} 檔"
            f"（{len(declining_or_flat)/len(overheated)*100:.1f}%）："
        )
        for r in declining_or_flat:
            print(
                f"    {r['code']}：trend_strength={r['trend_strength']*100:+.1f}%　"
                f"entry_gap_pct={r['entry_gap_pct']*100:+.1f}%　annual_vol={r['annual_vol']*100:.1f}%"
            )

    print("\n【黃燈原因細分】")
    yellow_reasons = {}
    for r in results:
        if r["light"] == "yellow":
            yellow_reasons.setdefault(r["reason_kind"], []).append(r)
    for reason, items in yellow_reasons.items():
        print(f"  {reason}：{len(items)} 檔")

    green = [r for r in results if r["light"] == "green"]
    print(f"\n【綠燈明細】共 {len(green)} 檔" + ("（沒有任何一檔亮綠燈）" if not green else "："))
    for r in green:
        print(
            f"    {r['code']}：annual_vol={r['annual_vol']*100:.1f}%　"
            f"trend_strength={r['trend_strength']*100:+.1f}%　entry_gap_pct={r['entry_gap_pct']*100:+.1f}%"
        )

    print("\n【完整明細】")
    print(f"{'代號':<6}{'燈號':<6}{'原因':<12}{'風險':<6}{'週期':<10}{'趨勢強度':>10}{'進場缺口':>10}{'年化波動':>10}")
    for r in sorted(results, key=lambda x: x["code"]):
        ts = f"{r['trend_strength']*100:+.1f}%" if r["trend_strength"] is not None else "N/A"
        print(
            f"{r['code']:<6}{r['light']:<6}{r['reason_kind']:<12}{r['risk_lvl']:<6}{r['horizon']:<10}"
            f"{ts:>10}{r['entry_gap_pct']*100:>9.1f}%{r['annual_vol']*100:>9.1f}%"
        )


if __name__ == "__main__":
    main()
