import pytest

from portfolio_risk.analysis import analyse_portfolio
from portfolio_risk.validation import PortfolioDataError

GOLDEN_TICKERS = ["AAPL", "MSFT", "TLT", "CASH"]


def test_golden_portfolio_full_analysis(golden_csv_path):
    analysis = analyse_portfolio(golden_csv_path)

    assert set(analysis) == {
        "positions",
        "total_portfolio_value",
        "largest_position",
        "weighted_volatility_exposure",
        "concentration_threshold",
    }
    assert analysis["total_portfolio_value"] == 100_000.0
    assert analysis["largest_position"]["ticker"] == "AAPL"
    assert analysis["largest_position"]["weight"] == pytest.approx(0.40)
    assert analysis["weighted_volatility_exposure"] == pytest.approx(0.0135)
    assert analysis["concentration_threshold"] == 0.25
    assert analysis["positions"]["above_threshold"].tolist() == [True, True, False, False]

    for key in ["total_portfolio_value", "weighted_volatility_exposure", "concentration_threshold"]:
        assert type(analysis[key]) is float, key


def test_positions_columns_in_predictable_order(golden_csv_path):
    positions = analyse_portfolio(golden_csv_path)["positions"]

    assert list(positions.columns) == [
        "ticker",
        "quantity",
        "price",
        "daily_volatility",
        "market_value",
        "weight",
        "above_threshold",
        "weighted_volatility_component",
    ]


def test_tickers_keep_original_order(golden_csv_path):
    positions = analyse_portfolio(golden_csv_path)["positions"]

    assert positions["ticker"].tolist() == GOLDEN_TICKERS


def test_custom_concentration_threshold_is_passed_through(golden_csv_path):
    analysis = analyse_portfolio(golden_csv_path, concentration_threshold=0.35)

    assert analysis["concentration_threshold"] == 0.35
    assert analysis["positions"]["above_threshold"].tolist() == [True, False, False, False]


def test_invalid_file_raises_portfolio_data_error(write_csv):
    path = write_csv("ticker,quantity,price,daily_volatility\nAAPL,0,400,0.018\n")

    with pytest.raises(PortfolioDataError, match="quantity must be greater than 0"):
        analyse_portfolio(path)


def test_invalid_concentration_threshold_raises_value_error(golden_csv_path):
    with pytest.raises(ValueError, match="between 0 and 1"):
        analyse_portfolio(golden_csv_path, concentration_threshold=1.5)
