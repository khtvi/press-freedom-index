"""
World Press Freedom Index Dashboard
==================================
Pure-Python Dash app.
Run locally with: python dash_app.py
Deploy with: gunicorn dash_app:server
"""

from __future__ import annotations

from pathlib import Path
import warnings

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from dash import Dash, Input, Output, dcc, html


warnings.filterwarnings("ignore")
APP_TITLE = "World Press Freedom Index"

COLORS = {
    "paper": "#f4efe6",
    "ink": "#0f172a",
    "panel": "#ffffff",
    "sidebar": "#161616",
    "muted": "#64748b",
    "red": "#b42318",
    "green": "#1f7a45",
    "gold": "#b8860b",
    "blue": "#12355b",
    "soft_blue": "#d9e7f4",
    "soft_red": "#f6ddd8",
}

ZONE_COLORS = ["#1f7a45", "#2f6690", "#c58b1b", "#d26a2e", "#b42318", "#7a7a7a"]
TREND_COLORS = ["#12355b", "#b42318", "#0f766e", "#2563eb", "#d97706", "#7c3aed", "#00897b"]
FREEDOM_BANDS: dict[str, tuple[str, tuple[int, int]]] = {
    "all": ("All Scores", (0, 100)),
    "good": ("Good", (85, 100)),
    "satisfactory": ("Satisfactory", (70, 84)),
    "problematic": ("Problematic", (55, 69)),
    "difficult": ("Difficult", (40, 54)),
    "serious": ("Very Serious", (0, 39)),
}


