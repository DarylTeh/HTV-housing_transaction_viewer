"""
Convert CSV files to Parquet format for faster loading and smaller file size.

Usage:
  python scripts/convert_to_parquet.py           # convert all files
  python scripts/convert_to_parquet.py --processed-only  # only convert data/processed/*.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed"


def convert_csv_to_parquet(csv_path: Path, parquet_path: Path, verbose: bool = True) -> bool:
    """Convert a single CSV file to Parquet format."""
    try:
        if verbose:
            print(f"Converting {csv_path.name}...", end=" ")
        
        # Read CSV with low_memory=False to avoid dtype warnings
        df = pd.read_csv(csv_path, low_memory=False)
        
        # Write to parquet
        df.to_parquet(parquet_path, engine="pyarrow", index=False, compression="snappy")
        
        csv_size_mb = csv_path.stat().st_size / (1024 * 1024)
        parquet_size_mb = parquet_path.stat().st_size / (1024 * 1024)
        compression_ratio = csv_size_mb / parquet_size_mb if parquet_size_mb > 0 else 0
        
        if verbose:
            print(f"✓ ({csv_size_mb:.1f}MB → {parquet_size_mb:.1f}MB, {compression_ratio:.1f}x compression)")
        return True
    except Exception as e:
        if verbose:
            print(f"✗ Error: {e}")
        return False


def convert_raw_data_files():
    """Convert raw data files in data/ directory to parquet."""
    print("Converting raw data files...")
    
    # Patterns for raw data files
    patterns = [
        "CondoResidentialTransaction*.csv",
        "ECResidentialTransaction*.csv",
        "Resale Flat Prices*.csv",
        "Generalinformationofschools.csv",
        "ListingofLicensedPharmacies.csv",
        "ListofGovernmentMarketsHawkerCentres.csv",
        "RentalIncome.csv",
        "singapore_all_pois.csv",
    ]
    
    converted = 0
    failed = 0
    
    for pattern in patterns:
        for csv_path in DATA_DIR.glob(pattern):
            if csv_path.is_dir():
                continue
            parquet_path = csv_path.with_suffix(".parquet")
            if convert_csv_to_parquet(csv_path, parquet_path):
                converted += 1
            else:
                failed += 1
    
    print(f"Raw data: {converted} converted, {failed} failed\n")
    return converted, failed


def convert_processed_data_files():
    """Convert processed data files in data/processed/ directory to parquet."""
    print("Converting processed data files...")
    
    converted = 0
    failed = 0
    
    for csv_path in PROCESSED_DIR.glob("*.csv"):
        parquet_path = csv_path.with_suffix(".parquet")
        if convert_csv_to_parquet(csv_path, parquet_path):
            converted += 1
        else:
            failed += 1
    
    print(f"Processed data: {converted} converted, {failed} failed\n")
    return converted, failed


def main():
    parser = argparse.ArgumentParser(description="Convert CSV files to Parquet format")
    parser.add_argument("--processed-only", action="store_true", help="Only convert data/processed/*.csv")
    parser.add_argument("--raw-only", action="store_true", help="Only convert raw data files")
    args = parser.parse_args()

    total_converted = 0
    total_failed = 0

    if args.processed_only:
        converted, failed = convert_processed_data_files()
    elif args.raw_only:
        converted, failed = convert_raw_data_files()
    else:
        # Convert both
        converted, failed = convert_raw_data_files()
        total_converted += converted
        total_failed += failed
        
        converted, failed = convert_processed_data_files()
        total_converted += converted
        total_failed += failed

    if total_converted > 0 or total_failed > 0:
        print(f"Total: {total_converted} converted, {total_failed} failed")
    else:
        print("No files converted.")

    sys.exit(0 if total_failed == 0 else 1)


if __name__ == "__main__":
    main()
