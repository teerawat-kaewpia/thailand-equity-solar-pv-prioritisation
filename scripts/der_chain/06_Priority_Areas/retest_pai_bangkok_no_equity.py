"""
RETEST: Bangkok district PAI WITHOUT the equity criterion (3-criterion model)
============================================================================
Rationale: inverted NTL/capita measures emitted light (economic activity,
commercial/street lighting, land use) — NOT household income or ability-to-pay.
At intra-city scale it conflates land use with poverty (e.g. Watthana, wealthy,
scored "energy-poor"; Bang Rak CBD scored "least poor"). So the equity slot is
dropped and the model re-run with only the three validly-measured criteria:
  C1 Rooftop-solar yield (PVOUT x building density)
  C3 Demand density (population)
  C4 Infrastructure access (grid)

Two diagnostic questions:
  Q1  Does dropping equity change the priority ranking? (Spearman between the
      3-criterion PAI and the earlier 4-criterion PAI). High agreement => the
      equity criterion was largely redundant with / confounded by urban form.
  Q2  Does the discarded NTL/capity-equity signal still correlate with the new
      efficiency-only PAI? If yes, it was tracking urban built-up form, not
      independent equity information (i.e. the earlier "alignment" was a
      confound, not a genuine efficiency-equity finding).

Reuses the per-criterion normalised columns from bangkok_district_PAI.csv
(min-max normalisation of each criterion is independent of which others are in
the model, so C1/C3/C4 normalised values are unchanged by removing C2).
Output: DER/Data/14_Processed_Bangkok/bangkok_district_PAI_3crit.csv
"""
import numpy as np
import pandas as pd
import geopandas as gpd
import fiona
from sklearn.cluster import KMeans
from scipy import stats
from pathlib import Path
import os

BASE   = Path(os.environ.get("ENERGY_DATA_ROOT", r"D:\Clude Code GIS\Energy"))
BKKDIR = BASE / "DER" / "Data" / "14_Processed_Bangkok"
GADM   = BASE / "DER" / "Data" / "01_Admin_Boundaries" / "gadm41_THA.gpkg"
CSV4   = BKKDIR / "bangkok_district_PAI.csv"      # 4-criterion result to compare
N_ZONES = 5

CRIT = ["C1_RooftopYield", "C3_Demand", "C4_Infra"]   # equity dropped

# ── Load 4-criterion result (has normalised columns + PAI4) ───────────────────
df = pd.read_csv(CSV4)
df = df.rename(columns={"PAI": "PAI4", "rank": "rank4", "zone": "zone4"})
print(f"Loaded {len(df)} districts from 4-criterion result")

# ── geometry for Moran's I ─────────────────────────────────────────────────────
adm2 = next(l for l in fiona.listlayers(str(GADM)) if l.endswith("_2"))
khet = gpd.read_file(str(GADM), layer=adm2)
khet = khet[khet["NAME_1"] == "Bangkok Metropolis"][["NAME_2", "geometry"]].to_crs("EPSG:4326")
gdf = khet.merge(df, on="NAME_2", how="left")

# ── normalised 3-criterion matrix (reused columns) ────────────────────────────
Xn = gdf[[c + "_norm" for c in CRIT]].to_numpy(dtype="float64")

# ── EWM ────────────────────────────────────────────────────────────────────────
n = Xn.shape[0]
Xp = Xn - Xn.min(axis=0) + 1e-6
P = Xp / Xp.sum(axis=0, keepdims=True)
with np.errstate(divide="ignore", invalid="ignore"):
    lnP = np.where(P > 0, np.log(P), 0.0)
e = np.clip(-(1.0 / np.log(n)) * (P * lnP).sum(axis=0), 0.0, 1.0)
d = 1.0 - e
w = d / d.sum()
print("\n=== 3-criterion EWM weights ===")
for c, wi in zip(CRIT, w):
    print(f"  {c:16s} w = {wi:.3f}")

# ── TOPSIS ─────────────────────────────────────────────────────────────────────
Xw = Xn * w
D_pos = np.sqrt(((Xw - w) ** 2).sum(axis=1))
D_neg = np.sqrt((Xw ** 2).sum(axis=1))
PAI3 = D_neg / (D_pos + D_neg + 1e-12)
gdf["PAI3"] = PAI3
gdf["rank3"] = pd.Series(PAI3).rank(ascending=False).astype(int)
print(f"\nPAI3 range: {PAI3.min():.4f} - {PAI3.max():.4f} | mean {PAI3.mean():.4f}")

# ── K-means zones ──────────────────────────────────────────────────────────────
lab = KMeans(n_clusters=N_ZONES, random_state=42, n_init=10).fit_predict(PAI3.reshape(-1, 1))
zmean = [PAI3[lab == z].mean() for z in range(N_ZONES)]
remap = {o: r + 1 for r, o in enumerate(np.argsort(zmean)[::-1])}
gdf["zone3"] = [remap[z] for z in lab]

# ── Moran's I ──────────────────────────────────────────────────────────────────
try:
    from libpysal.weights import Queen
    from esda.moran import Moran
    W = Queen.from_dataframe(gdf, use_index=False); W.transform = "r"
    mi = Moran(gdf["PAI3"].values, W, permutations=999)
    print(f"Moran's I (3-crit) = {mi.I:.4f}  (p = {mi.p_sim:.4f})")
except Exception as ex:
    print(f"Moran's I skipped: {ex}")

# ── Q1: does dropping equity change the ranking? ──────────────────────────────
rho_rank, p_rank = stats.spearmanr(gdf["PAI4"], gdf["PAI3"])
tau_rank, _ = stats.kendalltau(gdf["rank4"], gdf["rank3"])
maxshift = int((gdf["rank4"] - gdf["rank3"]).abs().max())
print("\n=== Q1: 3-criterion vs 4-criterion ranking agreement ===")
print(f"  Spearman rho = {rho_rank:.3f} (p={p_rank:.1e}) | Kendall tau = {tau_rank:.3f} | max rank shift = {maxshift}")
print("  (high agreement => equity criterion was largely redundant with urban form)")

# ── Q2: does the discarded equity signal still track the efficiency-only PAI? ──
rho_eq, p_eq = stats.spearmanr(gdf["C2_Equity_norm"], gdf["PAI3"])
print("\n=== Q2: discarded NTL-equity signal vs efficiency-only PAI3 ===")
print(f"  Spearman rho = {rho_eq:.3f} (p={p_eq:.1e})")
print("  (still-high => NTL/capita was tracking built-up form, not independent equity)")

# ── zone-level moves ──────────────────────────────────────────────────────────
print("\n=== Top 8 by 3-criterion PAI (with 4-crit rank for comparison) ===")
top = gdf.sort_values("rank3").head(8)[["NAME_2", "PAI3", "rank3", "rank4", "zone3"]]
print(top.to_string(index=False))
print("\n=== Bottom 5 ===")
print(gdf.sort_values("rank3").tail(5)[["NAME_2", "PAI3", "rank3", "rank4"]].to_string(index=False))

# ── save ───────────────────────────────────────────────────────────────────────
out = gdf.drop(columns="geometry").sort_values("rank3")
out.to_csv(BKKDIR / "bangkok_district_PAI_3crit.csv", index=False, encoding="utf-8-sig")
print(f"\nDone -> {BKKDIR / 'bangkok_district_PAI_3crit.csv'}")
