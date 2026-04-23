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
        overflow: hidden;
    }
    header, footer {
        visibility: hidden;
        height: 0;
    }
    .block-container {
        padding-top: 0.8rem;
        padding-bottom: 0.45rem;
        max-width: 100%;
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
        font-size: 2.1rem; font-weight: 800;
        color: var(--pf-deep-blue); margin-bottom: 0.02rem;
        letter-spacing: 0.2px;
        font-family: Georgia, 'Times New Roman', serif;
    }
    .subtitle {
        font-size: 0.98rem; color: #334155; margin-bottom: 0.9rem;
        font-family: 'Georgia', 'Times New Roman', serif;
    }
    .control-panel {
        background: linear-gradient(180deg, #ffffff 0%, #ffffff 65%, #fbfdff 100%);
        border: 1px solid #dbe6f2;
        border-top: 4px solid var(--pf-deep-blue);
        border-radius: 14px;
        padding: 0.75rem 1rem 0.15rem 1rem;
        margin-bottom: 0.75rem;
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
        padding-bottom: 0.25rem; margin: 0.4rem 0 0.75rem 0;
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
        padding: 0.55rem 0.75rem 0.12rem 0.75rem;
        margin-bottom: 0.55rem;
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

ctrl1, ctrl2 = st.columns([1, 1])
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

st.markdown('<div class="section-header">Dashboard</div>', unsafe_allow_html=True)

top10 = selected_df.nlargest(top_n, 'score')
bottom10 = selected_df.nsmallest(top_n, 'score')
trend_df = df[df['country'].isin(custom_countries)].copy() if custom_countries else pd.DataFrame(columns=df.columns)

grid_left, grid_right = st.columns([1.15, 0.85], gap='medium')

with grid_left:
    with st.container(border=True):
        st.markdown('<div class="chart-card-title">Top and Bottom Countries</div>', unsafe_allow_html=True)
        fig1, axes1 = plt.subplots(1, 2, figsize=(11.5, 3.1))
        sns.barplot(data=top10, x='score', y='country', palette='Greens_r', legend=False, ax=axes1[0])
        axes1[0].set_title(f'Top {top_n}', fontweight='bold')
        axes1[0].set_xlabel('')
        axes1[0].set_ylabel('')
        axes1[0].set_xlim(0, 100)
        sns.barplot(data=bottom10, x='score', y='country', palette='Reds_r', legend=False, ax=axes1[1])
        axes1[1].set_title(f'Bottom {top_n}', fontweight='bold')
        axes1[1].set_xlabel('')
        axes1[1].set_ylabel('')
        axes1[1].set_xlim(0, 100)
        plt.tight_layout()
        st.pyplot(fig1)
        plt.close(fig1)

    with st.container(border=True):
        st.markdown('<div class="chart-card-title">Trend Lines</div>', unsafe_allow_html=True)
        if not trend_df.empty:
            fig2, ax2 = plt.subplots(figsize=(11.5, 3.2))
            sns.lineplot(data=trend_df, x='year', y='score', hue='country', marker='o', linewidth=2, ax=ax2)
            ax2.set_xlabel('Year')
            ax2.set_ylabel('Score')
            ax2.set_xticks(years)
            ax2.set_xticklabels(years)
            ax2.legend(title='', bbox_to_anchor=(1.02, 1), loc='upper left', frameon=False)
            plt.tight_layout()
            st.pyplot(fig2)
            plt.close(fig2)
        else:
            st.info("Select countries to plot the trend line.")

with grid_right:
    with st.container(border=True):
        st.markdown('<div class="chart-card-title">World Map</div>', unsafe_allow_html=True)
        if iso_col:
            fig_map = px.choropleth(
                selected_df,
                locations=iso_col,
                color='score',
                hover_name='country',
                color_continuous_scale='RdYlGn',
                range_color=(0, 100),
                labels={'score': 'Score'}
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
                labels={'score': 'Score'}
            )
        fig_map.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            coloraxis_colorbar=dict(title="Score"),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            height=280,
            geo=dict(showframe=False, showcoastlines=False, showland=True, landcolor='#f8fafc', bgcolor='rgba(0,0,0,0)')
        )
        st.plotly_chart(fig_map, use_container_width=True)

    with st.container(border=True):
        st.markdown('<div class="chart-card-title">Regional Scores</div>', unsafe_allow_html=True)
        if region_col:
            zone_avg = selected_df.groupby(region_col)['score'].mean().sort_values(ascending=False).reset_index()
            fig3, ax3 = plt.subplots(figsize=(11.5, 3.2))
            sns.barplot(data=zone_avg, x='score', y=region_col, palette='coolwarm', legend=False, ax=ax3)
            ax3.set_xlabel('Average score')
            ax3.set_ylabel('')
            ax3.set_xlim(0, 100)
            plt.tight_layout()
            st.pyplot(fig3)
            plt.close(fig3)
        else:
            st.info("Regional grouping is unavailable in this file.")