def find_data_file() -> Path | None:
    candidates = [
        Path("press_freedom_index.csv"),
        Path("press_freedom_index.xlsx"),
        Path("press-freedom_index.csv"),
        Path("press-freedom_index.xlsx"),
        Path("press_freedom_index.xls"),
        Path("press-freedom_index.xls"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def standardize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame.columns = frame.columns.str.strip().str.lower().str.replace(" ", "_", regex=False)
    rename_map: dict[str, str] = {}
    for source_name, target_name in [
        ("year_(n)", "year"),
        ("rank_n", "rank"),
        ("score_n", "score"),
        ("en_country", "country"),
        ("country_en", "country"),
        ("zone", "zone"),
        ("region", "region"),
        ("continent", "continent"),
    ]:
        if source_name in frame.columns:
            rename_map[source_name] = target_name

    iso_source = next((column for column in frame.columns if "iso" in column), None)
    if iso_source and iso_source != "iso":
        rename_map[iso_source] = "iso"

    return frame.rename(columns=rename_map)


def load_data(data_file: Path) -> pd.DataFrame:
    if data_file.suffix.lower() in {".xlsx", ".xls"}:
        excel_file = pd.ExcelFile(data_file)
        frames = [standardize_columns(excel_file.parse(sheet)) for sheet in excel_file.sheet_names]
        df = pd.concat(frames, ignore_index=True)
    else:
        df = standardize_columns(pd.read_csv(data_file))

    df = df.drop_duplicates()
    df["score"] = pd.to_numeric(df["score"].astype(str).str.replace(",", ".", regex=False), errors="coerce")
    df = df.dropna(subset=["score", "rank", "year", "country"])
    df["year"] = df["year"].astype(int)
    df["rank"] = df["rank"].astype(int)
    return df


DATA_FILE = find_data_file()
if DATA_FILE is None:
    raise FileNotFoundError("No press freedom dataset file was found in the app folder.")

DF = load_data(DATA_FILE)
REGION_COL = next((c for c in ["zone", "region", "continent"] if c in DF.columns), None)
ISO_COL = next((c for c in DF.columns if "iso" in c.lower()), None)
if REGION_COL and REGION_COL != "zone":
    DF = DF.rename(columns={REGION_COL: "zone"})
REGION_COL = "zone" if "zone" in DF.columns else None

YEARS = sorted(DF["year"].unique())
LATEST_YEAR = max(YEARS)
START_YEAR = min(YEARS)
LATEST_DF = DF[DF["year"] == LATEST_YEAR].copy()
DEFAULT_COUNTRIES = [c for c in ["Norway", "Finland", "Philippines", "China", "Russia", "United States"] if c in DF["country"].unique()]
SPOTLIGHT_DEFAULT = "Philippines" if "Philippines" in DF["country"].values else sorted(DF["country"].unique())[0]
ZONE_OPTIONS = sorted(DF["zone"].dropna().astype(str).unique().tolist()) if REGION_COL else []


def filter_year_df(
    year: int,
    zone: str,
    search: str,
    score_range: list[int] | tuple[int, int],
    band_key: str,
) -> pd.DataFrame:
    year_df = DF[DF["year"] == year].copy()
    if REGION_COL and zone != "All zones":
        year_df = year_df[year_df["zone"] == zone]
    if search:
        year_df = year_df[year_df["country"].str.contains(search, case=False, na=False)]

    band_min, band_max = FREEDOM_BANDS.get(band_key, FREEDOM_BANDS["all"])[1]
    slider_min, slider_max = score_range
    score_min = max(int(slider_min), band_min)
    score_max = min(int(slider_max), band_max)
    return year_df[(year_df["score"] >= score_min) & (year_df["score"] <= score_max)].copy()


def filtered_series_df(
    country: str,
    zone: str,
    search: str,
    score_range: list[int] | tuple[int, int],
    band_key: str,
    end_year: int,
) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for year in YEARS:
        if year > end_year:
            continue
        frame = filter_year_df(year, zone, search, score_range, band_key)
        country_frame = frame[frame["country"] == country]
        if not country_frame.empty:
            frames.append(country_frame)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=DF.columns)


def filtered_average_series(
    zone: str,
    search: str,
    score_range: list[int] | tuple[int, int],
    band_key: str,
    end_year: int,
) -> pd.DataFrame:
    rows: list[dict] = []
    for year in YEARS:
        if year > end_year:
            continue
        frame = filter_year_df(year, zone, search, score_range, band_key)
        rows.append({"year": year, "score": frame["score"].mean() if not frame.empty else None})
    return pd.DataFrame(rows)


def metric_card(label: str, value: str, sub: str, accent: str) -> html.Div:
    return html.Div(
        [
            html.Div(label, style={"fontFamily": "Courier New, monospace", "fontSize": "11px", "letterSpacing": "0.08em", "textTransform": "uppercase", "color": "#64748b"}),
            html.Div(value, style={"fontFamily": "Georgia, serif", "fontSize": "30px", "fontWeight": 700, "color": COLORS["ink"], "lineHeight": 1.05, "marginTop": "6px"}),
            html.Div(sub, style={"fontFamily": "Courier New, monospace", "fontSize": "11px", "color": "#64748b", "marginTop": "6px"}),
        ],
        style={
            "background": COLORS["panel"],
            "borderTop": f"4px solid {accent}",
            "padding": "16px",
            "borderRadius": "8px",
            "boxShadow": "0 6px 18px rgba(15,23,42,0.06)",
            "minHeight": "112px",
        },
    )


def empty_figure(title: str, message: str, height: int) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=message, x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False, font={"size": 16, "family": "Courier New"})
    fig.update_layout(
        title=title,
        height=height,
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin={"l": 20, "r": 20, "t": 55, "b": 20},
        xaxis={"visible": False},
        yaxis={"visible": False},
    )
    return fig


def styled_bar_figure(frame: pd.DataFrame, title: str, ascending: bool, color: str) -> go.Figure:
    if frame.empty:
        return empty_figure(title, "No countries match the active filters.", 360)
    ordered = frame.sort_values("score", ascending=ascending).head(10)
    fig = go.Figure(
        go.Bar(
            x=ordered["score"],
            y=ordered["country"],
            orientation="h",
            marker={"color": color},
            customdata=ordered["rank"],
            hovertemplate="%{y}<br>Score: %{x:.2f}<br>Rank: #%{customdata}<extra></extra>",
        )
    )
    fig.update_layout(
        title=title,
        height=360,
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin={"l": 20, "r": 20, "t": 55, "b": 30},
        font={"family": "Georgia, serif", "size": 14},
        xaxis={"title": "Score", "range": [0, 100], "gridcolor": "rgba(15,23,42,0.08)"},
        yaxis={"title": None, "autorange": "reversed"},
    )
    return fig


