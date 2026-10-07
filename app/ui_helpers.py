"""Presentation helpers for the Portfolio Risk X-Ray interface.

These functions only format values already produced by analyse_portfolio.
They perform no finance calculations. Every user-derived string placed in
markup, such as tickers, file names and error text, goes through html.escape.
"""

from html import escape
from pathlib import Path
from typing import Any

import pandas as pd

# Segments below BAND_LABEL_MIN_WEIGHT are always labelled beneath the band. Segments below
# BAND_TIGHT_WEIGHT also carry a beneath-band label that CSS shows only when the band is narrow.
BAND_LABEL_MIN_WEIGHT = 0.08
BAND_TIGHT_WEIGHT = 0.15


def format_currency(value: float) -> str:
    return f"£{value:,.0f}"


def format_percent(fraction: float, decimals: int = 1) -> str:
    return f"{fraction:.{decimals}%}"


def threshold_from_percent(percent: float) -> float:
    return percent / 100


def concentration_label(above_threshold: bool) -> str:
    return "Above threshold" if above_threshold else "Within threshold"


def count_flagged(positions: pd.DataFrame) -> int:
    return int(positions["above_threshold"].sum())


def user_error_message(error: Exception, display_name: str, path: Path) -> str:
    """Return the error text with the internal file path replaced by the name the user knows."""
    return str(error).replace(str(path), display_name)


def header_html(source_label: str) -> str:
    return (
        '<div class="xr-header">'
        '<div class="xr-title">Portfolio Risk X-Ray</div>'
        '<div class="xr-subtitle">Transparent portfolio diagnostics</div>'
        f'<div class="xr-source">Source: {escape(source_label)}</div>'
        "</div>"
    )


def error_html(message: str) -> str:
    return (
        '<div class="xr-error">'
        '<div class="xr-error-title">Analysis could not run</div>'
        f"<div>{escape(message)}</div>"
        "</div>"
    )


def metrics_html(analysis: dict[str, Any]) -> str:
    positions = analysis["positions"]
    largest = analysis["largest_position"]
    flagged = count_flagged(positions)
    flagged_class = " is-above" if flagged else ""
    return (
        '<div class="xr-metrics">'
        + _metric_cell(
            "Portfolio value",
            format_currency(analysis["total_portfolio_value"]),
            "Sum of market values",
            "primary",
        )
        + _metric_cell(
            "Largest position",
            largest["ticker"],
            f"{format_percent(largest['weight'])} weight",
            "secondary",
        )
        + _metric_cell(
            "Weighted volatility exposure",
            format_percent(analysis["weighted_volatility_exposure"], 2),
            "Per day. Not portfolio volatility",
            "secondary",
        )
        + "</div>"
        '<div class="xr-supporting">'
        f"<span><b>{len(positions)}</b> positions</span>"
        f'<span class="xr-breaches{flagged_class}"><b>{flagged}</b> above threshold</span>'
        f"<span>Threshold <b>{format_percent(analysis['concentration_threshold'])}</b>"
        " · breach when weight &gt; threshold</span>"
        "</div>"
    )


def allocation_band_html(positions: pd.DataFrame, total_value: float, threshold: float) -> str:
    """Portfolio X-Ray: one 100% band, one segment per position, width equal to engine weight."""
    ranked = _rank(positions, "weight")
    segments = []
    beneath = []
    always_beneath = False
    for index, row in enumerate(ranked.itertuples(index=False)):
        ticker = escape(row.ticker)
        weight = format_percent(row.weight)
        inline = row.weight >= BAND_LABEL_MIN_WEIGHT
        tight = inline and row.weight < BAND_TIGHT_WEIGHT
        classes = (
            "xr-seg"
            + (" is-alt" if index % 2 else "")
            + (" is-above" if row.above_threshold else "")
            + (" is-tight" if tight else "")
        )
        label = (
            f'<span class="xr-seg-ticker">{ticker}</span><span class="xr-seg-weight">{weight}</span>'
            if inline
            else ""
        )
        segments.append(f'<div class="{classes}" style="width:{row.weight:.4%}">{label}</div>')
        if not inline or tight:
            always_beneath = always_beneath or not inline
            fallback = ' class="xr-fallback"' if tight else ""
            beneath.append(f"<span{fallback}><b>{ticker}</b> {weight}</span>")
    small = (
        f'<div class="xr-band-small{"" if always_beneath else " is-fallback-only"}">'
        "<span>Smaller positions:</span>" + "".join(beneath) + "</div>"
        if beneath
        else ""
    )
    return (
        '<div class="xr-xray">'
        '<div class="xr-xray-head">'
        '<div><div class="xr-xray-title">Portfolio X-Ray</div>'
        '<div class="xr-question">Where is the portfolio capital allocated?</div></div>'
        f'<div class="xr-xray-total">{format_currency(total_value)} = 100%</div>'
        "</div>"
        f'<div class="xr-band">{"".join(segments)}</div>'
        f"{small}"
        '<div class="xr-chart-note">Segment width is the position weight. An amber edge marks '
        f"a weight above the {format_percent(threshold)} concentration threshold.</div>"
        "</div>"
    )


