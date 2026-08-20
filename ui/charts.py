"""K 線圖、RSI 圖、KD 圖、三大法人籌碼圖。圖表邏輯與計算方式原樣保留，只調整成可重複呼叫的函式。"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from config import COLORS


def get_missing_dates(index: pd.DatetimeIndex):
    """算出「有交易資料的日期範圍」內實際缺席的日子（週末、國定假日等），
    餵給 Plotly 的 rangebreaks 用來跳過，讓 K 線圖不會因為假日而斷開、比較有連貫性。
    直接用實際抓到的交易日反推缺席日期，不用額外維護假日清單。"""
    if len(index) == 0:
        return []
    all_days = pd.date_range(start=index.min(), end=index.max(), freq="D")
    return all_days.difference(index)


def base_layout(height: int, showlegend: bool = True) -> dict:
    return dict(
        height=height,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Noto Sans TC, -apple-system, sans-serif", color=COLORS["text"], size=14),
        hovermode="x unified",
        showlegend=showlegend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=13)),
    )


def render_price_chart(price_df: pd.DataFrame):
    """K 線 ＋ MA20/MA60 ＋ 成交量子圖。平板上關掉 rangeslider、簡化 modebar，避免誤觸。
    保留 on_select="rerun" 點選功能，但呼叫端不能把它當成唯一入口（另外提供日期下拉選單）。"""
    close_diff = price_df["Close"].diff().fillna(0)
    vol_colors = [COLORS["up"] if v >= 0 else COLORS["down"] for v in close_diff]
    missing_dates = get_missing_dates(price_df.index)

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.68, 0.32], vertical_spacing=0.05)
    fig.add_trace(
        go.Candlestick(
            x=price_df.index,
            open=price_df["Open"],
            high=price_df["High"],
            low=price_df["Low"],
            close=price_df["Close"],
            name="K線",
            increasing_line_color=COLORS["up"],
            increasing_fillcolor=COLORS["up"],
            decreasing_line_color=COLORS["down"],
            decreasing_fillcolor=COLORS["down"],
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=price_df.index, y=price_df["MA20"], name="月線 MA20",
            line=dict(color=COLORS["ma20"], width=1.6),
            hovertemplate="MA20 %{y:.2f}<extra></extra>",
        ),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=price_df.index, y=price_df["MA60"], name="季線 MA60",
            line=dict(color=COLORS["ma60"], width=1.6),
            hovertemplate="MA60 %{y:.2f}<extra></extra>",
        ),
        row=1, col=1,
    )
    fig.add_trace(
        go.Bar(
            x=price_df.index, y=price_df["Volume"], name="成交量",
            marker_color=vol_colors, marker_line_width=0,
            hovertemplate="成交量 %{y:,.0f} 張<extra></extra>",
        ),
        row=2, col=1,
    )
    fig.update_layout(**base_layout(height=520))
    fig.update_xaxes(showgrid=False, rangeslider_visible=False, rangebreaks=[dict(values=missing_dates)], row=1, col=1)
    fig.update_xaxes(gridcolor=COLORS["grid"], rangebreaks=[dict(values=missing_dates)], row=2, col=1)
    fig.update_yaxes(gridcolor=COLORS["grid"], row=1, col=1)
    fig.update_yaxes(gridcolor=COLORS["grid"], row=2, col=1)

    return st.plotly_chart(
        fig,
        use_container_width=True,
        config={"displayModeBar": False, "scrollZoom": False},
        key="price_chart",
        on_select="rerun",
        selection_mode="points",
    )


def render_rsi_chart(price_df: pd.DataFrame, missing_dates) -> None:
    fig = go.Figure()
    fig.add_hrect(y0=70, y1=100, fillcolor=COLORS["overbought_zone"], line_width=0)
    fig.add_hrect(y0=0, y1=30, fillcolor=COLORS["oversold_zone"], line_width=0)
    fig.add_trace(
        go.Scatter(
            x=price_df.index, y=price_df["RSI"], name="RSI",
            line=dict(color=COLORS["accent"], width=2),
            hovertemplate="RSI %{y:.1f}<extra></extra>",
        )
    )
    fig.add_hline(y=70, line_dash="dot", line_width=1, line_color=COLORS["up"])
    fig.add_hline(y=30, line_dash="dot", line_width=1, line_color=COLORS["down"])
    fig.update_layout(**base_layout(height=260, showlegend=False))
    fig.update_yaxes(range=[0, 100], gridcolor=COLORS["grid"])
    fig.update_xaxes(gridcolor=COLORS["grid"], rangebreaks=[dict(values=missing_dates)])
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def render_kd_chart(price_df: pd.DataFrame, missing_dates) -> None:
    fig = go.Figure()
    fig.add_hrect(y0=80, y1=100, fillcolor=COLORS["overbought_zone"], line_width=0)
    fig.add_hrect(y0=0, y1=20, fillcolor=COLORS["oversold_zone"], line_width=0)
    fig.add_trace(
        go.Scatter(
            x=price_df.index, y=price_df["K"], name="K",
            line=dict(color=COLORS["k_line"], width=2),
            hovertemplate="K %{y:.1f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=price_df.index, y=price_df["D"], name="D",
            line=dict(color=COLORS["d_line"], width=2),
            hovertemplate="D %{y:.1f}<extra></extra>",
        )
    )
    fig.add_hline(y=80, line_dash="dot", line_width=1, line_color=COLORS["up"])
    fig.add_hline(y=20, line_dash="dot", line_width=1, line_color=COLORS["down"])
    fig.update_layout(**base_layout(height=280))
    fig.update_yaxes(range=[0, 100], gridcolor=COLORS["grid"])
    fig.update_xaxes(gridcolor=COLORS["grid"], rangebreaks=[dict(values=missing_dates)])
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


_COMPARE_LINE_COLORS = [COLORS["accent"], COLORS["up"], COLORS["ma60"], COLORS["ma20"]]


def render_compare_chart(price_dfs: dict, labels: dict) -> None:
    """多檔股票比較：各自從查詢區間第一天換算成「累積漲跌幅（%）」再疊在同一張圖，
    這樣不同股價level的股票（例如一檔20元、一檔900元）才能放在同一個Y軸上比較。"""
    fig = go.Figure()
    all_missing = set()
    for i, (code, df) in enumerate(price_dfs.items()):
        if df is None or df.empty:
            continue
        base = float(df["Close"].iloc[0])
        pct_change = (df["Close"] / base - 1) * 100
        label = labels.get(code, code)
        fig.add_trace(
            go.Scatter(
                x=df.index, y=pct_change, name=f"{code} {label}".strip(),
                line=dict(color=_COMPARE_LINE_COLORS[i % len(_COMPARE_LINE_COLORS)], width=2.2),
                hovertemplate="%{y:+.1f}%<extra>" + f"{code} {label}".strip() + "</extra>",
            )
        )
        all_missing.update(get_missing_dates(df.index))

    fig.add_hline(y=0, line_width=1, line_color="#cbd5e1")
    fig.update_layout(**base_layout(height=380))
    fig.update_yaxes(gridcolor=COLORS["grid"], ticksuffix="%")
    fig.update_xaxes(gridcolor=COLORS["grid"], rangebreaks=[dict(values=sorted(all_missing))])
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def render_chip_chart(chip_df: pd.DataFrame) -> None:
    fig = go.Figure()
    for col, color in [
        ("外資買賣超", COLORS["foreign"]),
        ("投信買賣超", COLORS["trust"]),
        ("自營商買賣超", COLORS["dealer"]),
    ]:
        if col in chip_df.columns:
            fig.add_trace(
                go.Bar(
                    x=chip_df.index, y=chip_df[col], name=col,
                    marker_color=color, marker_line_width=0,
                    hovertemplate=f"{col} %{{y:,.0f}} 張<extra></extra>",
                )
            )
    fig.add_hline(y=0, line_width=1, line_color="#cbd5e1")
    fig.update_layout(**base_layout(height=320), barmode="relative")
    fig.update_yaxes(gridcolor=COLORS["grid"])
    missing_dates = get_missing_dates(chip_df.index)
    fig.update_xaxes(gridcolor=COLORS["grid"], rangebreaks=[dict(values=missing_dates)])
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
