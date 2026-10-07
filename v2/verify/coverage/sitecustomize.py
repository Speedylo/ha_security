"""Starts branch coverage in every Python process that inherits COVERAGE_PROCESS_START (4.12, 2026-10-07).

On PYTHONPATH for the coverage run only (notes/tests_bite_prediction_20261007.md). `coverage` is not
installed into either interpreter: each has its own copy under LIB, chosen by version here. Debian's
own sitecustomize, which this one shadows, is run afterwards so nothing else changes.
"""
import os
import sys

LIB = "/home/younes/r2exp/tb/cov/lib"

if os.environ.get("COVERAGE_PROCESS_START"):
    sys.path.insert(0, f"{LIB}/py{sys.version_info[0]}{sys.version_info[1]}")
    try:
        import coverage
        coverage.process_startup()
    except Exception as err:  # never stop a process from starting because measurement could not
        sys.stderr.write(f"sitecustomize: coverage did not start: {err}\n")

_debian = f"/usr/lib/python{sys.version_info[0]}.{sys.version_info[1]}/sitecustomize.py"
if os.path.exists(_debian):
    with open(_debian) as _f:
        exec(compile(_f.read(), _debian, "exec"))