def concentration_scan_html(positions: pd.DataFrame, threshold: float) -> str:
    """One equal-sized ring per position: progress round the ring is the weight on a 0–100% scale."""
    ranked = _rank(positions, "weight")
    rings = []
    for row in ranked.itertuples(index=False):
        ticker = escape(row.ticker)
        weight = format_percent(row.weight)
        state = "ABOVE" if row.above_threshold else "WITHIN"
        state_class = " is-above" if row.above_threshold else ""
        rings.append(
            f'<div class="xr-ring{state_class}" role="img" '
            f'aria-label="{ticker} {weight} weight, {state.lower()} threshold">'
            '<div class="xr-ring-dial">'
            + _ring_svg(row.weight, row.above_threshold, threshold)
            + f'<span class="xr-ring-weight">{weight}</span>'
            "</div>"
            f'<div class="xr-ring-ticker">{ticker}</div>'
            f'<div class="xr-state">{state}</div>'
            "</div>"
        )
    return _chart(
        "Concentration scan",
        "Which positions breach the concentration threshold?",
        f'<div class="xr-scan-threshold">Threshold · <b>{format_percent(threshold)}</b></div>'
        '<div class="xr-rings">' + "".join(rings) + "</div>"
        '<div class="xr-chart-note">Blue = within threshold · Amber = excess concentration</div>',
    )


def weighted_volatility_chart_html(positions: pd.DataFrame, exposure: float) -> str:
    """Horizontal bars of weighted_volatility_component, with the engine total shown above."""
    ranked = _rank(positions, "weighted_volatility_component")
    largest = ranked["weighted_volatility_component"].max()
    rows = []
    for row in ranked.itertuples(index=False):
        component = row.weighted_volatility_component
        rows.append(
            '<div class="xr-row">'
            f'<span class="xr-ticker">{escape(row.ticker)}</span>'
            + _bar_plot(component / largest if largest > 0 else 0.0, format_percent(component, 2))
            + "</div>"
        )
    return _chart(
        "Weighted volatility exposure",
        "Which positions make up the weighted volatility exposure?",
        '<div class="xr-total">'
        f'<div class="xr-total-value">{format_percent(exposure, 2)} / day</div>'
        '<div class="xr-total-label">Total weighted volatility exposure</div>'
        "</div>"
        '<div class="xr-rows">' + "".join(rows) + "</div>"
        '<div class="xr-chart-note">Weight × stand-alone daily volatility. '
        "Correlation is not included.</div>",
    )


def exposure_breakdown_html(positions: pd.DataFrame) -> str:
    head = "".join(
        f'<th scope="col">{label}</th>'
        for label in [
            "Ticker",
            "Market value",
            "Weight",
            "Daily volatility",
            "Weighted volatility component",
            "Concentration",
        ]
    )
    body = []
    for row in positions.itertuples(index=False):
        cells = [
            escape(row.ticker),
            format_currency(row.market_value),
            format_percent(row.weight),
            format_percent(row.daily_volatility, 2),
            format_percent(row.weighted_volatility_component, 2),
            concentration_label(row.above_threshold),
        ]
        state_class = ' class="is-above"' if row.above_threshold else ""
        body.append(f"<tr{state_class}>" + "".join(f"<td>{cell}</td>" for cell in cells) + "</tr>")
    return (
        '<div class="xr-table-wrap"><table class="xr-table">'
        f"<thead><tr>{head}</tr></thead>"
        f"<tbody>{''.join(body)}</tbody>"
        "</table></div>"
    )


