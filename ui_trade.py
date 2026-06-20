# ================= ui_trade.py =================
import streamlit as st
import datetime
import requests
import pandas as pd

from storage import compute_balance_history, get_current_balance, get_initial_balance, load_trades, save_trade
from risk_engine import compute_risk_and_perf
from ai_engines import generate_risk_recommendation, generate_trade_journal_entry


GOOD_COLOR = "#16a34a"
BAD_COLOR = "#dc2626"
NEUTRAL_COLOR = "#d97706"

SYMBOL_DEFAULTS = {
    "BTC": {"sl_buffer": 350.0, "rr": 2.0, "fee_pct": 0.06, "exchange": "Binance"},
    "ETH": {"sl_buffer": 25.0, "rr": 2.0, "fee_pct": 0.06, "exchange": "Binance"},
    "SOL": {"sl_buffer": 5.0, "rr": 2.2, "fee_pct": 0.08, "exchange": "Binance"},
    "BNB": {"sl_buffer": 8.0, "rr": 2.0, "fee_pct": 0.06, "exchange": "Binance"},
    "XRP": {"sl_buffer": 0.03, "rr": 2.5, "fee_pct": 0.10, "exchange": "Binance"},
}

TRADE_CSS = """
<style>
.risk-hero { border:1px solid #dbeafe; background:#f8fbff; border-radius:10px; padding:14px; margin-bottom:8px; }
.risk-hero-title { font-size:13px; font-weight:700; color:#1f2937; text-transform:uppercase; letter-spacing:0.04em; }
.risk-hero-value { font-size:44px; font-weight:900; color:#0f172a; line-height:1.0; margin-top:4px; }
.score-box { border:1px solid #e5e7eb; border-radius:10px; padding:10px; background:#ffffff; }
.score-label { font-size:13px; font-weight:700; color:#1f2937; }
.score-value { font-size:34px; font-weight:900; line-height:1.0; margin-top:2px; }
.status-pill { display:inline-block; padding:6px 10px; border-radius:8px; font-weight:800; font-size:13px; }
</style>
"""


def _score_color(score: float) -> str:
    if float(score) >= 70:
        return GOOD_COLOR
    if float(score) >= 50:
        return NEUTRAL_COLOR
    return BAD_COLOR


def _context_explanation(p_score: float, m_score: float, risk_pct: float) -> str:
    if p_score >= 70 and m_score >= 70:
        return f"Strong performance and supportive market conditions justify proactive risk sizing around {risk_pct:.2f}% if setup quality is intact."
    if p_score >= 70 and m_score < 50:
        return f"Strong performance supports risk, but weak market conditions call for caution and selective execution near {risk_pct:.2f}%."
    if p_score < 50 and m_score >= 70:
        return f"Market conditions are constructive, but weak recent performance suggests tighter discipline and conservative use of the {risk_pct:.2f}% recommendation."
    if p_score < 50 and m_score < 50:
        return f"Both performance and market conditions are weak, so keep risk defensive and prioritize process quality around {risk_pct:.2f}%."
    return f"Conditions are mixed; use {risk_pct:.2f}% as a reference and lean on confirmation before full-size entries."


def _balance_message(current_balance: float, initial_balance: float, drawdown_pct: float) -> str:
    if current_balance > initial_balance and drawdown_pct <= 0.5:
        return "Account growing - risk scaling appropriately."
    if drawdown_pct > 0 or current_balance < initial_balance:
        return "Drawdown detected - risk reduced to protect capital."
    return "Capital stable - maintain disciplined sizing."


def _symbol_pair(base_symbol: str) -> str:
    return f"{base_symbol.upper()}USDT"


