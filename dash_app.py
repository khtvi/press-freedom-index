from __future__ import annotations

from pathlib import Path
import json
import warnings

import pandas as pd
from flask import Flask, render_template_string


warnings.filterwarnings("ignore")
APP_TITLE = "Press Freedom Index Dashboard"


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
        ("region", "zone"),
        ("continent", "zone"),
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
    if "zone" not in df.columns:
        df["zone"] = "Unspecified"
    df["zone"] = df["zone"].fillna("Unspecified").astype(str)
    return df


DATA_FILE = find_data_file()
if DATA_FILE is None:
    raise FileNotFoundError("No press freedom dataset file was found in the app folder.")

DF = load_data(DATA_FILE)
YEARS = sorted(DF["year"].unique())
LATEST_YEAR = int(max(YEARS))
START_YEAR = int(min(YEARS))
LATEST_DF = DF[DF["year"] == LATEST_YEAR].copy()
DEFAULT_COUNTRIES = [
    country
    for country in ["Norway", "Finland", "Philippines", "China", "Russia", "United States"]
    if country in DF["country"].values
]
SPOTLIGHT_DEFAULT = "Philippines" if "Philippines" in DF["country"].values else sorted(DF["country"].unique())[0]
ZONE_OPTIONS = sorted(DF["zone"].dropna().astype(str).unique().tolist())
LATEST_AVG = float(LATEST_DF["score"].mean())


def build_payload() -> dict:
    all_rows = DF[[c for c in ["year", "country", "score", "rank", "zone", "iso"] if c in DF.columns]].copy()
    return {
        "years": [int(year) for year in YEARS],
        "latestYear": LATEST_YEAR,
        "startYear": START_YEAR,
        "countryCount": int(DF["country"].nunique()),
        "countries": sorted(DF["country"].unique().tolist()),
        "zones": ZONE_OPTIONS,
        "defaultCountries": DEFAULT_COUNTRIES,
        "spotlightDefault": SPOTLIGHT_DEFAULT,
        "allRows": all_rows.to_dict(orient="records"),
    }


