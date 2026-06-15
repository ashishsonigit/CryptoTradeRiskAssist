# ================= ui_regime.py =================
import streamlit as st
from ui_components import (
    metric_with_explanation,
    inject_css,
    inject_layout_css
)


def render_regime_ui(regime):
    inject_layout_css()
    inject_css()
    st.title("🌐 Market Regime Engine")

    if regime is None:
        st.info("No regime data available.")
        return

    # ---------------------------------------------------------
    # 1. CORE SCORES
    # ---------------------------------------------------------
    st.subheader("1. Regime Component Scores")

    c1, c2, c3 = st.columns(3)

    with c1:
        metric_with_explanation(
            "Trend Score",
            f"{regime.trend_score:.2f}",
            "Directional strength of the market.",
            "Derived from MA slopes, price structure, and trend filters."
        )

    with c2:
        metric_with_explanation(
            "Volatility Score",
            f"{regime.volatility_score:.2f}",
            "Market stability vs turbulence.",
            "Computed from ATR, realized volatility, and compression."
        )

    with c3:
        metric_with_explanation(
            "Breadth Score",
            f"{regime.breadth_score:.2f}",
            "Participation across assets.",
            "Based on % of assets above key moving averages."
        )

    st.markdown("---")

    # ---------------------------------------------------------
    # 2. LIQUIDITY + MACRO + COMPOSITE
    # ---------------------------------------------------------
    st.subheader("2. Liquidity, Macro & Composite Risk")

    c4, c5, c6 = st.columns(3)

    with c4:
        metric_with_explanation(
            "Liquidity Score",
            f"{regime.liquidity_score:.2f}",
            "Capital inflows/outflows.",
            "Derived from ETF flows, stablecoin supply, and exchange liquidity."
        )

    with c5:
        metric_with_explanation(
            "Macro Score",
            f"{regime.macro_score:.2f}",
            "Macro environment.",
            "Based on rates, inflation, and risk‑on/off indicators."
        )

    with c6:
        metric_with_explanation(
            "Market Risk Score",
            f"{regime.market_risk_score:.2f}",
            "Composite of all components.",
            (
                "Market Risk Score = Weighted sum of:\n"
                "- Trend\n- Volatility\n- Breadth\n- Liquidity\n- Macro"
            )
        )

    st.markdown("---")

    # ---------------------------------------------------------
    # 3. MODE + MULTIPLIER
    # ---------------------------------------------------------
    st.subheader("3. Regime Mode & Risk Multiplier")

    c7, c8 = st.columns(2)

    with c7:
        metric_with_explanation(
            "Regime Mode",
            regime.market_risk_mode,
            "Qualitative environment label.",
            (
                "Mode is derived from Market Risk Score thresholds:\n"
                "- Hostile\n- Defensive\n- Neutral\n- Constructive\n- Aggressive"
            )
        )

    with c8:
        metric_with_explanation(
            "Regime Multiplier",
            f"{regime.market_risk_multiplier:.2f}",
            "Scales your risk based on regime.",
            (
                "Final Risk = Trade Performance Risk × Regime Multiplier\n\n"
                "Multiplier < 1 → Reduce risk\n"
                "Multiplier = 1 → Neutral\n"
                "Multiplier > 1 → Increase risk"
            )
        )

    st.markdown("---")

    # ---------------------------------------------------------
    # 4. RAW DATA
    # ---------------------------------------------------------
    with st.expander("Show Raw Regime Data"):
        st.json({
            "trend_score": regime.trend_score,
            "volatility_score": regime.volatility_score,
            "breadth_score": regime.breadth_score,
            "liquidity_score": regime.liquidity_score,
            "macro_score": regime.macro_score,
            "market_risk_score": regime.market_risk_score,
            "market_risk_mode": regime.market_risk_mode,
            "market_risk_multiplier": regime.market_risk_multiplier,
        })
