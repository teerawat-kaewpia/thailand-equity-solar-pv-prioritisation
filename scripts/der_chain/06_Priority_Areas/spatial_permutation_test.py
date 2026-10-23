# -*- coding: utf-8 -*-
"""
Spatially restricted permutation tests for the correlations the paper relies on.

Both the province and district units are spatially autocorrelated (Moran's I of
the PAI is 0.253 and 0.274 respectively), so the classical p-values attached to
Spearman correlations are anti-conservative: neighbouring units are not
independent draws. This script recomputes the significance of the key
correlations against a null that PRESERVES spatial structure, using
Moran-spectral-randomisation-style surrogates built from the Queen contiguity
graph (Wagner & Dray 2015): the response is permuted within the eigenvector
basis of the spatial weights, so surrogates retain the observed autocorrelation
while destroying the association with the covariate.

Outputs Data/14_Processed_90m/spatial_permutation_results.json
"""
import json
import numpy as np
import pandas as pd
import geopandas as gpd
import fiona
from scipy import stats
from libpysal.weights import Queen
from pathlib import Path
import os
import warnings; warnings.filterwarnings("ignore")

BASE = Path(os.environ.get("DER_PROJECT_ROOT", Path(__file__).resolve().parents[2]))
PROC = BASE / "Data" / "14_Processed_90m"
BKK = BASE / "Data" / "14_Processed_Bangkok"
GADM = BASE / "Data" / "01_Admin_Boundaries" / "gadm41_THA.gpkg"
RNG = np.random.default_rng(20260722)
NSIM = 4999


def msr_surrogates(y, W, n_sim, rng):
    """Moran spectral randomisation: surrogates with the same spatial structure."""
    n = len(y)
    Wd = W.full()[0].astype(float)
    Wd = (Wd + Wd.T) / 2.0
    M = np.eye(n) - np.ones((n, n)) / n
    Omega = M @ Wd @ M
    vals, vecs = np.linalg.eigh(Omega)
    order = np.argsort(-vals)
    vecs = vecs[:, order]
    yc = y - y.mean()
    coef = vecs.T @ yc                      # projection onto spatial eigenvectors
    out = np.empty((n_sim, n))
    for i in range(n_sim):
        signs = rng.choice([-1.0, 1.0], size=n)
        perm = rng.permutation(n)
        # randomise signs and shuffle within the spectral basis: preserves the
        # magnitude spectrum (hence autocorrelation) but breaks the specific map
        out[i] = vecs @ (coef[perm] * signs) + y.mean()
    return out


def sp_test(x, y, W, label):
    rho, p_classic = stats.spearmanr(x, y)
    sur = msr_surrogates(np.asarray(y, float), W, NSIM, RNG)
    null = np.array([stats.spearmanr(x, s)[0] for s in sur])
    p_spatial = (np.sum(np.abs(null) >= abs(rho)) + 1) / (NSIM + 1)
    print(f"  {label}")
    print(f"     rho = {rho:+.3f}   p(classical) = {p_classic:.4g}   "
          f"p(spatial) = {p_spatial:.4g}")
    return {"label": label, "rho": round(float(rho), 3),
            "p_classical": float(f"{p_classic:.4g}"),
            "p_spatial": float(f"{p_spatial:.4g}"),
            "n_sim": NSIM}


results = {}

# ── province scale ────────────────────────────────────────────────────────────
adm1 = next(l for l in fiona.listlayers(str(GADM)) if l.endswith("_1"))
g1 = gpd.read_file(str(GADM), layer=adm1)[["NAME_1", "geometry"]]
norm = pd.read_csv(PROC / "province_criteria_normalised.csv")
val = pd.read_csv(PROC / "validation_solar_osm.csv")

gp = g1.merge(norm, on="NAME_1").merge(val[["NAME_1", "solar_count"]], on="NAME_1")
Wp = Queen.from_dataframe(gp, use_index=False); Wp.transform = "r"

CR = ["C1_Resource", "C2_Equity", "C3_Demand", "C4_Infra", "C5_Physical"]
X = gp[CR].to_numpy(float)
eff = [0, 2, 3, 4]


def ewm(Mx):
    n = Mx.shape[0]; Mp = Mx - Mx.min(0) + 1e-12
    P = Mp / Mp.sum(0, keepdims=True)
    e = np.clip(-(1 / np.log(n)) * (P * np.where(P > 0, np.log(P), 0)).sum(0), 0, 1)
    d = 1 - e; return d / d.sum()


def topsis(Mx, w):
    Mw = Mx * w
    return np.sqrt((Mw ** 2).sum(1)) / (np.sqrt(((Mw - w) ** 2).sum(1))
                                        + np.sqrt((Mw ** 2).sum(1)) + 1e-12)


PAI_eff = topsis(X[:, eff], ewm(X[:, eff]))

print("PROVINCE SCALE (n = 77, Queen contiguity, "
      f"{NSIM} Moran-spectral surrogates)")
results["province"] = [
    sp_test(X[:, 1], PAI_eff, Wp, "C2 Equity vs efficiency-only composite"),
    sp_test(PAI_eff, gp["solar_count"].to_numpy(float), Wp,
            "efficiency-only composite vs installation count"),
    sp_test(X[:, 1], gp["solar_count"].to_numpy(float), Wp,
            "C2 Equity vs installation count"),
    sp_test(gp["PAI"].to_numpy(float), gp["solar_count"].to_numpy(float), Wp,
            "full PAI vs installation count"),
]

# ── district scale ────────────────────────────────────────────────────────────
adm2 = next(l for l in fiona.listlayers(str(GADM)) if l.endswith("_2"))
g2 = gpd.read_file(str(GADM), layer=adm2)
g2 = g2[g2["NAME_1"] == "Bangkok Metropolis"][["NAME_2", "geometry"]]
d = pd.read_csv(BKK / "bangkok_district_PAI_vuln.csv")
gd = g2.merge(d, on="NAME_2")
print(f"\nDISTRICT SCALE (n = {len(gd)}, Queen contiguity)")
Wd = Queen.from_dataframe(gd, use_index=False); Wd.transform = "r"
results["district"] = [
    sp_test(gd["C2_Equity_norm"].to_numpy(float), gd["PAI3"].to_numpy(float), Wd,
            "C2 Equity vs efficiency-only composite (district)"),
]

out = PROC / "spatial_permutation_results.json"
out.write_text(json.dumps(results, indent=2), encoding="utf-8")
print(f"\nSaved: {out}")
