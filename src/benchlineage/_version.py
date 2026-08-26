"""Single source of the BenchLineage version.

Kept free of package imports so every module (and ``pyproject``-adjacent
checks) can read one value without circular-import risk. The release process
bumps exactly this line plus the pins guarded by ``scripts/check_repository.py``.
"""

__version__ = "0.3.8"
