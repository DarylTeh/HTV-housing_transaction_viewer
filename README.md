# Singapore Housing Transaction Viewer

This app is a beginner-friendly Streamlit dashboard for Singapore housing buyers. It pulls open government data for:
- HDB resale flats
- Private property transactions (condo, executive condo, landed)

The app is built to:
- refresh data daily at 9am Singapore time
- store CSV snapshots in the repository
- display easy-to-use filters
- compare price trends and percent gain over time
- include an affordability calculator with MSR/TDSR guidance
- offer simple explanations for HDB/condo/PR/foreigner rules
- use Google Maps Distance Matrix if you provide a key, and fallback to OpenStreetMap if not

## Files
- `app.py` — Streamlit app
- `scripts/update_data.py` — data ingestion and CSV exporter
- `.github/workflows/daily_update.yml` — GitHub Actions refresh schedule
- `requirements.txt` — Python dependencies
- `policy_notes.md` — beginner-friendly policy explanations

## Setup
1. Install dependencies:
   ```bash
   python -m pip install -r requirements.txt
   ```
2. Run the app locally:
   ```bash
   streamlit run app.py
   ```
3. If you want to use Google Maps features, set the env var:
   - Windows PowerShell:
     ```powershell
     $env:GOOGLE_MAPS_API_KEY = "YOUR_API_KEY"
     ```
   - macOS / Linux:
     ```bash
     export GOOGLE_MAPS_API_KEY="YOUR_API_KEY"
     ```

## Data refresh
The GitHub Action is scheduled to run daily at 1:00 UTC (9:00 SGT).
It will:
- fetch the latest datasets from Singapore open data
- save the latest CSVs in `data/latest/`
- archive daily snapshots in `data/archive/`
- commit updates back to the repository

## Notes for hosting
1. Initialize git:
   ```bash
   git init
   git add .
   git commit -m "Initial Streamlit housing viewer"
   ```
2. Add a GitHub remote and push.
3. Connect the repository to Streamlit Cloud.
4. In Streamlit Cloud, set the required secrets:
   - `GOOGLE_MAPS_API_KEY` (optional, recommended)

## What is local CSV vs raw data?
- **Local CSV**: the app reads and stores transformed data in comma-separated files, which are easy to view, inspect, and commit to GitHub.
- **Raw data**: the source JSON or API response from the government open data platform.

The app converts raw data into clean CSV for reliability and faster dashboard loading.
