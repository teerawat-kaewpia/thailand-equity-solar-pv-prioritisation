# -*- coding: utf-8 -*-
"""
Build a VALID province equity criterion from official poverty incidence,
replacing inverted NTL/capita (which measures emitted light / land use, not
household affordability).

Source: NESDC "สถิติความยากจนและการกระจายรายได้ 2567", Table 1.5
        = สัดส่วนคนจน (poverty incidence, % of population with per-capita
        consumption expenditure below the poverty line) by province, from the
        NSO Household Socio-Economic Survey (SES).

Joins to GADM ADM1 on the Thai native name (NL_NAME_1). Reports any name
mismatches for manual fixing. Missing values ("-", insufficient sample -> very
low poverty in wealthy provinces) are imputed from the nearest available year.

Output: DER/Data/14_Processed_90m/C2_poverty_province.csv
"""
import pandas as pd
import numpy as np
import geopandas as gpd
import fiona
import unicodedata
from pathlib import Path
import os

def norm_th(s):
    """NFC-normalise and strip GADM 'จังหวัด'/'อำเภอเมือง' prefixes + whitespace."""
    s = unicodedata.normalize("NFC", str(s)).strip()
    for pre in ("จังหวัด", "อำเภอเมือง"):
        if s.startswith(pre):
            s = s[len(pre):].strip()
    return s

BASE = Path(os.environ.get("ENERGY_DATA_ROOT", r"D:\Clude Code GIS\Energy"))  # raw data (Tier-2), override via env
XLSX = BASE / "Energy map" / "สถิติความยากจนและการกระจายรายได้_2567.xlsx"
GADM = BASE / "DER" / "Data" / "01_Admin_Boundaries" / "gadm41_THA.gpkg"
OUT  = BASE / "DER" / "Data" / "14_Processed_90m" / "C2_poverty_province.csv"

# manual Thai-name reconciliation (poverty-file spelling -> GADM NL_NAME_1)
THAI_FIX = {
    "สุราษฎ์ธานี": "สุราษฎร์ธานี",
    "กาฬสินธ์": "กาฬสินธุ์",
    "หนองบัวลำภู": "หนองบัวลำภู",
    "พระนครศรีอยุธยา": "พระนครศรีอยุธยา",
}

# ── read poverty table 1.5 ─────────────────────────────────────────────────────
raw = pd.read_excel(XLSX, "1.5", header=None)
hdr = raw.iloc[2].tolist()
year_cols = {int(v): i for i, v in enumerate(hdr)
             if isinstance(v, (int, float)) and not pd.isna(v) and 2500 < v < 2600}
KEEP_YEARS = [2563, 2564, 2565, 2566, 2567]   # 2020-2024 CE

EXCLUDE = {"รวม", "ในเขตเทศบาล", "นอกเขตเทศบาล", "ทั่วประเทศ"}
rows = []
for r in range(3, len(raw)):
    prov = raw.iat[r, 1]
    if not isinstance(prov, str) or prov.strip() in EXCLUDE:
        continue
    prov = norm_th(prov)
    rec = {"prov_th": norm_th(THAI_FIX.get(prov, prov))}
    for y in KEEP_YEARS:
        v = raw.iat[r, year_cols[y]]
        rec[y] = np.nan if (v == "-" or pd.isna(v)) else float(v)
    rows.append(rec)
pov = pd.DataFrame(rows)
print(f"Provinces parsed: {len(pov)}")

# ── impute missing from nearest available year (row-wise) ─────────────────────
def impute_row(row):
    vals = {y: row[y] for y in KEEP_YEARS}
    # primary year 2565 (2022, matches NTL); fall back outward
    order = [2565, 2566, 2564, 2567, 2563]
    for y in order:
        if not pd.isna(vals[y]):
            return vals[y]
    return np.nan
pov["poverty_pct"] = pov.apply(impute_row, axis=1)
# A5: keep the edition year actually used for each province (provenance for the C2 raster tags)
pov["year_used"] = pov.apply(lambda r: next((y for y in [2565, 2566, 2564, 2567, 2563]
                                             if not pd.isna(r[y])), np.nan), axis=1)
n_missing_primary = pov[2565].isna().sum()
print(f"  provinces with 2565 missing (imputed from nearest year): {n_missing_primary}")

