#!/usr/bin/env python
"""Quick syntax check for modified files."""
import sys
import py_compile

files = [
    'app.py',
    'budget_calculator.py',
    'amenity_search.py',
    'policy_context.py',
]

errors = []
for fname in files:
    try:
        py_compile.compile(fname, doraise=True)
        print(f"✓ {fname}")
    except py_compile.PyCompileError as e:
        print(f"✗ {fname}: {e}")
        errors.append(fname)

if errors:
    print(f"\n{len(errors)} file(s) with syntax errors")
    sys.exit(1)
else:
    print(f"\nAll {len(files)} files compile successfully!")
    sys.exit(0)
