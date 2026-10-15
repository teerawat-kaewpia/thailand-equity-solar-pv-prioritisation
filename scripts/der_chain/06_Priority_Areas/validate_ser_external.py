# -*- coding: utf-8 -*-
"""
Convergent external validation of the equity criterion against an INDEPENDENT
official index: the NESDC Thailand Provincial Socioeconomic & Financial
Resilience Index (SER, 2566-2567), which is built from data not used in our PAI.

Tests:
  (1) our C2 (poverty incidence) vs SER vulnerability score  -> should agree
  (2) our C2 vs SER poverty-burden proxy                      -> same concept
  (3) our composite PAI vs SER resilience / vulnerability     -> expected ~0
      (PAI is a DER deployment-priority index, not a socioeconomic ranking;
       orthogonality confirms the two measure different things and that the
       PAI top set has a defensible efficiency-equity dual character)

Output: DER/Data/14_Processed_90m/validation_ser_external.csv
"""
import pandas as pd, numpy as np, geopandas as gpd, fiona, unicodedata, warnings
from scipy import stats
warnings.filterwarnings("ignore")

BASE = r"D:\Clude Code GIS\Energy"
SER  = BASE + r"\Energy map\Thailand_Provincial_Socioeconomic_Resilience_Index_2566_2567\Thailand_Provincial_Index_2566_2567_GIS_v1.csv"
PROC = BASE + r"\DER\Data\14_Processed_90m"
GADM = BASE + r"\DER\Data\01_Admin_Boundaries\gadm41_THA.gpkg"

def norm(s):
    s = unicodedata.normalize("NFC", str(s)).strip()
    for p in ("จังหวัด", "อำเภอเมือง"):
        if s.startswith(p):
            s = s[len(p):].strip()
    return s

ser = pd.read_csv(SER, encoding="utf-8-sig")
ser["th"] = ser["province_th"].map(norm)
adm1 = next(l for l in fiona.listlayers(GADM) if l.endswith("_1"))
g = gpd.read_file(GADM, layer=adm1)[["NAME_1", "NL_NAME_1"]]
g["th"] = g["NL_NAME_1"].map(norm)

# GADM v4.1 mislabels two provinces' Thai names, which silently dropped Bangkok
# and Chaiyaphum (and cross-matched Chai Nat/Chiang Mai) and gave a spurious
# n = 75. Fix the two known errors so the Thai crosswalk is one-to-one:
#   Bangkok Metropolis: NL_NAME_1 = "จังหวัดเชียงใหม่"  -> should be กรุงเทพมหานคร
#   Chaiyaphum:         NL_NAME_1 = "จังหวัดชัยนาท"     -> should be ชัยภูมิ
GADM_TH_FIX = {"Bangkok Metropolis": "กรุงเทพมหานคร", "Chaiyaphum": "ชัยภูมิ"}
g["th"] = g.apply(lambda r: GADM_TH_FIX.get(r["NAME_1"], r["th"]), axis=1)
assert g["th"].nunique() == 77, "Thai crosswalk not one-to-one after fix"

th2en = dict(zip(g["th"], g["NAME_1"]))
ser["NAME_1"] = ser["th"].map(th2en)
assert ser["NAME_1"].notna().all(), \
    f"unmatched SER provinces: {ser.loc[ser['NAME_1'].isna(), 'province_th'].tolist()}"

pai = pd.read_csv(PROC + r"\province_PAI_summary.csv")[["NAME_1", "PAI", "rank", "C2"]]
m = pai.merge(ser[["NAME_1", "resilience_score_baseline", "vulnerability_score_baseline",
                   "poverty_burden_proxy_pct_2566"]], on="NAME_1", validate="one_to_one")
assert len(m) == 77, f"expected 77 provinces, got {len(m)}"
print(f"Provinces cross-matched with SER: {len(m)}")

def sp(a, b):
    r, p = stats.spearmanr(m[a], m[b])
    return r, p

rows = [
    ("our C2 (poverty) vs SER vulnerability", *sp("C2", "vulnerability_score_baseline")),
    ("our C2 (poverty) vs SER poverty proxy", *sp("C2", "poverty_burden_proxy_pct_2566")),
    ("our PAI vs SER resilience",             *sp("PAI", "resilience_score_baseline")),
    ("our PAI vs SER vulnerability",          *sp("PAI", "vulnerability_score_baseline")),
]
res = pd.DataFrame(rows, columns=["comparison", "spearman_rho", "p_value"])
res["spearman_rho"] = res["spearman_rho"].round(3)
res["p_value"] = res["p_value"].round(4)
res.to_csv(PROC + r"\validation_ser_external.csv", index=False, encoding="utf-8-sig")
print(res.to_string(index=False))
print(f"\nSaved: validation_ser_external.csv")
