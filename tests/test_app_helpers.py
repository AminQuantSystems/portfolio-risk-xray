from pathlib import Path

import pytest

from portfolio_risk.analysis import analyse_portfolio
from ui_helpers import (
    allocation_band_html,
    calculation_trace,
    concentration_scan_html,
    concentration_label,
    count_flagged,
    error_html,
    exposure_breakdown_html,
    format_currency,
    format_percent,
    header_html,
    metrics_html,
    threshold_from_percent,
    user_error_message,
    weighted_volatility_chart_html,
)

MALICIOUS = "<script>alert(1)</script>"
QUOTED = "x\" onmouseover=\"alert(1)' x='"


@pytest.fixture
def golden_analysis(golden_csv_path):
    return analyse_portfolio(golden_csv_path)


@pytest.fixture
def malicious_analysis(write_csv):
    path = write_csv(f"ticker,quantity,price,daily_volatility\n{MALICIOUS},100,400,0.018\n")
    return analyse_portfolio(path)


@pytest.fixture
def quoted_analysis(write_csv):
    csv_field = '"' + QUOTED.replace('"', '""') + '"'
    path = write_csv(f"ticker,quantity,price,daily_volatility\n{csv_field},100,400,0.018\n")
    return analyse_portfolio(path)


def test_format_currency():
    assert format_currency(100_000.0) == "£100,000"


def test_format_percent():
    assert format_percent(0.4) == "40.0%"
    assert format_percent(0.013499999999999998, 2) == "1.35%"


def test_threshold_from_percent():
    assert threshold_from_percent(25.0) == 0.25


def test_concentration_label():
    assert concentration_label(True) == "Above threshold"
    assert concentration_label(False) == "Within threshold"


def test_count_flagged_counts_engine_flags(golden_analysis):
    assert count_flagged(golden_analysis["positions"]) == 2


def test_user_error_message_hides_internal_path():
    path = Path("C:/temp/abc123/portfolio.csv")
    error = ValueError(f"{path} is empty")

    assert user_error_message(error, "my_book.csv", path) == "my_book.csv is empty"


def test_metrics_show_engine_results(golden_analysis):
    html = metrics_html(golden_analysis)

    for text in ["£100,000", "AAPL", "40.0% weight", "Weighted volatility exposure", "1.35%", "25.0%"]:
        assert text in html
    assert "<b>4</b> positions" in html
    assert "<b>2</b> above threshold" in html
    assert "Threshold <b>25.0%</b> · breach when weight &gt; threshold" in html


def test_metrics_give_portfolio_value_primary_emphasis(golden_analysis):
    html = metrics_html(golden_analysis)

    assert html.count("is-primary") == 1
    assert html.count("is-secondary") == 2
    assert html.index("is-primary") < html.index("Portfolio value") < html.index("is-secondary")


def test_allocation_band_segments_use_engine_weights(golden_analysis):
    html = allocation_band_html(golden_analysis["positions"], 100_000.0, 0.25)

    for width in ["40.0000%", "30.0000%", "20.0000%", "10.0000%"]:
        assert f"width:{width}" in html
    for ticker, weight in [("AAPL", "40.0%"), ("MSFT", "30.0%"), ("TLT", "20.0%"), ("CASH", "10.0%")]:
        assert f'<span class="xr-seg-ticker">{ticker}</span><span class="xr-seg-weight">{weight}</span>' in html
    assert html.count("is-above") == 2


def test_allocation_band_keeps_every_position_as_its_own_segment(write_csv):
    rows = "\n".join(f"T{index},1,{price},0.01" for index, price in enumerate([9000, 500, 300, 100, 50, 50]))
    analysis = analyse_portfolio(write_csv(f"ticker,quantity,price,daily_volatility\n{rows}\n"))
    positions = analysis["positions"]

    html = allocation_band_html(positions, analysis["total_portfolio_value"], 0.25)

    assert html.count('<div class="xr-seg') == len(positions) == 6
    for weight in positions["weight"]:
        assert f"width:{weight:.4%}" in html
    assert "Smaller positions:" in html


