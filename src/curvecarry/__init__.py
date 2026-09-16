"""curvecarry: G7 yield curve models and a duration-neutral, FX-hedged carry strategy.

Package-wide conventions (see CLAUDE.md, invariants table):
- yields are decimals (0.0425, never 4.25); conversion happens once, in a loader
- ``par`` and ``zero`` curves are never mixed; curve functions assert on ``curve_type``
- every number that affects a result is read from ``config.toml``
"""

__version__ = "0.1.0"
