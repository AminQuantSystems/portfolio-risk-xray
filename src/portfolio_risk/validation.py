"""Load a portfolio CSV and reject invalid positions.

Bad data always raises PortfolioDataError. Rows are never dropped, missing
values are never filled, and invalid numbers are never repaired.
"""

import math
from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = ["ticker", "quantity", "price", "daily_volatility"]
NUMERIC_COLUMNS = ["quantity", "price", "daily_volatility"]
MAX_DAILY_VOLATILITY = 1.0


class PortfolioDataError(ValueError):
    """Portfolio input is missing, malformed, or financially invalid."""


def load_portfolio(path: str | Path) -> pd.DataFrame:
    """Read a portfolio CSV and return validated positions.

    Returned columns: ticker (string), quantity, price, daily_volatility (float64).
    """
    raw = _read_csv_as_text(path)
    _check_columns(raw)
    if raw.empty:
        raise PortfolioDataError(f"{path} contains no positions")

    portfolio = pd.DataFrame({"ticker": _normalise_tickers(raw["ticker"])})
    for column in NUMERIC_COLUMNS:
        portfolio[column] = _parse_numbers(raw[column], portfolio["ticker"])
    _check_ranges(portfolio)
    return portfolio[REQUIRED_COLUMNS]


def _read_csv_as_text(path: str | Path) -> pd.DataFrame:
    # Read every field as text so pandas cannot guess types, and only an empty
    # field counts as missing: tickers such as "NA" must stay as written.
    try:
        raw = pd.read_csv(
            path,
            dtype=str,
            keep_default_na=False,
            na_values=[""],
            skip_blank_lines=False,
        )
    except FileNotFoundError as error:
        raise PortfolioDataError(f"portfolio file not found: {path}") from error
    except pd.errors.EmptyDataError as error:
        raise PortfolioDataError(f"{path} is empty") from error
    except pd.errors.ParserError as error:
        raise PortfolioDataError(f"{path} could not be parsed: {error}") from error

    # If every row has more fields than the header, pandas silently uses the
    # first field as the index and shifts every column one place left.
    if not raw.index.equals(pd.RangeIndex(len(raw))):
        raise PortfolioDataError(f"{path} has rows with more fields than the header")
    return raw


def _check_columns(raw: pd.DataFrame) -> None:
    columns = list(raw.columns)
    missing = [column for column in REQUIRED_COLUMNS if column not in columns]
    unexpected = [column for column in columns if column not in REQUIRED_COLUMNS]
    if missing or unexpected:
        raise PortfolioDataError(
            f"columns must be exactly {REQUIRED_COLUMNS} in any order; "
            f"found {columns} (missing {missing}, unexpected {unexpected})"
        )


def _normalise_tickers(raw_tickers: pd.Series) -> pd.Series:
    _reject(raw_tickers.isna(), "ticker is missing")
    tickers = raw_tickers.str.strip().str.upper()
    _reject(tickers == "", "ticker is blank")
    _reject(tickers.duplicated(keep=False), "ticker is duplicated after normalisation", tickers)
    return tickers.astype("string")


def _parse_numbers(raw: pd.Series, tickers: pd.Series) -> pd.Series:
    text = raw.str.strip()
    _reject(text.isna() | (text == ""), f"{raw.name} is missing", tickers)

    # errors="coerce" only marks unparseable text as NaN so it can be reported below.
    numbers = pd.to_numeric(text, errors="coerce")
    _reject(numbers.isna(), f"{raw.name} is not a number", tickers, raw)
    _reject(numbers.isin([math.inf, -math.inf]), f"{raw.name} is not finite", tickers, raw)
    return numbers.astype("float64")


def _check_ranges(portfolio: pd.DataFrame) -> None:
    tickers = portfolio["ticker"]
    quantity = portfolio["quantity"]
    price = portfolio["price"]
    volatility = portfolio["daily_volatility"]

    _reject(quantity <= 0, "quantity must be greater than 0 (V1 is long-only)", tickers, quantity)
    _reject(price <= 0, "price must be greater than 0", tickers, price)
    _reject(volatility < 0, "daily_volatility must not be negative", tickers, volatility)
    _reject(
        volatility > MAX_DAILY_VOLATILITY,
        "daily_volatility must not exceed 1.0; enter 1.8% as 0.018",
        tickers,
        volatility,
    )


def _reject(
    invalid: pd.Series,
    problem: str,
    tickers: pd.Series | None = None,
    values: pd.Series | None = None,
) -> None:
    """Raise PortfolioDataError naming every invalid row, or do nothing."""
    if not invalid.any():
        return
    rows = []
    for index in invalid[invalid].index:
        # Line 1 is the header, so the first data row is line 2.
        label = f"line {index + 2}"
        if tickers is not None:
            label += f" {tickers[index]}"
        if values is not None:
            label += f" ({values[index]})"
        rows.append(label)
    raise PortfolioDataError(f"{problem}: {', '.join(rows)}")
