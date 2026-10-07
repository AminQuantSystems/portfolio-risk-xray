import pandas as pd
import pytest

from portfolio_risk.validation import PortfolioDataError
from portfolio_risk.valuation import total_portfolio_value, value_portfolio


def validated_frame(quantities: list[float], prices: list[float]) -> pd.DataFrame:
    """Build a frame shaped like load_portfolio output, for totals no CSV can easily reach."""
    tickers = [f"T{number}" for number in range(len(quantities))]
    return pd.DataFrame(
        {
            "ticker": pd.array(tickers, dtype="string"),
            "quantity": pd.Series(quantities, dtype="float64"),
            "price": pd.Series(prices, dtype="float64"),
            "daily_volatility": pd.Series([0.01] * len(quantities), dtype="float64"),
        }
    )


def test_golden_market_values(golden_portfolio):
    valued = value_portfolio(golden_portfolio)

    assert valued["market_value"].tolist() == [40_000.0, 30_000.0, 20_000.0, 10_000.0]


def test_golden_total_portfolio_value(golden_portfolio):
    valued = value_portfolio(golden_portfolio)

    assert total_portfolio_value(valued) == 100_000.0


def test_golden_weights(golden_portfolio):
    valued = value_portfolio(golden_portfolio)

    assert valued["weight"].tolist() == pytest.approx([0.40, 0.30, 0.20, 0.10])


def test_weights_sum_to_one(golden_portfolio):
    valued = value_portfolio(golden_portfolio)

    assert valued["weight"].sum() == pytest.approx(1.0)


def test_columns_and_numeric_dtypes(golden_portfolio):
    valued = value_portfolio(golden_portfolio)

    assert list(valued.columns) == [
        "ticker",
        "quantity",
        "price",
        "daily_volatility",
        "market_value",
        "weight",
    ]
    for column in ["quantity", "price", "daily_volatility", "market_value", "weight"]:
        assert valued[column].dtype == "float64", column


def test_input_dataframe_is_not_changed(golden_portfolio):
    before = golden_portfolio.copy()

    value_portfolio(golden_portfolio)

    pd.testing.assert_frame_equal(golden_portfolio, before)


def test_row_order_is_unchanged(golden_portfolio):
    valued = value_portfolio(golden_portfolio)

    assert valued["ticker"].tolist() == ["AAPL", "MSFT", "TLT", "CASH"]


def test_zero_total_portfolio_value_rejected():
    empty = validated_frame([], [])

    with pytest.raises(PortfolioDataError, match="total portfolio value is zero"):
        value_portfolio(empty)


def test_non_finite_total_portfolio_value_rejected():
    # Each input is finite, but 1e200 * 1e200 overflows to infinity.
    overflowing = validated_frame([1e200], [1e200])

    with pytest.raises(PortfolioDataError, match="total portfolio value is not finite"):
        value_portfolio(overflowing)
