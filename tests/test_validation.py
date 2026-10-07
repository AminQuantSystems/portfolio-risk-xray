import pandas as pd
import pytest

from portfolio_risk.validation import PortfolioDataError, load_portfolio

HEADER = "ticker,quantity,price,daily_volatility"
VALID_ROW = "MSFT,100,300,0.015"


def csv_text(*rows: str, header: str = HEADER) -> str:
    return "\n".join([header, *rows]) + "\n"


def test_golden_csv_loads(golden_csv_path):
    portfolio = load_portfolio(golden_csv_path)

    expected = pd.DataFrame(
        {
            "ticker": pd.array(["AAPL", "MSFT", "TLT", "CASH"], dtype="string"),
            "quantity": [100.0, 100.0, 200.0, 1.0],
            "price": [400.0, 300.0, 100.0, 10000.0],
            "daily_volatility": [0.018, 0.015, 0.009, 0.0],
        }
    )
    pd.testing.assert_frame_equal(portfolio, expected)


def test_ticker_whitespace_is_stripped(write_csv):
    path = write_csv(csv_text("  AAPL  ,100,400,0.018", VALID_ROW))

    assert load_portfolio(path)["ticker"].tolist() == ["AAPL", "MSFT"]


def test_ticker_case_is_normalised_to_uppercase(write_csv):
    path = write_csv(csv_text("aapl,100,400,0.018", "Msft,100,300,0.015"))

    assert load_portfolio(path)["ticker"].tolist() == ["AAPL", "MSFT"]


def test_ticker_na_is_kept_as_literal_ticker(write_csv):
    path = write_csv(csv_text("NA,100,400,0.018", VALID_ROW))

    tickers = load_portfolio(path)["ticker"]

    assert tickers.tolist() == ["NA", "MSFT"]
    assert not tickers.isna().any()


def test_missing_ticker_rejected(write_csv):
    path = write_csv(csv_text(VALID_ROW, ",100,400,0.018"))

    with pytest.raises(PortfolioDataError, match="ticker is missing: line 3"):
        load_portfolio(path)


def test_blank_ticker_rejected(write_csv):
    path = write_csv(csv_text(VALID_ROW, "   ,100,400,0.018"))

    with pytest.raises(PortfolioDataError, match="ticker is blank: line 3"):
        load_portfolio(path)


@pytest.mark.parametrize("duplicate", ["AAPL", "aapl", " AAPL ", "Aapl"])
def test_duplicate_ticker_rejected_after_normalisation(write_csv, duplicate):
    path = write_csv(csv_text("AAPL,100,400,0.018", f"{duplicate},50,400,0.018"))

    with pytest.raises(PortfolioDataError, match="ticker is duplicated"):
        load_portfolio(path)


def test_zero_quantity_rejected(write_csv):
    path = write_csv(csv_text(VALID_ROW, "AAPL,0,400,0.018"))

    with pytest.raises(PortfolioDataError, match="quantity must be greater than 0.*line 3 AAPL"):
        load_portfolio(path)


def test_negative_quantity_rejected(write_csv):
    path = write_csv(csv_text(VALID_ROW, "AAPL,-100,400,0.018"))

    with pytest.raises(PortfolioDataError, match="quantity must be greater than 0.*line 3 AAPL"):
        load_portfolio(path)


def test_zero_price_rejected(write_csv):
    path = write_csv(csv_text(VALID_ROW, "AAPL,100,0,0.018"))

    with pytest.raises(PortfolioDataError, match="price must be greater than 0.*line 3 AAPL"):
        load_portfolio(path)


def test_negative_price_rejected(write_csv):
    path = write_csv(csv_text(VALID_ROW, "AAPL,100,-400,0.018"))

    with pytest.raises(PortfolioDataError, match="price must be greater than 0.*line 3 AAPL"):
        load_portfolio(path)


@pytest.mark.parametrize(
    ("row", "column"),
    [
        ("AAPL,ten,400,0.018", "quantity"),
        ("AAPL,100,£400,0.018", "price"),
        ("AAPL,100,400,1.8%", "daily_volatility"),
    ],
)
def test_non_numeric_value_rejected(write_csv, row, column):
    path = write_csv(csv_text(VALID_ROW, row))

    with pytest.raises(PortfolioDataError, match=f"{column} is not a number: line 3 AAPL"):
        load_portfolio(path)


