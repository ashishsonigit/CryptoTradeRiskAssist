# ================= ui_history.py =================
import streamlit as st
import pandas as pd

from storage import load_trades
from ai_engines import generate_trade_journal_entry


def render_history():
    st.title("📚 Trade History")

    trades = load_trades()
    df = pd.DataFrame(trades)

    if df.empty:
        st.info("No trades recorded yet.")
        return

    st.subheader("Trades Table")
    st.dataframe(df)

    st.markdown("## 🧠 AI Trade Journaling")

    for trade in trades:
        label = f"{trade.get('symbol', 'Unknown')} — {trade.get('result', '')} — {trade.get('pnl_r', 0)}R"
        with st.expander(label):
            journal = generate_trade_journal_entry(trade)
            st.write(journal)
