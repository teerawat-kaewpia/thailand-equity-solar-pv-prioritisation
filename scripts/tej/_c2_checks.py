"""Hard checks for the C2 poverty table (A4 verification, test 2). Any failure raises AssertionError,
so a builder that calls validate_c2() stops instead of writing a bad table.

Checks: exactly 77 rows; every GADM province matched once (no unmatched, no extra); no duplicated or
missing English or Thai key; poverty values numeric and inside 0-100.
"""
import pandas as pd

N_PROVINCES = 77


def validate_c2(df, gadm_names, value_col="poverty_pct", en_col="NAME_1", th_col="prov_th"):
    assert len(df) == N_PROVINCES, f"C2 table has {len(df)} rows, expected {N_PROVINCES}"
    for col in (en_col, th_col):
        assert df[col].notna().all(), f"missing {col}: {df[df[col].isna()].index.tolist()}"
        dup = df[df[col].duplicated(keep=False)][col].tolist()
        assert not dup, f"duplicated {col}: {sorted(set(dup))}"
    gadm = set(gadm_names)
    unmatched = sorted(gadm - set(df[en_col]))
    extra = sorted(set(df[en_col]) - gadm)
    assert not unmatched and not extra, f"unmatched GADM provinces {unmatched}, names not in GADM {extra}"
    v = pd.to_numeric(df[value_col], errors="coerce")
    assert v.notna().all(), f"non-numeric or missing {value_col}: {df[v.isna()][en_col].tolist()}"
    bad = df[(v < 0) | (v > 100)][en_col].tolist()
    assert not bad, f"{value_col} outside 0-100: {bad}"
    return True
