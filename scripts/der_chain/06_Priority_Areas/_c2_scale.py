"""Pixel-level scaling of C2 (amendment A5, 2026-10-10).

C2_poverty_90m.tif holds the raw provincial poverty incidence (%), unscaled. Pixel-level TOPSIS scripts
need every layer on [0,1], so they scale C2 here, explicitly, with the 2nd-98th percentile clip over the
77 province values. This is the transform the raster itself carried before A5, so moving it here leaves
the pixel-level analyses unchanged. Province-level PAI does not use this module: it clips and scales the
province means once, in compute_pai_province_level.py.
"""
import numpy as np
import pandas as pd


def scale_c2_pixels(arr, nodata, proc):
    v = pd.read_csv(proc / "C2_poverty_province.csv")["poverty_pct"].to_numpy(float)
    assert np.nanmax(v) > 1.0, "C2_poverty_province.csv must hold poverty in percent"
    lo, hi = np.nanpercentile(v, 2), np.nanpercentile(v, 98)
    m = arr != nodata
    assert np.nanmax(arr[m]) > 1.0, "C2 raster is already scaled; it must hold raw percent (A5)"
    out = arr.astype("float32").copy()
    out[m] = np.clip((arr[m].astype("float64") - lo) / (hi - lo + 1e-12), 0.0, 1.0).astype("float32")
    return out
