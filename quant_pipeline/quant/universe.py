"""The benchmark of the pipeline.

The universe is the S&P 500 on each date. The membership seed in the dbt
project holds it. See quant.reference. SPY is the benchmark. The backtest
compares the portfolio against SPY.
"""

from __future__ import annotations

# The benchmark ticker. The pipeline downloads it, but does not screen it.
BENCHMARK: str = "SPY"
