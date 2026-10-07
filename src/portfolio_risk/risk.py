"""Concentration flags and weighted volatility exposure.

Inputs must already have passed valuation.value_portfolio.

Weighted volatility exposure is a simple indicator: sum(weight * daily_volatility).
It is not portfolio volatility, marginal or component risk contribution, VaR,
or expected loss. It ignores correlations, so diversification never reduces it.
"""

import pandas as pd

DEFAULT_CONCENTRATION_THRESHOLD = 0.25


def largest_position(valued: pd.DataFrame) -> dict[str, str | float]:
    """Return {"ticker", "weight"} for the greatest weight; ties go to the first row in file order."""
    row = valued.loc[valued["weight"].idxmax()]
    return {"ticker": str(row["ticker"]), "weight": float(row["weight"])}


def flag_concentration(
    valued: pd.DataFrame, threshold: float = DEFAULT_CONCENTRATION_THRESHOLD
) -> pd.DataFrame:
    """Return a copy with above_threshold = weight > threshold.

    A weight equal to the threshold is not flagged.
    """
    if not 0.0 <= threshold <= 1.0:
        raise ValueError(f"concentration threshold must be between 0 and 1, got {threshold}")
    flagged = valued.copy()
    flagged["above_threshold"] = flagged["weight"] > threshold
    return flagged


def add_weighted_volatility_components(valued: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with weighted_volatility_component = weight * daily_volatility."""
    components = valued.copy()
    components["weighted_volatility_component"] = components["weight"] * components["daily_volatility"]
    return components


def weighted_volatility_exposure(components: pd.DataFrame) -> float:
    """Return sum(weighted_volatility_component), a daily fraction (0.0135 = 1.35% per day)."""
    return float(components["weighted_volatility_component"].sum(skipna=False))
