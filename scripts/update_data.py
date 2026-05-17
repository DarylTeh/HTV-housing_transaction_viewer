"""Refresh data/latest CSV snapshots from configured sources (xlsx now, live API later)."""

import csv
import datetime
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources import (  # noqa: E402
    DATA_SOURCE_MODE,
    LATEST_DIR,
    load_dataset,
)

ARCHIVE_DIR = ROOT / "data" / "archive"


def ensure_directories():
    LATEST_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)


def save_csv(name: str, df: pd.DataFrame):
    if df is None or df.empty:
        print(f"Warning: No data to save for {name}")
        return

    today = datetime.date.today().isoformat()
    latest_path = LATEST_DIR / f"{name}.csv"
    archive_path = ARCHIVE_DIR / f"{name}_{today}.csv"

    df.to_csv(latest_path, index=False, quoting=csv.QUOTE_NONNUMERIC)
    df.to_csv(archive_path, index=False, quoting=csv.QUOTE_NONNUMERIC)
    print(f"SAVED: {latest_path} ({len(df)} rows)")
    print(f"ARCHIVED: {archive_path}")


def run():
    ensure_directories()
    print(f"Data source mode: {DATA_SOURCE_MODE}")

    for name in ("hdb_resale", "private_property"):
        print(f"\nFetching {name}...")
        df = load_dataset(name)
        if df.empty:
            print(f"FAILED: Could not load {name}")
            continue
        save_csv(name, df)

    print("\nBuilding processed slices for fast app load…")
    import subprocess

    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_processed_data.py"), "--fast"],
        check=False,
    )

    print("\nDATA_REFRESH_COMPLETE: All sources processed")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print(f"FATAL_ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