DATA_JSON = json.dumps(build_payload())

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
  --ink:#101010;--ink2:#1c1c1c;--paper:#f5f0e8;--paper2:#ece5d8;
  --red:#c43a28;--red2:#e45a42;--green:#1f7a45;--green2:#2ea85d;
  --gold:#c29018;--blue:#163a5f;--line:#d8d0c4;--wire:#7b7b7b;
  --mono:'Courier New','Lucida Console',monospace;
  --serif:'Georgia','Times New Roman',serif;
  --header-h:150px;
  --sidebar-w:280px;
}
html,body{width:100%;height:100%}
body{
  font-family:var(--serif);
  background:var(--paper);
  color:var(--ink);
  background-image:repeating-linear-gradient(0deg,transparent,transparent 29px,rgba(0,0,0,.04) 29px,rgba(0,0,0,.04) 30px);
  padding-top:var(--header-h);
}
.masthead{background:var(--ink);color:var(--paper);border-bottom:4px solid var(--red)}
.site-header{position:fixed;top:0;left:0;right:0;z-index:50;box-shadow:0 6px 18px rgba(0,0,0,.2)}
.masthead-top{display:flex;align-items:center;justify-content:space-between;padding:.85rem 1.8rem;border-bottom:1px solid rgba(255,255,255,.12)}
.masthead-title{font-size:1.95rem;font-weight:900;line-height:1;letter-spacing:-.02em}
.masthead-title span{color:var(--red2)}
.masthead-meta{font-family:var(--mono);font-size:12px;line-height:1.55;color:rgba(255,255,255,.58);text-align:right}
.masthead-nav{display:flex;overflow-x:auto}
.nav-item{padding:.85rem 1.2rem;font-family:var(--mono);font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:rgba(255,255,255,.66);border-right:1px solid rgba(255,255,255,.08);border-bottom:2px solid transparent;cursor:pointer;white-space:nowrap}
.nav-item:hover{background:rgba(255,255,255,.05);color:#fff}
.nav-item.active{color:#fff;border-bottom:2px solid var(--red2)}
.ticker{background:var(--red);color:#fff;display:flex;gap:1.2rem;padding:.65rem 1.8rem;font-family:var(--mono);font-size:12px;font-weight:700}
.ticker-label{background:rgba(0,0,0,.25);padding:.3rem .8rem;border-radius:2px;flex-shrink:0}
.ticker-rail{overflow:hidden;flex:1}
.ticker-scroll{display:flex;gap:2rem;white-space:nowrap;animation:scroll 30s linear infinite}
@keyframes scroll{0%{transform:translateX(0)}100%{transform:translateX(-50%)}}
.layout{display:block;min-height:calc(100vh - var(--header-h))}
.sidebar{position:fixed;top:var(--header-h);left:0;bottom:0;width:var(--sidebar-w);background:var(--ink2);color:var(--paper);padding:1rem .95rem;border-right:2px solid var(--red);display:flex;flex-direction:column;gap:.85rem;overflow:hidden}
.sidebar-heading{font-family:var(--mono);font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:var(--red2);padding-bottom:5px;border-bottom:1px solid rgba(255,255,255,.12)}
.status-ok{display:flex;align-items:center;gap:6px;background:rgba(31,122,69,.22);border:1px solid var(--green);border-radius:4px;padding:.5rem .6rem;font-family:var(--mono);font-size:10px;color:var(--green2)}
.dot-green{width:7px;height:7px;border-radius:50%;background:var(--green2)}
.filter-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.filter-group{display:flex;flex-direction:column;gap:5px}
.filter-label{font-family:var(--mono);font-size:9px;letter-spacing:.08em;text-transform:uppercase;color:rgba(255,255,255,.56)}
select,input{width:100%;padding:.48rem .58rem;border-radius:3px;border:1px solid rgba(255,255,255,.14);background:rgba(255,255,255,.05);color:var(--paper);font-family:var(--mono);font-size:11px}
select option{background:var(--ink2);color:var(--paper)}
.range-labels,.summary-line{display:flex;justify-content:space-between;font-family:var(--mono);font-size:10px;color:rgba(255,255,255,.65)}
.tags{display:flex;flex-wrap:wrap;gap:4px}
.tag{background:rgba(196,58,40,.2);border:1px solid var(--red);color:#ffd8d0;font-family:var(--mono);font-size:10px;padding:.22rem .42rem;border-radius:2px;cursor:pointer}
.tag.active{background:var(--red);color:#fff}
.scale-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px}
.scale-chip{border:1px solid rgba(255,255,255,.15);background:rgba(255,255,255,.05);color:rgba(255,255,255,.82);padding:.36rem .42rem;border-radius:3px;font-family:var(--mono);font-size:9px;cursor:pointer;text-align:left}
.scale-chip.active{border-color:var(--gold);background:rgba(194,144,24,.18);color:#fff}
.freedom-scale{display:grid;grid-template-columns:1fr 1fr;gap:4px 10px;font-family:var(--mono);font-size:9px;line-height:1.55;color:rgba(255,255,255,.6)}
.freedom-row{display:flex;justify-content:space-between}
.sidebar-stats{display:grid;grid-template-columns:1fr 1fr;gap:6px}
.sidebar-stat{background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.08);border-radius:4px;padding:.5rem}
.sidebar-stat-label{font-family:var(--mono);font-size:9px;text-transform:uppercase;color:rgba(255,255,255,.45)}
.sidebar-stat-value{font-size:.9rem;font-weight:700;color:#fff;margin-top:.12rem}
.main{margin-left:var(--sidebar-w);padding:1.45rem 1.55rem 2rem;min-height:calc(100vh - var(--header-h));overflow:visible}
.metrics-strip{display:grid;grid-template-columns:repeat(5,1fr);gap:1px;background:var(--ink);border:1px solid var(--ink);border-radius:4px;overflow:hidden}
.metric-cell{background:var(--paper2);padding:1rem 1.1rem;position:relative;min-height:88px}
.metric-cell::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:var(--ink)}
.metric-cell.highlight::before{background:var(--red)}
.metric-cell.ph::before{background:#003a8c}
.m-label{font-family:var(--mono);font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:var(--wire);margin-bottom:.35rem}
.m-value{font-size:1.2rem;font-weight:700;line-height:1.05;color:var(--ink)}
.m-sub{font-family:var(--mono);font-size:10px;color:var(--wire);margin-top:.35rem}
.section{margin-top:1.55rem}
.section-label{display:flex;align-items:baseline;gap:10px;border-top:3px solid var(--ink);padding-top:.75rem}
.section-number{font-family:var(--mono);font-size:11px;background:var(--ink);color:var(--paper);padding:2px 7px;border-radius:1px;font-weight:700}
.section-title{font-size:1.1rem;font-weight:700}
.section-sub{margin-left:auto;font-family:var(--mono);font-size:10px;letter-spacing:.06em;color:var(--wire);text-transform:uppercase}
.two-col{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:.9rem}
.card{background:#fff;border:1px solid rgba(0,0,0,.12);border-radius:2px;padding:1rem;box-shadow:3px 3px 0 rgba(0,0,0,.06)}
.card.tight{padding:0;overflow:hidden}
.card-title{font-family:var(--mono);font-size:10px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--wire);padding-bottom:.55rem;margin-bottom:.7rem;border-bottom:1px solid #eee}
.bars{display:flex;flex-direction:column;gap:.55rem}
.bar-row{display:flex;align-items:center;gap:8px}
.bar-country{width:118px;text-align:right;font-size:12px;color:#555;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.bar-track{flex:1;height:20px;background:#ede7dd;border-radius:1px;overflow:hidden}
.bar-fill{height:100%;transition:width .9s ease}
.bar-fill.green{background:linear-gradient(90deg,#23884e,#31af62)}
.bar-fill.red{background:linear-gradient(90deg,#2a2a2a,#444)}
.bar-fill.ph{background:linear-gradient(90deg,#003a8c,#0050bc)}
.bar-score{width:42px;text-align:right;font-family:var(--mono);font-size:12px;font-weight:700}
.bar-score.good{color:var(--green)}
.bar-score.bad{color:var(--red)}
.zone-row,.change-row{display:flex;align-items:center;gap:9px}
.zone-name,.change-name{width:138px;font-size:12px;color:#555;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.zone-track{flex:1;height:18px;background:#ede7dd;border-radius:1px;overflow:hidden}
.zone-fill{height:100%;transition:width .9s ease}
.zone-score,.change-score{width:42px;text-align:right;font-family:var(--mono);font-size:12px;font-weight:700;color:#555}
.change-center{flex:1;position:relative;height:18px;background:#ede7dd;border-radius:1px;overflow:hidden}
.change-mid{position:absolute;left:50%;top:0;bottom:0;width:1px;background:rgba(0,0,0,.15)}
.change-fill-pos{position:absolute;left:50%;top:0;bottom:0;background:linear-gradient(90deg,rgba(31,122,69,.4),#31af62)}
.change-fill-neg{position:absolute;right:50%;top:0;bottom:0;background:linear-gradient(90deg,#c43a28,rgba(196,58,40,.45))}
.map-frame{position:relative;height:320px;background:linear-gradient(160deg,#183a5d,#0f2032)}
.map-label{position:absolute;left:14px;top:12px;z-index:2;color:#fff;font-size:1rem;font-weight:700}
.map-sub{position:absolute;left:14px;top:33px;z-index:2;color:rgba(255,255,255,.62);font-family:var(--mono);font-size:10px;text-transform:uppercase}
.map-legend{position:absolute;left:14px;bottom:12px;z-index:2}
.legend-grad{width:150px;height:9px;border-radius:4px;background:linear-gradient(90deg,#c43a28,#d79a16,#31af62)}
.legend-labels{display:flex;justify-content:space-between;width:150px;font-family:var(--mono);font-size:9px;color:rgba(255,255,255,.62);margin-top:4px}
.canvas-holder{height:260px}
.plot-holder{height:320px}
.ph-grid{display:grid;grid-template-columns:1fr 205px;gap:14px}
.ph-stat{display:flex;flex-direction:column;gap:9px}
.ph-stat-item{background:var(--paper2);border-left:3px solid #003a8c;padding:.75rem .85rem}
.ph-stat-label{font-family:var(--mono);font-size:10px;text-transform:uppercase;color:var(--wire)}
.ph-stat-value{font-size:1.18rem;font-weight:700;margin-top:.2rem}
.ph-stat-note{font-size:11px;color:var(--red);margin-top:.18rem}
.tooltip-box{position:fixed;z-index:999;background:var(--ink);color:var(--paper);padding:.55rem .7rem;border-radius:2px;font-family:var(--mono);font-size:11px;line-height:1.6;pointer-events:none;opacity:0;transition:opacity .12s;border-left:3px solid var(--red);max-width:220px}
.empty-state{padding:1.5rem;border:1px dashed rgba(0,0,0,.16);background:#faf7f1;border-radius:4px;font-family:var(--mono);font-size:12px;color:#666;text-align:center}
@media (max-width:1180px){
  body{padding-top:0}
  .site-header{position:static}
  .layout{display:block}
  .sidebar{position:static;width:auto;border-right:none;border-bottom:2px solid var(--red);overflow:visible}
  .main{margin-left:0;min-height:auto}
  .metrics-strip{grid-template-columns:repeat(2,1fr)}
  .two-col,.ph-grid,.sidebar-stats,.scale-grid,.filter-grid{grid-template-columns:1fr}
}
</style>
</head>
<body>
<div class="tooltip-box" id="tooltip"></div>
<header class="site-header">
  <div class="masthead">
    <div class="masthead-top">
      <div class="masthead-title">THE PRESS FREEDOM <span>INDEX</span></div>
      <div class="masthead-meta">
        DATA ANALYSIS DASHBOARD · {{ start_year }}-{{ latest_year }}<br>
        SOURCE: REPORTERS WITHOUT BORDERS (RSF)
      </div>
    </div>
    <nav class="masthead-nav">
      <div class="nav-item active" data-target="section-rankings">Rankings</div>
      <div class="nav-item" data-target="section-trends">Trends</div>
      <div class="nav-item" data-target="section-zones">Zones</div>
      <div class="nav-item" data-target="section-map">World Map</div>
      <div class="nav-item" data-target="section-insights">Insights</div>
      <div class="nav-item" data-target="section-changes">Changes</div>
      <div class="nav-item" data-target="section-spotlight">Spotlight</div>
    </nav>
  </div>
  <div class="ticker">
    <span class="ticker-label">BREAKING</span>
    <div class="ticker-rail"><div class="ticker-scroll" id="tickerScroll"></div></div>
  </div>
</header>

<div class="layout">
  <aside class="sidebar">
    <div>
      <div class="sidebar-heading">Data Status</div>
      <div class="status-ok" style="margin-top:10px">
        <div class="dot-green"></div>
        <span>{{ row_count }} rows · {{ country_count }} countries · loaded</span>
      </div>
    </div>

    <div>
      <div class="sidebar-heading">Filters</div>
      <div class="filter-grid">
        <div class="filter-group">
          <span class="filter-label">Year</span>
          <select id="yearSelect"></select>
        </div>
        <div class="filter-group">
          <span class="filter-label">Zone</span>
          <select id="zoneSelect"></select>
        </div>
      </div>
      <div class="filter-group" style="margin-top:10px">
        <span class="filter-label">Spotlight Country</span>
        <select id="spotlightSelect"></select>
      </div>
      <div class="filter-group" style="margin-top:10px">
        <span class="filter-label">Country Search</span>
        <input id="countrySearch" type="text" placeholder="Filter by country name">
      </div>
      <div class="filter-group" style="margin-top:10px">
        <span class="filter-label">Score Range</span>
        <div class="range-labels"><span id="scoreMinLabel">0</span><span id="scoreMaxLabel">100</span></div>
        <input id="scoreMinRange" type="range" min="0" max="100" step="1" value="0">
        <input id="scoreMaxRange" type="range" min="0" max="100" step="1" value="100">
      </div>
      <div class="filter-group" style="margin-top:10px">
        <span class="filter-label">Countries (Trend View)</span>
        <div class="tags" id="countryTags"></div>
      </div>
      <div class="filter-group" style="margin-top:10px">
        <span class="filter-label">Freedom Scale</span>
        <div class="scale-grid" id="scaleFilters"></div>
      </div>
    </div>

    <div>
      <div class="sidebar-heading">Snapshot</div>
      <div class="summary-line"><span>Visible countries</span><span id="filteredCount">{{ country_count }}</span></div>
      <div class="summary-line" style="margin-top:7px"><span>Visible average</span><span id="sidebarAvgValue">{{ latest_avg }}</span></div>
      <div class="sidebar-stats" style="margin-top:10px">
        <div class="sidebar-stat">
          <div class="sidebar-stat-label">Top Country</div>
          <div class="sidebar-stat-value" id="sidebarBestValue">{{ latest_best }}</div>
        </div>
        <div class="sidebar-stat">
          <div class="sidebar-stat-label">Lowest Score</div>
          <div class="sidebar-stat-value" id="sidebarWorstValue">{{ latest_worst }}</div>
        </div>
      </div>
    </div>
  </aside>

  <main class="main">
    <div class="metrics-strip" id="metricsStrip"></div>

    <section class="section" id="section-rankings">
      <div class="section-label">
        <span class="section-number">01</span>
        <span class="section-title">Country Rankings</span>
        <span class="section-sub">Click any bar for details</span>
      </div>
      <div class="two-col">
        <div class="card">
          <div class="card-title">Most Free - Top 10</div>
          <div class="bars" id="top10bars"></div>
        </div>
        <div class="card">
          <div class="card-title">Least Free - Bottom 10</div>
          <div class="bars" id="bottom10bars"></div>
        </div>
      </div>
    </section>

    <section class="section" id="section-trends">
      <div class="section-label">
        <span class="section-number">02</span>
        <span class="section-title">Score Trends Over Time</span>
        <span class="section-sub">{{ start_year }}-{{ latest_year }}</span>
      </div>
      <div class="card" style="margin-top:.9rem">
        <div class="card-title">Press Freedom Score - Selected Countries</div>
        <div class="canvas-holder"><canvas id="trendChart"></canvas></div>
      </div>
    </section>

    <section class="section" id="section-zones">
      <div class="section-label">
        <span class="section-number">03</span>
        <span class="section-title">Zones</span>
      </div>
      <div class="card" style="margin-top:.9rem">
        <div class="card-title">Average Score by Zone</div>
        <div class="bars" id="zonebars"></div>
      </div>
    </section>

    <section class="section" id="section-map">
      <div class="section-label">
        <span class="section-number">04</span>
        <span class="section-title">World Map</span>
        <span class="section-sub">Interactive choropleth</span>
      </div>
      <div class="card tight" style="margin-top:.9rem">
        <div class="map-frame">
          <div id="mapPanel" style="position:absolute;inset:0"></div>
          <div class="map-label">World Press Freedom</div>
          <div class="map-sub">Hover or click any country</div>
          <div class="map-legend">
            <div class="legend-grad"></div>
            <div class="legend-labels"><span>0 Worst</span><span>100 Best</span></div>
          </div>
        </div>
      </div>
    </section>

    <section class="section" id="section-insights">
      <div class="section-label">
        <span class="section-number">05</span>
        <span class="section-title">Deeper Insights</span>
        <span class="section-sub">Distribution and score-rank relationship</span>
      </div>
      <div class="two-col">
        <div class="card">
          <div class="card-title">Score Distribution</div>
          <div class="plot-holder" id="distributionPlot"></div>
        </div>
        <div class="card">
          <div class="card-title">Rank vs Score</div>
          <div class="plot-holder" id="scatterPlot"></div>
        </div>
      </div>
    </section>

    <section class="section" id="section-changes">
      <div class="section-label">
        <span class="section-number">06</span>
        <span class="section-title">Most Improved vs Declined</span>
        <span class="section-sub">{{ start_year }} to {{ latest_year }}</span>
      </div>
      <div class="two-col">
        <div class="card">
          <div class="card-title">Most Improved</div>
          <div class="bars" id="improved"></div>
        </div>
        <div class="card">
          <div class="card-title">Most Declined</div>
          <div class="bars" id="declined"></div>
        </div>
      </div>
    </section>

    <section class="section" id="section-spotlight">
      <div class="section-label">
        <span class="section-number">07</span>
        <span class="section-title" id="spotlightHeading">Country Spotlight</span>
        <span class="section-sub">Filtered context</span>
      </div>
      <div class="card" style="margin-top:.9rem">
        <div class="ph-grid">
          <div>
            <div class="card-title" id="spotlightChartTitle">Score Over Time vs Filtered Average</div>
            <div class="canvas-holder"><canvas id="phChart"></canvas></div>
          </div>
          <div class="ph-stat">
            <div class="ph-stat-item">
              <div class="ph-stat-label" id="spotlightScoreLabel">Score</div>
              <div class="ph-stat-value" id="phScoreValue">-</div>
            </div>
            <div class="ph-stat-item">
              <div class="ph-stat-label" id="spotlightRankLabel">Rank</div>
              <div class="ph-stat-value" id="phRankValue">-</div>
            </div>
            <div class="ph-stat-item">
              <div class="ph-stat-label" id="spotlightChangeLabel">Change Since {{ start_year }}</div>
              <div class="ph-stat-value" id="phChangeValue">-</div>
              <div class="ph-stat-note" id="spotlightChangeNote">Compared with {{ start_year }}</div>
            </div>
            <div class="ph-stat-item">
              <div class="ph-stat-label" id="spotlightDeltaLabel">vs Filtered Avg</div>
              <div class="ph-stat-value" id="phDeltaValue">-</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  </main>
</div>

<script>
const DATA = {{ data_json | safe }};
const ALL_ROWS = DATA.allRows.map(row => ({
  ...row,
  year: Number(row.year),
  score: Number(row.score),
  rank: Number(row.rank),
  zone: row.zone || 'Unspecified'
}));
const ISO_COL = ALL_ROWS.some(row => row.iso) ? 'iso' : null;
const FREEDOM_BANDS = {
  all: {label:'All Scores', min:0, max:100},
  good: {label:'Good', min:85, max:100},
  satisfactory: {label:'Satisfactory', min:70, max:84},
  problematic: {label:'Problematic', min:55, max:69},
  difficult: {label:'Difficult', min:40, max:54},
  serious: {label:'Very Serious', min:0, max:39}
};
const state = {
  year: DATA.latestYear,
  zone: 'All zones',
  spotlight: DATA.spotlightDefault,
  search: '',
  scoreMin: 0,
  scoreMax: 100,
  band: 'all',
  countries: [...DATA.defaultCountries]
};
const trendPalette = ['#163a5f','#c43a28','#0f766e','#2563eb','#d97706','#7c3aed','#00897b'];
const tooltip = document.getElementById('tooltip');
let trendChart;
let phChart;

function showTip(e, html){
  tooltip.innerHTML = html;
  tooltip.style.opacity = '1';
  tooltip.style.left = (e.clientX + 14) + 'px';
  tooltip.style.top = (e.clientY - 12) + 'px';
}
function hideTip(){ tooltip.style.opacity = '0'; }
function formatNumber(v){ return Number(v).toFixed(1); }
function yearRows(year){ return ALL_ROWS.filter(row => row.year === Number(year)); }
function currentRows(){
  const band = FREEDOM_BANDS[state.band];
  const min = Math.max(state.scoreMin, band.min);
  const max = Math.min(state.scoreMax, band.max);
  return yearRows(state.year).filter(row => {
    if (state.zone !== 'All zones' && row.zone !== state.zone) return false;
    if (state.search && !row.country.toLowerCase().includes(state.search)) return false;
    if (row.score < min || row.score > max) return false;
    return true;
  });
}
function mean(values){
  return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;
}
function sortDesc(rows){ return [...rows].sort((a, b) => b.score - a.score || a.rank - b.rank); }
function sortAsc(rows){ return [...rows].sort((a, b) => a.score - b.score || b.rank - a.rank); }
function zoneStats(rows){
  const grouped = new Map();
  rows.forEach(row => {
    const record = grouped.get(row.zone) || {zone: row.zone, total: 0, count: 0};
    record.total += row.score;
    record.count += 1;
    grouped.set(row.zone, record);
  });
  const colors = ['#1f7a45','#2f6690','#c29018','#d26a2e','#c43a28','#6f6f6f'];
  return [...grouped.values()].map((item, index) => ({
    zone: item.zone,
    score: item.total / item.count,
    count: item.count,
    color: colors[index % colors.length]
  })).sort((a, b) => b.score - a.score);
}
function compareRows(rows){
  const startMap = new Map(yearRows(DATA.startYear).map(row => [row.country, row]));
  return rows.filter(row => startMap.has(row.country)).map(row => ({
    country: row.country,
    change: row.score - startMap.get(row.country).score
  }));
}
function seriesForCountry(country){
  const out = [];
  for (const year of DATA.years) {
    if (year > state.year) continue;
    const row = currentRowsForYear(year).find(item => item.country === country);
    if (row) out.push(row);
  }
  return out;
}
function currentRowsForYear(year){
  const band = FREEDOM_BANDS[state.band];
  const min = Math.max(state.scoreMin, band.min);
  const max = Math.min(state.scoreMax, band.max);
  return yearRows(year).filter(row => {
    if (state.zone !== 'All zones' && row.zone !== state.zone) return false;
    if (state.search && !row.country.toLowerCase().includes(state.search)) return false;
    if (row.score < min || row.score > max) return false;
    return true;
  });
}
function averageSeries(){
  const out = [];
  for (const year of DATA.years) {
    if (year > state.year) continue;
    const rows = currentRowsForYear(year);
    out.push({year, score: mean(rows.map(row => row.score))});
  }
  return out;
}
function spotlightRow(rows){
  return rows.find(row => row.country === state.spotlight) || sortDesc(rows)[0] || null;
}
function renderEmpty(targetId, message){
  document.getElementById(targetId).innerHTML = `<div class="empty-state">${message}</div>`;
}
function buildMetrics(rows){
  const container = document.getElementById('metricsStrip');
  if (!rows.length) {
    container.innerHTML = '<div class="empty-state" style="grid-column:1/-1">No countries match the current filters.</div>';
    return;
  }
  const avg = mean(rows.map(row => row.score));
  const best = sortDesc(rows)[0];
  const spotlight = spotlightRow(rows);
  const cards = [
    {label:'Selected Year', value: state.year, sub:'RSF Annual Index', cls:'highlight'},
    {label:'Countries', value: rows.length, sub:'tracked globally'},
    {label:'Global Avg', value: formatNumber(avg), sub:'out of 100'},
    {label:'Most Free', value: best.country, sub:`score: ${formatNumber(best.score)}`, cls:'highlight'},
    {label: spotlight.country, value: formatNumber(spotlight.score), sub:`rank #${spotlight.rank} · ${spotlight.score - avg >= 0 ? '+' : ''}${formatNumber(spotlight.score - avg)} vs avg`, cls:'ph'}
  ];
  container.innerHTML = cards.map(card => `
    <div class="metric-cell ${card.cls || ''}">
      <div class="m-label">${card.label}</div>
      <div class="m-value">${card.value}</div>
      <div class="m-sub">${card.sub}</div>
    </div>`).join('');
}
function buildTicker(rows){
  const el = document.getElementById('tickerScroll');
  if (!rows.length) {
    el.innerHTML = '<span>No countries match the current filters.&nbsp;·&nbsp;</span><span>Try widening the score range or switching zone.&nbsp;·&nbsp;</span>';
    return;
  }
  const avg = mean(rows.map(row => row.score));
  const best = sortDesc(rows)[0];
  const worst = sortAsc(rows)[0];
  const zoneTop = zoneStats(rows)[0];
  const spotlight = spotlightRow(rows);
  const items = [
    `${best.country} leads the visible rankings with ${formatNumber(best.score)}`,
    `${spotlight.country} ranks #${spotlight.rank} in the current view`,
    `Filtered average: ${formatNumber(avg)} / 100`,
    zoneTop ? `${zoneTop.zone} scores highest among visible zones` : 'No zone data available',
    `${worst.country} is the lowest-scoring visible country`
  ];
  el.innerHTML = items.concat(items).map(item => `<span>${item} &nbsp;·&nbsp;</span>`).join('');
}
function buildBarList(targetId, rows, kind){
  const target = document.getElementById(targetId);
  if (!rows.length) {
    renderEmpty(targetId, 'No countries available for this view.');
    return;
  }
  target.innerHTML = '';
  rows.slice(0, 10).forEach((row, index) => {
    const el = document.createElement('div');
    const scoreClass = kind === 'green' ? 'good' : 'bad';
    const fillClass = row.country === state.spotlight ? 'ph' : kind;
    el.className = 'bar-row';
    el.innerHTML = `
      <span class="bar-country">${row.country}</span>
      <div class="bar-track"><div class="bar-fill ${fillClass}" style="width:0%"></div></div>
      <span class="bar-score ${scoreClass}">${formatNumber(row.score)}</span>`;
    el.addEventListener('mouseenter', event => showTip(event, `<b>${row.country}</b><br>Score: ${formatNumber(row.score)} / 100<br>Rank: #${row.rank}`));
    el.addEventListener('mouseleave', hideTip);
    el.addEventListener('click', () => { state.spotlight = row.country; refreshAll(); });
    target.appendChild(el);
    setTimeout(() => { el.querySelector('.bar-fill').style.width = row.score + '%'; }, index * 45 + 80);
  });
}
function buildZoneList(rows){
  const target = document.getElementById('zonebars');
  const zones = zoneStats(rows);
  if (!zones.length) {
    renderEmpty('zonebars', 'No zone data available for the active filters.');
    return;
  }
  target.innerHTML = '';
  zones.forEach((row, index) => {
    const el = document.createElement('div');
    el.className = 'zone-row';
    el.innerHTML = `
      <span class="zone-name">${row.zone}</span>
      <div class="zone-track"><div class="zone-fill" style="width:0%;background:${row.color}"></div></div>
      <span class="zone-score">${formatNumber(row.score)}</span>`;
    el.addEventListener('mouseenter', event => showTip(event, `<b>${row.zone}</b><br>Avg score: ${formatNumber(row.score)}<br>Countries: ${row.count}`));
    el.addEventListener('mouseleave', hideTip);
    el.addEventListener('click', () => {
      state.zone = row.zone;
      document.getElementById('zoneSelect').value = row.zone;
      refreshAll();
    });
    target.appendChild(el);
    setTimeout(() => { el.querySelector('.zone-fill').style.width = row.score + '%'; }, index * 45 + 80);
  });
}
function buildChangeList(targetId, rows, positive){
  const target = document.getElementById(targetId);
  const changes = compareRows(rows)
    .filter(item => positive ? item.change > 0 : item.change < 0)
    .sort((a, b) => positive ? b.change - a.change : a.change - b.change)
    .slice(0, 8);
  if (!changes.length) {
    renderEmpty(targetId, 'No change comparison available for these filters.');
    return;
  }
  target.innerHTML = '';
  changes.forEach((row, index) => {
    const pct = Math.min(Math.abs(row.change), 30) / 30 * 50;
    const el = document.createElement('div');
    el.className = 'change-row';
    el.innerHTML = `
      <span class="change-name">${row.country}</span>
      <div class="change-center">
        <div class="change-mid"></div>
        ${positive ? `<div class="change-fill-pos" style="width:0%"></div>` : `<div class="change-fill-neg" style="width:0%"></div>`}
      </div>
      <span class="change-score">${row.change > 0 ? '+' : ''}${formatNumber(row.change)}</span>`;
    el.addEventListener('mouseenter', event => showTip(event, `<b>${row.country}</b><br>Change: ${row.change > 0 ? '+' : ''}${formatNumber(row.change)} pts<br>${DATA.startYear} to ${state.year}`));
    el.addEventListener('mouseleave', hideTip);
    el.addEventListener('click', () => { state.spotlight = row.country; refreshAll(); });
    target.appendChild(el);
    setTimeout(() => {
      const fill = el.querySelector('.change-fill-pos, .change-fill-neg');
      if (fill) fill.style.width = pct + '%';
    }, index * 45 + 80);
  });
}
function buildMap(rows){
  if (!rows.length) {
    renderEmpty('mapPanel', 'No map rows match the current filters.');
    return;
  }
  const spotlight = spotlightRow(rows);
  const data = [{
    type: 'choropleth',
    locations: rows.map(row => ISO_COL ? row.iso : row.country),
    z: rows.map(row => row.score),
    text: rows.map(row => `${row.country}<br>Score: ${formatNumber(row.score)}<br>Rank: #${row.rank}`),
    hoverinfo: 'text',
    locationmode: ISO_COL ? 'ISO-3' : 'country names',
    colorscale: 'RdYlGn',
    zmin: 0,
    zmax: 100,
    marker: {line: {color: 'rgba(255,255,255,0.35)', width: 0.5}}
  }];
  if (spotlight && spotlight.iso) {
    data.push({
      type: 'scattergeo',
      locations: [spotlight.iso],
      locationmode: 'ISO-3',
      mode: 'markers',
      marker: {size: 12, color: '#f5f0e8', line: {color: '#c43a28', width: 3}},
      text: [`${spotlight.country}<br>Spotlight country`],
      hoverinfo: 'text',
      showlegend: false
    });
  }
  Plotly.react('mapPanel', data, {
    margin: {l:0, r:0, t:0, b:0},
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    geo: {
      projection: {type:'natural earth', scale:1.22},
      showframe: false,
      showcoastlines: false,
      showcountries: true,
      countrycolor: 'rgba(255,255,255,.25)',
      showland: true,
      landcolor: '#f8fafc',
      bgcolor: 'rgba(0,0,0,0)'
    }
  }, {displayModeBar:false, responsive:true});
  const panel = document.getElementById('mapPanel');
  panel.on('plotly_click', event => {
    const point = event?.points?.[0];
    if (!point) return;
    const country = rows.find(row => (ISO_COL ? row.iso : row.country) === point.location)?.country;
    if (country) {
      state.spotlight = country;
      refreshAll();
    }
  });
}
function buildDistributionPlot(rows){
  if (!rows.length) {
    renderEmpty('distributionPlot', 'No countries match the current filters.');
    return;
  }
  Plotly.react('distributionPlot', [{
    type: 'histogram',
    x: rows.map(row => row.score),
    nbinsx: 14,
    marker: {color: '#c29018', line: {color: '#9d6f0f', width: 1}},
    hovertemplate: 'Score bin: %{x}<br>Countries: %{y}<extra></extra>'
  }], {
    margin: {l: 35, r: 15, t: 8, b: 38},
    paper_bgcolor: '#ffffff',
    plot_bgcolor: '#ffffff',
    font: {family: 'Georgia, serif', size: 12, color: '#101010'},
    xaxis: {title: 'Score', gridcolor: 'rgba(0,0,0,.07)', range: [0, 100]},
    yaxis: {title: 'Countries', gridcolor: 'rgba(0,0,0,.07)'}
  }, {displayModeBar:false, responsive:true});
}
function buildScatterPlot(rows){
  if (!rows.length) {
    renderEmpty('scatterPlot', 'No countries match the current filters.');
    return;
  }
  const spotlight = spotlightRow(rows);
  const markerSizes = rows.map(row => row.country === spotlight?.country ? 14 : 9);
  const markerColors = rows.map(row => row.country === spotlight?.country ? '#c43a28' : '#163a5f');
  Plotly.react('scatterPlot', [{
    type: 'scatter',
    mode: 'markers',
    x: rows.map(row => row.rank),
    y: rows.map(row => row.score),
    text: rows.map(row => `${row.country}<br>Rank: #${row.rank}<br>Score: ${formatNumber(row.score)}<br>Zone: ${row.zone}`),
    hoverinfo: 'text',
    marker: {size: markerSizes, color: markerColors, opacity: 0.82, line: {color: '#ffffff', width: 1}}
  }], {
    margin: {l: 40, r: 15, t: 8, b: 40},
    paper_bgcolor: '#ffffff',
    plot_bgcolor: '#ffffff',
    font: {family: 'Georgia, serif', size: 12, color: '#101010'},
    xaxis: {title: 'Rank', autorange: 'reversed', gridcolor: 'rgba(0,0,0,.07)'},
    yaxis: {title: 'Score', range: [0, 100], gridcolor: 'rgba(0,0,0,.07)'}
  }, {displayModeBar:false, responsive:true});
  const panel = document.getElementById('scatterPlot');
  panel.on('plotly_click', event => {
    const point = event?.points?.[0];
    if (!point) return;
    const country = point.text?.split('<br>')[0];
    if (country) {
      state.spotlight = country;
      refreshAll();
    }
  });
}
function activeTrendCountries(rows){
  const available = new Set(rows.map(row => row.country));
  const active = state.countries.filter(country => available.has(country));
  if (active.length) return active;
  return rows.slice(0, 6).map(row => row.country);
}
function buildTrendChart(rows){
  const canvas = document.getElementById('trendChart');
  const countries = activeTrendCountries(rows);
  const labels = DATA.years.filter(year => year <= state.year);
  if (trendChart) trendChart.destroy();
  if (!countries.length) return;
  const datasets = countries.map((country, index) => ({
    label: country,
    data: labels.map(year => {
      const row = currentRowsForYear(year).find(item => item.country === country);
      return row ? row.score : null;
    }),
    borderColor: trendPalette[index % trendPalette.length],
    backgroundColor: country === state.spotlight ? 'rgba(22,58,95,.08)' : 'transparent',
    fill: country === state.spotlight,
    borderWidth: country === state.spotlight ? 2.8 : 2.1,
    pointRadius: 3,
    tension: 0.28
  }));
  trendChart = new Chart(canvas.getContext('2d'), {
    type: 'line',
    data: {labels, datasets},
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {legend: {position: 'bottom', labels: {boxWidth: 10, font: {size: 11, family: 'Courier New'}, padding: 10}}},
      scales: {
        x: {grid: {color: 'rgba(0,0,0,.06)'}, ticks: {font: {size: 11, family: 'Courier New'}}},
        y: {min: 0, max: 100, grid: {color: 'rgba(0,0,0,.06)'}, ticks: {font: {size: 11, family: 'Courier New'}}}
      }
    }
  });
}
function buildSpotlightChart(rows){
  const canvas = document.getElementById('phChart');
  const spotlight = spotlightRow(rows);
  if (phChart) phChart.destroy();
  if (!spotlight) return;
  const series = seriesForCountry(spotlight.country);
  const averages = averageSeries();
  phChart = new Chart(canvas.getContext('2d'), {
    type: 'line',
    data: {
      labels: series.map(row => row.year),
      datasets: [
        {label: spotlight.country, data: series.map(row => row.score), borderColor: '#003a8c', backgroundColor: 'rgba(0,58,140,.1)', fill: true, borderWidth: 2.8, pointRadius: 4, tension: 0.28},
        {label: 'Filtered average', data: averages.map(row => row.score), borderColor: '#c43a28', borderDash: [5,3], borderWidth: 1.8, pointRadius: 0, fill: false}
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {legend: {position: 'bottom', labels: {boxWidth: 10, font: {size: 11, family: 'Courier New'}, padding: 10}}},
      scales: {
        x: {grid: {color: 'rgba(0,0,0,.06)'}, ticks: {font: {size: 11, family: 'Courier New'}}},
        y: {min: 0, max: 100, grid: {color: 'rgba(0,0,0,.06)'}, ticks: {font: {size: 11, family: 'Courier New'}}}
      }
    }
  });
}
function buildSpotlightStats(rows){
  const spotlight = spotlightRow(rows);
  if (!spotlight) return;
  const avg = mean(rows.map(row => row.score));
  const series = seriesForCountry(spotlight.country);
  const first = series[0] || spotlight;
  document.getElementById('spotlightHeading').textContent = `${spotlight.country} Spotlight`;
  document.getElementById('spotlightChartTitle').textContent = `${spotlight.country} Score Over Time vs Filtered Average`;
  document.getElementById('spotlightScoreLabel').textContent = `Score (${state.year})`;
  document.getElementById('spotlightRankLabel').textContent = 'Visible Rank';
  document.getElementById('spotlightChangeLabel').textContent = `Change Since ${DATA.startYear}`;
  document.getElementById('spotlightChangeNote').textContent = `Compared with ${DATA.startYear}`;
  document.getElementById('spotlightDeltaLabel').textContent = 'vs Filtered Avg';
  document.getElementById('phScoreValue').textContent = `${formatNumber(spotlight.score)} / 100`;
  document.getElementById('phRankValue').textContent = `#${spotlight.rank}`;
  document.getElementById('phChangeValue').textContent = `${spotlight.score - first.score >= 0 ? '+' : ''}${formatNumber(spotlight.score - first.score)} pts`;
  document.getElementById('phDeltaValue').textContent = `${spotlight.score - avg >= 0 ? '+' : ''}${formatNumber(spotlight.score - avg)} pts`;
}
function refreshSpotlightOptions(rows){
  const select = document.getElementById('spotlightSelect');
  const countries = [...new Set(rows.map(row => row.country))].sort();
  if (!countries.includes(state.spotlight)) state.spotlight = countries[0] || DATA.spotlightDefault;
  select.innerHTML = countries.map(country => `<option value="${country}" ${country === state.spotlight ? 'selected' : ''}>${country}</option>`).join('');
}
function refreshCountryTags(rows){
  const available = [...new Set(rows.map(row => row.country))];
  const candidates = [...new Set([...state.countries, state.spotlight, ...DATA.defaultCountries, ...available.slice(0, 5)])].filter(country => available.includes(country)).slice(0, 8);
  const tags = document.getElementById('countryTags');
  tags.innerHTML = '';
  candidates.forEach(country => {
    const tag = document.createElement('span');
    tag.className = `tag ${state.countries.includes(country) ? 'active' : ''}`;
    tag.textContent = country;
    tag.addEventListener('click', () => {
      if (state.countries.includes(country)) {
        state.countries = state.countries.filter(item => item !== country);
      } else {
        state.countries.push(country);
      }
      refreshAll();
    });
    tags.appendChild(tag);
  });
}
function updateSidebar(rows){
  document.getElementById('filteredCount').textContent = rows.length;
  document.getElementById('sidebarAvgValue').textContent = rows.length ? formatNumber(mean(rows.map(row => row.score))) : '-';
  document.getElementById('sidebarBestValue').textContent = rows.length ? sortDesc(rows)[0].country : '-';
  document.getElementById('sidebarWorstValue').textContent = rows.length ? sortAsc(rows)[0].country : '-';
  document.getElementById('scoreMinLabel').textContent = state.scoreMin;
  document.getElementById('scoreMaxLabel').textContent = state.scoreMax;
  document.querySelectorAll('.scale-chip').forEach(chip => chip.classList.toggle('active', chip.dataset.key === state.band));
}
function refreshAll(){
  const rows = currentRows();
  buildTicker(rows);
  buildMetrics(rows);
  refreshSpotlightOptions(rows);
  refreshCountryTags(rows);
  updateSidebar(rows);
  buildBarList('top10bars', sortDesc(rows).slice(0, 10), 'green');
  buildBarList('bottom10bars', sortAsc(rows).slice(0, 10), 'red');
  buildZoneList(rows);
  buildMap(rows);
  buildDistributionPlot(rows);
  buildScatterPlot(rows);
  buildChangeList('improved', rows, true);
  buildChangeList('declined', rows, false);
  buildTrendChart(rows);
  buildSpotlightChart(rows);
  buildSpotlightStats(rows);
}
function updateLayoutOffsets(){
  const header = document.querySelector('.site-header');
  if (!header) return;
  const height = header.offsetHeight;
  document.documentElement.style.setProperty('--header-h', `${height}px`);
}

document.querySelectorAll('.nav-item').forEach(item => {
  item.addEventListener('click', () => {
    document.querySelectorAll('.nav-item').forEach(other => other.classList.remove('active'));
    item.classList.add('active');
    const target = document.getElementById(item.dataset.target);
    if (target) target.scrollIntoView({behavior:'smooth', block:'start'});
  });
});

const yearSelect = document.getElementById('yearSelect');
for (const year of [...DATA.years].reverse()) {
  const option = document.createElement('option');
  option.value = year;
  option.textContent = year;
  if (year === DATA.latestYear) option.selected = true;
  yearSelect.appendChild(option);
}
const zoneSelect = document.getElementById('zoneSelect');
zoneSelect.innerHTML = ['All zones', ...DATA.zones].map(zone => `<option value="${zone}">${zone}</option>`).join('');
const scaleFilters = document.getElementById('scaleFilters');
Object.entries(FREEDOM_BANDS).forEach(([key, band]) => {
  const chip = document.createElement('button');
  chip.type = 'button';
  chip.className = `scale-chip ${key === state.band ? 'active' : ''}`;
  chip.dataset.key = key;
  chip.textContent = band.label;
  chip.addEventListener('click', () => {
    state.band = key;
    state.scoreMin = band.min;
    state.scoreMax = band.max;
    document.getElementById('scoreMinRange').value = band.min;
    document.getElementById('scoreMaxRange').value = band.max;
    refreshAll();
  });
  scaleFilters.appendChild(chip);
});

yearSelect.addEventListener('change', event => { state.year = Number(event.target.value); refreshAll(); });
zoneSelect.addEventListener('change', event => { state.zone = event.target.value; refreshAll(); });
document.getElementById('spotlightSelect').addEventListener('change', event => { state.spotlight = event.target.value; refreshAll(); });
document.getElementById('countrySearch').addEventListener('input', event => { state.search = event.target.value.trim().toLowerCase(); refreshAll(); });
function syncScoreRange(){
  let min = Number(document.getElementById('scoreMinRange').value);
  let max = Number(document.getElementById('scoreMaxRange').value);
  if (min > max) [min, max] = [max, min];
  state.scoreMin = min;
  state.scoreMax = max;
  document.getElementById('scoreMinRange').value = min;
  document.getElementById('scoreMaxRange').value = max;
  state.band = 'all';
  refreshAll();
}
document.getElementById('scoreMinRange').addEventListener('input', syncScoreRange);
document.getElementById('scoreMaxRange').addEventListener('input', syncScoreRange);

updateLayoutOffsets();
refreshAll();
window.addEventListener('resize', () => {
  updateLayoutOffsets();
  refreshAll();
});
</script>
</body>
</html>
"""


@app.route("/")
def index():
    latest_best = LATEST_DF.sort_values("score", ascending=False).iloc[0]["country"]
    latest_worst = LATEST_DF.sort_values("score", ascending=True).iloc[0]["country"]
    return render_template_string(
        TEMPLATE,
        title=APP_TITLE,
        dataset_name=DATA_FILE.name,
        row_count=len(DF),
        country_count=DF["country"].nunique(),
        start_year=START_YEAR,
        latest_year=LATEST_YEAR,
        latest_avg=f"{LATEST_AVG:.1f}",
        latest_best=latest_best,
        latest_worst=latest_worst,
        data_json=DATA_JSON,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=False)
