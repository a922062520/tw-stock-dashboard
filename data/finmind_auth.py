"""FinMind API 金鑰（可選）。註冊免費帳號可以拿到 token，加進請求可以降低被限流的風險；
沒有設定 token 的話就維持原本的匿名呼叫，不影響功能——本機開發環境通常不會有
.streamlit/secrets.toml，這裡要能安全地退回 None，不能讓程式炸掉。
"""

from __future__ import annotations

import streamlit as st


def get_finmind_token() -> str | None:
    try:
        return st.secrets.get("FINMIND_TOKEN") or None
    except Exception:
        return None