def calculation_trace(analysis: dict[str, Any]) -> list[tuple[str, str]]:
    """Return (title, html) pairs explaining each result with values read from the analysis."""
    positions = analysis["positions"]
    ticker = analysis["largest_position"]["ticker"]
    row = positions.loc[positions["ticker"] == ticker].iloc[0]
    total = analysis["total_portfolio_value"]
    threshold = analysis["concentration_threshold"]
    exposure = analysis["weighted_volatility_exposure"]
    components = " + ".join(
        format_percent(value, 2) for value in positions["weighted_volatility_component"]
    )
    return [
        (
            "Portfolio weight",
            _trace_html(
                "weight = market_value ÷ total_portfolio_value",
                f"{ticker}: {format_currency(row['market_value'])} ÷ {format_currency(total)}"
                f" = {format_percent(row['weight'])}",
                "Each position's share of total portfolio value. Weights sum to 100%.",
            ),
        ),
        (
            "Concentration flag",
            _trace_html(
                "above_threshold = weight > concentration_threshold",
                f"{ticker}: {format_percent(row['weight'])} > {format_percent(threshold)}"
                f" is {'true' if row['above_threshold'] else 'false'},"
                f" so {concentration_label(row['above_threshold']).lower()}",
                "Strictly greater than. A weight equal to the threshold is not flagged. "
                "Displayed values are rounded; the comparison uses the exact weight.",
            ),
        ),
        (
            "Weighted volatility component",
            _trace_html(
                "weighted_volatility_component = weight × daily_volatility",
                f"{ticker}: {format_percent(row['weight'])} × {format_percent(row['daily_volatility'], 2)}"
                f" = {format_percent(row['weighted_volatility_component'], 2)}",
                "A position's stand-alone daily volatility scaled by its portfolio weight.",
            ),
        ),
        (
            "Weighted volatility exposure",
            _trace_html(
                "weighted_volatility_exposure = Σ(weighted_volatility_component)",
                f"{components} = {format_percent(exposure, 2)} per day",
                "A simple daily exposure indicator. It ignores correlations and is not portfolio "
                "volatility, marginal or component risk contribution, VaR or expected loss. "
                "Displayed values are rounded.",
            ),
        ),
    ]


def _rank(positions: pd.DataFrame, column: str) -> pd.DataFrame:
    """Largest first for display; stable so ties keep file order."""
    return positions.sort_values(column, ascending=False, kind="stable")


def _ring_svg(weight: float, above_threshold: bool, threshold: float) -> str:
    """Arcs on a fixed-size circle whose pathLength is 100, so dash lengths are weight percentages.

    Blue covers the weight up to the threshold; amber appears only when the engine flags the
    position, covering weight beyond the threshold. Arcs start at 12 o'clock and run clockwise.
    """
    blue = threshold if above_threshold else weight
    circle = 'cx="50" cy="50" r="42" pathLength="100" transform="rotate(-90 50 50)"'
    arcs = (
        f'<circle class="xr-ring-track" {circle}/>'
        f'<circle class="xr-ring-blue" {circle} stroke-dasharray="{blue * 100:.4f} 100"/>'
    )
    if above_threshold:
        arcs += (
            f'<circle class="xr-ring-amber" {circle} '
            f'stroke-dasharray="{(weight - threshold) * 100:.4f} 100" '
            f'stroke-dashoffset="{-threshold * 100:.4f}"/>'
        )
    tick = (
        f'<line class="xr-ring-tick" x1="50" y1="1" x2="50" y2="15" '
        f'transform="rotate({threshold * 360:.4f} 50 50)"/>'
    )
    return f'<svg class="xr-ring-svg" viewBox="0 0 100 100" aria-hidden="true">{arcs}{tick}</svg>'


def _bar_plot(fraction: float, label: str) -> str:
    return (
        '<span class="xr-plot">'
        f'<span class="xr-bar" style="width:{fraction:.4%}"></span>'
        f'<span class="xr-bar-label" style="left:{fraction:.4%}">{escape(label)}</span>'
        "</span>"
    )


def _chart(title: str, question: str, body: str) -> str:
    return (
        '<div class="xr-chart">'
        f'<div class="xr-chart-title">{escape(title)}</div>'
        f'<div class="xr-question">{escape(question)}</div>'
        f"{body}</div>"
    )


def _metric_cell(label: str, value: str, note: str, tier: str) -> str:
    return (
        f'<div class="xr-metric is-{tier}">'
        f'<div class="xr-label">{escape(label)}</div>'
        f'<div class="xr-value">{escape(value)}</div>'
        f'<div class="xr-note">{escape(note)}</div>'
        "</div>"
    )


def _trace_html(formula: str, example: str, explanation: str) -> str:
    return (
        '<div class="xr-trace">'
        f'<code class="xr-formula">{escape(formula)}</code>'
        f'<div class="xr-example">{escape(example)}</div>'
        f'<div class="xr-note">{escape(explanation)}</div>'
        "</div>"
    )
