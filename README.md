# Press Freedom Index Dashboard

Single-file Python dashboard for exploring the World Press Freedom Index dataset.

## Stack

- Python
- Flask
- Pandas
- Chart.js
- Plotly

## Files

- `dash_app.py`: main app
- `press-freedom_index.xlsx`: source dataset
- `requirements.txt`: Python dependencies
- `render.yaml`: Render deployment config

## Features

- Sticky masthead navigation
- Fixed filter sidebar
- Year, zone, spotlight country, search, score-range, and freedom-scale filters
- Top and bottom country rankings
- Multi-country trend chart
- Zone averages
- World choropleth map
- Distribution and rank-vs-score insight charts
- Improvement vs decline comparison
- Spotlight panel for a selected country

## Run Locally

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the app:

```bash
python dash_app.py
```

4. Open:

```text
http://127.0.0.1:8050
```

## Deployment

The app is configured for Render with:

```text
gunicorn dash_app:server
```

## Data Notes

- The app loads the Excel workbook from the project root.
- Column names are standardized in Python before analysis.
- Scores are coerced to numeric values.
- Year, rank, score, and country are required for rows to be used.

## Current App Behavior

- The sidebar controls the full dashboard state.
- Charts and summary cards are intended to move with the active filters.
- Clicking bars and map/scatter points updates the spotlight country.

## Troubleshooting

- If the app does not start, confirm the dataset file is present in the project root.
- If dependencies are missing, reinstall with `pip install -r requirements.txt`.
- If deployment fails, verify the start command is `gunicorn dash_app:server`.
