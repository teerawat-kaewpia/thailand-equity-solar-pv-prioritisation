# Author-built indices: English guide

This folder holds two composite indices built by the authors from official statistics. Neither is an official published product. Both are research prototypes. Their full methodology files are in Thai, the authors' working language, and are kept unchanged. This guide summarises them in English and explains the Thai names and values in the data files. The summary follows the Thai methodology files and Supplementary Section S8 (Tables S8a and S8b).

| File | Language | Content |
|---|---|---|
| `Thailand_Provincial_Index_2566_2567_GIS_v1.csv` | Thai names, English column headers | Provincial index, 77 provinces |
| `Thailand_Provincial_Socioeconomic_Resilience_Index_2566_2567_Methodology.md` | Thai | Full provincial method |
| `BKK_District_Index_2567_GIS_v1.csv` | Thai names, English column headers | Bangkok district index, 50 khet |
| `BKK_District_Socioeconomic_Resilience_Index_2567_v1.xlsx` | Thai | Bangkok workbook (raw data, weights, scores) |
| `BKK_District_Socioeconomic_Resilience_Index_2567_Methodology.md` | Thai | Full Bangkok method |

Thai years are Buddhist Era (B.E.): B.E. 2566 = 2023, 2567 = 2024.

## How the paper uses them

- **Bangkok district index:** only the vulnerability sub-index FV is used, as the equity criterion of the district demonstration (Supplementary Section S12). It is matched to districts by the English names in `data/bangkok/C2_vulnerability_district.csv`.
- **Provincial index:** FV and the overall score SER are compared with the paper's index as an external construct check (Supplementary Table S13f). Neither enters the Priority Area Index.

## Method summary (both indices)

- Two dimensions: economic capacity EC and vulnerability FV, each 0–100.
- Overall score: SER = 0.50·EC + 0.50·(100 − FV), so lower vulnerability raises the score.
- Each raw indicator is converted to a percentile rank within its unit set, S = (rank − 1) / (N − 1) × 100, with N = 77 provinces or 50 districts. Indicators where a lower value means more vulnerability are reverse-ranked.
- Right-skewed monetary inputs (registered capital) are Winsorised at the 95th percentile before ranking.
- Classes are fixed score bands: very high 80–100, high 60 to below 80, medium 40 to below 60, low 20 to below 40, very low below 20.

### Provincial index (reference period 2566–2567, v1.0 weighted baseline model)

| Code | Indicator | Weight within dimension |
|---|---|---|
| E1 | Gross provincial product per capita (NESDC, 2567) | 0.25 |
| E2 | Mean monthly household income (NSO, 2566) | 0.20 |
| E3 | Section 33 insured persons per 1,000 population (Social Security Office, 2567) | 0.20 |
| E4 | Newly registered juristic persons per 10,000 population (Department of Business Development, 2567) | 0.15 |
| E5 | Registered capital of new businesses per person, Winsorised at P95 (DBD, 2567) | 0.10 |
| E6 | Diversity of new businesses, normalised Shannon entropy of business categories (DBD, 2567) | 0.10 |
| V1 | Poverty burden proxy: estimated poor headcount / registered population × 100 (NESDC/NSO, DOPA, 2566) | 0.35 |
| V2 | Household expenditure / income × 100 (NSO, 2566) | 0.25 |
| V3 | Household debt / annual income (NSO, 2566) | 0.25 |
| V4 | Registered population change 2566–2567, reverse-ranked (DOPA) | 0.15 |

V1 is a proxy, not the official poverty rate. The paper's equity criterion C2 uses the official NESDC poverty incidence instead (Table 2 of the manuscript).

### Bangkok district index (base year 2567, v1.0 equal-weight baseline model)

| Code | Indicator | Weight within dimension |
|---|---|---|
| E1 | Newly registered juristic persons per 1,000 houses (DBD, 2567) | 0.25 |
| E2 | Registered capital per house, Winsorised at P95 (DBD, 2567) | 0.25 |
| E3 | Diversity of new businesses, normalised Shannon entropy (DBD, 2567) | 0.25 |
| E4 | Houses per km² (BMA, 2567) | 0.25 |
| V1 | Slum communities / all communities × 100 (BMA, 2567) | 0.25 |
| V2 | Registered population per house (BMA, 2567) | 0.25 |
| V3 | Green area per person, reverse-ranked (BMA, 2567) | 0.25 |
| V4 | Disaster incidents per 10,000 houses (BMA, 2567) | 0.25 |