def test_allocation_band_gives_mid_sized_segments_a_narrow_screen_fallback(golden_analysis):
    html = allocation_band_html(golden_analysis["positions"], 100_000.0, 0.25)

    assert html.count("is-tight") == 1
    assert '<div class="xr-band-small is-fallback-only">' in html
    assert '<span class="xr-fallback"><b>CASH</b> 10.0%</span>' in html


def test_allocation_band_labels_small_segments_beneath(golden_analysis):
    positions = golden_analysis["positions"].copy()
    positions.loc[positions["ticker"] == "CASH", "weight"] = 0.05

    html = allocation_band_html(positions, 100_000.0, 0.25)

    assert '<div class="xr-band-small"><span>Smaller positions:</span><span><b>CASH</b> 5.0%</span>' in html
    assert '<span class="xr-seg-ticker">CASH</span>' not in html


def _rings(html):
    """Split the scan into one chunk per ring, keyed by ticker."""
    chunks = html.split('role="img"')[1:]
    return {chunk.split('<div class="xr-ring-ticker">')[1].split("<")[0]: chunk for chunk in chunks}


def test_concentration_scan_draws_one_equal_ring_per_position(golden_analysis):
    html = concentration_scan_html(golden_analysis["positions"], 0.25)

    assert "Concentration scan" in html
    assert "Which positions breach the concentration threshold?" in html
    assert html.count('<svg class="xr-ring-svg" viewBox="0 0 100 100"') == 4
    assert html.count('r="42" pathLength="100"') == 4 + 4 + 2  # tracks, blue arcs, amber arcs
    assert html.count(">ABOVE<") == 2
    assert html.count(">WITHIN<") == 2
    assert "Threshold · <b>25.0%</b>" in html
    assert "Blue = within threshold · Amber = excess concentration" in html


def test_concentration_scan_splits_arcs_at_the_threshold(golden_analysis):
    rings = _rings(concentration_scan_html(golden_analysis["positions"], 0.25))

    expected = {
        "AAPL": ("25.0000", "15.0000"),
        "MSFT": ("25.0000", "5.0000"),
        "TLT": ("20.0000", None),
        "CASH": ("10.0000", None),
    }
    for ticker, (blue, amber) in expected.items():
        ring = rings[ticker]
        assert (
            'class="xr-ring-blue" cx="50" cy="50" r="42" pathLength="100" '
            f'transform="rotate(-90 50 50)" stroke-dasharray="{blue} 100"'
        ) in ring
        if amber is None:
            assert "xr-ring-amber" not in ring
        else:
            assert f'stroke-dasharray="{amber} 100" stroke-dashoffset="-25.0000"' in ring
        assert 'transform="rotate(90.0000 50 50)"' in ring


def test_concentration_scan_labels_weight_from_engine(golden_analysis):
    rings = _rings(concentration_scan_html(golden_analysis["positions"], 0.25))

    for ticker, weight in [("AAPL", "40.0%"), ("MSFT", "30.0%"), ("TLT", "20.0%"), ("CASH", "10.0%")]:
        assert f'<span class="xr-ring-weight">{weight}</span>' in rings[ticker]


def test_concentration_scan_uses_engine_flags(golden_analysis):
    positions = golden_analysis["positions"].copy()
    positions.loc[positions["ticker"] == "MSFT", "above_threshold"] = False

    rings = _rings(concentration_scan_html(positions, 0.25))

    assert ">WITHIN<" in rings["MSFT"]
    assert "xr-ring-amber" not in rings["MSFT"]
    assert 'stroke-dasharray="30.0000 100"' in rings["MSFT"]


def test_weighted_volatility_chart_uses_engine_components_and_total(golden_analysis):
    html = weighted_volatility_chart_html(
        golden_analysis["positions"], golden_analysis["weighted_volatility_exposure"]
    )

    assert '<div class="xr-chart-title">Weighted volatility exposure</div>' in html
    assert "Which positions make up the weighted volatility exposure?" in html
    assert '<div class="xr-total-value">1.35% / day</div>' in html
    assert '<div class="xr-total-label">Total weighted volatility exposure</div>' in html
    for width, label in [("100.0000%", "0.72%"), ("62.5000%", "0.45%"), ("25.0000%", "0.18%"), ("0.0000%", "0.00%")]:
        assert f'style="left:{width}">{label}</span>' in html
    assert "Weight × stand-alone daily volatility. Correlation is not included." in html
    assert "contribution" not in html.lower()


