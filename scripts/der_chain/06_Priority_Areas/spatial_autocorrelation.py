"""
Spatial autocorrelation of PAI at province level (Moran's I)
=============================================================
Uses province-mean PAI with queen contiguity spatial weights.
Reports global Moran's I + p-value (999 permutations).
Also computes LISA (local Moran's I) to identify spatial clusters.
"""

import numpy as np
import pandas as pd
import geopandas as gpd
import fiona
from pathlib import Path
import os
import warnings
warnings.filterwarnings("ignore")

try:
    from esda.moran import Moran, Moran_Local
    from libpysal.weights import Queen
    HAS_ESDA = True
except ImportError:
    HAS_ESDA = False

BASE    = Path(os.environ.get("ENERGY_DATA_ROOT", r"D:\Clude Code GIS\Energy"))
GADM    = BASE / "DER" / "Data" / "01_Admin_Boundaries" / "gadm41_THA.gpkg"
STATS   = BASE / "DER" / "Data" / "14_Processed_90m" / "province_PAI_summary.csv"
OUT_CSV = BASE / "DER" / "Data" / "14_Processed_90m" / "province_LISA.csv"

# ── Load province geometries + PAI stats ──────────────────────────────────────
print("Loading data...")
layers = fiona.listlayers(str(GADM))
adm1   = next((l for l in layers if l.endswith("_1")), layers[1])
prov   = gpd.read_file(str(GADM), layer=adm1)
prov   = prov[["GID_1", "NAME_1", "geometry"]].copy()
prov   = prov.to_crs("EPSG:32647")   # UTM 47N for distance-based weights

stats  = pd.read_csv(STATS)
prov   = prov.merge(stats[["GID_1", "PAI", "dominant_zone"]], on="GID_1")
print(f"  {len(prov)} provinces | PAI range: {prov['PAI'].min():.4f}–{prov['PAI'].max():.4f}")

if not HAS_ESDA:
    print("\nesda / libpysal not installed. Running manual Moran's I calculation...")
    # Manual global Moran's I with queen contiguity approximation
    # Build adjacency from spatial join
    prov_reproj = prov.copy()
    prov_reproj["geometry"] = prov_reproj.geometry.buffer(1000)   # 1km buffer
    adj = gpd.sjoin(prov_reproj[["GID_1", "geometry"]],
                    prov[["GID_1", "geometry"]],
                    how="left", predicate="intersects")
    adj = adj[adj["GID_1_left"] != adj["GID_1_right"]]

    pai_vals = prov.set_index("GID_1")["PAI"]
    n  = len(prov)
    z  = pai_vals - pai_vals.mean()
    W  = 0.0
    numerator = 0.0
    for gid, neighbors in adj.groupby("GID_1_left")["GID_1_right"]:
        for nb in neighbors:
            if nb in z.index:
                numerator += z[gid] * z[nb]
                W += 1.0
    denom = (z ** 2).sum()
    moran_I = (n / W) * (numerator / denom)
    print(f"\nManual Global Moran's I = {moran_I:.4f}")
    print("(p-value not computed — install esda+libpysal for full test)")
    print("\nNote: Run  pip install esda libpysal  for permutation test + LISA")
    print("\nProvince PAI ranked:")
    print(prov[["NAME_1","PAI","dominant_zone"]].sort_values("PAI",ascending=False).to_string(index=False))
else:
    # ── Build spatial weights ──────────────────────────────────────────────────
    print("Building Queen contiguity weights...")
    w = Queen.from_dataframe(prov, silence_warnings=True)
    w.transform = "r"   # row-standardize

    # ── Global Moran's I ──────────────────────────────────────────────────────
    print("Computing Global Moran's I (999 permutations)...")
    mi = Moran(prov["PAI"].values, w, permutations=999)
    print(f"\n  Global Moran's I = {mi.I:.4f}")
    print(f"  E[I] (expected) = {mi.EI:.4f}")
    print(f"  z-score         = {mi.z_norm:.4f}")
    print(f"  p-value (norm)  = {mi.p_norm:.4f}")
    print(f"  p-value (rand)  = {mi.p_rand:.4f}")
    if mi.p_norm < 0.05:
        direction = "positive" if mi.I > 0 else "negative"
        print(f"  → Statistically significant {direction} spatial autocorrelation (p<0.05)")

    # ── Local Moran's I (LISA) ─────────────────────────────────────────────────
    print("\nComputing LISA (local Moran's I)...")
    lm = Moran_Local(prov["PAI"].values, w, permutations=999, seed=42)
    prov["LISA_I"]   = lm.Is
    prov["LISA_p"]   = lm.p_sim
    prov["LISA_q"]   = lm.q   # 1=HH, 2=LH, 3=LL, 4=HL

    quad_map = {1: "HH", 2: "LH", 3: "LL", 4: "HL"}
    prov["LISA_type"] = prov.apply(
        lambda r: quad_map[int(r["LISA_q"])] if r["LISA_p"] < 0.05 else "ns", axis=1
    )

    cluster_summary = prov["LISA_type"].value_counts()
    print("\n  LISA cluster summary (p<0.05):")
    print(cluster_summary.to_string())

    print("\n  HH clusters (high-high, significant):")
    hh = prov[prov["LISA_type"] == "HH"][["NAME_1","PAI","LISA_I","LISA_p"]].sort_values("PAI",ascending=False)
    print(hh.to_string(index=False))

    print("\n  LL clusters (low-low, significant):")
    ll = prov[prov["LISA_type"] == "LL"][["NAME_1","PAI","LISA_I","LISA_p"]].sort_values("PAI")
    print(ll.to_string(index=False))

    # Save LISA results
    prov.drop(columns="geometry").to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    print(f"\nLISA saved: {OUT_CSV}")
