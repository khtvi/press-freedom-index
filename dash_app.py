"""
World Press Freedom Index — Dashboard
=====================================
HTML-first Flask dashboard with a one-page editorial layout.
Run locally with: python dash_app.py
Deploy with: gunicorn dash_app:server
"""

from __future__ import annotations

from pathlib import Path
import json
import warnings

import numpy as np
import pandas as pd
import plotly.express as px
from flask import Flask, render_template_string


warnings.filterwarnings("ignore")
APP_TITLE = "Press Freedom Index — Dashboard"


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
YEARS = sorted(DF["year"].unique())
LATEST_YEAR = int(max(YEARS))
LATEST_DF = DF[DF["year"] == LATEST_YEAR].copy()
YEARLY_MEANS = DF.groupby("year")["score"].mean()
YEARLY_STATS = DF.groupby("year")["score"].agg(["mean", "median", "std", "min", "max"]).reset_index()
YEARLY_STATS["q25"] = DF.groupby("year")["score"].quantile(0.25).values
YEARLY_STATS["q75"] = DF.groupby("year")["score"].quantile(0.75).values
COUNTRY_COVERAGE = DF.groupby("country")["year"].nunique().sort_values(ascending=False)
COUNTRY_VOLATILITY = DF.groupby("country")["score"].std().dropna().sort_values(ascending=False)
OVERALL_AVG = float(YEARLY_MEANS.mean())
LATEST_AVG = float(YEARLY_MEANS.loc[LATEST_YEAR])
DEFAULT_COUNTRIES = [
    c for c in ["Norway", "Finland", "Philippines", "China", "Russia", "United States"]
    if c in DF["country"].values
]
SPOTLIGHT_DEFAULT = "Philippines" if "Philippines" in DF["country"].values else sorted(DF["country"].unique())[0]
SPOTLIGHT_LATEST = LATEST_DF[LATEST_DF["country"] == SPOTLIGHT_DEFAULT]
if SPOTLIGHT_LATEST.empty:
    SPOTLIGHT_LATEST = LATEST_DF.loc[[LATEST_DF["score"].idxmax()]]


def zone_stats(selected_df: pd.DataFrame) -> list[dict]:
    if not REGION_COL:
        return []
    zone_avg = selected_df.groupby(REGION_COL)["score"].mean().sort_values(ascending=False)
    out: list[dict] = []
    palette = ["#1a6b3a", "#2e6da4", "#d4a017", "#e67e22", "#c0392b"]
    for idx, (zone, score) in enumerate(zone_avg.items()):
        out.append({"zone": str(zone), "score": float(score), "color": palette[idx % len(palette)]})
    return out


def build_payload() -> dict:
    years_payload: dict[str, dict] = {}
    for year in YEARS:
        year_df = DF[DF["year"] == year]
        spotlight_row = year_df[year_df["country"] == SPOTLIGHT_DEFAULT]
        if spotlight_row.empty:
            spotlight_row = year_df.loc[[year_df["score"].idxmax()]]
        spotlight_record = spotlight_row[["country", "score", "rank"]].iloc[0].to_dict()
        years_payload[str(year)] = {
            "top": year_df.nlargest(10, "score")[["country", "score", "rank"]].to_dict(orient="records"),
            "bottom": year_df.nsmallest(10, "score")[["country", "score", "rank"]].to_dict(orient="records"),
            "zone": zone_stats(year_df),
            "map": year_df[[c for c in ["country", "score", "rank", "iso"] if c in year_df.columns]].to_dict(orient="records"),
            "best": year_df.loc[year_df["score"].idxmax(), ["country", "score", "rank"]].to_dict(),
            "worst": year_df.loc[year_df["score"].idxmin(), ["country", "score", "rank"]].to_dict(),
            "spotlight": spotlight_record,
            "avg": float(year_df["score"].mean()),
            "median": float(year_df["score"].median()),
            "std": float(year_df["score"].std(ddof=0)),
            "q25": float(year_df["score"].quantile(0.25)),
            "q75": float(year_df["score"].quantile(0.75)),
        }

    compare_start = int(YEARS[0])
    compare_end = int(YEARS[-1])
    compare_df = pd.DataFrame({
        "start": DF[DF["year"] == compare_start].set_index("country")["score"],
        "end": DF[DF["year"] == compare_end].set_index("country")["score"],
    }).dropna()
    compare_df["change"] = compare_df["end"] - compare_df["start"]

    spotlight_series = DF[DF["country"] == SPOTLIGHT_DEFAULT].sort_values("year")[["year", "score", "rank"]].to_dict(orient="records")
    trend_series: dict[str, list[dict]] = {}
    for country in DEFAULT_COUNTRIES:
        country_df = DF[DF["country"] == country].sort_values("year")
        if not country_df.empty:
            trend_series[country] = country_df[["year", "score"]].to_dict(orient="records")

    payload = {
        "years": [int(year) for year in YEARS],
        "latestYear": LATEST_YEAR,
        "overallAvg": OVERALL_AVG,
        "latestAvg": LATEST_AVG,
        "countryCount": int(DF["country"].nunique()),
        "countries": sorted(DF["country"].unique().tolist()),
        "defaultCountries": DEFAULT_COUNTRIES,
        "spotlightDefault": SPOTLIGHT_DEFAULT,
        "latestSpotlight": {
            "country": str(SPOTLIGHT_LATEST["country"].iloc[0]),
            "score": float(SPOTLIGHT_LATEST["score"].iloc[0]),
            "rank": int(SPOTLIGHT_LATEST["rank"].iloc[0]),
            "deltaVsLatestAvg": float(SPOTLIGHT_LATEST["score"].iloc[0] - LATEST_AVG),
        },
        "countryCoverage": COUNTRY_COVERAGE.head(1).reset_index().rename(columns={"year": "years"}).to_dict(orient="records"),
        "compareStart": compare_start,
        "compareEnd": compare_end,
        "compareData": compare_df.reset_index().rename(columns={"index": "country"}).to_dict(orient="records"),
        "yearData": years_payload,
        "yearlyAverageSeries": [{"year": int(year), "score": float(score)} for year, score in YEARLY_MEANS.items()],
        "trendSeries": trend_series,
        "spotlightSeries": spotlight_series,
        "rawRows": len(DF),
        "zoneCol": REGION_COL,
        "isoCol": ISO_COL,
    }
    return payload