def test_weighted_volatility_chart_handles_zero_exposure(write_csv):
    analysis = analyse_portfolio(write_csv("ticker,quantity,price,daily_volatility\nCASH,1,10000,0.0\n"))

    html = weighted_volatility_chart_html(analysis["positions"], analysis["weighted_volatility_exposure"])

    assert 'class="xr-bar" style="width:0.0000%"' in html


def test_exposure_breakdown_columns_and_values(golden_analysis):
    html = exposure_breakdown_html(golden_analysis["positions"])

    for header in [
        "Ticker",
        "Market value",
        "Weight",
        "Daily volatility",
        "Weighted volatility component",
        "Concentration",
    ]:
        assert f'<th scope="col">{header}</th>' in html
    for value in ["£40,000", "£30,000", "£20,000", "£10,000", "0.72%", "0.45%", "0.18%", "0.00%"]:
        assert value in html
    assert html.count('class="is-above"') == 2


def test_calculation_trace_uses_engine_values(golden_analysis):
    trace = dict(calculation_trace(golden_analysis))

    assert list(trace) == [
        "Portfolio weight",
        "Concentration flag",
        "Weighted volatility component",
        "Weighted volatility exposure",
    ]
    assert "AAPL: £40,000 ÷ £100,000 = 40.0%" in trace["Portfolio weight"]
    assert "AAPL: 40.0% &gt; 25.0% is true, so above threshold" in trace["Concentration flag"]
    assert "Displayed values are rounded; the comparison uses the exact weight." in trace["Concentration flag"]
    assert "AAPL: 40.0% × 1.80% = 0.72%" in trace["Weighted volatility component"]
    assert "0.72% + 0.45% + 0.18% + 0.00% = 1.35% per day" in trace["Weighted volatility exposure"]


TICKER_RENDERERS = pytest.mark.parametrize(
    "render",
    [
        metrics_html,
        lambda analysis: allocation_band_html(analysis["positions"], 40_000.0, 0.25),
        lambda analysis: concentration_scan_html(analysis["positions"], 0.25),
        lambda analysis: weighted_volatility_chart_html(analysis["positions"], 0.018),
        lambda analysis: exposure_breakdown_html(analysis["positions"]),
        lambda analysis: "".join(body for _, body in calculation_trace(analysis)),
    ],
    ids=[
        "metrics",
        "allocation_band",
        "concentration",
        "weighted_volatility_chart",
        "exposure_breakdown",
        "calculation_trace",
    ],
)


@TICKER_RENDERERS
def test_malicious_ticker_is_escaped(malicious_analysis, render):
    html = render(malicious_analysis)

    assert "<SCRIPT>" not in html.upper()
    assert "&lt;SCRIPT&gt;ALERT(1)&lt;/SCRIPT&gt;" in html


@TICKER_RENDERERS
def test_quoted_ticker_is_escaped(quoted_analysis, render):
    html = render(quoted_analysis)

    assert QUOTED.upper() not in html
    assert "&quot; ONMOUSEOVER=&quot;ALERT(1)&#x27; X=&#x27;" in html


def test_malicious_file_name_is_escaped():
    html = header_html(f"{MALICIOUS}.csv")

    assert "<script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;.csv" in html


def test_quoted_file_name_is_escaped():
    html = header_html(f"{QUOTED}.csv")

    assert QUOTED not in html
    assert "&quot; onmouseover=&quot;alert(1)&#x27; x=&#x27;.csv" in html


def test_error_message_is_escaped():
    html = error_html(f"ticker is blank: {MALICIOUS}")

    assert "<script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


def test_quoted_error_message_is_escaped():
    html = error_html(f"ticker is blank: {QUOTED}")

    assert QUOTED not in html
    assert "&quot; onmouseover=&quot;alert(1)&#x27; x=&#x27;" in html
