#!/usr/bin/env python
"""Demo: Income-based budget calculator example."""

from budget_calculator import calculate_budget, format_currency

# Example 1: Single buyer, $6000/month income, age 35
print("=" * 70)
print("EXAMPLE 1: Single Buyer, $6,000/month income, Age 35")
print("=" * 70)

result1 = calculate_budget(
    gross_monthly_income=6000.0,
    num_buyers=1,
    ages=[35],
    cpf_pledge_pct=0,
)

print(f"Income: {format_currency(result1.gross_monthly_income)}/month")
print(f"Buyers: {result1.num_buyers}")
print(f"Ages: {result1.ages}")
print(f"CPF Pledged: {result1.cpf_pledge_pct}%")
print()
print(f"💡 HDB Max Budget:     {format_currency(result1.hdb_max_budget)}")
print(f"💡 Private Max Budget: {format_currency(result1.private_max_budget)}")
print(f"🎯 Recommended Budget: {format_currency(result1.recommended_budget)}")
if result1.limitations:
    print("\n⚠️  Notes:")
    for limitation in result1.limitations:
        print(f"   - {limitation}")

# Example 2: Dual income, $10,000/month, ages 35 & 33, 20% CPF pledge
print("\n" + "=" * 70)
print("EXAMPLE 2: Dual Buyers, $10,000/month income, Ages 35 & 33, 20% CPF Pledged")
print("=" * 70)

result2 = calculate_budget(
    gross_monthly_income=10000.0,
    num_buyers=2,
    ages=[35, 33],
    cpf_pledge_pct=20,
)

print(f"Combined Income: {format_currency(result2.gross_monthly_income)}/month")
print(f"Buyers: {result2.num_buyers} ({', '.join(str(a) for a in result2.ages)} years old)")
print(f"CPF Pledged: {result2.cpf_pledge_pct}%")
print()
print(f"💡 HDB Max Budget:     {format_currency(result2.hdb_max_budget)}")
print(f"💡 Private Max Budget: {format_currency(result2.private_max_budget)}")
print(f"🎯 Recommended Budget: {format_currency(result2.recommended_budget)}")
if result2.limitations:
    print("\n⚠️  Notes:")
    for limitation in result2.limitations:
        print(f"   - {limitation}")

# Example 3: Age at loan end check (45 year old buying now)
print("\n" + "=" * 70)
print("EXAMPLE 3: Older Buyer (Age 45), showing age-at-completion warning")
print("=" * 70)

result3 = calculate_budget(
    gross_monthly_income=8000.0,
    num_buyers=1,
    ages=[45],
    cpf_pledge_pct=0,
)

print(f"Income: {format_currency(result3.gross_monthly_income)}/month")
print(f"Age: {result3.ages[0]}")
print(f"Age at loan end: {result3.ages[0] + 25} (25-year loan)")
print()
print(f"💡 HDB Max Budget:     {format_currency(result3.hdb_max_budget)}")
print(f"💡 Private Max Budget: {format_currency(result3.private_max_budget)}")
print(f"🎯 Recommended Budget: {format_currency(result3.recommended_budget)}")
if result3.limitations:
    print("\n⚠️  Notes:")
    for limitation in result3.limitations:
        print(f"   - {limitation}")

print("\n" + "=" * 70)
print("Budget Calculator Demo Complete!")
print("=" * 70)
