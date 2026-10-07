"""Portfolio Risk X-Ray local interface.

Run from the repository root:
    python -m streamlit run app/streamlit_app.py
"""

import tempfile
from pathlib import Path
from typing import Any

import streamlit as st

from portfolio_risk.analysis import analyse_portfolio
from portfolio_risk.risk import DEFAULT_CONCENTRATION_THRESHOLD
from portfolio_risk.validation import PortfolioDataError
from ui_helpers import (
    allocation_band_html,
    calculation_trace,
    concentration_scan_html,
    error_html,
    exposure_breakdown_html,
    header_html,
    metrics_html,
    threshold_from_percent,
    user_error_message,
    weighted_volatility_chart_html,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_PATH = PROJECT_ROOT / "data" / "sample_portfolio.csv"
STYLES = (Path(__file__).parent / "styles.css").read_text(encoding="utf-8")
DEFAULT_THRESHOLD_PERCENT = DEFAULT_CONCENTRATION_THRESHOLD * 100

Result = tuple[dict[str, Any] | None, str | None, str]


def analyse(path: Path, display_name: str, threshold: float) -> Result:
    try:
        return analyse_portfolio(path, concentration_threshold=threshold), None, display_name
    except PortfolioDataError as error:
        return None, user_error_message(error, display_name, path), display_name


def analyse_upload(upload: Any, threshold: float) -> Result:
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "portfolio.csv"
        path.write_bytes(upload.getvalue())
        return analyse(path, upload.name, threshold)


def render_controls() -> tuple[bool, Any, float]:
    with st.sidebar:
        st.html('<div class="xr-sidebar-title">Controls</div>')
        with st.form("controls"):
            upload = st.file_uploader(
                "Portfolio CSV",
                type=["csv"],
                help="Leave empty to analyse data/sample_portfolio.csv.",
            )
            threshold_percent = st.number_input(
                "Concentration threshold (%)",
                min_value=0.0,
                max_value=100.0,
                value=DEFAULT_THRESHOLD_PERCENT,
                step=1.0,
                format="%.1f",
            )
            submitted = st.form_submit_button("Analyse", type="primary", width="stretch")
        st.html(
            '<div class="xr-assumptions">Daily volatility · single currency · long-only positions</div>'
        )
    return submitted, upload, threshold_from_percent(threshold_percent)


def render_analysis(analysis: dict[str, Any]) -> None:
    positions = analysis["positions"]
    threshold = analysis["concentration_threshold"]
    st.html(metrics_html(analysis))
    st.html(allocation_band_html(positions, analysis["total_portfolio_value"], threshold))
    # st.html strips <svg>, which the concentration rings need. Every user-derived string in
    # this markup is escaped by ui_helpers, so allowing raw HTML here is safe.
    st.markdown(
        '<div class="xr-pair">'
        + concentration_scan_html(positions, threshold)
        + weighted_volatility_chart_html(positions, analysis["weighted_volatility_exposure"])
        + "</div>",
        unsafe_allow_html=True,
    )

    st.html('<div class="xr-section">Exposure breakdown</div>')
    st.html(exposure_breakdown_html(positions))

    st.html('<div class="xr-section">Calculation trace</div>')
    for title, body in calculation_trace(analysis):
        with st.expander(title):
            st.html(body)

    st.html(
        '<div class="xr-footnote">Weighted volatility exposure is a simple indicator. It is not '
        "portfolio volatility, marginal or component risk contribution, VaR or expected loss.</div>"
    )


def main() -> None:
    st.set_page_config(page_title="Portfolio Risk X-Ray", layout="wide")
    st.html(f"<style>{STYLES}</style>")

    submitted, upload, threshold = render_controls()
    if submitted and upload is not None:
        st.session_state["result"] = analyse_upload(upload, threshold)
    elif submitted or "result" not in st.session_state:
        st.session_state["result"] = analyse(SAMPLE_PATH, SAMPLE_PATH.name, threshold)

    analysis, error, source_label = st.session_state["result"]
    st.html(header_html(source_label))
    if error is not None:
        st.html(error_html(error))
        return
    render_analysis(analysis)


if __name__ == "__main__":
    main()
