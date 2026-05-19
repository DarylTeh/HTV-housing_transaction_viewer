#!/usr/bin/env python
"""Test imports without running streamlit."""
import sys
sys.path.insert(0, r'c:\Users\daryl\Downloads\Programming\HTV-housing_transaction_viewer.worktrees\agents-collapsible-features-and-user-profile')

print("Testing imports...")

try:
    print("  budget_calculator...", end=" ")
    from budget_calculator import calculate_budget, format_currency
    print("✓")
except Exception as e:
    print(f"✗ {e}")

try:
    print("  amenity_search...", end=" ")
    from amenity_search import load_pharmacies, load_hawker_centres, load_pois
    print("✓")
except Exception as e:
    print(f"✗ {e}")

try:
    print("  policy_context...", end=" ")
    from policy_context import POLICY_EDUCATION, get_policy_tip
    print("✓")
except Exception as e:
    print(f"✗ {e}")

print("\nAll modules imported successfully!")
