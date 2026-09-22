"""Session 1 fix: the sample-day mismatch check (data/checks/sample_day_mismatch.csv)."""

from pathlib import Path

import pandas as pd

from curvecarry import checks

STANDARD = [1, 2, 3, 5, 7, 10, 20, 30]


def _daily() -> pd.DataFrame:
    """March 2020: 2y and 10y print on 2, 16 and 31 March; 30y stops on 16 March;
    the non-standard 15y stops on 2 March. April: everything prints on the 30th."""
    rows = []
    for d in ["2020-03-02", "2020-03-16", "2020-03-31"]:
        rows += [(d, 2.0, 0.01), (d, 10.0, 0.02)]
    rows += [("2020-03-02", 30.0, 0.03), ("2020-03-16", 30.0, 0.03), ("2020-03-31", 30.0, None)]
    rows += [("2020-03-02", 15.0, 0.025)]
    rows += [("2020-04-30", t, 0.01) for t in (2.0, 10.0, 30.0, 15.0)]
    df = pd.DataFrame(rows, columns=["obs_date", "tenor_years", "yield"])
    return df


def test_sample_day_rows_counts_standard_tenors_sampled_before_the_latest_print() -> None:
    out = checks.sample_day_rows(_daily(), "XX", STANDARD)
    assert list(out.columns) == checks.SAMPLE_DAY_COLUMNS
    mar = out[out["date"] == "2020-03-31"].iloc[0]
    assert mar["latest_obs_date"] == "2020-03-31"
    assert mar["n_standard_tenors"] == 3  # 2, 10, 30 (15 is not standard)
    assert mar["n_earlier"] == 1 and mar["earlier_tenors"] == "30@2020-03-16"  # NaN on the 31st
    apr = out[out["date"] == "2020-04-30"].iloc[0]
    assert apr["n_earlier"] == 0 and apr["earlier_tenors"] == ""


def test_write_sample_day_replaces_only_the_country(tmp_path: Path) -> None:
    p = tmp_path / "sample_day_mismatch.csv"
    checks.write_sample_day(_daily(), "XX", STANDARD, path=p)
    checks.write_sample_day(_daily(), "YY", STANDARD, path=p)
    # a re-run for XX with a clean April replaces XX's rows and keeps YY's
    clean = _daily()
    clean = clean[clean["obs_date"] != "2020-03-16"]
    out = checks.write_sample_day(clean, "XX", STANDARD, path=p)
    assert sorted(set(out["country"])) == ["XX", "YY"]
    assert (out[out["country"] == "YY"]["n_earlier"].astype(int) == [1, 0]).all()
    xx_mar = out[(out["country"] == "XX") & (out["date"] == "2020-03-31")].iloc[0]
    assert xx_mar["earlier_tenors"] == "30@2020-03-02"
    assert p.read_text(encoding="utf-8").splitlines()[0] == ",".join(checks.SAMPLE_DAY_COLUMNS)