# ── join to GADM on Thai name ──────────────────────────────────────────────────
# CORRECTION 2026-10-09: GADM 4.1 NL_NAME_1 is wrong for two provinces (Bangkok Metropolis carries
# "จังหวัดเชียงใหม่", Chaiyaphum carries "จังหวัดชัยนาท"), so joining on it gave Bangkok the Chiang Mai
# value and Chaiyaphum the Chai Nat value. Join on an explicit Thai -> GADM English dictionary instead.
TH2EN = {
    "กรุงเทพมหานคร": "Bangkok Metropolis", "สมุทรปราการ": "Samut Prakan", "นนทบุรี": "Nonthaburi",
    "ปทุมธานี": "Pathum Thani", "พระนครศรีอยุธยา": "Phra Nakhon Si Ayutthaya", "อ่างทอง": "Ang Thong",
    "ลพบุรี": "Lop Buri", "สิงห์บุรี": "Sing Buri", "ชัยนาท": "Chai Nat", "สระบุรี": "Saraburi",
    "ชลบุรี": "Chon Buri", "ระยอง": "Rayong", "จันทบุรี": "Chanthaburi", "ตราด": "Trat",
    "ฉะเชิงเทรา": "Chachoengsao", "ปราจีนบุรี": "Prachin Buri", "นครนายก": "Nakhon Nayok",
    "สระแก้ว": "Sa Kaeo", "นครราชสีมา": "Nakhon Ratchasima", "บุรีรัมย์": "Buri Ram", "สุรินทร์": "Surin",
    "ศรีสะเกษ": "Si Sa Ket", "อุบลราชธานี": "Ubon Ratchathani", "ยโสธร": "Yasothon", "ชัยภูมิ": "Chaiyaphum",
    "อำนาจเจริญ": "Amnat Charoen", "บึงกาฬ": "Bueng Kan", "หนองบัวลำภู": "Nong Bua Lam Phu",
    "ขอนแก่น": "Khon Kaen", "อุดรธานี": "Udon Thani", "เลย": "Loei", "หนองคาย": "Nong Khai",
    "มหาสารคาม": "Maha Sarakham", "ร้อยเอ็ด": "Roi Et", "กาฬสินธุ์": "Kalasin", "สกลนคร": "Sakon Nakhon",
    "นครพนม": "Nakhon Phanom", "มุกดาหาร": "Mukdahan", "เชียงใหม่": "Chiang Mai", "ลำพูน": "Lamphun",
    "ลำปาง": "Lampang", "อุตรดิตถ์": "Uttaradit", "แพร่": "Phrae", "น่าน": "Nan", "พะเยา": "Phayao",
    "เชียงราย": "Chiang Rai", "แม่ฮ่องสอน": "Mae Hong Son", "นครสวรรค์": "Nakhon Sawan",
    "อุทัยธานี": "Uthai Thani", "กำแพงเพชร": "Kamphaeng Phet", "ตาก": "Tak", "สุโขทัย": "Sukhothai",
    "พิษณุโลก": "Phitsanulok", "พิจิตร": "Phichit", "เพชรบูรณ์": "Phetchabun", "ราชบุรี": "Ratchaburi",
    "กาญจนบุรี": "Kanchanaburi", "สุพรรณบุรี": "Suphan Buri", "นครปฐม": "Nakhon Pathom",
    "สมุทรสาคร": "Samut Sakhon", "สมุทรสงคราม": "Samut Songkhram", "เพชรบุรี": "Phetchaburi",
    "ประจวบคีรีขันธ์": "Prachuap Khiri Khan", "นครศรีธรรมราช": "Nakhon Si Thammarat", "กระบี่": "Krabi",
    "พังงา": "Phangnga", "ภูเก็ต": "Phuket", "สุราษฎร์ธานี": "Surat Thani", "ระนอง": "Ranong",
    "ชุมพร": "Chumphon", "สงขลา": "Songkhla", "สตูล": "Satun", "ตรัง": "Trang", "พัทลุง": "Phatthalung",
    "ปัตตานี": "Pattani", "ยะลา": "Yala", "นราธิวาส": "Narathiwat",
}
assert len(TH2EN) == 77 and len(set(TH2EN.values())) == 77
adm1 = next(l for l in fiona.listlayers(str(GADM)) if l.endswith("_1"))
g = gpd.read_file(str(GADM), layer=adm1)[["NAME_1"]].copy()
EN2TH = {v: k for k, v in TH2EN.items()}
g["nl"] = g["NAME_1"].map(EN2TH)
assert g["nl"].notna().all() and g["nl"].is_unique, "every GADM province needs one Thai name"

merged = g.merge(pov, left_on="nl", right_on="prov_th", how="left")
unmatched_gadm = merged[merged["poverty_pct"].isna()]
unmatched_pov  = set(pov["prov_th"]) - set(g["nl"])

# write Thai diagnostics to UTF-8 file (never print Thai to cp1252 console)
diag = []
diag.append(f"GADM provinces without poverty match: {len(unmatched_gadm)}")
for _, r in unmatched_gadm.iterrows():
    diag.append(f"  GADM: {r['NAME_1']} / nl={r['nl']}")
diag.append(f"Poverty names not found in GADM: {len(unmatched_pov)}")
for nm in sorted(unmatched_pov):
    diag.append(f"  POV: {nm}")
(OUT.parent / "C2_poverty_join_diagnostics.txt").write_text(
    "\n".join(diag), encoding="utf-8")
print(f"GADM without match: {len(unmatched_gadm)} | POV not in GADM: {len(unmatched_pov)} "
      f"(details -> C2_poverty_join_diagnostics.txt)")

# ── save ───────────────────────────────────────────────────────────────────────
final = merged[["NAME_1", "nl", "poverty_pct", "year_used"]].copy()
final.columns = ["NAME_1", "prov_th", "poverty_pct", "year_used"]
final["year_used"] = final["year_used"].astype(int)
# CORRECTION 2026-10-10: stop on any join or range fault instead of writing a bad table
assert len(unmatched_gadm) == 0, f"GADM provinces without a poverty value: {unmatched_gadm['NAME_1'].tolist()}"
assert len(final) == 77 and final["NAME_1"].is_unique and final["prov_th"].is_unique, \
    "C2 join must be one-to-one over the 77 provinces"
_v = pd.to_numeric(final["poverty_pct"], errors="coerce")
assert _v.notna().all() and _v.between(0, 100).all(), "poverty_pct missing or outside 0-100"
final.to_csv(OUT, index=False, encoding="utf-8-sig")
print(f"\nMatched {final['poverty_pct'].notna().sum()}/77 provinces")
print(f"poverty_pct range: {final['poverty_pct'].min():.2f} - {final['poverty_pct'].max():.2f}  "
      f"(mean {final['poverty_pct'].mean():.2f})")
print(f"Saved: {OUT}")