def zone_figure(frame: pd.DataFrame) -> go.Figure:
    if frame.empty or REGION_COL is None:
        return empty_figure("Average Score by Zone", "No zone data available for the active filters.", 360)
    zone_df = frame.groupby("zone", dropna=False)["score"].agg(["mean", "count"]).reset_index().sort_values("mean", ascending=False)
    zone_df["zone"] = zone_df["zone"].fillna("Unspecified")
    fig = go.Figure(
        go.Bar(
            x=zone_df["mean"],
            y=zone_df["zone"],
            orientation="h",
            marker={"color": ZONE_COLORS[: len(zone_df)]},
            customdata=zone_df["count"],
            hovertemplate="%{y}<br>Avg score: %{x:.2f}<br>Countries: %{customdata}<extra></extra>",
        )
    )
    fig.update_layout(
        title="Average Score by Zone",
        height=360,
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin={"l": 20, "r": 20, "t": 55, "b": 30},
        font={"family": "Georgia, serif", "size": 14},
        xaxis={"title": "Average Score", "range": [0, 100], "gridcolor": "rgba(15,23,42,0.08)"},
        yaxis={"title": None, "autorange": "reversed"},
    )
    return fig


def map_figure(frame: pd.DataFrame, spotlight_country: str) -> go.Figure:
    if frame.empty:
        return empty_figure("World Press Freedom Map", "No map rows match the current filters.", 540)
    map_frame = frame.copy()
    if ISO_COL and ISO_COL in map_frame.columns:
        fig = px.choropleth(
            map_frame,
            locations=ISO_COL,
            color="score",
            hover_name="country",
            hover_data={"rank": True, "score": ":.2f"},
            color_continuous_scale="RdYlGn",
            range_color=(0, 100),
        )
        focus = map_frame[map_frame["country"] == spotlight_country]
        if not focus.empty:
            fig.add_trace(
                go.Scattergeo(
                    locations=focus[ISO_COL],
                    locationmode="ISO-3",
                    text=focus["country"],
                    mode="markers",
                    marker={"size": 13, "color": "#f4efe6", "line": {"color": COLORS["red"], "width": 3}},
                    hovertemplate="%{text}<br>Spotlight country<extra></extra>",
                    showlegend=False,
                )
            )
    else:
        fig = px.choropleth(
            map_frame,
            locations="country",
            locationmode="country names",
            color="score",
            hover_name="country",
            hover_data={"rank": True, "score": ":.2f"},
            color_continuous_scale="RdYlGn",
            range_color=(0, 100),
        )
    fig.update_layout(
        title="World Press Freedom Map",
        height=540,
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin={"l": 0, "r": 0, "t": 55, "b": 0},
        font={"family": "Georgia, serif", "size": 14},
        geo={
            "projection": {"type": "natural earth", "scale": 1.1},
            "showframe": False,
            "showcoastlines": False,
            "showland": True,
            "landcolor": "#f8fafc",
            "showcountries": True,
            "countrycolor": "rgba(255,255,255,0.35)",
        },
    )
    return fig


def change_figure(frame: pd.DataFrame, selected_year: int, positive: bool) -> go.Figure:
    if frame.empty:
        title = "Most Improved" if positive else "Most Declined"
        return empty_figure(title, "No change comparison is available for these filters.", 360)
    start_map = DF[DF["year"] == START_YEAR].set_index("country")["score"]
    compare = frame[["country", "score"]].copy()
    compare["start"] = compare["country"].map(start_map)
    compare = compare.dropna()
    compare["change"] = compare["score"] - compare["start"]
    compare = compare.sort_values("change", ascending=not positive)
    compare = compare[compare["change"] > 0] if positive else compare[compare["change"] < 0]
    compare = compare.head(8)
    title = f"{'Most Improved' if positive else 'Most Declined'} ({START_YEAR} to {selected_year})"
    if compare.empty:
        return empty_figure(title, "No countries meet the comparison criteria.", 360)
    fig = go.Figure(
        go.Bar(
            x=compare["change"],
            y=compare["country"],
            orientation="h",
            marker={"color": COLORS["green"] if positive else COLORS["red"]},
            hovertemplate="%{y}<br>Change: %{x:.2f} pts<extra></extra>",
        )
    )
    fig.update_layout(
        title=title,
        height=360,
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin={"l": 20, "r": 20, "t": 55, "b": 30},
        font={"family": "Georgia, serif", "size": 14},
        xaxis={"title": "Score Change", "gridcolor": "rgba(15,23,42,0.08)"},
        yaxis={"title": None, "autorange": "reversed"},
    )
    return fig


