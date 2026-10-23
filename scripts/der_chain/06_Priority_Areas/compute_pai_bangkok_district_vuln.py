# -*- coding: utf-8 -*-
"""
District PAI rebuild WITH a valid equity criterion (BMA social-vulnerability
index) restored — reversing the earlier efficiency-only model.

4 criteria: rooftop-solar yield, equity (BMA vulnerability), demand density,
infrastructure access. Reuses the normalised efficiency columns from
bangkok_district_PAI.csv; equity is the BMA vulnerability score, normalised [0,1].

Key test (same as province): is the equity criterion ORTHOGONAL to the composite
when populated with a VALID measure, or does it correlate with the efficiency
criteria? Compares against the efficiency-only 3-criterion model.
Output: bangkok_district_PAI_vuln.csv
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
N_ZONES = 5

CRIT = ["C1_RooftopYield", "C2_Equity", "C3_Demand", "C4_Infra"]

# efficiency criteria (normalised) from the existing district run
eff = pd.read_csv(BKKDIR / "bangkok_district_PAI.csv")[
    ["NAME_2", "C1_RooftopYield_norm", "C3_Demand_norm", "C4_Infra_norm", "PAI3"]
    if False else ["NAME_2", "C1_RooftopYield_norm", "C3_Demand_norm", "C4_Infra_norm"]]
# valid equity (BMA vulnerability)
vul = pd.read_csv(BKKDIR / "C2_vulnerability_district.csv")[["NAME_2", "C2_norm"]]
vul.columns = ["NAME_2", "C2_Equity_norm"]
# efficiency-only PAI for comparison
eff3 = pd.read_csv(BKKDIR / "bangkok_district_PAI_3crit.csv")[["NAME_2", "PAI3", "rank3"]]

df = eff.merge(vul, on="NAME_2", how="left").merge(eff3, on="NAME_2", how="left")
print(f"Districts: {len(df)} | equity matched: {df['C2_Equity_norm'].notna().sum()}")

Xn = df[["C1_RooftopYield_norm", "C2_Equity_norm", "C3_Demand_norm", "C4_Infra_norm"]].to_numpy(float)

# ── EWM ────────────────────────────────────────────────────────────────────────
n = Xn.shape[0]
Xp = Xn - Xn.min(0) + 1e-6
P = Xp / Xp.sum(0, keepdims=True)
with np.errstate(divide="ignore", invalid="ignore"):
    lnP = np.where(P > 0, np.log(P), 0.0)
e = np.clip(-(1/np.log(n)) * (P*lnP).sum(0), 0, 1)
w = (1-e) / (1-e).sum()
print("\n=== 4-criterion EWM weights (valid equity) ===")
for c, wi in zip(CRIT, w):
    print(f"  {c:16s} w={wi:.3f}")

# ── TOPSIS ─────────────────────────────────────────────────────────────────────
Xw = Xn * w
PAI = np.sqrt((Xw**2).sum(1)) / (np.sqrt(((Xw-w)**2).sum(1)) + np.sqrt((Xw**2).sum(1)) + 1e-12)
df["PAI_vuln"] = PAI
df["rank_vuln"] = pd.Series(PAI).rank(ascending=False).astype(int)
print(f"\nPAI range {PAI.min():.4f}-{PAI.max():.4f} mean {PAI.mean():.4f}")

# ── K-means + Moran ────────────────────────────────────────────────────────────
lab = KMeans(N_ZONES, random_state=42, n_init=10).fit_predict(PAI.reshape(-1, 1))
zmean = [PAI[lab == z].mean() for z in range(N_ZONES)]
remap = {o: r+1 for r, o in enumerate(np.argsort(zmean)[::-1])}
df["zone_vuln"] = [remap[z] for z in lab]

adm2 = next(l for l in fiona.listlayers(str(GADM)) if l.endswith("_2"))
kh = gpd.read_file(str(GADM), layer=adm2)
kh = kh[kh["NAME_1"] == "Bangkok Metropolis"][["NAME_2", "geometry"]].to_crs("EPSG:4326")
gg = kh.merge(df[["NAME_2", "PAI_vuln"]], on="NAME_2")
try:
    from libpysal.weights import Queen
    from esda.moran import Moran
    W = Queen.from_dataframe(gg, use_index=False); W.transform = "r"
    mi = Moran(gg["PAI_vuln"].values, W, permutations=999)
    print(f"Moran's I = {mi.I:.4f} (p={mi.p_sim:.4f})")
except Exception as ex:
    print(f"Moran skipped: {ex}")

# ── ORTHOGONALITY TEST (the decisive check) ───────────────────────────────────
print("\n=== Equity orthogonality with VALID measure ===")
r_eq_pai, p_eq_pai = stats.spearmanr(df["C2_Equity_norm"], df["PAI_vuln"])
print(f"  Equity vs PAI(4-crit):  rho={r_eq_pai:+.3f} (p={p_eq_pai:.3f})  [mechanical if equity in PAI]")
r_eq_eff, p_eq_eff = stats.spearmanr(df["C2_Equity_norm"], df["PAI3"])
print(f"  Equity vs efficiency-only PAI3:  rho={r_eq_eff:+.3f} (p={p_eq_eff:.3f})  <-- true orthogonality test")
print("  Equity vs each efficiency criterion:")
for c, lab_ in [("C1_RooftopYield_norm","RooftopYield"),("C3_Demand_norm","Demand"),("C4_Infra_norm","Infra")]:
    rr, pp = stats.spearmanr(df["C2_Equity_norm"], df[c])
    print(f"    vs {lab_:12s} rho={rr:+.3f} (p={pp:.3f})")

# ── ranking shift vs efficiency-only ──────────────────────────────────────────
r_rank, _ = stats.spearmanr(df["PAI3"], df["PAI_vuln"])
maxshift = int((df["rank3"] - df["rank_vuln"]).abs().max())
print(f"\nRanking: 4-crit(equity) vs 3-crit(efficiency-only): rho={r_rank:.3f}, max shift={maxshift}")

print("\n=== Top 8 (equity model) with efficiency-only rank ===")
print(df.nsmallest(8, "rank_vuln")[["NAME_2","PAI_vuln","rank_vuln","rank3","C2_Equity_norm"]].to_string(index=False))

df.to_csv(BKKDIR / "bangkok_district_PAI_vuln.csv", index=False, encoding="utf-8-sig")
print(f"\nSaved -> bangkok_district_PAI_vuln.csv")