Sources: BMA = Bangkok Metropolitan Administration, Bangkok Statistics 2567. DBD = Department of Business Development, newly registered juristic persons open data, January to December 2567. NESDC = Office of the National Economic and Social Development Council. NSO = National Statistical Office. DOPA = Department of Provincial Administration (registered population).

## Column dictionary

`Thailand_Provincial_Index_2566_2567_GIS_v1.csv`

| Column | Meaning |
|---|---|
| `province_th` | Province name in Thai |
| `province_join_name` | Thai name used to join to boundaries (English names in the crosswalk below) |
| `region_nso` | NSO region, Thai label (glossary below) |
| `rank_baseline` | Rank by overall score SER, 1 = highest |
| `resilience_score_baseline` | Overall score SER, 0–100 |
| `economic_score_baseline` | Economic capacity EC, 0–100 |
| `vulnerability_score_baseline` | Vulnerability FV, 0–100 |
| `class_baseline` | SER class, Thai label (glossary below) |
| `gpp_per_capita_2567` | Gross provincial product per capita, THB, 2567 |
| `household_income_monthly_2566` | Mean monthly household income, THB, 2566 |
| `poverty_burden_proxy_pct_2566` | Indicator V1, %, 2566 |

`BKK_District_Index_2567_GIS_v1.csv`

| Column | Meaning |
|---|---|
| `district_th` | District (khet) name in Thai |
| `district_join_name` | Thai name with the prefix เขต (khet), used to join to boundaries |
| `rank_baseline` | Rank by overall score SER, 1 = highest |
| `resilience_score_baseline` | Overall score SER, 0–100 |
| `economic_score_baseline` | Economic capacity EC, 0–100 |
| `vulnerability_score_baseline` | Vulnerability FV, 0–100 (the value the paper uses) |
| `class_baseline` | SER class, Thai label (glossary below) |

## Glossary of Thai values

| Thai | English |
|---|---|
| สูงมาก | Very high (80–100) |
| สูง | High (60 to below 80) |
| ปานกลาง | Medium (40 to below 60) |
| ต่ำ | Low (20 to below 40) |
| ต่ำมาก | Very low (below 20) |
| กรุงเทพมหานคร | Bangkok |
| ภาคกลาง | Central |
| ภาคตะวันออกเฉียงเหนือ | Northeast |
| ภาคเหนือ | North |
| ภาคใต้ | South |

## Crosswalk: provinces (77)

English names are the GADM 4.1 names used throughout the paper and in `data/province/`. Pairs are taken from the corrected poverty table (amendment A4).

