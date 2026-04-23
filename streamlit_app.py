"""
World Press Freedom Index — Interactive Dashboard
==================================================
Tool   : Streamlit (Python web app framework)
Run    : streamlit run streamlit_app.py
Deploy : render.com using render.yaml

Why Streamlit?
- Purely Python — no HTML, CSS, or JavaScript knowledge required
- File upload, filters, and interactive charts built-in
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
    .main-title {
        font-size: 2.2rem; font-weight: 700;
        color: #1F4E79; margin-bottom: 0.2rem;
    }
    .subtitle {
        font-size: 1rem; color: #555; margin-bottom: 1.5rem;
    }
    .section-header {
        font-size: 1.3rem; font-weight: 600;
        color: #1F4E79; border-bottom: 2px solid #2E75B6;
        padding-bottom: 0.3rem; margin: 1.5rem 0 1rem 0;
    }
    .info-box {
        background: #EBF3FB; border-left: 4px solid #1F4E79;
        padding: 0.8rem 1rem; border-radius: 0 8px 8px 0;
        font-size: 0.9rem; color: #1F4E79; margin: 0.5rem 0 1rem 0;
    }
    .stat-box {
        background: #F0F6FF; border-radius: 8px;
        padding: 0.6rem 1rem; border-left: 3px solid #2E75B6;
        font-size: 0.85rem; color: #1F4E79;
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
# SIDEBAR
# =============================================================================
with st.sidebar:
    st.markdown("## 📰 Press Freedom Index")
    st.markdown("Data by **Reporters Without Borders (RSF)**")
    st.divider()

    if DATA_FILE is None:
        st.error("No dataset file found in the app folder.")
    else:
        st.success(f"Loaded local dataset: {DATA_FILE.name}")

    st.markdown("""
**How the dashboard works:**
1. The dataset loads automatically from the app folder
2. Use the filters below to change the year, rankings, and spotlight country
3. Hover over charts and the map to explore details
    """)

    st.divider()

    # About the dashboard — required by rubric (explain features and user interaction)
    with st.expander("ℹ️ About This Dashboard"):
        st.markdown("""
**Tool:** Streamlit (Python)

**Why Streamlit?**
Pure Python — no web development knowledge needed. Converts a data script into an interactive web app.

**Features:**
- Auto-loads the local dataset from the app folder
- Year selector updates rankings and map in real time
- Country multiselect filters the trend chart
- Interactive Plotly world map with hover tooltips
- Philippines spotlight section
- Download cleaned data as CSV
- Ready for deployment on Render with `openpyxl` included

**How to interact:**
1. Use the **Year** filter to change which year appears in Charts 1, 3, and 4
2. Add or remove countries in the **Countries** multiselect to control Chart 2
3. Change the ranking size and comparison years in the sidebar
4. Hover over the world map to see each country's score
5. Expand **View Raw Data** at the bottom to browse and download

