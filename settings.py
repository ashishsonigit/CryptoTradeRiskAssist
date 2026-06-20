# ================= settings.py =================
import streamlit as st

from storage import get_current_balance, load_trades, reset_performance_history


def render_settings():
    st.title("Settings & Configuration")

    st.subheader("Account Balance")
    st.session_state["initial_balance"] = st.number_input(
        "Initial Balance",
        min_value=100.0,
        value=float(st.session_state.get("initial_balance", 10000.0)),
        step=100.0,
    )
    st.session_state["balance"] = get_current_balance(load_trades(), st.session_state["initial_balance"])
    st.metric("Current Balance", f"${st.session_state['balance']:,.2f}")

    st.markdown("---")

    # ---------------------------------------------------------
    # RISK ENGINE TYPE
    # ---------------------------------------------------------
    st.subheader("Risk Engine Type")

    st.session_state["risk_engine_type"] = st.selectbox(
        "Select Risk Engine Mode",
        ["Aggressive", "Moderate", "Conservative"],
        index=["Aggressive", "Moderate", "Conservative"].index(
            st.session_state.get("risk_engine_type", "Moderate")
        ),
    )

    # ---------------------------------------------------------
    # BASE RISK %
    # ---------------------------------------------------------
    st.subheader("Base Risk %")

    st.session_state["base_risk_pct"] = st.number_input(
        "Base Risk %",
        min_value=0.1,
        max_value=5.0,
        value=float(st.session_state.get("base_risk_pct", 1.0)),
        step=0.1,
    )

    st.markdown("---")

    # ---------------------------------------------------------
    # PERFORMANCE LAYER CONFIG
    # ---------------------------------------------------------
    st.subheader("Performance Layer Configuration")

    st.session_state["winrate_short"] = st.number_input(
        "Winrate Short Window", 5, 50, int(st.session_state.get("winrate_short", 20))
    )
    st.session_state["winrate_long"] = st.number_input(
        "Winrate Long Window", 20, 200, int(st.session_state.get("winrate_long", 50))
    )
    st.session_state["pnl_recent"] = st.number_input(
        "PnL Recent Window", 5, 50, int(st.session_state.get("pnl_recent", 20))
    )
    st.session_state["pnl_long"] = st.number_input(
        "PnL Long Window", 20, 200, int(st.session_state.get("pnl_long", 50))
    )

    st.markdown("### Sensitivity Coefficients")

    st.session_state["coef_a"] = st.number_input(
        "Loss Streak Penalty (a)", 1.0, 20.0, float(st.session_state.get("coef_a", 8.0))
    )
    st.session_state["coef_k"] = st.number_input(
        "PnL Trend Sensitivity (k)", 0.1, 2.0, float(st.session_state.get("coef_k", 0.5))
    )
    st.session_state["coef_m"] = st.number_input(
        "Expectancy Sensitivity (m)", 10.0, 100.0, float(st.session_state.get("coef_m", 50.0))
    )

    st.markdown("### P-Score Weights")

    st.session_state["w_winrate"] = st.slider(
        "Winrate Weight", 0.0, 1.0, float(st.session_state.get("w_winrate", 0.25))
    )
    st.session_state["w_streak"] = st.slider(
        "Loss Streak Weight", 0.0, 1.0, float(st.session_state.get("w_streak", 0.15))
    )
    st.session_state["w_pnl"] = st.slider(
        "PnL Trend Weight", 0.0, 1.0, float(st.session_state.get("w_pnl", 0.20))
    )
    st.session_state["w_quality"] = st.slider(
        "Trade Quality Weight", 0.0, 1.0, float(st.session_state.get("w_quality", 0.20))
    )
    st.session_state["w_expectancy"] = st.slider(
        "Expectancy Weight", 0.0, 1.0, float(st.session_state.get("w_expectancy", 0.20))
    )

    st.markdown("---")

    # ---------------------------------------------------------
    # MARKET LAYER CONFIG
    # ---------------------------------------------------------
    st.subheader("Market Layer Configuration")
    st.markdown("#### Block Weights")

    st.session_state["m_w_price"] = st.slider(
        "Price Structure & Volatility Weight",
        0.0,
        1.0,
        float(st.session_state.get("m_w_price", 0.30)),
    )
    st.session_state["m_w_macro"] = st.slider(
        "Macro & Cross-Asset Weight",
        0.0,
        1.0,
        float(st.session_state.get("m_w_macro", 0.30)),
    )
    st.session_state["m_w_flow"] = st.slider(
        "Positioning & Flow Weight",
        0.0,
        1.0,
        float(st.session_state.get("m_w_flow", 0.25)),
    )
    st.session_state["m_w_sentiment"] = st.slider(
        "Sentiment & Narrative Weight",
        0.0,
        1.0,
        float(st.session_state.get("m_w_sentiment", 0.15)),
    )

    st.markdown("---")

    # ---------------------------------------------------------
    # MAINTENANCE
    # ---------------------------------------------------------
    st.subheader("Maintenance")
    st.write("Reset all trades, balance, and performance metrics.")

    if st.button("Reset All Performance Data"):
        reset_performance_history()
        st.success("Performance history cleared.")
        st.rerun()

    st.markdown("---")
    st.subheader("About")
    st.write("TradePlanner 3.0 - Built for precision, clarity, and speed.")