def trend_figure(
    selected_year: int,
    zone: str,
    search: str,
    score_range: list[int] | tuple[int, int],
    band_key: str,
    countries: list[str],
) -> go.Figure:
    valid_years = [year for year in YEARS if year <= selected_year]
    if not countries:
        return empty_figure("Score Trends", "Select at least one visible country for the trend chart.", 430)
    fig = go.Figure()
    for index, country in enumerate(countries):
        series = filtered_series_df(country, zone, search, score_range, band_key, selected_year)
        if series.empty:
            continue
        fig.add_trace(
            go.Scatter(
                x=series["year"],
                y=series["score"],
                mode="lines+markers",
                name=country,
                line={"width": 3 if country == "Philippines" else 2.2, "color": TREND_COLORS[index % len(TREND_COLORS)]},
                marker={"size": 8},
                hovertemplate=f"{country}<br>Year: %{{x}}<br>Score: %{{y:.2f}}<extra></extra>",
            )
        )
    if not fig.data:
        return empty_figure("Score Trends", "No trend data remains after the active filters.", 430)
    fig.update_layout(
        title="Score Trends for Selected Countries",
        height=430,
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin={"l": 20, "r": 20, "t": 55, "b": 30},
        font={"family": "Georgia, serif", "size": 14},
        legend={"orientation": "h", "yanchor": "bottom", "y": -0.22, "x": 0},
        xaxis={"title": "Year", "tickmode": "array", "tickvals": valid_years, "gridcolor": "rgba(15,23,42,0.08)"},
        yaxis={"title": "Score", "range": [0, 100], "gridcolor": "rgba(15,23,42,0.08)"},
    )
    return fig


def spotlight_figure(
    spotlight_country: str,
    selected_year: int,
    zone: str,
    search: str,
    score_range: list[int] | tuple[int, int],
    band_key: str,
) -> go.Figure:
    series = filtered_series_df(spotlight_country, zone, search, score_range, band_key, selected_year)
    averages = filtered_average_series(zone, search, score_range, band_key, selected_year)
    if series.empty:
        return empty_figure("Country Spotlight", "The spotlight country is not available under the current filters.", 430)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=series["year"],
            y=series["score"],
            mode="lines+markers",
            name=spotlight_country,
            line={"color": COLORS["blue"], "width": 3},
            marker={"size": 8},
            fill="tozeroy",
            fillcolor="rgba(18,53,91,0.08)",
            hovertemplate=f"{spotlight_country}<br>Year: %{{x}}<br>Score: %{{y:.2f}}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=averages["year"],
            y=averages["score"],
            mode="lines",
            name="Filtered average",
            line={"color": COLORS["red"], "width": 2, "dash": "dash"},
            hovertemplate="Filtered average<br>Year: %{x}<br>Score: %{y:.2f}<extra></extra>",
        )
    )
    fig.update_layout(
        title=f"{spotlight_country} vs Filtered Average",
        height=430,
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin={"l": 20, "r": 20, "t": 55, "b": 30},
        font={"family": "Georgia, serif", "size": 14},
        legend={"orientation": "h", "yanchor": "bottom", "y": -0.22, "x": 0},
        xaxis={"title": "Year", "gridcolor": "rgba(15,23,42,0.08)"},
        yaxis={"title": "Score", "range": [0, 100], "gridcolor": "rgba(15,23,42,0.08)"},
    )
    return fig