def test_missing_volatility_rejected(write_csv):
    path = write_csv(csv_text(VALID_ROW, "AAPL,100,400,"))

    with pytest.raises(PortfolioDataError, match="daily_volatility is missing: line 3 AAPL"):
        load_portfolio(path)


def test_negative_volatility_rejected(write_csv):
    path = write_csv(csv_text(VALID_ROW, "AAPL,100,400,-0.018"))

    with pytest.raises(PortfolioDataError, match="daily_volatility must not be negative: line 3 AAPL"):
        load_portfolio(path)


def test_volatility_above_one_rejected(write_csv):
    path = write_csv(csv_text(VALID_ROW, "AAPL,100,400,1.8"))

    with pytest.raises(PortfolioDataError, match="daily_volatility must not exceed 1.0.*line 3 AAPL"):
        load_portfolio(path)


def test_zero_volatility_allowed(write_csv):
    path = write_csv(csv_text(VALID_ROW, "CASH,1,10000,0.0"))

    portfolio = load_portfolio(path)

    assert portfolio["daily_volatility"].tolist() == [0.015, 0.0]


def test_empty_file_rejected(write_csv):
    path = write_csv("")

    with pytest.raises(PortfolioDataError, match="is empty"):
        load_portfolio(path)


def test_header_without_positions_rejected(write_csv):
    path = write_csv(csv_text())

    with pytest.raises(PortfolioDataError, match="contains no positions"):
        load_portfolio(path)


def test_missing_required_column_rejected(write_csv):
    path = write_csv(csv_text("AAPL,100,400", header="ticker,quantity,price"))

    with pytest.raises(PortfolioDataError, match=r"missing \['daily_volatility'\]"):
        load_portfolio(path)


def test_extra_column_rejected(write_csv):
    header = f"{HEADER},sector"
    path = write_csv(csv_text("AAPL,100,400,0.018,Tech", header=header))

    with pytest.raises(PortfolioDataError, match=r"unexpected \['sector'\]"):
        load_portfolio(path)


def test_columns_in_any_order_are_returned_in_canonical_order(write_csv):
    header = "daily_volatility,price,ticker,quantity"
    path = write_csv(csv_text("0.018,400,AAPL,100", "0.015,300,MSFT,100", header=header))

    portfolio = load_portfolio(path)

    assert list(portfolio.columns) == ["ticker", "quantity", "price", "daily_volatility"]
    assert portfolio.iloc[0].tolist() == ["AAPL", 100.0, 400.0, 0.018]
    assert portfolio.iloc[1].tolist() == ["MSFT", 100.0, 300.0, 0.015]


def test_missing_file_raises_portfolio_data_error(tmp_path):
    path = tmp_path / "does_not_exist.csv"

    with pytest.raises(PortfolioDataError, match="portfolio file not found") as error:
        load_portfolio(path)

    assert str(path) in str(error.value)
    assert isinstance(error.value.__cause__, FileNotFoundError)


def test_non_utf8_file_raises_portfolio_data_error(tmp_path):
    path = tmp_path / "portfolio.csv"
    path.write_bytes(b"ticker,quantity,price,daily_volatility\n\xff\xfeAAPL,100,400,0.018\n")

    with pytest.raises(PortfolioDataError) as error:
        load_portfolio(path)

    assert str(error.value) == f"portfolio file is not valid UTF-8 text: {path}"
    assert isinstance(error.value.__cause__, UnicodeDecodeError)


def test_blank_row_inside_csv_rejected(write_csv):
    path = write_csv(csv_text("AAPL,100,400,0.018", "", VALID_ROW))

    with pytest.raises(PortfolioDataError, match="ticker is missing: line 3"):
        load_portfolio(path)


def test_rows_with_more_fields_than_header_rejected(write_csv):
    path = write_csv(csv_text("AAPL,100,400,0.018,0.5"))

    with pytest.raises(PortfolioDataError, match="more fields than the header"):
        load_portfolio(path)
