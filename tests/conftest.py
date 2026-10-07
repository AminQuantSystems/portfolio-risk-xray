from collections.abc import Callable
from pathlib import Path

import pandas as pd
import pytest

from portfolio_risk.validation import load_portfolio

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def golden_csv_path() -> Path:
    return PROJECT_ROOT / "data" / "sample_portfolio.csv"


@pytest.fixture
def golden_portfolio(golden_csv_path: Path) -> pd.DataFrame:
    """The validated £100,000 golden portfolio."""
    return load_portfolio(golden_csv_path)


@pytest.fixture
def write_csv(tmp_path: Path) -> Callable[[str], Path]:
    """Write CSV text to a temporary file and return its path."""

    def _write(text: str) -> Path:
        path = tmp_path / "portfolio.csv"
        path.write_text(text, encoding="utf-8")
        return path

    return _write
