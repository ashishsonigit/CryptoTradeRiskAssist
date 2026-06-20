PARAMETER_DEFINITIONS = {
    "initial_balance": {
        "label": "Initial Balance",
        "what_it_means": "Starting account value used as the baseline for growth and drawdown.",
        "why_it_matters": "All balance, return, and risk-scaling logic reference this value.",
        "how_computed": "User configured in Settings. Default is 10000.",
        "data_sources": "User input",
        "units_or_range": "Currency, > 0",
    },
    "current_balance": {
        "label": "Current Balance",
        "what_it_means": "Latest account value after applying all saved trade PnL.",
        "why_it_matters": "Used to size risk amount and position units for the next trade.",
        "how_computed": "Initial balance + cumulative realized PnL from trade history.",
        "data_sources": "trade_history.json",
        "units_or_range": "Currency",
    },
    "base_risk_pct": {
        "label": "Base Risk %",
        "what_it_means": "Your base risk profile before market/performance adjustments.",
        "why_it_matters": "Acts as the anchor for the risk engine recommendation.",
        "how_computed": "User configured in Settings, then adjusted by risk engine factors.",
        "data_sources": "User input",
        "units_or_range": "Percent, typically 0.1 to 5.0",
    },
    "recommended_risk_pct": {
        "label": "Recommended Risk %",
        "what_it_means": "Risk engine suggested risk per trade under current conditions.",
        "why_it_matters": "Provides dynamic risk discipline based on P/M scores and equity stress.",
        "how_computed": "Risk engine formula using performance, market, balance ratio, and drawdown protection.",
        "data_sources": "performance_layer + market_layer + account balance state",
        "units_or_range": "Percent, clamped to safety bounds",
    },
    "actual_risk_pct": {
        "label": "Actual Risk Taken %",
        "what_it_means": "The risk percent you choose for this planned trade.",
        "why_it_matters": "Directly controls risk amount and position size.",
        "how_computed": "User input in Trade Configuration.",
        "data_sources": "User input",
        "units_or_range": "Percent",
    },
    "p_score": {
        "label": "Performance Score",
        "what_it_means": "Composite score of trading performance quality.",
        "why_it_matters": "Influences recommended risk and execution confidence.",
        "how_computed": "Weighted blend of winrate, loss streak, drift, quality, expectancy, growth, and drawdown.",
        "data_sources": "trade_history.json",
        "units_or_range": "0 to 100",
    },
    "m_score": {
        "label": "Market Score",
        "what_it_means": "Composite score of current market environment quality.",
        "why_it_matters": "Used by risk engine to gate or expand exposure.",
        "how_computed": "Weighted blend of price structure, macro, flow, and sentiment pillars.",
        "data_sources": "market_snapshot providers",
        "units_or_range": "0 to 100",
    },
    "symbol": {
        "label": "Symbol",
        "what_it_means": "Trading instrument selected for planning.",
        "why_it_matters": "Drives fetched price and symbol-specific defaults.",
        "how_computed": "User selected from available symbols.",
        "data_sources": "User input",
        "units_or_range": "Ticker",
    },
    "sl_distance": {
        "label": "SL Distance",
        "what_it_means": "Price distance between entry and stop-loss.",
        "why_it_matters": "Defines risk per unit and therefore position size.",
        "how_computed": "User configurable; defaults from symbol profile.",
        "data_sources": "User input + symbol defaults",
        "units_or_range": "Price units",
    },
    "entry_price": {
        "label": "Entry Price",
        "what_it_means": "Current market price used as planned entry.",
        "why_it_matters": "Anchor for stop, target, RR, and PnL calculations.",
        "how_computed": "Auto-fetched from selected symbol price feed.",
        "data_sources": "Binance ticker endpoint",
        "units_or_range": "Price",
    },
    "stop_loss_price": {
        "label": "Stop Loss Price",
        "what_it_means": "Invalidation level where trade risk is cut.",
        "why_it_matters": "Used to compute SL distance and position sizing.",
        "how_computed": "For long: entry - SL distance. For short: entry + SL distance.",
        "data_sources": "Entry + SL Distance + Direction",
        "units_or_range": "Price",
    },
    "exit_price": {
        "label": "Exit Price",
        "what_it_means": "Planned target or expected exit level.",
        "why_it_matters": "Determines projected reward and realized PnL estimate.",
        "how_computed": "User configurable in Plan section.",
        "data_sources": "User input",
        "units_or_range": "Price",
    },
    "rr": {
        "label": "RR",
        "what_it_means": "Reward-to-risk ratio for the planned trade.",
        "why_it_matters": "Helps evaluate quality of payoff versus risk.",
        "how_computed": "abs(exit - entry) / abs(entry - stop)",
        "data_sources": "Entry, Exit, Stop",
        "units_or_range": "Ratio",
    },
    "units": {
        "label": "Position Size (Units)",
        "what_it_means": "How many units to trade at current plan.",
        "why_it_matters": "Ensures consistent risk sizing across changing balances.",
        "how_computed": "(Current Balance * Actual Risk %) / SL Distance",
        "data_sources": "Balance + Risk % + SL Distance",
        "units_or_range": "Asset units",
    },
    "pnl": {
        "label": "PnL",
        "what_it_means": "Estimated profit or loss for the planned trade.",
        "why_it_matters": "Updates balance and determines win/loss outcome.",
        "how_computed": "Direction-adjusted (exit-entry)*units minus fees.",
        "data_sources": "Entry, Exit, Units, Fee",
        "units_or_range": "Currency",
    },
}


MARKET_DATA_SOURCES = {
    "binance_price": {
        "label": "Binance Price/Klines",
        "endpoint_default": "https://api.binance.com",
        "data_points": "spot price, OHLCV candles, ATR/EMA/ADX inputs",
        "fallback": "Keeps previous/default snapshot values when unavailable",
    },
    "binance_funding": {
        "label": "Binance Funding Rates",
        "endpoint_default": "https://api.binance.com/fapi/v1/fundingRate",
        "data_points": "funding_z",
        "fallback": "Uses neutral funding signal (0.0)",
    },
    "binance_oi": {
        "label": "Binance Open Interest",
        "endpoint_default": "https://api.binance.com/futures/data/openInterestHist",
        "data_points": "oi_z",
        "fallback": "Uses neutral OI signal (0.0)",
    },
    "fear_greed": {
        "label": "Alternative.me Fear & Greed",
        "endpoint_default": "https://api.alternative.me/fng/",
        "data_points": "fear_greed",
        "fallback": "Uses neutral sentiment value (50)",
    },
    "fred": {
        "label": "FRED Macro",
        "endpoint_default": "https://api.stlouisfed.org/fred",
        "data_points": "us10y_current, us10y_avg_5d",
        "fallback": "Uses baseline macro defaults when unavailable",
    },
    "alphavantage": {
        "label": "AlphaVantage Cross-Asset",
        "endpoint_default": "https://www.alphavantage.co/query",
        "data_points": "dxy_score, equities_score proxies",
        "fallback": "Uses neutral cross-asset scores",
    },
    "defillama": {
        "label": "DefiLlama Stablecoins",
        "endpoint_default": "https://stablecoins.llama.fi",
        "data_points": "stable_30d_change_pct",
        "fallback": "Uses neutral liquidity change (0.0)",
    },
}


def get_parameter_definition(key: str):
    return PARAMETER_DEFINITIONS.get(key)


def get_market_source_definition(key: str):
    return MARKET_DATA_SOURCES.get(key)