def stats_for_rows(frame: pd.DataFrame, spotlight_country: str) -> tuple[list[html.Div], str, str, str, str, str, str, str]:
    if frame.empty:
        cards = [
            metric_card("Selected Year", "-", "No countries in view", COLORS["red"]),
            metric_card("Visible Avg", "-", "Adjust the filters", COLORS["blue"]),
            metric_card("Most Free", "-", "No visible country", COLORS["green"]),
            metric_card("Most Restricted", "-", "No visible country", COLORS["red"]),
            metric_card("Spotlight", "-", "No visible country", COLORS["gold"]),
        ]
        return cards, "0 countries visible", "-", "-", "Country Spotlight", "-", "-", "-"

    visible_avg = frame["score"].mean()
    best = frame.sort_values("score", ascending=False).iloc[0]
    worst = frame.sort_values("score", ascending=True).iloc[0]
    spotlight_row = frame[frame["country"] == spotlight_country]
    if spotlight_row.empty:
        spotlight_row = frame.sort_values("score", ascending=False).head(1)
    spotlight = spotlight_row.iloc[0]
    cards = [
        metric_card("Selected Year", str(int(frame["year"].iloc[0])), f"{len(frame)} countries visible", COLORS["red"]),
        metric_card("Visible Avg", f"{visible_avg:.1f}", "score out of 100", COLORS["blue"]),
        metric_card("Most Free", best["country"], f"score {best['score']:.2f} · rank #{int(best['rank'])}", COLORS["green"]),
        metric_card("Most Restricted", worst["country"], f"score {worst['score']:.2f} · rank #{int(worst['rank'])}", COLORS["red"]),
        metric_card(spotlight["country"], f"{spotlight['score']:.1f}", f"rank #{int(spotlight['rank'])} · {spotlight['score'] - visible_avg:+.1f} vs avg", COLORS["gold"]),
    ]
    best_label = best["country"]
    score_label = f"{spotlight['country']} score ({int(frame['year'].iloc[0])})"
    rank_label = f"{spotlight['country']} rank"
    change_label = f"{spotlight['country']} change since {START_YEAR}"
    delta_label = f"{spotlight['country']} vs filtered avg"
    return cards, f"{len(frame)} countries visible", f"{visible_avg:.2f}", best_label, f"{spotlight['country']} Spotlight", score_label, rank_label, change_label, delta_label


app = Dash(__name__)
server = app.server
app.title = APP_TITLE


def filter_panel() -> html.Div:
    return html.Div(
        [
            html.Div(
                [
                    html.Div("Data Snapshot", style={"fontFamily": "Courier New, monospace", "fontSize": "11px", "letterSpacing": "0.12em", "textTransform": "uppercase", "color": "#f29d8f", "marginBottom": "10px"}),
                    html.Div(
                        f"{len(DF)} rows loaded · {DF['country'].nunique()} countries · {START_YEAR}-{LATEST_YEAR}",
                        style={"padding": "12px 14px", "border": "1px solid #1f7a45", "background": "rgba(31,122,69,0.2)", "borderRadius": "8px", "fontFamily": "Courier New, monospace", "fontSize": "12px", "color": "#7dd3a0"},
                    ),
                ]
            ),
            html.Div(
                [
                    html.Div("Filters", style={"fontFamily": "Courier New, monospace", "fontSize": "11px", "letterSpacing": "0.12em", "textTransform": "uppercase", "color": "#f29d8f", "marginBottom": "10px"}),
                    html.Label("Year", style={"fontFamily": "Courier New, monospace", "fontSize": "11px", "textTransform": "uppercase", "color": "#cbd5e1"}),
                    dcc.Dropdown(options=[{"label": str(year), "value": int(year)} for year in sorted(YEARS, reverse=True)], value=LATEST_YEAR, id="year-dropdown", clearable=False),
                    html.Label("Zone", style={"fontFamily": "Courier New, monospace", "fontSize": "11px", "textTransform": "uppercase", "color": "#cbd5e1", "marginTop": "14px"}),
                    dcc.Dropdown(options=[{"label": "All zones", "value": "All zones"}] + [{"label": zone, "value": zone} for zone in ZONE_OPTIONS], value="All zones", id="zone-dropdown", clearable=False),
                    html.Label("Country Search", style={"fontFamily": "Courier New, monospace", "fontSize": "11px", "textTransform": "uppercase", "color": "#cbd5e1", "marginTop": "14px"}),
                    dcc.Input(id="country-search", type="text", placeholder="Filter by country", debounce=True, style={"width": "100%", "padding": "10px", "borderRadius": "8px", "border": "1px solid #334155", "background": "#0f172a", "color": "white"}),
                    html.Label("Spotlight Country", style={"fontFamily": "Courier New, monospace", "fontSize": "11px", "textTransform": "uppercase", "color": "#cbd5e1", "marginTop": "14px"}),
                    dcc.Dropdown(id="spotlight-dropdown", clearable=False),
                    html.Label("Score Range", style={"fontFamily": "Courier New, monospace", "fontSize": "11px", "textTransform": "uppercase", "color": "#cbd5e1", "marginTop": "14px"}),
                    dcc.RangeSlider(id="score-slider", min=0, max=100, step=1, value=[0, 100], marks={0: "0", 25: "25", 50: "50", 75: "75", 100: "100"}),
                    html.Label("Freedom Scale", style={"fontFamily": "Courier New, monospace", "fontSize": "11px", "textTransform": "uppercase", "color": "#cbd5e1", "marginTop": "20px"}),
                    dcc.RadioItems(
                        id="scale-radio",
                        options=[{"label": label, "value": key} for key, (label, _) in FREEDOM_BANDS.items()],
                        value="all",
                        labelStyle={"display": "block", "marginBottom": "8px", "fontFamily": "Courier New, monospace", "fontSize": "12px"},
                        inputStyle={"marginRight": "8px"},
                    ),
                    html.Label("Trend Countries", style={"fontFamily": "Courier New, monospace", "fontSize": "11px", "textTransform": "uppercase", "color": "#cbd5e1", "marginTop": "14px"}),
                    dcc.Dropdown(id="trend-dropdown", multi=True),
                    html.Div(id="filtered-count", style={"marginTop": "18px", "fontFamily": "Courier New, monospace", "fontSize": "12px", "color": "#cbd5e1"}),
                    html.Div(
                        [
                            html.Div([html.Div("Visible Avg", style={"fontFamily": "Courier New, monospace", "fontSize": "10px", "textTransform": "uppercase", "color": "#94a3b8"}), html.Div(id="visible-avg", style={"fontFamily": "Georgia, serif", "fontSize": "24px", "fontWeight": 700})], style={"background": "rgba(255,255,255,0.06)", "padding": "12px", "borderRadius": "8px"}),
                            html.Div([html.Div("Visible Best", style={"fontFamily": "Courier New, monospace", "fontSize": "10px", "textTransform": "uppercase", "color": "#94a3b8"}), html.Div(id="visible-best", style={"fontFamily": "Georgia, serif", "fontSize": "24px", "fontWeight": 700})], style={"background": "rgba(255,255,255,0.06)", "padding": "12px", "borderRadius": "8px"}),
                        ],
                        style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "10px", "marginTop": "14px"},
                    ),
                ]
            ),
        ],
        style={"display": "flex", "flexDirection": "column", "gap": "20px", "padding": "20px", "background": COLORS["sidebar"], "color": "white", "minHeight": "100vh"},
    )


