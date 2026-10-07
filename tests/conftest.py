from collections.abc import Callable
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def golden_csv_path() -> Path:
    return PROJECT_ROOT / "data" / "sample_portfolio.csv"


@pytest.fixture
def write_csv(tmp_path: Path) -> Callable[[str], Path]:
    """Write CSV text to a temporary file and return its path."""

    def _write(text: str) -> Path:
        path = tmp_path / "portfolio.csv"
        path.write_text(text, encoding="utf-8")
        return path

    return _write
