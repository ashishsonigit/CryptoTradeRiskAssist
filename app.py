# ================= app.py =================
import streamlit as st

from market_snapshot import schedule_market_updates
from ui_trade import render_trade_planning
from ui_market import render_market_dashboard
from ui_perf import render_performance_dashboard
from ui_history import render_history
from settings import render_settings


PAGES = {
    "Trade Planner": render_trade_planning,
    "Market Layer": render_market_dashboard,
    "Performance Layer": render_performance_dashboard,
    "Trade History": render_history,
    "Settings": render_settings,
}


def main():
    st.set_page_config(
        page_title="TradePlanner 3.0",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    schedule_market_updates()

    st.sidebar.title("📌 Navigation")
    choice = st.sidebar.radio("Go to", list(PAGES.keys()))

    PAGES[choice]()


if __name__ == "__main__":
    main()