def graph_card(title: str, graph_id: str, height: int) -> html.Div:
    return html.Div(
        [html.Div(title, style={"fontFamily": "Courier New, monospace", "fontSize": "11px", "letterSpacing": "0.08em", "textTransform": "uppercase", "color": "#64748b", "marginBottom": "10px"}), dcc.Graph(id=graph_id, config={"displayModeBar": False}, style={"height": f"{height}px"})],
        style={"background": "white", "borderRadius": "10px", "padding": "16px", "boxShadow": "0 8px 24px rgba(15,23,42,0.06)"},
    )


app.layout = html.Div(
    [
        html.Div(filter_panel(), style={"width": "340px", "flexShrink": 0}),
        html.Div(
            [
                html.Div(
                    [
                        html.Div("THE PRESS FREEDOM INDEX", style={"fontFamily": "Georgia, serif", "fontSize": "34px", "fontWeight": 800, "color": COLORS["ink"]}),
                        html.Div("Pure-Python Dash dashboard with centralized filtering and Plotly visuals", style={"fontFamily": "Courier New, monospace", "fontSize": "12px", "letterSpacing": "0.08em", "textTransform": "uppercase", "color": COLORS["muted"], "marginTop": "6px"}),
                    ],
                    style={"marginBottom": "18px"},
                ),
                html.Div(id="metric-cards", style={"display": "grid", "gridTemplateColumns": "repeat(5, minmax(0, 1fr))", "gap": "12px"}),
                html.Div(
                    [
                        html.Div(graph_card("Country Rankings", "top-graph", 380)),
                        html.Div(graph_card("Lowest Scores", "bottom-graph", 380)),
                    ],
                    style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "14px", "marginTop": "16px"},
                ),
                html.Div(
                    [
                        html.Div(graph_card("Score Trends", "trend-graph", 450)),
                        html.Div(graph_card("Average Score by Zone", "zone-graph", 380)),
                    ],
                    style={"display": "grid", "gridTemplateColumns": "1.35fr 1fr", "gap": "14px", "marginTop": "16px"},
                ),
                html.Div(graph_card("World Map", "map-graph", 560), style={"marginTop": "16px"}),
                html.Div(
                    [
                        html.Div(graph_card("Most Improved", "improved-graph", 380)),
                        html.Div(graph_card("Most Declined", "declined-graph", 380)),
                    ],
                    style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "14px", "marginTop": "16px"},
                ),
                html.Div(
                    [
                        html.Div(graph_card("Country Spotlight", "spotlight-graph", 450), style={"flex": 1}),
                        html.Div(
                            [
                                html.Div(id="spotlight-heading", style={"fontFamily": "Georgia, serif", "fontSize": "28px", "fontWeight": 700, "color": COLORS["ink"]}),
                                html.Div(id="spotlight-score-label", style={"fontFamily": "Courier New, monospace", "fontSize": "11px", "textTransform": "uppercase", "color": COLORS["muted"], "marginTop": "14px"}),
                                html.Div(id="spotlight-score", style={"fontFamily": "Georgia, serif", "fontSize": "28px", "fontWeight": 700}),
                                html.Div(id="spotlight-rank-label", style={"fontFamily": "Courier New, monospace", "fontSize": "11px", "textTransform": "uppercase", "color": COLORS["muted"], "marginTop": "14px"}),
                                html.Div(id="spotlight-rank", style={"fontFamily": "Georgia, serif", "fontSize": "28px", "fontWeight": 700}),
                                html.Div(id="spotlight-change-label", style={"fontFamily": "Courier New, monospace", "fontSize": "11px", "textTransform": "uppercase", "color": COLORS["muted"], "marginTop": "14px"}),
                                html.Div(id="spotlight-change", style={"fontFamily": "Georgia, serif", "fontSize": "28px", "fontWeight": 700}),
                                html.Div(id="spotlight-delta-label", style={"fontFamily": "Courier New, monospace", "fontSize": "11px", "textTransform": "uppercase", "color": COLORS["muted"], "marginTop": "14px"}),
                                html.Div(id="spotlight-delta", style={"fontFamily": "Georgia, serif", "fontSize": "28px", "fontWeight": 700}),
                            ],
                            style={"width": "280px", "background": "white", "borderRadius": "10px", "padding": "18px", "boxShadow": "0 8px 24px rgba(15,23,42,0.06)"},
                        ),
                    ],
                    style={"display": "flex", "gap": "14px", "marginTop": "16px", "alignItems": "stretch"},
                ),
            ],
            style={"flex": 1, "padding": "24px", "background": COLORS["paper"]},
        ),
    ],
    style={"display": "flex", "minHeight": "100vh", "background": COLORS["paper"]},
)


