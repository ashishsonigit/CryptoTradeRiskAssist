# ================= storage.py =================
import json
import os

STORAGE_FILE = "trade_history.json"
DEFAULT_INITIAL_BALANCE = 10000.0


def load_trades():
    if not os.path.exists(STORAGE_FILE):
        return []
    with open(STORAGE_FILE, "r") as f:
        return json.load(f)


def save_trades(trades):
    with open(STORAGE_FILE, "w") as f:
        json.dump(trades, f, indent=4)


# ---------------------------------------------------------
# FIX: Add missing save_trade() function
# ---------------------------------------------------------
def save_trade(trade: dict):
    """
    Appends a single trade to the JSON storage.
    """
    trades = load_trades()
    trades.append(trade)
    save_trades(trades)


def get_initial_balance(state=None):
    if state is not None:
        try:
            return float(state.get("initial_balance", DEFAULT_INITIAL_BALANCE))
        except Exception:
            return DEFAULT_INITIAL_BALANCE
    return DEFAULT_INITIAL_BALANCE


def compute_balance_history(trades, initial_balance):
    balance = float(initial_balance)
    peak_balance = float(initial_balance)
    rows = []

    for trade in trades:
        pnl = float(trade.get("pnl", 0.0) or 0.0)
        balance_before = float(trade.get("balance_before", balance))
        balance_after = float(trade.get("balance_after", balance_before + pnl))
        cumulative_pnl = float(trade.get("cumulative_pnl", balance_after - float(initial_balance)))

        balance = balance_after
        peak_balance = max(peak_balance, balance_after)
        drawdown_pct = ((peak_balance - balance_after) / peak_balance * 100.0) if peak_balance > 0 else 0.0

        enriched = dict(trade)
        enriched["balance_before"] = balance_before
        enriched["balance_after"] = balance_after
        enriched["cumulative_pnl"] = cumulative_pnl
        enriched["drawdown_pct"] = drawdown_pct
        rows.append(enriched)

    return rows


def get_current_balance(trades, initial_balance):
    history = compute_balance_history(trades, initial_balance)
    if not history:
        return float(initial_balance)
    return float(history[-1].get("balance_after", initial_balance))


def get_peak_balance(trades, initial_balance):
    history = compute_balance_history(trades, initial_balance)
    if not history:
        return float(initial_balance)
    return max(float(initial_balance), max(float(t.get("balance_after", initial_balance)) for t in history))

# ---------------------------------------------------------
# RESET PERFORMANCE HISTORY
# ---------------------------------------------------------
def reset_performance_history():
    """
    Clears all stored trades and resets performance history.
    Used by the Settings page.
    """
    # Clear trades
    save_trades([])

    # Reset session state values if they exist
    import streamlit as st
    initial_balance = float(st.session_state.get("initial_balance", DEFAULT_INITIAL_BALANCE))
    if "balance" in st.session_state:
        st.session_state["balance"] = initial_balance
    else:
        st.session_state["balance"] = initial_balance
    if "market_snapshot" in st.session_state:
        st.session_state["market_snapshot"] = {}
