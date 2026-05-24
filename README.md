# Singapore Housing Transaction Viewer

This app is for Singapore housing buyers. Pulls open government/URA/HDB data for:
- HDB resale flats
- Private property transactions (condo, executive condo, landed)

The app can:
- refresh data daily at 9am Singapore time
- store CSV snapshots in the repository
- display easy-to-use filters
- compare price trends and percent gain over time
- include an affordability calculator with MSR/TDSR guidance
- offer simple explanations for HDB/condo/PR/foreigner rules
- use Google Maps Distance Matrix if you provide a key, and fallback to OpenStreetMap if not

I only maintain this myself so don't expect proper documentation lol.

## Files
- `app.py` - Streamlit app
- `scripts/update_data.py` - data ingestion and CSV exporter
- `.github/workflows/daily_update.yml` - GitHub Actions refresh schedule
- `requirements.txt` - Python dependencies
- `policy_notes.md` - beginner-friendly policy explanations

If you can't figure out what these files do, maybe coding isn't for you lmao.

## Setup
1. Install dependencies:
   ```bash
   python -m pip install -r requirements.txt
   ```
2. Run the app locally:
   ```bash
   streamlit run app.py
   ```
3. If you want to use Google Maps features locally, set the env var:
   - Windows PowerShell:
     ```powershell
     $env:GOOGLE_MAPS_API_KEY = "YOUR_API_KEY"
     ```
   - macOS / Linux:
     ```bash
     export GOOGLE_MAPS_API_KEY="YOUR_API_KEY"
     ```

Note: this only sets the API key for the current local shell. It does not apply to Streamlit Cloud. Don't ask me why, I also don't know. If you can't even set environment variables, why are you even trying to use this lmao. 环境变量都不会设，真是笑死人 lol.

## Data refresh
The GitHub Action is scheduled to run daily at 1:00 UTC (9:00 SGT).
It will:
- fetch the latest datasets from Singapore open data
- save the latest CSVs in `data/latest/`
- archive daily snapshots in `data/archive/`
- commit updates back to the repository

If it fails, I'll fix when I feel like it. This is automated, you don't need to do anything. Unless you're too incompetent to set up GitHub Actions, then that's your problem lol. 自动化都不会用，真是可悲 lmao.

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

If you don't know how to do this, then go figure out yourself. I'm not here to teach you git basics. This is basic stuff, if you can't handle it you shouldn't be coding lmao. Git都不会用，还想当程序员 lol.

### Additional runtime environment variables
- `HTV_DATA_SOURCE` - optional. Set to `local_xlsx` or `live_api` if using a live data source instead of local CSV/XLSX.
- `HTV_PREFER_CSV` - optional. Set to `1` to prefer CSV cache when available, or `auto` to let the app decide.

Honestly I don't even remember what these do. Just leave it as default. If you mess with these and break something, don't come crying to me lol. 乱改设置坏了别怪我 lmao.

## What is local CSV vs raw data?
- **Local CSV**: the app reads and stores transformed data in comma-separated files, which are easy to view, inspect, and commit to GitHub.
- **Raw data**: the source JSON or API response from the government open data platform.

The app converts raw data into clean CSV for reliability and faster dashboard loading. Don't ask me to explain the difference, just use the CSV. This is basic data engineering, if you don't understand it you're in the wrong field lol. 数据处理都不懂，还想搞开发 lmao.
