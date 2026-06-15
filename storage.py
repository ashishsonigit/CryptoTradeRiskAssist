# ================= storage.py =================
import json
import os

STORAGE_FILE = "trade_history.json"


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
    if "balance" in st.session_state:
        st.session_state["balance"] = 10000.0
    if "market_snapshot" in st.session_state:
        st.session_state["market_snapshot"] = {}
