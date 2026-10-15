"""C2 poverty input audit (2026-10-09).

The DER builder (DER\\Scripts\\02_Preprocessing\\build_c2_poverty_province.py) joins NESDC Table 1.5 to
GADM on the GADM Thai name NL_NAME_1. GADM 4.1 carries wrong Thai names for two provinces, so this
script re-joins on an independent Thai -> GADM English name dictionary (no GADM Thai names used),
then compares every province with the value the DER pipeline used.

Reads DER read-only. Writes DER_TEJ\\Data\\c2_fix\\C2_poverty_province_corrected.csv and an audit JSON.
"""
import json
import sys
import unicodedata
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import RAW, SRC, DER_ORIGINAL, out_path

E = RAW
XLSX = E / "Energy map" / "สถิติความยากจนและการกระจายรายได้_2567.xlsx"
DER_CSV = DER_ORIGINAL / "Data" / "14_Processed_90m" / "C2_poverty_province.csv"

# Thai province name (as in NESDC Table 1.5, NFC) -> GADM 4.1 NAME_1
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
SPELLING = {"สุราษฎ์ธานี": "สุราษฎร์ธานี", "กาฬสินธ์": "กาฬสินธุ์"}   # NESDC spellings (as in the DER builder)
EXCLUDE = {"รวม", "ในเขตเทศบาล", "นอกเขตเทศบาล", "ทั่วประเทศ"}
ORDER = [2565, 2566, 2564, 2567, 2563]   # DER imputation rule: 2022 first, then nearest year


def nfc(s):
    return unicodedata.normalize("NFC", str(s)).strip()


assert len(TH2EN) == 77 and len(set(TH2EN.values())) == 77
raw = pd.read_excel(XLSX, "1.5", header=None)
hdr = raw.iloc[2].tolist()
yc = {int(v): i for i, v in enumerate(hdr) if isinstance(v, (int, float)) and not pd.isna(v) and 2500 < v < 2600}
rows = []
for r in range(3, len(raw)):
    p = raw.iat[r, 1]
    if not isinstance(p, str) or p.strip() in EXCLUDE:
        continue
    th = SPELLING.get(nfc(p), nfc(p))
    if th not in TH2EN:
        continue                      # region subtotals
    vals = {y: (None if (raw.iat[r, yc[y]] == "-" or pd.isna(raw.iat[r, yc[y]])) else float(raw.iat[r, yc[y]])) for y in ORDER}
    used = next(y for y in ORDER if vals[y] is not None)
    rows.append({"NAME_1": TH2EN[th], "prov_th": th, "poverty_pct": vals[used], "year_used": used, "excel_row": r + 1})
new = pd.DataFrame(rows)
assert len(new) == 77 and new.NAME_1.is_unique and new.prov_th.is_unique, "independent join must be 1:1"
import geopandas as gpd
from _c2_checks import validate_c2
_g = gpd.read_file(SRC / "Data" / "01_Admin_Boundaries" / "gadm41_THA.gpkg", layer="ADM_ADM_1")
validate_c2(new, _g.NAME_1)                      # A4 test 2: stop on any join or range fault

old = pd.read_csv(DER_CSV)
cmp_ = new.merge(old[["NAME_1", "prov_th", "poverty_pct"]], on="NAME_1", suffixes=("", "_der"))
cmp_["diff"] = cmp_.poverty_pct - cmp_.poverty_pct_der
bad = cmp_[cmp_["diff"].abs() > 1e-9]
print(f"provinces 77 | differing from the DER input: {len(bad)}")
print(bad[["NAME_1", "prov_th_der", "poverty_pct_der", "prov_th", "poverty_pct", "year_used"]].to_string(index=False))

out = out_path("Data", "c2_fix", "C2_poverty_province_corrected.csv")
out.parent.mkdir(parents=True, exist_ok=True)
new.sort_values("NAME_1")[["NAME_1", "prov_th", "poverty_pct", "year_used", "excel_row"]].to_csv(out, index=False, encoding="utf-8-sig")
json.dump({"source": str(XLSX), "table": "1.5", "rule": "2565 (2022) first, then 2566, 2564, 2567, 2563",
           "n": 77, "n_differing": int(len(bad)),
           "differing": bad[["NAME_1", "prov_th_der", "poverty_pct_der", "prov_th", "poverty_pct", "year_used"]].to_dict("records"),
           "cause": "GADM 4.1 NL_NAME_1 is 'จังหวัดเชียงใหม่' for Bangkok Metropolis and 'จังหวัดชัยนาท' for Chaiyaphum; the DER builder joined on NL_NAME_1"},
          open(out.parent / "c2_audit.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("written:", out)
