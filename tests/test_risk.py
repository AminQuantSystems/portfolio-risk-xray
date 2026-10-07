import math

import pandas as pd
import pytest

from portfolio_risk.risk import (
    add_weighted_volatility_components,
    flag_concentration,
    largest_position,
    weighted_volatility_exposure,
)
from portfolio_risk.validation import load_portfolio
from portfolio_risk.valuation import value_portfolio

GOLDEN_TICKERS = ["AAPL", "MSFT", "TLT", "CASH"]


def test_largest_position_is_aapl_at_40_percent(golden_valued_portfolio):
    largest = largest_position(golden_valued_portfolio)

    assert isinstance(largest, dict)
    assert set(largest) == {"ticker", "weight"}
    assert largest["ticker"] == "AAPL"
    assert largest["weight"] == pytest.approx(0.40)


def test_largest_position_tie_returns_first_ticker_in_file_order(write_csv):
    path = write_csv(
        "ticker,quantity,price,daily_volatility\n"
        "SMALL,50,100,0.01\n"
        "FIRST,100,100,0.02\n"
        "SECOND,100,100,0.01\n"
    )
    valued = value_portfolio(load_portfolio(path))

    largest = largest_position(valued)

    assert largest["ticker"] == "FIRST"
    assert largest["weight"] == pytest.approx(0.40)


def test_default_threshold_flags_only_aapl_and_msft(golden_valued_portfolio):
    flagged = flag_concentration(golden_valued_portfolio)

    assert flagged["above_threshold"].tolist() == [True, True, False, False]


def test_weight_equal_to_threshold_is_not_flagged(golden_valued_portfolio):
    flagged = flag_concentration(golden_valued_portfolio, threshold=0.40)

    assert flagged["above_threshold"].tolist() == [False, False, False, False]


def test_negative_threshold_rejected(golden_valued_portfolio):
    with pytest.raises(ValueError, match="between 0 and 1"):
        flag_concentration(golden_valued_portfolio, threshold=-0.01)


def test_threshold_above_one_rejected(golden_valued_portfolio):
    with pytest.raises(ValueError, match="between 0 and 1"):
        flag_concentration(golden_valued_portfolio, threshold=1.01)


def test_nan_threshold_rejected(golden_valued_portfolio):
    with pytest.raises(ValueError, match="between 0 and 1"):
        flag_concentration(golden_valued_portfolio, threshold=math.nan)


def test_golden_weighted_volatility_components(golden_valued_portfolio):
    components = add_weighted_volatility_components(golden_valued_portfolio)

    assert components["weighted_volatility_component"].tolist() == pytest.approx(
        [0.0072, 0.0045, 0.0018, 0.0]
    )


def test_golden_weighted_volatility_exposure(golden_valued_portfolio):
    components = add_weighted_volatility_components(golden_valued_portfolio)

    assert weighted_volatility_exposure(components) == pytest.approx(0.0135)


def test_cash_weighted_volatility_component_is_zero(golden_valued_portfolio):
    components = add_weighted_volatility_components(golden_valued_portfolio)
    cash = components[components["ticker"] == "CASH"]

    assert cash["weight"].item() == pytest.approx(0.10)
    assert cash["weighted_volatility_component"].item() == 0.0


def test_valued_dataframe_is_not_changed(golden_valued_portfolio):
    before = golden_valued_portfolio.copy()

    flag_concentration(golden_valued_portfolio)
    add_weighted_volatility_components(golden_valued_portfolio)
    largest_position(golden_valued_portfolio)

    pd.testing.assert_frame_equal(golden_valued_portfolio, before)


def test_row_order_is_unchanged(golden_valued_portfolio):
    flagged = flag_concentration(golden_valued_portfolio)
    components = add_weighted_volatility_components(golden_valued_portfolio)

    assert flagged["ticker"].tolist() == GOLDEN_TICKERS
    assert components["ticker"].tolist() == GOLDEN_TICKERS


def test_risk_column_dtypes(golden_valued_portfolio):
    flagged = flag_concentration(golden_valued_portfolio)
    components = add_weighted_volatility_components(golden_valued_portfolio)

    assert flagged["above_threshold"].dtype == "bool"
    assert components["weighted_volatility_component"].dtype == "float64"
    assert isinstance(weighted_volatility_exposure(components), float)