DATA = build_payload()
DATA_JSON = json.dumps(DATA)

map_source = LATEST_DF.copy()
if ISO_COL and ISO_COL in map_source.columns:
    fig_map = px.choropleth(
        map_source,
        locations=ISO_COL,
        color="score",
        hover_name="country",
        color_continuous_scale="RdYlGn",
        range_color=(0, 100),
        labels={"score": "Score"},
    )
else:
    fig_map = px.choropleth(
        map_source,
        locations="country",
        locationmode="country names",
        color="score",
        hover_name="country",
        color_continuous_scale="RdYlGn",
        range_color=(0, 100),
        labels={"score": "Score"},
    )
fig_map.update_layout(
    margin=dict(l=0, r=0, t=0, b=0),
    coloraxis_colorbar=dict(title="Score", len=0.68),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    geo=dict(showframe=False, showcoastlines=False, showland=True, landcolor="#f8fafc"),
)
MAP_JSON = fig_map.to_json()

app = Flask(__name__)
server = app

TEMPLATE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{ title }}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.5.1/dist/chart.umd.min.js"></script>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{
  --ink:#0d0d0d;--ink2:#1a1a1a;--paper:#f5f0e8;--paper2:#ede8dc;
  --red:#c0392b;--red2:#e74c3c;--green:#1a6b3a;--green2:#27ae60;
  --gold:#b8860b;--blue:#1a3a5c;--blue2:#2e6da4;
  --wire:#888;--stamp:#c0392b;
  --mono:'Courier New','Lucida Console',monospace;
  --serif:'Georgia','Times New Roman',serif;
  --display:'Georgia','Times New Roman',serif;
}
html,body{width:100%;height:100%;overflow:hidden}
body{
  font-family:var(--serif);
  background:var(--paper);
  color:var(--ink);
  min-height:100vh;
  background-image:repeating-linear-gradient(0deg,transparent,transparent 27px,rgba(0,0,0,.04) 27px,rgba(0,0,0,.04) 28px);
}
.masthead{background:var(--ink);color:var(--paper);padding:0;border-bottom:4px solid var(--red)}
.masthead-top{display:flex;align-items:center;justify-content:space-between;padding:.6rem 2rem;border-bottom:1px solid rgba(255,255,255,.12)}
.masthead-title{font-family:var(--display);font-size:1.6rem;font-weight:900;letter-spacing:-.01em;line-height:1}
.masthead-title span{color:var(--red2)}
.masthead-meta{font-family:var(--mono);font-size:9px;color:rgba(255,255,255,.5);text-align:right;line-height:1.6}
.masthead-nav{display:flex;gap:0;overflow-x:auto}
.nav-item{padding:.45rem 1.1rem;font-family:var(--mono);font-size:10px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;cursor:pointer;color:rgba(255,255,255,.6);border-right:1px solid rgba(255,255,255,.08);transition:all .2s;white-space:nowrap;border-bottom:2px solid transparent}
.nav-item:hover{color:#fff;background:rgba(255,255,255,.06)}
.nav-item.active{color:#fff;border-bottom:2px solid var(--red2)}
.ticker{background:var(--red);color:#fff;font-family:var(--mono);font-size:10px;font-weight:600;letter-spacing:.05em;padding:.3rem 2rem;display:flex;gap:2rem;overflow:hidden}
.ticker-label{background:rgba(0,0,0,.3);padding:1px 8px;border-radius:2px;flex-shrink:0}
.ticker-scroll{display:flex;gap:2rem;animation:scroll 30s linear infinite;flex-shrink:0}
@keyframes scroll{0%{transform:translateX(0)}100%{transform:translateX(-50%)}}
.layout{display:grid;grid-template-columns:260px 1fr;min-height:calc(100vh - 90px);height:calc(100vh - 90px);overflow:hidden}
.sidebar{background:var(--ink2);color:var(--paper);padding:1.5rem 1.2rem;display:flex;flex-direction:column;gap:1.2rem;border-right:2px solid var(--red);overflow:hidden}
.sidebar-heading{font-family:var(--mono);font-size:9px;letter-spacing:.12em;text-transform:uppercase;color:var(--red2);padding-bottom:6px;border-bottom:1px solid rgba(255,255,255,.1)}
.upload-zone{border:1.5px dashed rgba(255,255,255,.2);border-radius:4px;padding:12px 10px;text-align:center;cursor:pointer;transition:all .2s;background:rgba(255,255,255,.04)}
.upload-zone:hover{border-color:var(--red2);background:rgba(192,57,43,.1)}
.upload-zone .ico{font-size:22px;margin-bottom:4px}
.upload-zone p{font-size:11px;font-weight:600;color:var(--paper2)}
.upload-zone span{font-size:9px;color:rgba(255,255,255,.35);font-family:var(--mono)}
.status-ok{display:flex;align-items:center;gap:6px;background:rgba(26,107,58,.25);border:1px solid var(--green);border-radius:4px;padding:8px 10px;font-family:var(--mono);font-size:10px;color:var(--green2)}
.dot-green{width:6px;height:6px;background:var(--green2);border-radius:50%;flex-shrink:0;animation:blink 2s infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}
.filter-group{display:flex;flex-direction:column;gap:6px}
.filter-label{font-family:var(--mono);font-size:9px;letter-spacing:.08em;color:rgba(255,255,255,.45);text-transform:uppercase}
select,input{width:100%;padding:7px 9px;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.12);border-radius:3px;color:var(--paper);font-family:var(--mono);font-size:11px;cursor:pointer;-webkit-appearance:none}
select:hover,input:hover{border-color:rgba(255,255,255,.3)}
select option{background:var(--ink2);color:var(--paper)}
.tags{display:flex;flex-wrap:wrap;gap:4px}
.tag{background:rgba(192,57,43,.2);border:1px solid var(--red);color:var(--red2);font-family:var(--mono);font-size:9px;padding:2px 7px;border-radius:2px;cursor:pointer;transition:all .15s}
.tag.active{background:var(--red);color:#fff}
.tag:hover{background:var(--red);color:#fff}
.sidebar-footer{margin-top:auto;font-family:var(--mono);font-size:9px;color:rgba(255,255,255,.25);line-height:1.7;border-top:1px solid rgba(255,255,255,.1);padding-top:10px}
.main{padding:1.5rem 2rem;display:flex;flex-direction:column;gap:2rem;overflow:auto}
.page-scale{transform:scale(.88);transform-origin:top left;width:113.6%;height:113.6%}
.metrics-strip{display:grid;grid-template-columns:repeat(5,1fr);gap:1px;background:var(--ink);border:1px solid var(--ink);border-radius:4px;overflow:hidden}
.metric-cell{background:var(--paper2);padding:12px 14px;position:relative;cursor:pointer;transition:background .15s}
.metric-cell:hover{background:#e8e2d4}
.metric-cell::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:var(--ink)}
.metric-cell.highlight::before{background:var(--red)}
.metric-cell.ph::before{background:#0038a8}
.m-label{font-family:var(--mono);font-size:9px;letter-spacing:.08em;text-transform:uppercase;color:var(--wire);margin-bottom:4px}
.m-value{font-family:var(--display);font-size:1.4rem;font-weight:700;color:var(--ink);line-height:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.m-sub{font-family:var(--mono);font-size:9px;color:var(--wire);margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.section-label{display:flex;align-items:baseline;gap:10px;border-top:3px solid var(--ink);padding-top:8px}
.section-number{font-family:var(--mono);font-size:10px;background:var(--ink);color:var(--paper);padding:1px 7px;border-radius:1px;font-weight:600}
.section-title{font-family:var(--display);font-size:1.2rem;font-weight:700;color:var(--ink)}
.section-sub{font-family:var(--mono);font-size:9px;color:var(--wire);margin-left:auto;letter-spacing:.05em;white-space:nowrap}
.card{background:#fff;border:1px solid rgba(0,0,0,.12);border-radius:2px;padding:1.2rem;box-shadow:3px 3px 0 rgba(0,0,0,.06)}
.card-title{font-family:var(--mono);font-size:9px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--wire);margin-bottom:8px;padding-bottom:7px;border-bottom:1px solid #eee}
.two-col{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.bar-row{display:flex;align-items:center;gap:7px;padding:2px 0;border-radius:2px;transition:background .1s}
.bar-row:hover{background:rgba(0,0,0,.03)}
.bar-country{width:102px;text-align:right;font-family:var(--serif);font-size:10px;color:#555;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex-shrink:0}
.bar-track{flex:1;background:#f0ece4;border-radius:1px;height:14px;overflow:hidden;position:relative}
.bar-fill{height:100%;border-radius:1px;position:relative;transition:width 1s cubic-bezier(.4,0,.2,1)}
.bar-fill.green{background:linear-gradient(90deg,#1a6b3a,#27ae60)}
.bar-fill.red{background:linear-gradient(90deg,#c0392b,#e74c3c)}
.bar-fill.ph{background:linear-gradient(90deg,#003087,#0038a8)}
.bar-fill.censored{background:repeating-linear-gradient(-45deg,#1a1a1a 0,#1a1a1a 4px,#333 4px,#333 8px)}
.bar-score{width:34px;font-family:var(--mono);font-size:9px;color:var(--wire);text-align:right;font-weight:600;flex-shrink:0}
.bar-score.good{color:var(--green)}
.bar-score.bad{color:var(--red)}
.tooltip-box{position:fixed;z-index:999;background:var(--ink);color:var(--paper);padding:8px 12px;border-radius:2px;font-family:var(--mono);font-size:10px;pointer-events:none;opacity:0;transition:opacity .15s;border-left:3px solid var(--red);line-height:1.6;box-shadow:4px 4px 0 rgba(0,0,0,.3);max-width:200px}
.zone-bar{display:flex;align-items:center;gap:8px;padding:2px 0;cursor:pointer}
.zone-name{width:140px;font-family:var(--serif);font-size:10px;color:#555;flex-shrink:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.zone-track{flex:1;background:#f0ece4;height:14px;border-radius:1px;overflow:hidden}
.zone-fill{height:100%;border-radius:1px;transition:width 1s ease}
.zone-score{width:34px;font-family:var(--mono);font-size:9px;font-weight:600;color:var(--wire)}
.map-frame{background:linear-gradient(160deg,#1a3a5c,#0d1f33);border-radius:2px;height:165px;position:relative;overflow:hidden}
.map-frame::before{content:'';position:absolute;inset:0;background:radial-gradient(ellipse at 50% 60%,rgba(44,106,164,.4) 0%,transparent 70%);pointer-events:none}
.map-label{font-family:var(--display);font-size:.9rem;color:#fff;font-weight:700;position:absolute;z-index:2;left:12px;top:10px}
.map-sub{font-family:var(--mono);font-size:9px;color:rgba(255,255,255,.55);position:absolute;z-index:2;left:12px;top:30px;letter-spacing:.06em;text-transform:uppercase}
.map-legend{position:absolute;z-index:2;left:12px;bottom:10px;display:flex;flex-direction:column;gap:4px}
.legend-grad{width:120px;height:8px;border-radius:4px;background:linear-gradient(90deg,#c0392b,#f39c12,#27ae60)}
.legend-labels{display:flex;justify-content:space-between;width:120px;font-family:var(--mono);font-size:8px;color:rgba(255,255,255,.5)}
.ph-grid{display:grid;grid-template-columns:1fr 170px;gap:10px}
.ph-stat{display:flex;flex-direction:column;gap:8px}
.ph-stat-item{background:var(--paper2);border-left:3px solid #0038a8;padding:8px 10px;border-radius:0 2px 2px 0}
.ph-stat-label{font-family:var(--mono);font-size:9px;letter-spacing:.06em;text-transform:uppercase;color:var(--wire)}
.ph-stat-value{font-family:var(--display);font-size:1.15rem;font-weight:700;color:var(--ink)}
.ph-stat-note{font-family:var(--serif);font-size:10px;color:var(--red);margin-top:1px}
.change-bar{display:flex;align-items:center;gap:6px;padding:1px 0}
.change-name{width:92px;font-size:10px;font-family:var(--serif);color:#555;flex-shrink:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.change-center{flex:1;display:flex;align-items:center;position:relative;height:14px}
.change-mid{position:absolute;left:50%;top:0;bottom:0;width:1px;background:rgba(0,0,0,.15)}
.change-fill-pos{position:absolute;left:50%;height:100%;border-radius:0 2px 2px 0;background:linear-gradient(90deg,rgba(26,107,58,.5),#27ae60);transition:width .8s ease}
.change-fill-neg{position:absolute;right:50%;height:100%;border-radius:2px 0 0 2px;background:linear-gradient(90deg,#c0392b,rgba(192,57,43,.5));transition:width .8s ease}
.change-val{width:34px;font-family:var(--mono);font-size:9px;font-weight:600;flex-shrink:0;text-align:right}
.change-val.pos{color:var(--green)}
.change-val.neg{color:var(--red)}
.expander,.footer{display:none}
.canvas-holder{position:relative;height:140px;width:100%}
.canvas-holder.tall{height:160px}
</style>
</head>
<body>
<div class="tooltip-box" id="tooltip"></div>
<header>
  <div class="masthead">
    <div class="masthead-top">
      <div class="masthead-title">THE PRESS FREEDOM <span>INDEX</span></div>
      <div class="masthead-meta">
        DATA ANALYSIS DASHBOARD · 2014–2023<br>
        SOURCE: REPORTERS WITHOUT BORDERS (RSF)
      </div>
    </div>
    <nav class="masthead-nav">
      <div class="nav-item active" data-target="section-rankings">Rankings</div>
      <div class="nav-item" data-target="section-trends">Trends</div>
      <div class="nav-item" data-target="section-zones-map">Zones</div>
      <div class="nav-item" data-target="section-zones-map">World Map</div>
      <div class="nav-item" data-target="section-changes">Changes</div>
      <div class="nav-item" data-target="section-spotlight">Philippines</div>
    </nav>
  </div>
  <div class="ticker">
    <span class="ticker-label">BREAKING</span>
    <div style="overflow:hidden;flex:1">
      <div class="ticker-scroll" id="tickerScroll"></div>
    </div>
  </div>
</header>
<div class="layout">
  <aside class="sidebar">
    <div>
      <div class="sidebar-heading">Data Snapshot</div>
      <div class="status-ok" style="margin-top:8px">
        <div class="dot-green"></div>
        <span>{{ row_count }} rows · {{ country_count }} countries · loaded</span>
      </div>
      <div style="font-size:10px;font-family:var(--mono);line-height:1.9;color:rgba(255,255,255,.62);margin-top:10px">
        <div style="display:flex;justify-content:space-between"><span>Coverage</span><span>{{ year_start }}-{{ year_end }}</span></div>
        <div style="display:flex;justify-content:space-between"><span>Latest average</span><span>{{ latest_avg }}</span></div>
        <div style="display:flex;justify-content:space-between"><span>Top country</span><span>{{ latest_best }}</span></div>
        <div style="display:flex;justify-content:space-between"><span>Lowest score</span><span>{{ latest_worst }}</span></div>
      </div>
    </div>
    <div>
      <div class="sidebar-heading">Filters</div>
      <div class="filter-group">
        <span class="filter-label">Year</span>
        <select id="yearSelect"></select>
      </div>
      <div class="filter-group" style="margin-top:10px">
        <span class="filter-label">Countries (Trend View)</span>
        <div class="tags" id="countryTags"></div>
      </div>
    </div>
    <div>
      <div class="sidebar-heading">Freedom Scale</div>
      <div style="font-size:10px;font-family:var(--mono);line-height:2;color:rgba(255,255,255,.5)">
        <div style="display:flex;justify-content:space-between"><span style="color:#27ae60">▓ 85–100</span><span>Good</span></div>
        <div style="display:flex;justify-content:space-between"><span style="color:#7dbb4c">▓ 70–84</span><span>Satisfactory</span></div>
        <div style="display:flex;justify-content:space-between"><span style="color:#f39c12">▓ 55–69</span><span>Problematic</span></div>
        <div style="display:flex;justify-content:space-between"><span style="color:#e67e22">▓ 40–54</span><span>Difficult</span></div>
        <div style="display:flex;justify-content:space-between"><span style="color:#c0392b">▓ 0–39</span><span>Very Serious</span></div>
      </div>
    </div>
  </aside>
  <main class="main">
    <div class="page-scale">
    <div class="metrics-strip animate" id="metricsStrip"></div>

    <section id="section-rankings">
      <div class="section-label">
        <span class="section-number">01</span>
        <span class="section-title">Country Rankings</span>
        <span class="section-sub">CLICK ANY BAR FOR DETAILS</span>
      </div>
      <div class="two-col" style="margin-top:8px">
        <div class="card">
          <div class="card-title">Most Free — Top 10</div>
          <div id="top10bars"></div>
        </div>
        <div class="card">
          <div class="card-title">Least Free — Bottom 10</div>
          <div id="bottom10bars"></div>
        </div>
      </div>
    </section>

    <section id="section-trends">
      <div class="section-label">
        <span class="section-number">02</span>
        <span class="section-title">Score Trends Over Time</span>
        <span class="section-sub">2014 – 2023</span>
      </div>
      <div class="card" style="margin-top:8px">
        <div class="card-title">Press Freedom Score — Selected Countries</div>
        <div class="canvas-holder tall"><canvas id="trendChart"></canvas></div>
      </div>
    </section>

    <section id="section-zones-map">
      <div class="section-label">
        <span class="section-number">03 – 04</span>
        <span class="section-title">Zones &amp; World Map</span>
      </div>
      <div class="two-col" style="margin-top:8px">
        <div class="card">
          <div class="card-title">Average Score by Zone</div>
          <div id="zonebars"></div>
        </div>
        <div class="card" style="padding:0;overflow:hidden">
          <div class="card-title" style="padding:.8rem .8rem .4rem">Interactive Choropleth Map</div>
          <div class="map-frame">
            <div id="mapPanel" style="position:absolute;inset:0"></div>
            <div class="map-label">🗺 World Press Freedom</div>
            <div class="map-sub">Hover any country · Powered by Plotly</div>
            <div class="map-legend">
              <div class="legend-grad"></div>
              <div class="legend-labels"><span>0 — Worst</span><span>100 — Best</span></div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section id="section-changes">
      <div class="section-label">
        <span class="section-number">05</span>
        <span class="section-title">Most Improved vs Declined</span>
        <span class="section-sub">2014 → 2023</span>
      </div>
      <div class="two-col" style="margin-top:8px">
        <div class="card">
          <div class="card-title">Most Improved</div>
          <div id="improved"></div>
        </div>
        <div class="card">
          <div class="card-title">Most Declined</div>
          <div id="declined"></div>
        </div>
      </div>
    </section>

    <section id="section-spotlight">
      <div class="section-label">
        <span class="section-number" style="background:#0038a8">🇵🇭</span>
        <span class="section-title">Philippines Spotlight</span>
        <span class="section-sub">LOCAL CONTEXT</span>
      </div>
      <div class="card" style="margin-top:8px">
        <div class="ph-grid">
          <div>
            <div class="card-title">Score Over Time vs Global Average</div>
            <div class="canvas-holder"><canvas id="phChart"></canvas></div>
          </div>
          <div class="ph-stat">
            <div class="ph-stat-item">
              <div class="ph-stat-label">Score ({{ latest_year }})</div>
              <div class="ph-stat-value" id="phScoreValue">{{ ph_score }}</div>
            </div>
            <div class="ph-stat-item">
              <div class="ph-stat-label">Global Rank</div>
              <div class="ph-stat-value" id="phRankValue">{{ ph_rank }}</div>
            </div>
            <div class="ph-stat-item">
              <div class="ph-stat-label">Decade Change</div>
              <div class="ph-stat-value" id="phChangeValue" style="color:var(--red)">{{ ph_change }}</div>
              <div class="ph-stat-note">▼ Compared with {{ years[0] }}</div>
            </div>
            <div class="ph-stat-item">
              <div class="ph-stat-label">vs Global Avg</div>
              <div class="ph-stat-value" id="phDeltaValue" style="color:var(--green)">{{ ph_delta }}</div>
            </div>
          </div>
        </div>
      </div>
    </section>
    </div>
  </main>
</div>

<script>
const DATA = {{ data_json | safe }};
const OVERALL_AVG = DATA.overallAvg;
const YEARS = DATA.years;
const YEAR_DATA = DATA.yearData;
const ISO_COL = DATA.isoCol;

const COLORS = {
  'Norway':'#27ae60','Finland':'#2ecc71','US':'#2e6da4',
  'United States':'#2e6da4','Philippines':'#0038a8',
  'Russia':'#e74c3c','China':'#e67e22'
};

const state = { year: DATA.latestYear, countries: [...DATA.defaultCountries] };

const tooltip = document.getElementById('tooltip');
function showTip(e, html){ tooltip.innerHTML = html; tooltip.style.opacity='1'; moveTip(e); }
function moveTip(e){ tooltip.style.left = (e.clientX + 14) + 'px'; tooltip.style.top = (e.clientY - 10) + 'px'; }
function hideTip(){ tooltip.style.opacity='0'; }
document.addEventListener('mousemove', moveTip);

function formatNumber(v){ return Number(v).toFixed(1); }
function clamp(v, min, max){ return Math.max(min, Math.min(max, v)); }
function yearRecord(year){ return YEAR_DATA[String(year)]; }

function buildMetrics(){
  const rec = yearRecord(state.year);
  const spotlight = rec.spotlight || rec.best;
  const delta = spotlight.score - rec.avg;
  const html = [
    {label:'Selected Year', value: state.year, sub:'RSF Annual Index', cls:'highlight'},
    {label:'Countries', value: DATA.countryCount || 180, sub:'tracked globally'},
    {label:'Global Avg', value: formatNumber(rec.avg), sub:'out of 100'},
    {label:'Most Free', value: rec.best.country, sub:`score: ${formatNumber(rec.best.score)}`, cls:'highlight'},
    {label:'🇵🇭 Philippines', value: formatNumber(spotlight.score), sub:`rank #${spotlight.rank} · ${delta >= 0 ? '+' : ''}${formatNumber(delta)} vs avg`, cls:'ph'},
  ];
  const strip = document.getElementById('metricsStrip');
  strip.innerHTML = '';
  html.forEach(item => {
    const cell = document.createElement('div');
    cell.className = `metric-cell ${item.cls || ''}`;
    cell.innerHTML = `<div class="m-label">${item.label}</div><div class="m-value">${item.value}</div><div class="m-sub">${item.sub}</div>`;
    strip.appendChild(cell);
  });
}

function buildTicker(){
  const el = document.getElementById('tickerScroll');
  const rec = yearRecord(state.year);
  const zoneTop = (rec.zone || [])[0];
  const spotlight = rec.spotlight || rec.best;
  const items = [
    `Norway leads global rankings with ${rec.best.score.toFixed(1)}`,
    `${spotlight.country} ranks #${spotlight.rank} of ${DATA.countryCount}`,
    `Global press freedom average: ${rec.avg.toFixed(1)} / 100`,
    zoneTop ? `${zoneTop.zone} scores highest among all zones` : 'Europe scores highest among all zones',
    `North Korea remains at bottom for the latest year`,
  ];
  el.innerHTML = items.concat(items).map(i => `<span>${i} &nbsp;·&nbsp;</span>`).join('');
}

function buildBars(containerId, data, kind){
  const el = document.getElementById(containerId);
  el.innerHTML = '';
  data.slice(0, 10).forEach((d, i) => {
    const pct = clamp(d.score, 0, 100);
    const cls = d.score < 35 ? 'censored' : kind;
    const scoreClass = kind === 'green' ? 'good' : 'bad';
    const ph = d.country === 'Philippines';
    const row = document.createElement('div');
    row.className = 'bar-row';
    row.innerHTML = `
      <span class="bar-country" style="${ph?'color:#0038a8;font-weight:600':''}">${d.country}</span>
      <div class="bar-track"><div class="bar-fill ${ph?'ph':cls}" style="width:0%"></div></div>
      <span class="bar-score ${scoreClass}">${formatNumber(d.score)}</span>`;
    row.addEventListener('mouseenter', e => showTip(e, `<b>${d.country}</b><br>Score: ${formatNumber(d.score)} / 100<br>Rank: #${d.rank}`));
    row.addEventListener('mouseleave', hideTip);
    el.appendChild(row);
    setTimeout(()=>{ row.querySelector('.bar-fill').style.width = pct + '%'; }, i * 55 + 120);
  });
}

function buildZoneBars(data){
  const el = document.getElementById('zonebars');
  el.innerHTML='';
  (data || []).forEach((d, i) => {
    const row = document.createElement('div');
    row.className = 'zone-bar';
    row.innerHTML=`
      <span class="zone-name">${d.zone}</span>
      <div class="zone-track"><div class="zone-fill" style="width:0%;background:${d.color}"></div></div>
      <span class="zone-score">${formatNumber(d.score)}</span>`;
    row.addEventListener('mouseenter', e => showTip(e, `<b>${d.zone}</b><br>Avg score: ${formatNumber(d.score)}`));
    row.addEventListener('mouseleave', hideTip);
    el.appendChild(row);
    setTimeout(()=>{ row.querySelector('.zone-fill').style.width = d.score + '%'; }, i * 70 + 120);
  });
}

function buildChangeBars(containerId, data, positive){
  const el = document.getElementById(containerId);
  el.innerHTML='';
  const sorted = [...data].sort((a,b) => positive ? b.change - a.change : a.change - b.change).slice(0, 8);
  sorted.forEach((d,i)=>{
    const abs = Math.min(Math.abs(d.change), 30);
    const pct = (abs / 30) * 45;
    const row = document.createElement('div');
    row.className = 'change-bar';
    row.innerHTML = `
      <span class="change-name">${d.country}</span>
      <div class="change-center">
        <div class="change-mid"></div>
        ${positive ? `<div class="change-fill-pos" style="width:0%"></div>` : `<div class="change-fill-neg" style="width:0%"></div>`}
      </div>
      <span class="change-val ${positive?'pos':'neg'}">${positive?'+':''}${formatNumber(d.change)}</span>`;
    row.addEventListener('mouseenter', e => showTip(e, `<b>${d.country}</b><br>Change: ${d.change > 0 ? '+' : ''}${formatNumber(d.change)} pts<br>${DATA.compareStart} → ${DATA.compareEnd}`));
    row.addEventListener('mouseleave', hideTip);
    el.appendChild(row);
    setTimeout(()=>{
      const fill = row.querySelector('.change-fill-pos, .change-fill-neg');
      if (fill) fill.style.width = pct + '%';
    }, i * 70 + 120);
  });
}

function buildMap(){
  const rec = yearRecord(state.year);
  const mapRows = rec.map || [];
  const rows = mapRows.filter(r => (ISO_COL ? r.iso : r.country));
  const locations = rows.map(r => ISO_COL ? r.iso : r.country);
  const scores = rows.map(r => r.score);
  const hover = rows.map(r => `${r.country}<br>Score: ${formatNumber(r.score)}`);
  const data = [{
    type: 'choropleth',
    locations: locations,
    z: scores,
    text: hover,
    hoverinfo: 'text',
    locationmode: ISO_COL ? 'ISO-3' : 'country names',
    colorscale: 'RdYlGn',
    zmin: 0,
    zmax: 100,
    marker: {line: {color: 'rgba(255,255,255,0.35)', width: 0.5}}
  }];
  const layout = {
    margin: {l:0, r:0, t:0, b:0},
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    geo: {showframe:false, showcoastlines:false, showland:true, landcolor:'#f8fafc', bgcolor:'rgba(0,0,0,0)'}
  };
  Plotly.react('mapPanel', data, layout, {displayModeBar:false, responsive:true});
}

let trendChart;
let phChart;
function buildTrendChart(){
  const ctx = document.getElementById('trendChart').getContext('2d');
  const countries = activeCountries();
  const labels = YEARS;
  const datasets = countries.map((country, index) => {
    const series = DATA.trendSeries[country] || [];
    const lookup = new Map(series.map(p => [p.year, p.score]));
    const points = labels.map(y => lookup.get(y) ?? null);
    return {
      label: country,
      data: points,
      borderColor: COLORS[country] || ['#12355b','#b42318','#0f766e','#2563eb','#d97706','#7c3aed'][index % 6],
      backgroundColor: country === 'Philippines' ? 'rgba(0,56,168,.08)' : 'transparent',
      fill: country === 'Philippines',
      pointRadius: 3,
      borderWidth: country === 'Philippines' ? 2.5 : 1.8,
      borderDash: ['Russia','US','United States'].includes(country) ? [4,3] : [],
      tension: 0.28,
    };
  });
  if (trendChart) trendChart.destroy();
  trendChart = new Chart(ctx,{
    type:'line',
    data:{labels, datasets},
    options:{
      responsive:true,maintainAspectRatio:false,
      plugins:{legend:{position:'bottom',labels:{boxWidth:10,font:{size:9,family:'Courier New'},padding:8}}},
      scales:{
        x:{grid:{color:'rgba(0,0,0,.06)'},ticks:{font:{size:9,family:'Courier New'}}},
        y:{min:0,max:100,grid:{color:'rgba(0,0,0,.06)'},ticks:{font:{size:9,family:'Courier New'}}}
      }
    }
  });
}

function buildPhChart(){
  const ctx = document.getElementById('phChart').getContext('2d');
  const series = DATA.spotlightSeries;
  const avgLookup = new Map((DATA.yearlyAverageSeries || []).map(p => [p.year, p.score]));
  if (phChart) phChart.destroy();
  phChart = new Chart(ctx,{
    type:'line',
    data:{
      labels:series.map(p => p.year),
      datasets:[
        {label:'Philippines',data:series.map(p => p.score),borderColor:'#0038a8',backgroundColor:'rgba(0,56,168,.1)',fill:true,pointRadius:4,borderWidth:2.5,pointBackgroundColor:'#0038a8',tension:0.28},
        {label:'Global avg',data:series.map(p => avgLookup.get(p.year) ?? null),borderColor:'#c0392b',borderDash:[5,3],borderWidth:1.5,pointRadius:0,fill:false}
      ]
    },
    options:{
      responsive:true,maintainAspectRatio:false,
      plugins:{legend:{position:'bottom',labels:{boxWidth:10,font:{size:9,family:'Courier New'},padding:6}}},
      scales:{
        x:{grid:{color:'rgba(0,0,0,.06)'},ticks:{font:{size:9,family:'Courier New'}}},
        y:{min:20,max:100,grid:{color:'rgba(0,0,0,.06)'},ticks:{font:{size:9,family:'Courier New'}}}
      }
    }
  });
}

function buildMetricsText(){
  buildMetrics();
  const lastPoint = DATA.latestSpotlight;
  const firstPoint = DATA.spotlightSeries[0];
  document.getElementById('phScoreValue').textContent = `${formatNumber(lastPoint.score)} / 100`;
  document.getElementById('phRankValue').textContent = `#${lastPoint.rank} of ${DATA.countryCount}`;
  document.getElementById('phChangeValue').textContent = `${lastPoint.score - firstPoint.score >= 0 ? '+' : '−'}${formatNumber(Math.abs(lastPoint.score - firstPoint.score))} pts`;
  document.getElementById('phDeltaValue').textContent = `${lastPoint.deltaVsLatestAvg >= 0 ? '+' : ''}${formatNumber(lastPoint.deltaVsLatestAvg)} pts`;
}

function refreshAll(){
  const rec = yearRecord(state.year);
  buildTicker();
  buildMetricsText();
  buildBars('top10bars', rec.top, 'green');
  buildBars('bottom10bars', rec.bottom, 'red');
  buildZoneBars(rec.zone);
  buildChangeBars('improved', DATA.compareData.filter(d => d.change > 0), true);
  buildChangeBars('declined', DATA.compareData.filter(d => d.change < 0), false);
  buildTrendChart();
  buildPhChart();
  buildMap();
}

function activeCountries(){
  const active = Array.from(document.querySelectorAll('.tag.active')).map(t => t.dataset.country);
  return active.length ? active : [...DATA.defaultCountries];
}

function updateStateFromUI(){
  state.year = parseInt(document.getElementById('yearSelect').value, 10);
  refreshAll();
}

document.querySelectorAll('.nav-item').forEach(n => {
  n.addEventListener('click', () => {
    document.querySelectorAll('.nav-item').forEach(x => x.classList.remove('active'));
    n.classList.add('active');
    const targetId = n.dataset.target;
    const target = targetId ? document.getElementById(targetId) : null;
    if (target) {
      target.scrollIntoView({behavior:'smooth', block:'start'});
    }
  });
});

const yearSelect = document.getElementById('yearSelect');
const yearNumbers = YEARS.slice().reverse();
yearNumbers.forEach(y => {
  const opt = document.createElement('option');
  opt.value = y; opt.textContent = y;
  if (y === DATA.latestYear) opt.selected = true;
  yearSelect.appendChild(opt);
});
yearSelect.addEventListener('change', updateStateFromUI);

const tags = document.getElementById('countryTags');
DATA.defaultCountries.forEach(country => {
  const span = document.createElement('span');
  span.className = 'tag active';
  span.dataset.country = country;
  span.textContent = country;
  span.addEventListener('click', () => {
    span.classList.toggle('active');
    refreshAll();
  });
  tags.appendChild(span);
});

buildTicker();
refreshAll();

window.addEventListener('resize', () => {
  buildTrendChart();
  buildPhChart();
  buildMap();
});
</script>
</body>
</html>
"""


@app.route("/")
def index():
    spotlight_row = LATEST_DF[LATEST_DF["country"] == SPOTLIGHT_DEFAULT]
    if spotlight_row.empty:
        spotlight_row = LATEST_DF.loc[[LATEST_DF["score"].idxmax()]]
    score = float(spotlight_row["score"].iloc[0])
    rank = int(spotlight_row["rank"].iloc[0])
    first_score = float(DF[DF["country"] == SPOTLIGHT_DEFAULT].sort_values("year")["score"].iloc[0])
    ph_delta = score - OVERALL_AVG
    ph_change = score - first_score
    return render_template_string(
        TEMPLATE,
        title=APP_TITLE,
        row_count=len(DF),
        country_count=DF["country"].nunique(),
        years=YEARS,
        latest_year=LATEST_YEAR,
        year_start=YEARS[0],
        year_end=YEARS[-1],
        latest_avg=f"{LATEST_AVG:.1f}",
        latest_best=LATEST_DF.loc[LATEST_DF["score"].idxmax(), "country"],
        latest_worst=LATEST_DF.loc[LATEST_DF["score"].idxmin(), "country"],
        ph_score=f"{score:.1f}",
        ph_rank=f"#{rank} of {DF['country'].nunique()}",
        ph_change=f"{ph_change:+.1f} pts",
        ph_delta=f"{(score - LATEST_AVG):+.1f} pts",
        data_json=DATA_JSON,
        map_json=MAP_JSON,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=False)
