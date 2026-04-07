from __future__ import annotations

import numpy as np
import pandas as pd


def compute_returns(df: pd.DataFrame, price_col: str = "close") -> pd.DataFrame:
    out = df.copy()
    out["return_1d"] = out[price_col].pct_change()
    return out


def add_log_returns(df: pd.DataFrame, price_col: str = "close", out_col: str = "log_return") -> pd.DataFrame:
    out = df.copy()
    out[out_col] = np.log(out[price_col] / out[price_col].shift(1))
    return out
