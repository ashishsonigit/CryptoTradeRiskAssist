# ================= ui_docs.py =================
import streamlit as st
from ui_components import inject_css, inject_layout_css


def render_docs_ui():
    inject_layout_css()
    inject_css()
    st.title("📚 Documentation — Trade Planner 3.0")

    st.markdown(
        """
        ## Overview

        Trade Planner is a modular trading workflow system designed to help you:

        - Plan trades with risk‑aware sizing  
        - Analyze trade performance with institutional‑grade metrics  
        - Adjust risk dynamically using a Market layer e  
        - Maintain a searchable, filterable, exportable trade history  

        ---

        ## 1. Trade Planner

        The Trade Planner module allows you to:

        - Select direction (Long/Short)  
        - Input RR, stop distance, fees, and symbol  
        - Auto‑fetch price  
        - Calculate final risk % using:
            - Trade Performance Risk  
            - Regime Multiplier  
        - Preview trade (entry, stop, breakeven, units, risk amount)  
        - Record actual trades  
        - Generate a clean summary table  

        **Hybrid Explanation System:**  
        - Hover tooltips → quick hints  
        - Dropdowns → full formulas  

        ---

        ## 2. Performance Dashboard

        The Performance Dashboard provides:

        - Winrate  
        - Max Drawdown  
        - Loss Streak  
        - Expectancy  
        - Profit Factor  
        - Equity Curve  
        - Rolling Winrate  
        - Drawdown Curve  
        - RR Distribution  
        - Expectancy Over Time  
        - Weekday × Hour Heatmap  
        - Full trade table  

        All metrics use the hybrid tooltip + dropdown explanation system.

        ---

        ## 3. Market Regime Engine

        The Regime Engine computes:

        - Trend Score  
        - Volatility Score  
        - Breadth Score  
        - Liquidity Score  
        - Macro Score  
        - Composite Market Risk Score  
        - Regime Mode  
        - Regime Multiplier  

        These values help scale your risk based on market conditions.

        ---

        ## 4. Trade History

        The Trade History module includes:

        - Summary metrics  
        - Filters (direction, result, symbol)  
        - Search bar  
        - Full trade table  
        - CSV export  
        - Reset history  

        ---

        ## 5. UI & Layout

        Trade Planner 3.0 uses:

        - Grey sidebar  
        - Full‑width main content  
        - Bloomberg‑style spacing  
        - Hybrid explanation system  
        - Consistent metric styling  
        - Clean typography  

        All UI components are centralized in `ui_components.py`.

        ---

        ## Navigation

        Use the sidebar to switch between:

        - Trade Planner  
        - Performance Dashboard  
        - Market Regime  
        - Trade History  
        - Documentation  

        """
    )
