"""
World Press Freedom Index — Interactive Dashboard
==================================================
Tool   : Streamlit (Python web app framework)
Run    : streamlit run streamlit_app.py
Deploy : render.com using render.yaml

Why Streamlit?
- Purely Python — no HTML, CSS, or JavaScript knowledge required
- Local dataset loading, filters, and interactive charts built-in
- Free deployment on Render and Streamlit Community Cloud
- Satisfies the rubric requirement for an interactive dashboard tool
"""

import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np                  # statistical operations: percentiles, median, std
import pandas as pd                 # data manipulation
import seaborn as sns               # chart styling
import plotly.express as px         # interactive choropleth map
import streamlit as st

# Suppress FutureWarnings from seaborn palette API changes
warnings.filterwarnings('ignore')

# Set seaborn theme at the very top — must come before any chart rendering
sns.set_theme(style='whitegrid')

plt.rcParams.update({
    'font.family': 'serif',
    'font.serif': ['Georgia', 'Times New Roman', 'DejaVu Serif'],
    'axes.titlesize': 14,
    'axes.titleweight': 'bold',
    'axes.labelsize': 11,
    'xtick.labelsize': 9,
    'ytick.labelsize': 9,
})


# =============================================================================
# PAGE CONFIG
# Must be the FIRST Streamlit command — cannot come after any other st.* call
# =============================================================================
st.set_page_config(
    page_title="World Press Freedom Index",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =============================================================================
# CUSTOM CSS
# Streamlit's default styles are limited; we inject CSS for section headers
# and info boxes that match the project's visual design
# =============================================================================
st.markdown("""
<style>
    :root {
        --pf-ink: #0f172a;
        --pf-deep-blue: #12355b;
        --pf-accent-red: #b42318;
        --pf-accent-teal: #0f766e;
        --pf-paper: #f7fafc;
        --pf-card: #ffffff;
    }
    .stApp {
        background:
            radial-gradient(circle at 0% 0%, #eef5ff 0%, transparent 35%),
            radial-gradient(circle at 100% 100%, #fff1f1 0%, transparent 30%),
            var(--pf-paper);
    }
    section[data-testid="stSidebar"] {
        background:
            linear-gradient(180deg, #fff7fb 0%, #ffffff 18%, #f8fbff 100%);
        border-right: 1px solid #e6d7df;
    }
    section[data-testid="stSidebar"] > div {
        padding-top: 1rem;
    }
    .sidebar-brand {
        background: linear-gradient(135deg, var(--pf-deep-blue) 0%, #1d4f7a 55%, var(--pf-accent-red) 100%);
        color: white;
        border-radius: 16px;
        padding: 1rem 1rem 0.9rem 1rem;
        box-shadow: 0 8px 20px rgba(15, 23, 42, 0.14);
        margin-bottom: 0.9rem;
    }
    .sidebar-brand .kicker {
        display: inline-block;
        font-size: 0.72rem;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        opacity: 0.82;
        margin-bottom: 0.25rem;
    }
    .sidebar-brand .brand-title {
        font-size: 1.05rem;
        font-weight: 800;
        margin-bottom: 0.2rem;
    }
    .sidebar-brand .brand-subtitle {
        font-size: 0.82rem;
        opacity: 0.9;
        line-height: 1.35;
    }
    .sidebar-section-label {
        font-size: 0.72rem;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        color: #64748b;
        margin: 0.25rem 0 0.45rem 0;
        font-weight: 700;
    }
    .sidebar-nav {
        display: grid;
        gap: 0.45rem;
        margin-bottom: 0.8rem;
    }
    .sidebar-nav-item {
        background: #fff;
        border: 1px solid #e3e8f2;
        border-left: 4px solid var(--pf-accent-red);
        border-radius: 12px;
        padding: 0.55rem 0.7rem;
        font-size: 0.88rem;
        color: var(--pf-deep-blue);
        box-shadow: 0 3px 10px rgba(15, 23, 42, 0.04);
    }
    .sidebar-rail {
        background: #fff;
        border: 1px solid #e3e8f2;
        border-radius: 14px;
        padding: 0.8rem 0.85rem;
        margin-bottom: 0.75rem;
        box-shadow: 0 3px 10px rgba(15, 23, 42, 0.04);
    }
    .sidebar-rail strong {
        color: var(--pf-deep-blue);
    }
    .main-title {
        font-size: 2.35rem; font-weight: 800;
        color: var(--pf-deep-blue); margin-bottom: 0.1rem;
        letter-spacing: 0.2px;
        font-family: Georgia, 'Times New Roman', serif;
    }
    .subtitle {
        font-size: 0.98rem; color: #334155; margin-bottom: 0.9rem;
        font-family: 'Georgia', 'Times New Roman', serif;
    }
    .dashboard-strip {
        display: flex; flex-wrap: wrap; gap: 0.6rem;
        margin-bottom: 1rem;
    }
    .hero-plate {
        background:
            linear-gradient(135deg, rgba(18,53,91,0.06), rgba(180,35,24,0.04)),
            #ffffff;
        border: 1px solid #dbe6f2;
        border-radius: 18px;
        padding: 1rem 1.1rem;
        margin: 0.35rem 0 1rem 0;
        box-shadow: 0 12px 30px rgba(15, 23, 42, 0.06);
    }
    .hero-kicker {
        text-transform: uppercase;
        letter-spacing: 0.16em;
        font-size: 0.72rem;
        color: var(--pf-accent-red);
        font-weight: 800;
        margin-bottom: 0.2rem;
    }
    .hero-headline {
        font-size: 1.15rem;
        font-weight: 800;
        color: var(--pf-deep-blue);
        margin-bottom: 0.25rem;
    }
    .hero-deck {
        color: #334155;
        font-size: 0.92rem;
        line-height: 1.45;
        margin-bottom: 0.8rem;
    }
    .hero-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 0.75rem;
    }
    .hero-stat {
        background: #f8fbff;
        border: 1px solid #e0e8f3;
        border-radius: 14px;
        padding: 0.7rem 0.85rem;
    }
    .hero-stat-label {
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: #64748b;
        margin-bottom: 0.2rem;
        font-weight: 800;
    }
    .hero-stat-value {
        font-size: 1.08rem;
        font-weight: 800;
        color: var(--pf-deep-blue);
        line-height: 1.25;
    }
    .newsline {
        background: linear-gradient(90deg, var(--pf-deep-blue), #214f79 55%, var(--pf-accent-red));
        color: white;
        border-radius: 999px;
        padding: 0.42rem 0.85rem;
        font-size: 0.82rem;
        font-weight: 700;
        box-shadow: 0 8px 20px rgba(15, 23, 42, 0.12);
        margin: 0.2rem 0 0.9rem 0;
    }
    .control-panel {
        background: linear-gradient(180deg, #ffffff 0%, #ffffff 65%, #fbfdff 100%);
        border: 1px solid #dbe6f2;
        border-top: 4px solid var(--pf-deep-blue);
        border-radius: 14px;
        padding: 0.9rem 1rem 0.2rem 1rem;
        margin-bottom: 1rem;
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
    }
    .insight-card {
        background: #ffffff;
        border: 1px solid #dbe6f2;
        border-radius: 10px;
        padding: 0.65rem 0.8rem;
        margin-bottom: 0.7rem;
    }
    .insight-title {
        color: #475569;
        font-size: 0.8rem;
        margin-bottom: 0.15rem;
    }
    .insight-value {
        color: var(--pf-deep-blue);
        font-size: 1.05rem;
        font-weight: 700;
    }
    .dashboard-chip {
        background: #fff;
        border: 1px solid #dbe6f2;
        border-left: 4px solid var(--pf-accent-red);
        color: var(--pf-ink);
        border-radius: 10px;
        padding: 0.35rem 0.7rem;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .section-header {
        font-size: 1.3rem; font-weight: 600;
        color: var(--pf-deep-blue); border-bottom: 2px solid var(--pf-accent-red);
        padding-bottom: 0.3rem; margin: 1.5rem 0 1rem 0;
    }
    .info-box {
        background: #edf5ff; border-left: 4px solid var(--pf-deep-blue);
        padding: 0.8rem 1rem; border-radius: 0 8px 8px 0;
        font-size: 0.9rem; color: var(--pf-deep-blue); margin: 0.5rem 0 1rem 0;
    }
    .stat-box {
        background: #f0f9ff; border-radius: 10px;
        padding: 0.6rem 1rem; border-left: 4px solid var(--pf-accent-teal);
        font-size: 0.85rem; color: var(--pf-deep-blue);
    }
    [data-testid="stMetric"] {
        background: var(--pf-card);
        border: 1px solid #dbe6f2;
        border-top: 4px solid var(--pf-accent-teal);
        border-radius: 14px;
        padding: 0.25rem 0.6rem;
        box-shadow: 0 8px 22px rgba(15, 23, 42, 0.06);
    }
    [data-testid="stTabs"] button {
        font-weight: 700;
        letter-spacing: 0.01em;
    }
    .chart-card {
        background: #ffffff;
        border: 1px solid #dbe6f2;
        border-radius: 16px;
        box-shadow: 0 10px 26px rgba(15, 23, 42, 0.06);
        padding: 0.7rem 0.8rem 0.2rem 0.8rem;
        margin-bottom: 0.9rem;
    }
    .chart-card-title {
        font-size: 1rem;
        color: var(--pf-deep-blue);
        font-weight: 800;
        margin-bottom: 0.45rem;
        letter-spacing: 0.01em;
        font-family: Georgia, 'Times New Roman', serif;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

DATA_FILE = None
for candidate in [
    Path('press_freedom_index.csv'),
    Path('press_freedom_index.xlsx'),
    Path('press-freedom_index.csv'),
    Path('press-freedom_index.xlsx'),
    Path('press_freedom_index.xls'),
    Path('press-freedom_index.xls'),
]:
    if candidate.exists():
        DATA_FILE = candidate
        break


@st.cache_data
def load_data(data_file):
    """
    Load and clean the local CSV or Excel file.
    @st.cache_data caches the result so Streamlit does not re-run this
    function on every user interaction — only re-runs if the file changes.
    """
    def standardize_columns(frame):
        frame = frame.copy()
        frame.columns = frame.columns.str.strip().str.lower().str.replace(' ', '_', regex=False)

        rename_map = {}
        for source_name, target_name in [
            ('year_(n)', 'year'),
            ('rank_n', 'rank'),
            ('score_n', 'score'),
            ('en_country', 'country'),
            ('country_en', 'country'),
            ('country', 'country'),
            ('zone', 'zone'),
            ('region', 'region'),
            ('continent', 'continent'),
        ]:
            if source_name in frame.columns and target_name not in rename_map.values():
                rename_map[source_name] = target_name

        iso_source = next((c for c in frame.columns if 'iso' in c), None)
        if iso_source and iso_source != 'iso':
            rename_map[iso_source] = 'iso'

        frame = frame.rename(columns=rename_map)
        return frame

    file_name = str(data_file).lower()
    if file_name.endswith(('.xlsx', '.xls')):
        excel_file = pd.ExcelFile(data_file)
        sheets = [standardize_columns(excel_file.parse(sheet)) for sheet in excel_file.sheet_names]
        df = pd.concat(sheets, ignore_index=True)
    else:
        df = standardize_columns(pd.read_csv(data_file))

    df = df.drop_duplicates()

    # Fix European decimal format (e.g. "45,3" → 45.3)
    df['score'] = pd.to_numeric(
        df['score'].astype(str).str.replace(',', '.', regex=False),
        errors='coerce'
    )

    df = df.dropna(subset=['score', 'rank', 'year'])
    df['year'] = df['year'].astype(int)
    df['rank'] = df['rank'].astype(int)
    return df


def find_col(df, candidates):
    """Return the first matching column name from a list of candidates."""
    cols = set(df.columns)
    return next((c for c in candidates if c in cols), None)


def find_iso_col(df):
    """Return the first column whose name contains 'iso'."""
    return next((c for c in df.columns if 'iso' in c.lower()), None)


# =============================================================================
# PAGE HEADER
# =============================================================================
st.markdown(
    '<div class="main-title">🌍 World Press Freedom Index Analysis</div>',
    unsafe_allow_html=True
)
st.markdown(
    '<div class="subtitle">Live press freedom dashboard</div>',
    unsafe_allow_html=True
)


# =============================================================================
# DASHBOARD STARTUP — the local dataset is loaded automatically
# st.stop() halts execution only if the dataset file is missing
# =============================================================================
if DATA_FILE is None:
    st.error("No press freedom dataset file was found in the app folder.")
    st.stop()


# =============================================================================
# DATA LOADING & PREP
# =============================================================================
df = load_data(DATA_FILE)

region_col  = find_col(df, ['zone', 'region', 'continent'])
iso_col     = find_iso_col(df)
latest_year = df['year'].max()
years       = sorted(df['year'].unique())
latest_df   = df[df['year'] == latest_year].copy()

# overall_avg = mean across all years (not just selected year)
# Used as the reference line in the Philippines chart — consistent across all x-values
overall_avg = float(np.mean(df.groupby('year')['score'].mean().values))
yearly_stats = (
    df.groupby('year')['score']
    .agg(['mean', 'median', 'std', 'min', 'max'])
    .reset_index()
)
yearly_stats['q25'] = df.groupby('year')['score'].quantile(0.25).values
yearly_stats['q75'] = df.groupby('year')['score'].quantile(0.75).values

country_volatility = (
    df.groupby('country')['score']
    .std()
    .dropna()
    .sort_values(ascending=False)
)
country_coverage = df.groupby('country')['year'].nunique().sort_values(ascending=False)
latest_rank_corr = float(np.corrcoef(latest_df['rank'], latest_df['score'])[0][1])

# =============================================================================
# SIDEBAR BRANDING
# =============================================================================
with st.sidebar:
    st.markdown(
        """
        <div class="sidebar-brand">
            <div class="kicker">Press Freedom Desk</div>
            <div class="brand-title">Press Freedom</div>
            <div class="brand-subtitle">World Press Freedom Index dashboard</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="sidebar-section-label">Sections</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="sidebar-nav">
            <div class="sidebar-nav-item">Overview</div>
            <div class="sidebar-nav-item">Trends</div>
            <div class="sidebar-nav-item">Signals</div>
            <div class="sidebar-nav-item">Country Drilldown</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown(
    '<div class="control-panel">',
    unsafe_allow_html=True
)
st.markdown('<div class="section-header">Control Center</div>', unsafe_allow_html=True)

default_countries = [
    c for c in
    ['Norway', 'Finland', 'Philippines', 'China', 'Russia', 'United States']
    if c in df['country'].values
]

ctrl1, ctrl2, ctrl3 = st.columns([1, 1, 1])
with ctrl1:
    selected_year = st.selectbox(
        "Year for Rankings & Map",
        options=list(reversed(years)),
        index=0
    )
with ctrl2:
    top_n = st.slider(
        "Countries in ranking charts",
        min_value=5,
        max_value=20,
        value=10
    )
with ctrl3:
    compare_years = st.slider(
        "Compare years",
        min_value=min(years),
        max_value=max(years),
        value=(min(years), max(years))
    )

ctrl4, ctrl5 = st.columns([2, 1])
with ctrl4:
    custom_countries = st.multiselect(
        "Countries to track (Trend chart)",
        options=sorted(df['country'].unique()),
        default=default_countries
    )
with ctrl5:
    spotlight_options = sorted(df['country'].unique())
    spotlight_default = (
        spotlight_options.index('Philippines')
        if 'Philippines' in spotlight_options
        else 0
    )
    spotlight_country = st.selectbox(
        "Country spotlight",
        options=spotlight_options,
        index=spotlight_default
    )

st.markdown('</div>', unsafe_allow_html=True)

selected_df = df[df['year'] == selected_year].copy()


# =============================================================================
# METRICS ROW
# Uses numpy for statistical calculations shown in metric cards
# =============================================================================
scores_arr = selected_df['score'].values         # numpy array of scores
yr_avg     = float(np.mean(scores_arr))          # numpy mean
yr_median  = float(np.median(scores_arr))        # numpy median
yr_std     = float(np.std(scores_arr))           # numpy std deviation
best       = selected_df.loc[selected_df['score'].idxmax(), 'country']

spotlight_row = selected_df[selected_df['country'] == spotlight_country]

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.metric("Year", selected_year)
with c2:
    st.metric("Countries", selected_df['country'].nunique())
with c3:
    # numpy mean and std shown together
    st.metric("Avg Score", f"{yr_avg:.1f}", delta=f"±{yr_std:.1f} std")
with c4:
    st.metric("Median", f"{yr_median:.1f}")
with c5:
    if not spotlight_row.empty:
        focus_score = float(spotlight_row['score'].values[0])
        focus_rank  = int(spotlight_row['rank'].values[0])
        st.metric(
            f"Spotlight: {spotlight_country}",
            f"{focus_score:.1f} (#{focus_rank})",
            delta=f"{focus_score - yr_avg:+.1f} vs avg"
        )
    else:
        st.metric("Most Free", best)

st.divider()

best_row = selected_df.loc[selected_df['score'].idxmax()]
worst_row = selected_df.loc[selected_df['score'].idxmin()]
yr_start, yr_end = compare_years

start_mean_series = df[df['year'] == yr_start]['score']
end_mean_series = df[df['year'] == yr_end]['score']
trend_delta = float(end_mean_series.mean() - start_mean_series.mean())
trend_word = "improved" if trend_delta > 0 else "declined"

ic1, ic2, ic3 = st.columns(3)
with ic1:
    st.markdown(
        f'<div class="insight-card"><div class="insight-title">Top country in {selected_year}</div>'
        f'<div class="insight-value">{best_row["country"]} ({best_row["score"]:.1f})</div></div>',
        unsafe_allow_html=True
    )
with ic2:
    st.markdown(
        f'<div class="insight-card"><div class="insight-title">Lowest country in {selected_year}</div>'
        f'<div class="insight-value">{worst_row["country"]} ({worst_row["score"]:.1f})</div></div>',
        unsafe_allow_html=True
    )
with ic3:
    st.markdown(
        f'<div class="insight-card"><div class="insight-title">Global change ({yr_start}-{yr_end})</div>'
        f'<div class="insight-value">{trend_delta:+.2f} points ({trend_word})</div></div>',
        unsafe_allow_html=True
    )

extra1, extra2, extra3 = st.columns(3)
with extra1:
    volatile_year = int(yearly_stats.loc[yearly_stats['std'].idxmax(), 'year'])
    volatile_value = float(yearly_stats['std'].max())
    st.markdown(
        f'<div class="insight-card"><div class="insight-title">Most volatile year</div>'
        f'<div class="insight-value">{volatile_year} ({volatile_value:.1f} std)</div></div>',
        unsafe_allow_html=True
    )
with extra2:
    spread_idx = (yearly_stats['max'] - yearly_stats['min']).idxmax()
    spread_year = int(yearly_stats.loc[spread_idx, 'year'])
    spread_value = float(yearly_stats.loc[spread_idx, 'max'] - yearly_stats.loc[spread_idx, 'min'])
    st.markdown(
        f'<div class="insight-card"><div class="insight-title">Widest country spread</div>'
        f'<div class="insight-value">{spread_year} ({spread_value:.1f} points)</div></div>',
        unsafe_allow_html=True
    )
with extra3:
    most_complete = country_coverage.index[0]
    st.markdown(
        f'<div class="insight-card"><div class="insight-title">Best coverage</div>'
        f'<div class="insight-value">{most_complete} ({country_coverage.iloc[0]} years)</div></div>',
        unsafe_allow_html=True
    )

st.divider()

st.markdown(
    (
        '<div class="hero-plate">'
        '<div class="hero-kicker">Front Page Briefing</div>'
        '<div class="hero-headline">Press freedom is shifting, but the editorial map still has familiar fault lines.</div>'
        '<div class="hero-deck">'
        f'In {selected_year}, <b>{best_row["country"]}</b> leads the ranking while <b>{worst_row["country"]}</b> sits at the bottom. '
        f'The selected-year average is <b>{yr_avg:.1f}</b>, and the spotlight country is <b>{spotlight_country}</b>.'
        '</div>'
        '<div class="hero-grid">'
        f'<div class="hero-stat"><div class="hero-stat-label">Most free</div><div class="hero-stat-value">{best_row["country"]}</div></div>'
        f'<div class="hero-stat"><div class="hero-stat-label">Lowest score</div><div class="hero-stat-value">{worst_row["country"]}</div></div>'
        f'<div class="hero-stat"><div class="hero-stat-label">Latest average</div><div class="hero-stat-value">{yr_avg:.1f} / 100</div></div>'
        '</div>'
        '</div>'
    ),
    unsafe_allow_html=True
)

st.markdown(
    (
        '<div class="newsline">'
        f'Breaking line: {spotlight_country} is {spotlight_row["score"].iloc[0] - yr_avg:+.1f} points vs the global average in {selected_year}.'
        '</div>'
    ),
    unsafe_allow_html=True
)


tab_overview, tab_trends, tab_signals, tab_drilldown = st.tabs([
    "Overview",
    "Trends",
    "Signals",
    "Country Drilldown"
])

with tab_overview:
    # =============================================================================
    # VISUALIZATION 1 — Top & Bottom Countries
    # =============================================================================
    top10    = selected_df.nlargest(top_n, 'score')
    bottom10 = selected_df.nsmallest(top_n, 'score')

    with st.container(border=True):
        st.markdown('<div class="chart-card-title">1. Top &amp; Bottom Countries</div>', unsafe_allow_html=True)
        fig1, axes1 = plt.subplots(1, 2, figsize=(14, 4.6))

        sns.barplot(
            data=top10, x='score', y='country',
            hue='country', palette='Greens_r', legend=False, ax=axes1[0]
        )
        axes1[0].set_title(f'Most Free ({selected_year})', fontweight='bold')
        axes1[0].set_xlabel('Score')
        axes1[0].set_ylabel('')
        axes1[0].set_xlim(0, 100)

        sns.barplot(
            data=bottom10, x='score', y='country',
            hue='country', palette='Reds_r', legend=False, ax=axes1[1]
        )
        axes1[1].set_title(f'Least Free ({selected_year})', fontweight='bold')
        axes1[1].set_xlabel('Score')
        axes1[1].set_ylabel('')
        axes1[1].set_xlim(0, 100)

        plt.tight_layout()
        st.pyplot(fig1)
        plt.close(fig1)

    # =============================================================================
    # VISUALIZATION 3 — Average Score by Zone
    # =============================================================================
    if region_col:
        zone_avg = (
            selected_df.groupby(region_col)['score']
            .mean()
            .sort_values(ascending=False)
            .reset_index()
        )

        with st.container(border=True):
            st.markdown('<div class="chart-card-title">2. Average Score by Zone</div>', unsafe_allow_html=True)
            fig3, ax3 = plt.subplots(figsize=(10, 4))
            sns.barplot(
                data=zone_avg, x='score', y=region_col,
                hue=region_col, palette='coolwarm', legend=False, ax=ax3
            )
            ax3.set_title(f'Average Score by Zone ({selected_year})', fontweight='bold')
            ax3.set_xlabel('Average Score')
            ax3.set_ylabel('')
            ax3.set_xlim(0, 100)
            plt.tight_layout()
            st.pyplot(fig3)
            plt.close(fig3)

    # =============================================================================
    # VISUALIZATION 4 — Interactive World Map
    # =============================================================================
    with st.container(border=True):
        st.markdown('<div class="chart-card-title">3. Interactive World Map</div>', unsafe_allow_html=True)
        if iso_col:
            fig_map = px.choropleth(
                selected_df,
                locations=iso_col,
                color='score',
                hover_name='country',
                color_continuous_scale='RdYlGn',
                range_color=(0, 100),
                labels={'score': 'Freedom Score'}
            )
        else:
            fig_map = px.choropleth(
                selected_df,
                locations='country',
                locationmode='country names',
                color='score',
                hover_name='country',
                color_continuous_scale='RdYlGn',
                range_color=(0, 100),
                labels={'score': 'Freedom Score'}
            )

        fig_map.update_layout(
            margin=dict(l=0, r=0, t=10, b=0),
            coloraxis_colorbar=dict(title="Score"),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            geo=dict(
                showframe=False,
                showcoastlines=False,
                showland=True,
                landcolor='#f8fafc',
                bgcolor='rgba(0,0,0,0)'
            )
        )
        st.plotly_chart(fig_map, use_container_width=True)

with tab_trends:
    # =============================================================================
    # VISUALIZATION 2 — Score Trends Over Time
    # =============================================================================
    with st.container(border=True):
        st.markdown('<div class="chart-card-title">1. Score Trends Over Time</div>', unsafe_allow_html=True)
        if custom_countries:
            trend_df = df[df['country'].isin(custom_countries)].copy()

            fig2, ax2 = plt.subplots(figsize=(12, 4.6))
            sns.lineplot(
                data=trend_df, x='year', y='score',
                hue='country', marker='o', linewidth=2, ax=ax2
            )
            ax2.set_title('Score Trends', fontweight='bold')
            ax2.set_xlabel('Year')
            ax2.set_ylabel('Score')
            ax2.set_xticks(years)
            ax2.set_xticklabels(years)

            ax2.legend(title='Country', bbox_to_anchor=(1.05, 1), loc='upper left')
            plt.tight_layout()
            st.pyplot(fig2)
            plt.close(fig2)
        else:
            st.info("Select at least one country in Control Center to show the trend chart.")

    # =============================================================================
    # VISUALIZATION 6 — Score Distribution Box Plot (numpy annotations)
    # =============================================================================
    with st.container(border=True):
        st.markdown('<div class="chart-card-title">2. Score Distribution Per Year</div>', unsafe_allow_html=True)
        fig6, ax6 = plt.subplots(figsize=(14, 4.6))

        sns.boxplot(
            data=df, x='year', y='score',
            palette='Blues',
            linewidth=1.2,
            flierprops=dict(marker='o', markersize=3, alpha=0.4),
            ax=ax6
        )

        for i, yr in enumerate(years):
            yr_scores  = df[df['year'] == yr]['score'].values
            median_val = np.median(yr_scores)
            ax6.text(
                i, median_val + 1.8,
                f'{median_val:.0f}',
                ha='center', va='bottom',
                fontsize=8, color='#1F4E79', fontweight='bold'
            )

        ax6.set_title('Score Distribution by Year', fontweight='bold')
        ax6.set_xlabel('Year')
        ax6.set_ylabel('Score')
        ax6.set_ylim(0, 105)
        plt.tight_layout()
        st.pyplot(fig6)
        plt.close(fig6)

        st.markdown(
            f'<div class="stat-box">📊 <b>numpy stats for {selected_year}:</b> '
            f'Mean = {yr_avg:.1f} &nbsp;|&nbsp; '
            f'Median = {yr_median:.1f} &nbsp;|&nbsp; '
            f'Std Dev = {yr_std:.1f} &nbsp;|&nbsp; '
            f'25th pct = {np.percentile(scores_arr, 25):.1f} &nbsp;|&nbsp; '
            f'75th pct = {np.percentile(scores_arr, 75):.1f}'
            f'</div>',
            unsafe_allow_html=True
        )

with tab_signals:
    with st.container(border=True):
        st.markdown('<div class="chart-card-title">1. Global Pulse</div>', unsafe_allow_html=True)
        fig_pulse, ax_pulse = plt.subplots(figsize=(12, 4.2))
        ax_pulse.fill_between(
            yearly_stats['year'],
            yearly_stats['q25'],
            yearly_stats['q75'],
            color='#dbeafe',
            alpha=0.9,
            label='Middle 50% of countries'
        )
        ax_pulse.plot(
            yearly_stats['year'],
            yearly_stats['mean'],
            color='#12355b',
            linewidth=2.6,
            marker='o',
            label='Yearly average'
        )
        ax_pulse.plot(
            yearly_stats['year'],
            yearly_stats['median'],
            color='#b42318',
            linewidth=1.9,
            marker='s',
            linestyle='--',
            label='Yearly median'
        )
        ax_pulse.set_title('Global Press Freedom Pulse', fontweight='bold')
        ax_pulse.set_xlabel('Year')
        ax_pulse.set_ylabel('Score')
        ax_pulse.set_xticks(years)
        ax_pulse.set_ylim(0, 100)
        ax_pulse.legend(frameon=False)
        plt.tight_layout()
        st.pyplot(fig_pulse)
        plt.close(fig_pulse)

        st.markdown(
            f'<div class="stat-box">📌 <b>Pulse read:</b> the average score moved from {yearly_stats.iloc[0]["mean"]:.1f} in {int(yearly_stats.iloc[0]["year"])} '
            f'to {yearly_stats.iloc[-1]["mean"]:.1f} in {int(yearly_stats.iloc[-1]["year"])}. '
            f'The narrowest middle spread was {yearly_stats.loc[yearly_stats["q75"].sub(yearly_stats["q25"]).idxmin(), "year"]}.'
            f'</div>',
            unsafe_allow_html=True
        )

    if region_col:
        region_year = (
            df.groupby([region_col, 'year'])['score']
            .mean()
            .reset_index()
        )
        region_pivot = region_year.pivot(index=region_col, columns='year', values='score')
        with st.container(border=True):
            st.markdown('<div class="chart-card-title">2. Regional Heatmap</div>', unsafe_allow_html=True)
            fig_heat, ax_heat = plt.subplots(figsize=(13, 4.6))
            sns.heatmap(
                region_pivot,
                cmap='RdYlGn',
                annot=True,
                fmt='.1f',
                linewidths=0.5,
                linecolor='white',
                cbar_kws={'label': 'Average score'},
                ax=ax_heat
            )
            ax_heat.set_title('Regional Score Heatmap', fontweight='bold')
            ax_heat.set_xlabel('Year')
            ax_heat.set_ylabel('Region')
            plt.tight_layout()
            st.pyplot(fig_heat)
            plt.close(fig_heat)

    with st.container(border=True):
        st.markdown('<div class="chart-card-title">3. Score vs Rank Relationship</div>', unsafe_allow_html=True)
        fig_sr, ax_sr = plt.subplots(figsize=(11, 4.6))
        sns.regplot(
            data=latest_df,
            x='score',
            y='rank',
            scatter_kws={'alpha': 0.7, 's': 45, 'color': '#12355b'},
            line_kws={'color': '#b42318', 'lw': 2.2},
            ax=ax_sr
        )
        ax_sr.set_title(f'Latest Year: Score vs Rank ({latest_year})', fontweight='bold')
        ax_sr.set_xlabel('Score')
        ax_sr.set_ylabel('Rank (lower is better)')
        ax_sr.invert_yaxis()
        ax_sr.text(
            0.02, 0.95,
            f'r = {latest_rank_corr:.3f}',
            transform=ax_sr.transAxes,
            ha='left',
            va='top',
            fontsize=11,
            fontweight='bold',
            color='#12355b',
            bbox=dict(boxstyle='round,pad=0.35', fc='white', ec='#dbe6f2')
        )
        plt.tight_layout()
        st.pyplot(fig_sr)
        plt.close(fig_sr)

    top_vol = country_volatility.head(10).sort_values()
    with st.container(border=True):
        st.markdown('<div class="chart-card-title">4. Most Volatile Countries</div>', unsafe_allow_html=True)
        fig_vol, ax_vol = plt.subplots(figsize=(11, 4.6))
        sns.barplot(
            x=top_vol.values,
            y=top_vol.index,
            palette='flare',
            ax=ax_vol
        )
        ax_vol.set_title('Countries with the Biggest Score Swings', fontweight='bold')
        ax_vol.set_xlabel('Standard deviation of score across years')
        ax_vol.set_ylabel('Country')
        plt.tight_layout()
        st.pyplot(fig_vol)
        plt.close(fig_vol)

with tab_drilldown:
    # =============================================================================
    # VISUALIZATION 5 — Most Improved vs Most Declined
    # =============================================================================
    with st.container(border=True):
        st.markdown('<div class="chart-card-title">1. Most Improved vs Most Declined</div>', unsafe_allow_html=True)

        s_df = (df[df['year'] == yr_start][['country', 'score']]
                .rename(columns={'score': 'score_start'}))
        e_df = (df[df['year'] == yr_end  ][['country', 'score']]
                .rename(columns={'score': 'score_end'}))
        chg  = s_df.merge(e_df, on='country')
        chg['change'] = (chg['score_end'] - chg['score_start']).round(2)

        fig5, axes5 = plt.subplots(1, 2, figsize=(14, 4.6))

        sns.barplot(
            data=chg.nlargest(top_n, 'change'), x='change', y='country',
            hue='country', palette='Greens', legend=False, ax=axes5[0]
        )
        axes5[0].set_title(f'Most Improved ({yr_start}–{yr_end})', fontweight='bold')
        axes5[0].set_xlabel('Score Change')
        axes5[0].axvline(0, color='gray', linestyle='--', linewidth=0.8)

        sns.barplot(
            data=chg.nsmallest(top_n, 'change'), x='change', y='country',
            hue='country', palette='Reds_r', legend=False, ax=axes5[1]
        )
        axes5[1].set_title(f'Most Declined ({yr_start}–{yr_end})', fontweight='bold')
        axes5[1].set_xlabel('Score Change')
        axes5[1].axvline(0, color='gray', linestyle='--', linewidth=0.8)

        plt.tight_layout()
        st.pyplot(fig5)
        plt.close(fig5)

    # =============================================================================
    # COUNTRY SPOTLIGHT
    # =============================================================================
    spotlight_all = df[df['country'] == spotlight_country].sort_values('year')

    if not spotlight_all.empty:
        st.markdown(
            f'<div class="chart-card-title">2. {spotlight_country} Spotlight</div>',
            unsafe_allow_html=True
        )

        col_a, col_b = st.columns([2, 1])

        with col_a:
            fig_ph, ax_ph = plt.subplots(figsize=(10, 3.5))

            ax_ph.plot(
                spotlight_all['year'], spotlight_all['score'],
                marker='o', color='#1F4E79', linewidth=2.5,
                label=spotlight_country
            )

            ax_ph.axhline(
                overall_avg, color='crimson', linestyle='--',
                linewidth=1.2, label=f'Overall global avg ({overall_avg:.1f})'
            )

            ax_ph.fill_between(
                spotlight_all['year'], spotlight_all['score'], overall_avg,
                alpha=0.1, color='#1F4E79'
            )

            ax_ph.set_title(
                f'{spotlight_country} — Press Freedom Score Over Time',
                fontweight='bold'
            )
            ax_ph.set_xlabel('Year')
            ax_ph.set_ylabel('Score')
            ax_ph.set_xticks(years)
            ax_ph.set_xticklabels(years)
            ax_ph.legend()
            plt.tight_layout()
            st.pyplot(fig_ph)
            plt.close(fig_ph)

        with col_b:
            spotlight_latest = spotlight_all[spotlight_all['year'] == latest_year]
            if not spotlight_latest.empty:
                ps    = float(spotlight_latest['score'].values[0])
                pr    = int(spotlight_latest['rank'].values[0])
                total = latest_df['country'].nunique()
                ph_pct = float(np.mean(latest_df['score'].values < ps) * 100)

                st.metric("Score", f"{ps:.1f} / 100")
                st.metric("Global Rank", f"#{pr} of {total}")
                st.metric("Scores better than", f"{ph_pct:.0f}% of countries")

            spotlight_start_vals = spotlight_all[spotlight_all['year'] == yr_start]['score'].values
            spotlight_end_vals   = spotlight_all[spotlight_all['year'] == yr_end  ]['score'].values
            if len(spotlight_start_vals) > 0 and len(spotlight_end_vals) > 0:
                delta     = float(spotlight_end_vals[0]) - float(spotlight_start_vals[0])
                direction = "improved ↑" if delta > 0 else "declined ↓"
                st.metric(
                    f"Change ({yr_start}–{yr_end})",
                    f"{abs(delta):.1f} pts {direction}",
                    delta=f"{delta:+.1f}"
                )

    # =============================================================================
    # RAW DATA TABLE
    # =============================================================================
    with st.expander("📋 View Raw Data"):
        cols_show = ['country', 'year', 'score', 'rank']
        if region_col:
            cols_show.append(region_col)

        st.dataframe(
            df[[c for c in cols_show if c in df.columns]]
            .sort_values(['year', 'rank'], ascending=[False, True])
            .reset_index(drop=True),
            height=350
        )

        st.download_button(
            "⬇ Download as CSV",
            data=df.to_csv(index=False),
            file_name="press_freedom_data.csv",
            mime="text/csv"
        )

st.divider()
st.caption(
    "Data: Reporters Without Borders (RSF) · "
    "Dataset via Kaggle · Built with Python & Streamlit"
)