@app.callback(
    Output("spotlight-dropdown", "options"),
    Output("spotlight-dropdown", "value"),
    Output("trend-dropdown", "options"),
    Output("trend-dropdown", "value"),
    Output("metric-cards", "children"),
    Output("filtered-count", "children"),
    Output("visible-avg", "children"),
    Output("visible-best", "children"),
    Output("top-graph", "figure"),
    Output("bottom-graph", "figure"),
    Output("zone-graph", "figure"),
    Output("map-graph", "figure"),
    Output("improved-graph", "figure"),
    Output("declined-graph", "figure"),
    Output("trend-graph", "figure"),
    Output("spotlight-graph", "figure"),
    Output("spotlight-heading", "children"),
    Output("spotlight-score-label", "children"),
    Output("spotlight-score", "children"),
    Output("spotlight-rank-label", "children"),
    Output("spotlight-rank", "children"),
    Output("spotlight-change-label", "children"),
    Output("spotlight-change", "children"),
    Output("spotlight-delta-label", "children"),
    Output("spotlight-delta", "children"),
    Input("year-dropdown", "value"),
    Input("zone-dropdown", "value"),
    Input("country-search", "value"),
    Input("score-slider", "value"),
    Input("scale-radio", "value"),
    Input("spotlight-dropdown", "value"),
    Input("trend-dropdown", "value"),
)
def update_dashboard(
    year: int,
    zone: str,
    search: str | None,
    score_range: list[int],
    band_key: str,
    spotlight_country: str | None,
    trend_countries: list[str] | None,
):
    search = (search or "").strip()
    year_frame = filter_year_df(year, zone, search, score_range, band_key)
    visible_countries = sorted(year_frame["country"].unique().tolist())
    spotlight_country = spotlight_country if spotlight_country in visible_countries else (visible_countries[0] if visible_countries else SPOTLIGHT_DEFAULT)
    spotlight_options = [{"label": country, "value": country} for country in visible_countries] or [{"label": SPOTLIGHT_DEFAULT, "value": SPOTLIGHT_DEFAULT}]

    if trend_countries:
        trend_countries = [country for country in trend_countries if country in visible_countries]
    if not trend_countries:
        trend_countries = [country for country in DEFAULT_COUNTRIES if country in visible_countries][:6]
    if not trend_countries and visible_countries:
        trend_countries = visible_countries[:6]
    trend_options = [{"label": country, "value": country} for country in visible_countries]

    if year_frame.empty:
        metric_cards = [
            metric_card("Selected Year", str(year), "No countries in view", COLORS["red"]),
            metric_card("Visible Avg", "-", "Adjust filters", COLORS["blue"]),
            metric_card("Most Free", "-", "No visible country", COLORS["green"]),
            metric_card("Most Restricted", "-", "No visible country", COLORS["red"]),
            metric_card("Spotlight", "-", "No visible country", COLORS["gold"]),
        ]
        empty = empty_figure("No Data", "No countries match the current filter combination.", 360)
        spotlight_empty = empty_figure("Country Spotlight", "The spotlight view is empty under the current filters.", 430)
        return (
            spotlight_options,
            spotlight_country,
            trend_options,
            trend_countries,
            metric_cards,
            "0 countries visible",
            "-",
            "-",
            empty,
            empty,
            empty,
            empty_figure("World Map", "No countries match the current filter combination.", 540),
            empty,
            empty,
            empty_figure("Score Trends", "No trend data is available.", 430),
            spotlight_empty,
            "Country Spotlight",
            "Score",
            "-",
            "Rank",
            "-",
            f"Change Since {START_YEAR}",
            "-",
            "vs Filtered Avg",
            "-",
        )

    visible_avg = year_frame["score"].mean()
    best = year_frame.sort_values("score", ascending=False).iloc[0]["country"]
    metric_cards = [
        metric_card("Selected Year", str(year), f"{len(year_frame)} countries visible", COLORS["red"]),
        metric_card("Visible Avg", f"{visible_avg:.1f}", "score out of 100", COLORS["blue"]),
        metric_card("Most Free", year_frame.sort_values("score", ascending=False).iloc[0]["country"], f"score {year_frame['score'].max():.2f}", COLORS["green"]),
        metric_card("Most Restricted", year_frame.sort_values("score", ascending=True).iloc[0]["country"], f"score {year_frame['score'].min():.2f}", COLORS["red"]),
        metric_card(spotlight_country, f"{float(year_frame[year_frame['country'] == spotlight_country]['score'].iloc[0]):.1f}" if spotlight_country in visible_countries else "-", "spotlight country", COLORS["gold"]),
    ]

    spotlight_row = year_frame[year_frame["country"] == spotlight_country]
    if spotlight_row.empty:
        spotlight_row = year_frame.sort_values("score", ascending=False).head(1)
    spotlight = spotlight_row.iloc[0]
    spotlight_series = filtered_series_df(spotlight["country"], zone, search, score_range, band_key, year)
    first_score = spotlight_series.sort_values("year")["score"].iloc[0] if not spotlight_series.empty else spotlight["score"]
    delta_vs_avg = float(spotlight["score"] - visible_avg)

    return (
        spotlight_options,
        spotlight["country"],
        trend_options,
        trend_countries,
        metric_cards,
        f"{len(year_frame)} countries visible",
        f"{visible_avg:.2f}",
        best,
        styled_bar_figure(year_frame, "Top 10 Scores", ascending=False, color=COLORS["green"]),
        styled_bar_figure(year_frame, "Bottom 10 Scores", ascending=True, color=COLORS["red"]),
        zone_figure(year_frame),
        map_figure(year_frame, spotlight["country"]),
        change_figure(year_frame, year, positive=True),
        change_figure(year_frame, year, positive=False),
        trend_figure(year, zone, search, score_range, band_key, trend_countries),
        spotlight_figure(spotlight["country"], year, zone, search, score_range, band_key),
        f"{spotlight['country']} Spotlight",
        f"{spotlight['country']} score ({year})",
        f"{float(spotlight['score']):.2f} / 100",
        f"{spotlight['country']} rank",
        f"#{int(spotlight['rank'])}",
        f"{spotlight['country']} change since {START_YEAR}",
        f"{float(spotlight['score'] - first_score):+.2f} pts",
        f"{spotlight['country']} vs filtered avg",
        f"{delta_vs_avg:+.2f} pts",
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=False)
