"""Run the full V1 analysis on a portfolio CSV.

This module only sequences the tested steps. Every formula lives in
validation.py, valuation.py, or risk.py.
"""

from pathlib import Path
from typing import Any

from portfolio_risk.risk import (
    DEFAULT_CONCENTRATION_THRESHOLD,
    add_weighted_volatility_components,
    flag_concentration,
    largest_position,
    weighted_volatility_exposure,
)
from portfolio_risk.validation import load_portfolio
from portfolio_risk.valuation import total_portfolio_value, value_portfolio


def analyse_portfolio(
    path: str | Path,
    concentration_threshold: float = DEFAULT_CONCENTRATION_THRESHOLD,
) -> dict[str, Any]:
    """Load, value, and analyse a portfolio CSV.

    Raises PortfolioDataError for invalid portfolio data and ValueError for an
    invalid concentration threshold.
    """
    valued = value_portfolio(load_portfolio(path))
    flagged = flag_concentration(valued, concentration_threshold)
    positions = add_weighted_volatility_components(flagged)
    return {
        "positions": positions,
        "total_portfolio_value": total_portfolio_value(positions),
        "largest_position": largest_position(positions),
        "weighted_volatility_exposure": weighted_volatility_exposure(positions),
        "concentration_threshold": float(concentration_threshold),
    }
