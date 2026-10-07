from pathlib import Path

import pytest

pytest.importorskip("streamlit")

from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).resolve().parent.parent / "app" / "streamlit_app.py"


def test_app_renders_default_sample_without_exceptions():
    app = AppTest.from_file(str(APP_PATH), default_timeout=30).run()

    assert not app.exception
    rendered = "".join(element.proto.body for element in app.get("html"))
    assert "Source: sample_portfolio.csv" in rendered
    assert "£100,000" in rendered
    assert "Analysis could not run" not in rendered
