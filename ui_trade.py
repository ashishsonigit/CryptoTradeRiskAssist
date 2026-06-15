# ================= ui_trade.py =================
import streamlit as st
import datetime
import requests
import pandas as pd

from storage import load_trades, save_trade
from risk_engine import compute_risk_and_perf
from ai_engines import generate_risk_recommendation, generate_trade_journal_entry


# ---------------------------------------------------------
# Fetch BTC Price
# ---------------------------------------------------------
def fetch_btc_price():
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT")
        return float(r.json()["price"])
    except:
        return None


# ---------------------------------------------------------
# MAIN TRADE PLANNER UI
# ---------------------------------------------------------
def render_trade_planning():
    st.title("📝 Trade Planner")

    trades = load_trades()
    state = st.session_state
    risk_result = compute_risk_and_perf(trades, state)

    perf = risk_result["perf"]
    market = risk_result["market"]
    acceptable_risk_pct = risk_result["acceptable_risk_pct"]

    # ---------------------------------------------------------
    # AUTO-FETCH BTC PRICE ON APP START
    # ---------------------------------------------------------
    if "fetched_price" not in st.session_state:
        price = fetch_btc_price()
        st.session_state["fetched_price"] = price if price else 0.0

    # Manual update button
    if st.button("🔄 Update BTC Price"):
        price = fetch_btc_price()
        if price:
            st.session_state["fetched_price"] = price
            st.success(f"Updated BTC Price: {price}")
        else:
            st.error("Failed to fetch price.")

    fetched_price = st.session_state["fetched_price"]

    st.write(f"**Current BTC Price:** {fetched_price}")

    st.markdown("---")

    # ---------------------------------------------------------
    # TRADE CONFIGURATION (5 equal-width inputs)
    # ---------------------------------------------------------
    st.subheader("Trade Configuration")

    colA, colB, colC, colD, colE = st.columns(5)

    with colA:
        default_sl_distance = st.number_input("SL Distance", value=350.0)

    with colB:
        default_rr = st.number_input("RR", value=2.0)

    with colC:
        default_fee = st.number_input("Fee %", value=0.06)

    with colD:
        exchange = st.selectbox("Exchange", ["Binance", "Bybit", "OKX"], index=0)

    with colE:
        default_risk_pct = st.number_input("Risk %", value=acceptable_risk_pct)

    st.markdown("---")

    # ---------------------------------------------------------
    # PLAN YOUR TRADE (5 equal-width inputs)
    # ---------------------------------------------------------
    st.subheader("Plan Your Trade")

    with st.form("trade_form"):

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            symbol = st.text_input("Symbol", "BTCUSD")

        with col2:
            direction = st.selectbox("Direction", ["Long", "Short"])

        with col3:
            entry = st.number_input("Entry Price", value=fetched_price)

        with col4:
            stop_price = st.number_input("Stop Loss Price", value=entry - default_sl_distance)

        with col5:
            rr = st.number_input("RR Override", value=default_rr)

        # ---------------------------------------------------------
        # CALCULATED EXIT PRICE (DEFAULT) — BUT CONFIGURABLE
        # ---------------------------------------------------------
        if direction == "Long":
            calculated_exit = entry + (entry - stop_price) * rr
        else:
            calculated_exit = entry - (stop_price - entry) * rr

        st.write("### Exit Price (Configurable)")
        exit_price = st.number_input("Exit Price", value=calculated_exit)

        # ---------------------------------------------------------
        # PLAN BUTTON
        # ---------------------------------------------------------
        plan_trade = st.form_submit_button("📐 Plan")

    # ---------------------------------------------------------
    # COMPUTE TRADE RESULT
    # ---------------------------------------------------------
    if plan_trade:
        sl_distance = abs(entry - stop_price)
        risk_pct = default_risk_pct / 100

        units = (state.get("balance", 10000) * risk_pct) / sl_distance if sl_distance > 0 else 0

        fee_rate = default_fee / 100
        fee_cost = units * entry * fee_rate

        breakeven_price = entry + fee_rate * entry

        pnl = (exit_price - entry) * units if direction == "Long" else (entry - exit_price) * units
        pnl_after_fee = pnl - fee_cost

        result = "Win" if pnl_after_fee > 0 else "Loss"

        st.session_state["computed_trade"] = {
            "date": datetime.date.today().isoformat(),
            "time": datetime.datetime.now().strftime("%H:%M:%S"),
            "symbol": symbol,
            "exchange": exchange,
            "direction": direction,
            "units": units,
            "entry": entry,
            "exit": exit_price,
            "breakeven_price": breakeven_price,
            "breakeven_distance": abs(breakeven_price - entry),
            "stop_loss_price": stop_price,
            "stop_loss_distance": abs(entry - stop_price),
            "trading_fee": fee_cost,
            "pnl": pnl_after_fee,
            "result": result,
        }

        st.success("Trade planned. Review below.")

    # ---------------------------------------------------------
    # SHOW COMPUTED TRADE
    # ---------------------------------------------------------
    if "computed_trade" in st.session_state:
        st.subheader("Planned Trade")

        df = pd.DataFrame([st.session_state["computed_trade"]])
        st.dataframe(df)

        if st.button("💾 Register Trade"):
            save_trade(st.session_state["computed_trade"])
            st.session_state["last_recorded_trade"] = st.session_state["computed_trade"]
            st.session_state.pop("computed_trade")
            st.success("Trade saved.")
            st.rerun()

    st.markdown("---")

    # ---------------------------------------------------------
    # AI SECTION (BOTTOM ONLY)
    # ---------------------------------------------------------
    st.subheader("🧠 AI Insights")

    risk_expl = generate_risk_recommendation(perf, market, acceptable_risk_pct)
    st.info(risk_expl)

    if "last_recorded_trade" in st.session_state:
        journal = generate_trade_journal_entry(st.session_state["last_recorded_trade"])
        st.info(journal)
