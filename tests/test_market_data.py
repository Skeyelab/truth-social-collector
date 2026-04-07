import pandas as pd

from truthbrush_oil_study.market_data import compute_returns


def test_compute_returns_adds_daily_returns():
    df = pd.DataFrame({"close": [100.0, 105.0]})

    out = compute_returns(df)

    assert "return_1d" in out.columns
    assert round(out.loc[1, "return_1d"], 6) == round((105.0 / 100.0) - 1.0, 6)