| Thai | English |
|---|---|
| กระบี่ | Krabi |
| กรุงเทพมหานคร | Bangkok Metropolis |
| กาญจนบุรี | Kanchanaburi |
| กาฬสินธุ์ | Kalasin |
| กำแพงเพชร | Kamphaeng Phet |
| ขอนแก่น | Khon Kaen |
| จันทบุรี | Chanthaburi |
| ฉะเชิงเทรา | Chachoengsao |
| ชลบุรี | Chon Buri |
| ชัยนาท | Chai Nat |
| ชัยภูมิ | Chaiyaphum |
| ชุมพร | Chumphon |
| ตรัง | Trang |
| ตราด | Trat |
| ตาก | Tak |
| นครนายก | Nakhon Nayok |
| นครปฐม | Nakhon Pathom |
| นครพนม | Nakhon Phanom |
| นครราชสีมา | Nakhon Ratchasima |
| นครศรีธรรมราช | Nakhon Si Thammarat |
| นครสวรรค์ | Nakhon Sawan |
| นนทบุรี | Nonthaburi |
| นราธิวาส | Narathiwat |
| น่าน | Nan |
| บึงกาฬ | Bueng Kan |
| บุรีรัมย์ | Buri Ram |
| ปทุมธานี | Pathum Thani |
| ประจวบคีรีขันธ์ | Prachuap Khiri Khan |
| ปราจีนบุรี | Prachin Buri |
| ปัตตานี | Pattani |
| พระนครศรีอยุธยา | Phra Nakhon Si Ayutthaya |
| พะเยา | Phayao |
| พังงา | Phangnga |
| พัทลุง | Phatthalung |
| พิจิตร | Phichit |
| พิษณุโลก | Phitsanulok |
| ภูเก็ต | Phuket |
| มหาสารคาม | Maha Sarakham |
| มุกดาหาร | Mukdahan |
| ยะลา | Yala |
| ยโสธร | Yasothon |
| ระนอง | Ranong |
| ระยอง | Rayong |
| ราชบุรี | Ratchaburi |
| ร้อยเอ็ด | Roi Et |
| ลพบุรี | Lop Buri |
| ลำปาง | Lampang |
| ลำพูน | Lamphun |
| ศรีสะเกษ | Si Sa Ket |
| สกลนคร | Sakon Nakhon |
| สงขลา | Songkhla |
| สตูล | Satun |
| สมุทรปราการ | Samut Prakan |
| สมุทรสงคราม | Samut Songkhram |
| สมุทรสาคร | Samut Sakhon |
| สระบุรี | Saraburi |
| สระแก้ว | Sa Kaeo |
| สิงห์บุรี | Sing Buri |
| สุพรรณบุรี | Suphan Buri |
| สุราษฎร์ธานี | Surat Thani |
| สุรินทร์ | Surin |
| สุโขทัย | Sukhothai |
| หนองคาย | Nong Khai |
| หนองบัวลำภู | Nong Bua Lam Phu |
| อำนาจเจริญ | Amnat Charoen |
| อุดรธานี | Udon Thani |
| อุตรดิตถ์ | Uttaradit |
| อุทัยธานี | Uthai Thani |
| อุบลราชธานี | Ubon Ratchathani |
| อ่างทอง | Ang Thong |
| เชียงราย | Chiang Rai |
| เชียงใหม่ | Chiang Mai |
| เพชรบุรี | Phetchaburi |
| เพชรบูรณ์ | Phetchabun |
| เลย | Loei |
| แพร่ | Phrae |
| แม่ฮ่องสอน | Mae Hong Son |

## Crosswalk: Bangkok districts (50)

English names are the GADM 4.1 level-2 names used in `data/bangkok/`. Four Thai names are matched by a fixed rule because GADM spells them differently (ทวีวัฒนา, ธนบุรี, บางกะปิ, หลักสี่).

| Thai | English |
|---|---|
| คลองสาน | Khlong San |
| คลองสามวา | Khlong Sam Wa |
| คลองเตย | Khlong Toey |
| คันนายาว | Khan Na Yao |
| จตุจักร | Chatuchak |
| จอมทอง | Chom Thong |
| ดอนเมือง | Don Muang |
| ดินแดง | Din Dang |
| ดุสิต | Dusit |
| ตลิ่งชัน | Taling Chan |
| ทวีวัฒนา | Thawi Wattana |
| ทุ่งครุ | Thungkru |
| ธนบุรี | Thon Buri |
| บางกอกน้อย | Bangkok Noi |
| บางกอกใหญ่ | Bangkok Yai |
| บางกะปิ | Bang Kapi |
| บางขุนเทียน | Bangkhuntien |
| บางคอแหลม | Bang Kho Laem |
| บางซื่อ | Bang Su |
| บางนา | Bang Na |
| บางบอน | Bang Bon |
| บางพลัด | Bang Plad |
| บางรัก | Bang Rak |
| บางเขน | Bang Khen |
| บางแค | Bang Khae |
| บึงกุ่ม | Bung Kum |
| ปทุมวัน | Pathum Wan |
| ประเวศ | Prawet |
| ป้อมปราบศัตรูพ่าย | Pom Pram Sattru |
| พญาไท | Phaya Thai |
| พระนคร | Phra Nakhon |
| พระโขนง | Prakanong |
| ภาษีเจริญ | Phasi Charoen |
| มีนบุรี | Min Buri |
| ยานนาวา | Yannawa |
| ราชเทวี | Ratchathewi |
| ราษฎร์บูรณะ | Rat Burana |
| ลาดกระบัง | Lat Krabang |
| ลาดพร้าว | Lat Phrao |
| วังทองหลาง | Wang Thonglang |
| วัฒนา | Wattana |
| สวนหลวง | Suan Luang |
| สะพานสูง | Saphan Sung |
| สัมพันธวงศ์ | Samphantawong |
| สาทร | Sathorn |
| สายไหม | Sai Mai |
| หนองจอก | Nong Chok |
| หนองแขม | Nongkheam |
| หลักสี่ | Lak Si |
| ห้วยขวาง | Huai Kwang |