def _apply_symbol_defaults(state, base_symbol: str, price: float):
    defaults = SYMBOL_DEFAULTS.get(base_symbol, SYMBOL_DEFAULTS["BTC"])
    state["tp_sl_distance"] = float(defaults["sl_buffer"])
    state["tp_rr"] = float(defaults["rr"])
    state["tp_fee_pct"] = float(defaults["fee_pct"])
    state["tp_exchange"] = str(defaults["exchange"])
    state["tp_entry"] = float(price)
    state["tp_direction"] = state.get("tp_direction", "Long")

    if state["tp_direction"] == "Long":
        stop = float(price) - float(state["tp_sl_distance"])
        exit_price = float(price) + (float(price) - stop) * float(state["tp_rr"])
    else:
        stop = float(price) + float(state["tp_sl_distance"])
        exit_price = float(price) - (stop - float(price)) * float(state["tp_rr"])

    state["tp_stop"] = float(stop)
    state["tp_exit"] = float(exit_price)


def fetch_symbol_price(base_symbol: str):
    pair = _symbol_pair(base_symbol)
    try:
        r = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={pair}", timeout=8)
        r.raise_for_status()
        return float(r.json()["price"])
    except Exception:
        return None


# ---------------------------------------------------------
# MAIN TRADE PLANNER UI
# ---------------------------------------------------------
def render_trade_planning():
    st.markdown(TRADE_CSS, unsafe_allow_html=True)
    st.title("Trade Planner")

    trades = load_trades()
    state = st.session_state
    risk_result = compute_risk_and_perf(trades, state)

    perf = risk_result["perf"]
    market = risk_result["market"]
    acceptable_risk_pct = risk_result["acceptable_risk_pct"]
    breakdown = risk_result.get("risk_breakdown", {})
    initial_balance = float(risk_result.get("initial_balance", get_initial_balance(state)))
    current_balance = float(risk_result.get("current_balance", get_current_balance(trades, initial_balance)))
    current_drawdown_pct = float(risk_result.get("current_drawdown_pct", 0.0))
    balance_message = _balance_message(current_balance, initial_balance, current_drawdown_pct)

    if "tp_selected_symbol" not in state:
        state["tp_selected_symbol"] = "BTC"
    if "tp_loaded_symbol" not in state:
        state["tp_loaded_symbol"] = ""
    if "tp_current_price" not in state:
        state["tp_current_price"] = None
    if "tp_base_risk_pct" not in state:
        state["tp_base_risk_pct"] = float(acceptable_risk_pct)

    # ---------------------------------------------------------
    # VISUAL HIERARCHY
    # ---------------------------------------------------------
    p_score = float(risk_result.get("P_score", perf.get("P_score", 50)))
    m_score = float(risk_result.get("M_score", market.get("M_score", 50)))
    p_color = _score_color(p_score)
    m_color = _score_color(m_score)

    bal_col, risk_col = st.columns([0.38, 0.62])
    with bal_col:
        st.markdown(
            f"<div class='score-box'><div class='score-label'>Balance</div><div class='score-value' style='color:#0f172a;'>${current_balance:,.2f}</div></div>",
            unsafe_allow_html=True,
        )
    with risk_col:
        st.markdown(
            f"<div class='risk-hero'><div class='risk-hero-title'>Recommended Risk</div><div class='risk-hero-value'>{acceptable_risk_pct:.2f}%</div></div>",
            unsafe_allow_html=True,
        )

    score_left, score_mid, score_right = st.columns(3)
    with score_left:
        st.markdown(
            f"<div class='score-box'><div class='score-label'>Performance Score</div><div class='score-value' style='color:{p_color};'>{p_score:.1f}</div></div>",
            unsafe_allow_html=True,
        )
    with score_mid:
        st.markdown(
            f"<div class='score-box'><div class='score-label'>Market Score</div><div class='score-value' style='color:{m_color};'>{m_score:.1f}</div></div>",
            unsafe_allow_html=True,
        )
    with score_right:
        balance_delta = current_balance - initial_balance
        delta_color = GOOD_COLOR if balance_delta >= 0 else BAD_COLOR
        st.markdown(
            f"<div class='score-box'><div class='score-label'>Net PnL</div><div class='score-value' style='color:{delta_color};'>{balance_delta:,.2f}</div></div>",
            unsafe_allow_html=True,
        )
    st.write(f"Explanation: {_context_explanation(p_score, m_score, acceptable_risk_pct)}")
    st.write(balance_message)
    st.markdown("---")

    # ---------------------------------------------------------
    # TRADE CONFIGURATION
    # ---------------------------------------------------------
    st.subheader("Trade Configuration")

    colS, colA, colB, colC, colD, colE = st.columns(6)

    with colS:
        selected_symbol = st.selectbox(
            "Symbol",
            ["BTC", "ETH", "SOL", "BNB", "XRP"],
            key="tp_selected_symbol",
        )

    if selected_symbol != state.get("tp_loaded_symbol") or state.get("tp_current_price") is None:
        fetched = fetch_symbol_price(selected_symbol)
        if fetched is not None:
            state["tp_loaded_symbol"] = selected_symbol
            state["tp_current_price"] = float(fetched)
            _apply_symbol_defaults(state, selected_symbol, float(fetched))
        else:
            state["tp_current_price"] = None

    symbol_ready = state.get("tp_current_price") is not None

    with colA:
        default_sl_distance = st.number_input(
            "SL Distance",
            value=float(state.get("tp_sl_distance", 350.0)),
            key="tp_sl_distance",
            disabled=not symbol_ready,
        )

    with colB:
        default_rr = st.number_input(
            "RR",
            value=float(state.get("tp_rr", 2.0)),
            key="tp_rr",
            disabled=not symbol_ready,
        )

    with colC:
        default_fee = st.number_input(
            "Fee %",
            value=float(state.get("tp_fee_pct", 0.06)),
            key="tp_fee_pct",
            disabled=not symbol_ready,
        )

    with colD:
        default_exchange = str(state.get("tp_exchange", "Binance"))
        exchange_options = ["Binance", "Bybit", "OKX"]
        exchange = st.selectbox(
            "Exchange",
            exchange_options,
            index=exchange_options.index(default_exchange) if default_exchange in exchange_options else 0,
            key="tp_exchange",
            disabled=not symbol_ready,
        )

    with colE:
        default_risk_pct = st.number_input(
            "Actual Risk Taken %",
            value=float(state.get("tp_base_risk_pct", acceptable_risk_pct)),
            key="tp_base_risk_pct",
            disabled=not symbol_ready,
        )

    if symbol_ready:
        st.write(f"Current Price: {float(state.get('tp_current_price', 0.0)):.4f}")
    else:
        st.error(f"Could not fetch live price for {_symbol_pair(selected_symbol)}. Try again shortly.")

    if symbol_ready:
        entry_live = float(state.get("tp_current_price", 0.0))
        direction_live = str(state.get("tp_direction", "Long"))
        if direction_live == "Long":
            stop_live = entry_live - float(default_sl_distance)
            exit_live = entry_live + (entry_live - stop_live) * float(default_rr)
        else:
            stop_live = entry_live + float(default_sl_distance)
            exit_live = entry_live - (stop_live - entry_live) * float(default_rr)
        state["tp_entry"] = float(entry_live)
        state["tp_stop"] = float(stop_live)
        state["tp_exit"] = float(exit_live)

    st.markdown("---")

    # ---------------------------------------------------------
    # PLAN TRADE
    # ---------------------------------------------------------
    st.subheader("Plan Trade")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        symbol = st.text_input(
            "Symbol",
            value=_symbol_pair(selected_symbol),
            disabled=True,
        )

    with col2:
        direction = st.selectbox("Direction", ["Long", "Short"], key="tp_direction", disabled=not symbol_ready)

    with col3:
        entry = st.number_input(
            "Entry Price",
            value=float(state.get("tp_current_price", 0.0)) if symbol_ready else 0.0,
            disabled=True,
        )

    with col4:
        if direction == "Long":
            stop_auto = entry - float(default_sl_distance)
        else:
            stop_auto = entry + float(default_sl_distance)
        stop_price = st.number_input(
            "Stop Loss Price",
            value=float(stop_auto),
            disabled=True,
        )

    with col5:
        rr = st.number_input("RR", value=float(default_rr), disabled=not symbol_ready)

    if direction == "Long":
        calculated_exit = entry + (entry - stop_price) * rr
    else:
        calculated_exit = entry - (stop_price - entry) * rr

    exit_price = st.number_input("Exit Price", value=float(calculated_exit), disabled=True)
    plan_trade = st.button("Plan", disabled=not symbol_ready)

    # ---------------------------------------------------------
    # COMPUTE TRADE RESULT
    # ---------------------------------------------------------
    if plan_trade and symbol_ready:
        sl_distance = abs(entry - stop_price)
        risk_pct = default_risk_pct / 100

        risk_amount = current_balance * risk_pct
        units = risk_amount / sl_distance if sl_distance > 0 else 0

        fee_rate = default_fee / 100
        fee_cost = units * entry * fee_rate

        breakeven_price = entry + fee_rate * entry

        pnl = (exit_price - entry) * units if direction == "Long" else (entry - exit_price) * units
        pnl_after_fee = pnl - fee_cost

        result = "Win" if pnl_after_fee > 0 else "Loss"
        balance_before = current_balance
        balance_after = balance_before + pnl_after_fee
        cumulative_pnl = balance_after - initial_balance

        st.session_state["computed_trade"] = {
            "date": datetime.date.today().isoformat(),
            "time": datetime.datetime.now().strftime("%H:%M:%S"),
            "initial_balance": initial_balance,
            "balance_before": balance_before,
            "balance_after": balance_after,
            "cumulative_pnl": cumulative_pnl,
            "symbol": _symbol_pair(selected_symbol),
            "exchange": exchange,
            "direction": direction,
            "units": units,
            "entry": entry,
            "exit": exit_price,
            "breakeven_price": breakeven_price,
            "breakeven_distance": abs(breakeven_price - entry),
            "stop_loss_price": stop_price,
            "stop_loss_distance": abs(entry - stop_price),
            "rr": rr,
            "risk_pct": default_risk_pct,
            "actual_risk_pct": default_risk_pct,
            "recommended_risk_pct": acceptable_risk_pct,
            "P_score": risk_result.get("P_score", 50),
            "M_score": risk_result.get("M_score", 50),
            "market_risk_mode": market.get("market_risk_mode", "Neutral"),
            "risk_breakdown": breakdown,
            "trading_fee": fee_cost,
            "pnl": pnl_after_fee,
            "result": result,
        }

        st.success("Trade planned. Review below.")
    elif plan_trade and not symbol_ready:
        st.error("Price is unavailable for the selected symbol.")

    # ---------------------------------------------------------
    # SHOW COMPUTED TRADE
    # ---------------------------------------------------------
    if "computed_trade" in st.session_state:
        st.subheader("Planned Trade")

        planned = st.session_state["computed_trade"]
        pnl_val = float(planned.get("pnl", 0.0))
        is_win = pnl_val >= 0
        pnl_color = GOOD_COLOR if is_win else BAD_COLOR
        status_bg = "#dcfce7" if is_win else "#fee2e2"
        status_txt = "Winning Trade" if is_win else "Losing Trade"
        status_dot = "🟢" if is_win else "🔴"

        st.markdown(
            f"<div class='status-pill' style='background:{status_bg}; color:{pnl_color};'>{status_dot} {status_txt}</div>",
            unsafe_allow_html=True,
        )
        st.markdown(f"<h3 style='margin-top:8px; color:{pnl_color};'>PnL: {pnl_val:.2f}</h3>", unsafe_allow_html=True)

        df = pd.DataFrame([planned])
        st.dataframe(df)

        if st.button("Register Trade"):
            save_trade(planned)
            st.session_state["last_recorded_trade"] = planned
            st.session_state["balance"] = float(planned.get("balance_after", current_balance))
            st.session_state.pop("computed_trade")
            st.success("Trade saved.")
            st.rerun()

    st.markdown("---")

    # ---------------------------------------------------------
    # AI SECTION (BOTTOM ONLY)
    # ---------------------------------------------------------
    st.subheader("AI Insights")

    risk_expl = generate_risk_recommendation(perf, market, acceptable_risk_pct)
    st.info(risk_expl)

    if "last_recorded_trade" in st.session_state:
        journal = generate_trade_journal_entry(st.session_state["last_recorded_trade"])
        st.info(journal)
