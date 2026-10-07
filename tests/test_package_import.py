import pandas as pd

import portfolio_risk


def test_package_imports() -> None:
    assert portfolio_risk.__version__ == "0.1.0"
    assert isinstance(pd.__version__, str)
