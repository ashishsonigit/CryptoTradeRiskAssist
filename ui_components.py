# ================= ui_components.py =================
import streamlit as st


def inject_layout_css():
    st.markdown(
        """
        <style>
        /* Sidebar: light grey background */
        section[data-testid="stSidebar"] {
            background-color: #f2f2f2 !important;
        }

        /* Highlight selected radio option in sidebar */
        div[data-testid="stSidebar"] .stRadio > label {
            width: 100%;
        }
        div[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label {
            border-radius: 6px;
            padding: 6px 10px;
            margin-bottom: 4px;
        }
        div[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label:hover {
            background-color: #e0e0e0;
        }
        div[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label[data-checked="true"] {
            background-color: #d0e4ff !important;
            border-left: 3px solid #1E90FF;
            font-weight: 600;
        }

        /* Main container: more width, balanced padding */
        .block-container {
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            max-width: 1100px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def inject_css():
    st.markdown(
        """
        <style>
        /* Custom Hybrid: uniform inputs/outputs */

        /* Text inputs, number inputs, selects */
        .stTextInput > div > div > input,
        .stNumberInput > div > div > input,
        .stSelectbox > div > div > div {
            height: 40px !important;
            padding: 6px 10px !important;
            border-radius: 6px !important;
            border: 1px solid #444 !important;
            font-size: 0.95rem !important;
        }

        /* Labels */
        label {
            font-size: 0.9rem !important;
            font-weight: 500 !important;
        }

        /* Metric label + value */
        .metric-label {
            font-weight: 500 !important;
            font-size: 0.95rem !important;
            margin-bottom: 2px !important;
        }
        .metric-text {
            font-weight: 700 !important;
            font-size: 1.05rem !important;
            margin-bottom: 6px !important;
        }

        .tooltip-icon {
            display: inline-block;
            margin-left: 6px;
            color: #1E90FF;
            cursor: help;
            font-size: 0.85rem;
        }

        /* Panels */
        .equal-panel {
            min-height: 380px;
            padding: 14px;
            border-radius: 8px;
            border: 1px solid #444;
        }

        /* Summary table */
        .summary-table td {
            padding: 6px 12px;
            font-size: 0.95rem;
            font-weight: 600;
        }
        .summary-table th {
            padding: 6px 12px;
            font-size: 0.95rem;
            text-align: left;
            font-weight: 500;
        }

        /* Chart explanation blocks */
        .chart-explainer-title {
            font-weight: 600;
            margin-top: 4px;
            margin-bottom: 2px;
        }
        .chart-explainer-body {
            font-size: 0.9rem;
            color: #cccccc;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def metric_with_explanation(label, value, tooltip, calc_text=None):
    st.markdown(
        f"""
        <div class='metric-label'>
            {label}
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(f"<div class='metric-text'>{value}</div>", unsafe_allow_html=True)

    if calc_text:
        with st.expander("Show calculation"):
            st.markdown(calc_text)
