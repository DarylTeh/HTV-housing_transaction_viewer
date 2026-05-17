import csv
import datetime
import os
import requests
import sys
from pathlib import Path

import pandas as pd

BASE_URL = "https://data.gov.sg/api/action"
DATA_SOURCES = [
    {
        "name": "hdb_resale",
        "query": "HDB resale flat prices",
        "resource_name": "HDB Resale Flat Prices",
    },
    {
        "name": "private_property",
        "query": "private residential property transactions",
        "resource_name": "Private Residential Property Transactions",
    },
]

ROOT = Path(__file__).resolve().parents[1]
LATEST_DIR = ROOT / "data" / "latest"
ARCHIVE_DIR = ROOT / "data" / "archive"


def ensure_directories():
    LATEST_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)


def request_json(url, params=None, timeout=30):
    response = requests.get(url, params=params, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    if not payload.get("success"):
        raise RuntimeError(f"API call failed: {payload}")
    return payload


def find_dataset(query):
    payload = request_json(f"{BASE_URL}/package_search", params={"q": query, "rows": 5})
    results = payload.get("result", {}).get("results", [])
    if not results:
        raise RuntimeError(f"No dataset found for query '{query}'")
    return results[0]


def find_resource(dataset, resource_name):
    resources = dataset.get("resources", [])
    for resource in resources:
        if resource_name.lower() in resource.get("name", "").lower():
            return resource
    return resources[0] if resources else None


def fetch_all_rows(resource_id, limit=1000):
    offset = 0
    rows = []
    while True:
        params = {"resource_id": resource_id, "limit": limit, "offset": offset}
        payload = request_json(f"{BASE_URL}/datastore_search", params=params)
        batch = payload.get("result", {}).get("records", [])
        if not batch:
            break
        rows.extend(batch)
        offset += len(batch)
        if len(batch) < limit:
            break
    return rows


def save_csv(name, rows):
    if not rows:
        raise RuntimeError(f"No rows returned for {name}")
    today = datetime.date.today().isoformat()
    latest_path = LATEST_DIR / f"{name}.csv"
    archive_path = ARCHIVE_DIR / f"{name}_{today}.csv"

    df = pd.DataFrame(rows)
    df.to_csv(latest_path, index=False, quoting=csv.QUOTE_NONNUMERIC)
    df.to_csv(archive_path, index=False, quoting=csv.QUOTE_NONNUMERIC)
    print(f"Updated {latest_path} ({len(df)} rows)")
    print(f"Saved archive {archive_path}")


def run():
    ensure_directories()
    for source in DATA_SOURCES:
        print(f"Fetching dataset for {source['name']}...")
        dataset = find_dataset(source["query"])
        resource = find_resource(dataset, source["resource_name"])
        if resource is None:
            raise RuntimeError(f"No resource found for {source['name']}")
        resource_id = resource.get("id") or resource.get("resource_id")
        if not resource_id:
            raise RuntimeError(f"Missing resource_id for {source['name']}")

        rows = fetch_all_rows(resource_id)
        save_csv(source["name"], rows)


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
