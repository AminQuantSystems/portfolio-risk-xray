"""Position market values, total portfolio value, and portfolio weights.

Inputs must already have passed validation.load_portfolio.
"""

import math

import pandas as pd

from portfolio_risk.validation import PortfolioDataError


def value_portfolio(portfolio: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of a validated portfolio with market_value and weight added.

    market_value = quantity * price
    weight = market_value / total_portfolio_value
    """
    valued = portfolio.copy()
    valued["market_value"] = (valued["quantity"] * valued["price"]).astype("float64")
    valued["weight"] = valued["market_value"] / total_portfolio_value(valued)
    return valued


def total_portfolio_value(valued: pd.DataFrame) -> float:
    """Return sum(market_value), rejecting a zero or non-finite total."""
    # skipna=False: a NaN market value must make the total NaN, not be skipped.
    total = float(valued["market_value"].sum(skipna=False))
    if not math.isfinite(total):
        raise PortfolioDataError(f"total portfolio value is not finite: {total}")
    if total == 0:
        raise PortfolioDataError("total portfolio value is zero; weights are undefined")
    return total
