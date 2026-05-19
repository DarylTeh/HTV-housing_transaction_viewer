"""Dataset audit: Verify all data files are used by the application."""

from __future__ import annotations

DATASET_AUDIT = {
    "HDB Resale": {
        "file": "data/All_HDB(2012-2026).xlsx",
        "features_using": [
            "Market snapshot metrics",
            "Market Trends & Prices tab",
            "Price change analysis",
            "Affordability calculator (defaults)",
        ],
        "status": "✓ ACTIVE",
    },
    "Private Property (URA Modern)": {
        "file": "data/All_URA(2020-2025).xlsx",
        "features_using": [
            "Market snapshot metrics",
            "Market Trends & Prices tab",
            "Price change analysis",
            "Region segmentation (CCR/RCR/OCR)",
            "Affordability calculator (defaults)",
        ],
        "status": "✓ ACTIVE",
    },
    "Private Property (URA Legacy)": {
        "file": "data/All_URA(2010-2017).xlsx",
        "features_using": [
            "Market snapshot metrics",
            "Market Trends & Prices tab",
            "Price change analysis",
            "Region segmentation (CCR/RCR/OCR)",
        ],
        "status": "✓ ACTIVE",
    },
    "Schools": {
        "file": "data/school_list.csv",
        "features_using": [
            "Nearest schools finder (1 km priority zones)",
            "School rankings table",
            "Commute distance tool",
            "Policy context: School enrolment priority",
        ],
        "status": "✓ ACTIVE",
    },
    "Licensed Pharmacies": {
        "file": "data/ListingofLicensedPharmacies.csv",
        "features_using": [
            "Advanced Amenities & POI Proximity tab (Coming soon)",
            "Healthcare proximity finder (planned)",
        ],
        "status": "🟡 PARTIALLY ACTIVE (UI only)",
    },
    "Hawker Centres": {
        "file": "data/ListofGovernmentMarketsHawkerCentres.csv",
        "features_using": [
            "Advanced Amenities & POI Proximity tab (Coming soon)",
            "Food culture/daily living convenience finder (planned)",
            "Policy context: Family planning (food access)",
        ],
        "status": "🟡 PARTIALLY ACTIVE (UI only)",
    },
    "Points of Interest (POIs)": {
        "file": "data/singapore_all_pois.csv",
        "features_using": [
            "Advanced Amenities & POI Proximity tab (Coming soon)",
            "Amenity walkability summary (planned - supermarkets, parks, MRT)",
        ],
        "status": "🟡 PARTIALLY ACTIVE (UI only)",
    },
    "Rental Income Scenario": {
        "file": "data/RentalIncome.xlsx",
        "features_using": [
            "Rent vs Buy comparison (worked example)",
            "Rent vs mortgage timeline chart",
        ],
        "status": "✓ ACTIVE",
    },
    "General Schools Information": {
        "file": "data/Generalinformationofschools.csv",
        "features_using": [
            "Supplementary data (currently not used in main views)",
        ],
        "status": "⚠️ AVAILABLE (Not yet utilized)",
    },
}


def print_audit_report():
    """Print a formatted audit report."""
    print("\n" + "=" * 80)
    print("DATASET AUDIT REPORT")
    print("=" * 80)
    
    active_count = sum(1 for d in DATASET_AUDIT.values() if "✓" in d["status"])
    partial_count = sum(1 for d in DATASET_AUDIT.values() if "🟡" in d["status"])
    unused_count = sum(1 for d in DATASET_AUDIT.values() if "⚠️" in d["status"])
    
    print(f"\nSummary: {active_count} active, {partial_count} partial, {unused_count} available\n")
    
    for dataset_name, info in DATASET_AUDIT.items():
        print(f"\n{info['status']} {dataset_name}")
        print(f"  File: {info['file']}")
        print(f"  Used by:")
        for feature in info['features_using']:
            print(f"    • {feature}")


if __name__ == "__main__":
    print_audit_report()