**Deployment note:**
This app is set up to deploy on Render. Keep `requirements.txt` and `render.yaml` in sync if you change dependencies or the start command.
        """)

    st.divider()
    st.caption("Built with Python · numpy · pandas · seaborn · Plotly · Streamlit")
    st.caption("BS Computer Science — Year 3")
    st.caption("Data: RSF via Kaggle")


# =============================================================================
# PAGE HEADER
# =============================================================================
st.markdown(
    '<div class="main-title">🌍 World Press Freedom Index Analysis</div>',
    unsafe_allow_html=True
)
st.markdown(
    '<div class="subtitle">Exploratory Data Analysis &nbsp;|&nbsp; '
    '2014–2023 &nbsp;|&nbsp; Reporters Without Borders (RSF)</div>',
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


# =============================================================================
# SIDEBAR FILTERS (rendered after file loads)
# =============================================================================
with st.sidebar:
    st.divider()
    st.markdown("### Filters")

    selected_year = st.selectbox(
        "Year for Rankings & Map",
        options=list(reversed(years)),
        index=0
    )

    default_countries = [
        c for c in
        ['Norway', 'Finland', 'Philippines', 'China', 'Russia', 'United States']
        if c in df['country'].values
    ]

    custom_countries = st.multiselect(
        "Countries to track (Trend chart)",
        options=sorted(df['country'].unique()),
        default=default_countries
    )

    top_n = st.slider(
        "Countries shown in ranking charts",
        min_value=5,
        max_value=20,
        value=10
    )

    compare_years = st.slider(
        "Compare years for change chart",
        min_value=min(years),
        max_value=max(years),
        value=(min(years), max(years))
    )

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


# =============================================================================
# VISUALIZATION 1 — Top & Bottom 10 Countries
# WHAT : Horizontal bars of the 10 most and least free countries
# WHY  : Horizontal bars fit long country names; side-by-side shows contrast
# DATA : Latest selected year rankings
# INSIGHT: Reveals the global extremes in press freedom
# =============================================================================
st.markdown(
    f'<div class="section-header">1. Top &amp; Bottom {top_n} Countries</div>',
    unsafe_allow_html=True
)

top10    = selected_df.nlargest(top_n, 'score')
bottom10 = selected_df.nsmallest(top_n, 'score')

fig1, axes1 = plt.subplots(1, 2, figsize=(14, 5))

sns.barplot(
    data=top10, x='score', y='country',
    hue='country', palette='Greens_r', legend=False, ax=axes1[0]
)
axes1[0].set_title(f'Most Free ({selected_year})', fontweight='bold')
axes1[0].set_xlabel('Score (0–100)')
axes1[0].set_ylabel('')
axes1[0].set_xlim(0, 100)

sns.barplot(
    data=bottom10, x='score', y='country',
    hue='country', palette='Reds_r', legend=False, ax=axes1[1]
)
axes1[1].set_title(f'Least Free ({selected_year})', fontweight='bold')
axes1[1].set_xlabel('Score (0–100)')
axes1[1].set_ylabel('')
axes1[1].set_xlim(0, 100)

plt.tight_layout()
st.pyplot(fig1)
plt.close(fig1)


# =============================================================================
# VISUALIZATION 2 — Score Trends Over Time
# WHAT : Multi-line chart tracking selected countries from 2014 to 2023
# WHY  : Line charts are ideal for time-series — clearly show trends and turning points
# DATA : User-selected countries from the sidebar multiselect
# INSIGHT: Shows whether individual countries are improving or deteriorating
# =============================================================================
st.markdown(
    '<div class="section-header">2. Score Trends Over Time</div>',
    unsafe_allow_html=True
)

if custom_countries:
    trend_df = df[df['country'].isin(custom_countries)].copy()

    fig2, ax2 = plt.subplots(figsize=(12, 5))
    sns.lineplot(
        data=trend_df, x='year', y='score',
        hue='country', marker='o', linewidth=2, ax=ax2
    )
    ax2.set_title('Press Freedom Score Trends', fontweight='bold')
    ax2.set_xlabel('Year')
    ax2.set_ylabel('Score (higher = more free)')

    # Set tick positions AND labels together to avoid FixedLocator warning
    ax2.set_xticks(years)
    ax2.set_xticklabels(years)

    ax2.legend(title='Country', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    st.pyplot(fig2)
    plt.close(fig2)
else:
    st.info("Select at least one country in the sidebar to show the trend chart.")


# =============================================================================
# VISUALIZATION 3 — Average Score by Zone
# WHAT : Horizontal bars of average press freedom per geographic zone
# WHY  : Bar chart aggregates many countries into one regional view
# DATA : Zone column from the dataset (e.g. Europe, MENA, Asia-Pacific)
# INSIGHT: Identifies which world regions systematically protect or suppress press freedom
# =============================================================================
if region_col:
    st.markdown(
        '<div class="section-header">3. Average Score by Zone</div>',
        unsafe_allow_html=True
    )

    zone_avg = (
        selected_df.groupby(region_col)['score']
        .mean()
        .sort_values(ascending=False)
        .reset_index()
    )

    fig3, ax3 = plt.subplots(figsize=(10, 4))
    sns.barplot(
        data=zone_avg, x='score', y=region_col,
        hue=region_col, palette='coolwarm', legend=False, ax=ax3
    )
    ax3.set_title(
        f'Average Press Freedom Score by Zone ({selected_year})',
        fontweight='bold'
    )
    ax3.set_xlabel('Average Score')
    ax3.set_ylabel('')
    ax3.set_xlim(0, 100)
    plt.tight_layout()
    st.pyplot(fig3)
    plt.close(fig3)


# =============================================================================
# VISUALIZATION 4 — Interactive World Map
# WHAT : Color-coded world map where each country shows its press freedom score
# WHY  : Geographic map makes spatial patterns visible at a glance without data literacy
# DATA : Latest selected year scores via ISO country codes
# INSIGHT: Confirms that press freedom is concentrated in Europe and scarce in MENA/Asia
# =============================================================================
st.markdown(
    '<div class="section-header">4. Interactive World Map</div>',
    unsafe_allow_html=True
)

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
    coloraxis_colorbar=dict(title="Score")
)
st.plotly_chart(fig_map, use_container_width=True)


# =============================================================================
# VISUALIZATION 5 — Most Improved vs Most Declined
# WHAT : Side-by-side bars of the biggest score changes from start to end year
# WHY  : Comparing two bars side by side makes magnitude of change easy to read
# DATA : Score difference computed via inner merge on country between two years
# INSIGHT: Reveals structural shifts — some countries have made dramatic changes
# =============================================================================
st.markdown(
    '<div class="section-header">5. Most Improved vs Most Declined</div>',
    unsafe_allow_html=True
)

yr_start, yr_end = compare_years

s_df = (df[df['year'] == yr_start][['country', 'score']]
        .rename(columns={'score': 'score_start'}))
e_df = (df[df['year'] == yr_end  ][['country', 'score']]
        .rename(columns={'score': 'score_end'}))
chg  = s_df.merge(e_df, on='country')
chg['change'] = (chg['score_end'] - chg['score_start']).round(2)

fig5, axes5 = plt.subplots(1, 2, figsize=(14, 5))

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
# VISUALIZATION 6 — Score Distribution Box Plot (numpy annotations)
# WHAT : Box plot showing the spread of scores across all countries per year
# WHY  : Box plots display median, interquartile range, and outliers — richer than a mean
#        numpy computes the median values annotated on each box
# DATA : All countries' scores for every year
# INSIGHT: Reveals whether global inequality in press freedom is growing or shrinking
# =============================================================================
st.markdown(
    '<div class="section-header">6. Score Distribution Per Year (Box Plot)</div>',
    unsafe_allow_html=True
)

fig6, ax6 = plt.subplots(figsize=(14, 5))

sns.boxplot(
    data=df, x='year', y='score',
    palette='Blues',
    linewidth=1.2,
    flierprops=dict(marker='o', markersize=3, alpha=0.4),
    ax=ax6
)

# Use numpy to compute and annotate median on each box
for i, yr in enumerate(years):
    yr_scores  = df[df['year'] == yr]['score'].values
    median_val = np.median(yr_scores)   # numpy median
    ax6.text(
        i, median_val + 1.8,
        f'{median_val:.0f}',
        ha='center', va='bottom',
        fontsize=8, color='#1F4E79', fontweight='bold'
    )

ax6.set_title(
    'Press Freedom Score Distribution by Year',
    fontweight='bold'
)
ax6.set_xlabel('Year')
ax6.set_ylabel('Press Freedom Score')
ax6.set_ylim(0, 105)
plt.tight_layout()
st.pyplot(fig6)
plt.close(fig6)

# Show numpy-computed stats below the chart
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


# =============================================================================
# COUNTRY SPOTLIGHT
# sort_values('year') is required before fill_between — needs ordered x-values
# =============================================================================
spotlight_all = df[df['country'] == spotlight_country].sort_values('year')

if not spotlight_all.empty:
    st.markdown(
        f'<div class="section-header">🌐 {spotlight_country} Spotlight</div>',
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

        # overall_avg used (not selected year avg) because this chart spans all years
        ax_ph.axhline(
            overall_avg, color='crimson', linestyle='--',
            linewidth=1.2, label=f'Overall global avg ({overall_avg:.1f})'
        )

        # fill_between works correctly because ph_all is sorted by year
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

            # numpy percentile: what % of countries does the spotlight score better than?
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
