# Scenario and screening protocol (pre-declared)

Status: LOCKED before any scenario, screening-class or linkage result is computed. The SHA-256 of this file is recorded in `Docs\PROTOCOL_LOCK.txt`. Any later change is made as a dated amendment at the end of this file. The text above the amendments is never edited.

Decisions agreed with the user on 2026-10-06. Workspace: `DER_TEJ`. Inputs from `..\DER` are read-only.

---

## 1. Policy scenarios (S)

### 1.1 Common budget
- One national programme budget **B**, expressed in abstract support units (B = 1,000,000 units). It is identical in S1, S2 and S3. Results are reported as shares or as allocation-weighted metrics, so the value of B does not affect them.

### 1.2 Allocation rules
Population P_i is the province total from WorldPop 2020 unconstrained UN-adjusted (the same product as C3), using a zonal sum over GADM 4.1 level 1. Of the 77 provinces:

| Scenario | Eligible set | Allocation within the set |
|---|---|---|
| S1 Uniform support | all 77 provinces | b_i = B · P_i / Σ P |
| S2 Equity-targeted support | the top **K = 15** provinces by full PAI (published v2 values) | b_i = B · P_i / Σ_{eligible} P |
| S3 Resource-and-infrastructure-oriented comparator | the top **K = 15** provinces by the efficiency-only composite (C1, C3, C4, C5 re-weighted by EWM, as in v2 §4.2) | b_i = B · P_i / Σ_{eligible} P |

- K = 15 (19.5% of 77) is fixed. Zone 1 (6 provinces) is descriptive context only and never sets a budget.
- S3 is described as a "resource-and-infrastructure-oriented comparator". It is NOT described as a proxy for "the market" unless official deployment data (D1/D2) are later added and show that association.
- Ties at rank 15: include both tied provinces and report it. None is expected (PAI has 4 decimals).

### 1.3 Outcome metrics (allocation-weighted, in physical units)
For each scenario, with weights w_i = b_i / B:
1. **Poverty-weighted beneficiary equivalents** = Σ b_i · poverty_i / 100 (poverty incidence %, NESDC Table 1.5, the same source as C2). This is NEVER described as the number of people who actually receive support.
2. Allocation-weighted mean poverty incidence (%).
3. Allocation-weighted mean PVOUT (kWh/kWp/yr): province mean of the Global Solar Atlas PVOUT raster, raw units.
4. Allocation-weighted **median** distance to transmission (km): province mean of the C4 distance raster.
5. Allocation-weighted **median** distance to the predicted MV network (km): province mean of the GridFinder MV distance.
6. Share of B going to provinces in each MV-proximity class (Section 2).
7. Number of provinces and number of regions reached.

The OSM installation counts are NOT a scenario outcome, because they do not meet the D1/D2 criteria. If an official deployment dataset passes D1/D2, it may be added only through a dated amendment written before it is computed.

### 1.4 Reporting rule
- Report one trade-off table: scenarios as rows, metrics as columns. Do not declare a "best" scenario.
- State that S2 covers more poverty by construction, because poverty is its own selection criterion. The informative quantities are the differences in metrics 3–5 and 6, meaning what is traded for that coverage.
- Optional (one figure only, not a new sensitivity family): the coverage curve of metric 1 against K = 5…30 for S2 and S3. The main text uses only K = 15.

---

## 2. MV-proximity screening classes (P)

- Variable: province mean distance to the GridFinder predicted MV network (km), the same input as v2 §4.4 and Table S9.
- Classes: Jenks natural breaks, k = 3, labelled **nearer / intermediate / farther**. Computed once on all 77 provinces. Class breaks are reported.
- Every class carries the same statement: *"Hosting capacity and connection feasibility are not assessable from the available data and require utility feeder-level verification."*
- The words feasibility, ready, connectable and reinforcement-needed are not used as labels.

---

## 3. PEA Power Map (generation side): linkage and gates

Source: PEA public Feature Service `NEW_TPM_Geodatabase_gdb` (modified 2026-08-21, years 2569/2570), downloaded 2026-10-06 to `Data\PEA_PowerMap_Gen\`. PEA labels it "for preliminary reference only".

### 3.1 Layer reconciliation (completed before locking, findings recorded here)
Done on the downloaded files, year 2569:
- L3 (`Check_Station_PEA_FULL`) has 701 records, 686 unique `pea_subname`, 15 duplicated names (30 records), sum of `available_..._pea_mw` = 15,478.3 MW, and 180 records ≤ 0 MW.
- L1 (`Gen_115_2233_LineArea`) has 187 polygons, sum 4,493.8 MW, and 40 polygons ≤ 0 MW.
- **All 187 L1 records match an L3 record exactly (same name and same MW).** L1 is therefore the subset of L3 records that have a service-area polygon. It is not a different unit.
- Duplicated names are distinct transformer records at the same substation (for example ขอนแก่น 1: TP and KT records).
- **Non-additivity evidence:** each record also carries `available_egat_zone_mw`, which has a single value per EGAT zone (62 zones). In 43 of 62 EGAT zones, the sum of positive PEA-record MW exceeds the EGAT-zone available MW (for example ZC07: 1,286.0 MW across 31 records against 90 MW upstream). Record-level MW values share an upstream constraint.

**Rule (binding):** PEA MW values are NOT summed, averaged or otherwise aggregated to province or any other area. No "MW by province" is produced. This holds unless PEA documentation, obtained later and added by amendment, states that the values are additive.

### 3.2 Linkage method (a): name-to-OSM matching
Target: OSM substations (`Energy map\GridNetwork_OSM\substations.geojson`, Overpass 2026-06-22).
1. Normalise names on both sides: Unicode NFC, Thai digits converted to Arabic digits, removal of the prefixes "สถานีไฟฟ้า", "สถานีไฟฟ้าย่อย", "สฟ.", "สถานีไฟฟ้าแรงสูง", "PEA" and the suffix "substation", removal of whitespace and punctuation, case-folding for Latin text. OSM `name`, `name:th`, `name:en`, `short_name` and `ref` are all candidates. L3 `pea_subname` is matched to Thai names, and `egat_subname_eng` is not used for PEA names.
2. Exact match: a normalised name equal to exactly one OSM feature gives a match.
3. Fuzzy match: allowed only when the similarity is ≥ 0.92 (rapidfuzz ratio), the best match leads the second-best by ≥ 0.05, and the OSM feature lies inside a province served by the record's `pea_zone`. Province–zone membership comes from the PEA zone structure. If that cannot be established from an official source, fuzzy matching is not used.
4. One-to-one only: an OSM feature matched by more than one L3 substation name puts all of those names in `ambiguous`. Transformer records with the same `pea_subname` share one substation location, so this is not a conflict.
5. Unmatched and ambiguous records go to `unresolved` and are never imputed.
6. Manual audit (recorded in `Docs\PEA_LINKAGE_AUDIT.md`): every record ≤ 0 MW, every record in the top decile of MW, and a random 10% sample of the rest (seed 20261006). A match the audit rejects becomes `unresolved`.

### 3.3 Pass gates (all must hold, computed after the audit)
- ≥ 80% of L3 2569 records matched.
- Matched substations lie in ≥ 70 of the 74 PEA-served provinces.
- ≥ 90% of Σ|MW| of L3 2569 records belongs to matched records. Absolute values are used because MW is never summed as capacity, and this is only a coverage weight.
- In each of the 12 PEA zones, ≥ 75% of that zone's Σ|MW| belongs to matched records.
- Matched, unmatched and ambiguous counts are reported by PEA zone whether or not the gates pass.

### 3.4 Use if the gates pass
- Layer name: **"PEA-reported remaining generation capacity at matched substations"**.
- Because of 3.1, the only province-level descriptor allowed is a count-based one: the **share of matched substation records reporting ≤ 0 MW** remaining generation capacity in the province. This needs user approval by amendment before it is computed. Jenks classes on any PEA-derived variable are built only after that approval.
- Words not used: hosting capacity, connection feasibility, ready, reinforcement needed.

### 3.5 If the gates fail
- Fallback (b), area-weighted overlapping polygons, is NOT used.
- PEA data are used only as (i) institutional and qualitative policy evidence: PEA publishes record-level remaining generation capacity, 180 of 701 records reported ≤ 0 MW in 2569, and the values share upstream EGAT-zone constraints. This supports the "utility verification gate" argument. (ii) Optionally, a PEA-zone-level description (12 zones) of the share of records ≤ 0 MW. This is a count, never MW sums.
- The provincial screening layer for the scenarios stays the MV-proximity classes of Section 2.

---

## Amendments

### A1 (2026-10-06): linkage unit and diagnostics. MADE AFTER THE FIRST LINKAGE RUN WAS SEEN
Disclosure: the first exact-stage run (records 25.4%, provinces 61/74, |MW| 27.3%, zones 0/12, FAIL) had already been computed when this amendment was written. A1 changes no threshold. It changes only the counting unit and adds diagnostics, following the reviewer's specification (2026-10-06). The run-1 result stays on file (`linkage_result_run1.json`).

1. **Matching unit = the 686 unique normalised `pea_subname` values** in L3 2569, not the 701 records. Before matching, the 15 duplicated names are resolved by cause (same station with multiple transformer records, or the same name under different EGAT supply points) and listed in the output.
2. Candidates = all OSM `power=substation` features with any name (`name`, `name:th`, `name:en`, `short_name`, `ref`). Operator does not restrict candidates.
3. Primary key = normalised station name. `pea_prefix`, `pea_zone`, the province from the OSM location and the OSM operator are corroborating evidence only.
4. Exact unique match first. The fuzzy stage stays as in 3.2(3) (locked thresholds, a zone–province consistency check, manual audit). With no official zone–province source in hand, it remains disabled.
5. One PEA station to one OSM feature. An OSM feature claimed by more than one station makes all of those stations `ambiguous`. This was already implemented.
6. Gates (thresholds unchanged): ≥ 80% of the **686 stations** matched, ≥ 70/74 PEA provinces, ≥ 90% of Σ|MW| over all 701 records (a record inherits its station's status), and ≥ 75% Σ|MW| coverage in each of the 12 PEA zones. The record-level match rate is also reported.
7. Diagnostics only (not pass/fail): the match rate among OSM features with an operator tag containing PEA/กฟภ./การไฟฟ้าส่วนภูมิภาค, the number of OSM candidates with a Thai-script name, and match, ambiguous and unmatched counts by PEA zone.
8. If the gates fail, protocol 3.5 applies unchanged. No provincial capacity indicator is built from PEA data.

### A2 (2026-10-08): scope alignment to the PEA service area. MADE AFTER SCENARIO RUN 1 WAS SEEN
Disclosure: run 1 (`Docs\SCENARIO_RUN_LOG.md`) had been computed. In it Bangkok Metropolis (PAI rank 14) took 58.4% of B in S2. Approved by the user on 2026-10-08.
Rationale (recorded as the user stated it): the primary decision context had already been set as the PEA service area. The PEA remaining-capacity data cover PEA only. The Bangkok/MEA analysis had been moved to the Supplementary before any scenario result existed. This is a scope-alignment amendment, not an outcome-driven exclusion.
1. Bangkok Metropolis, Nonthaburi and Samut Prakan (MEA service area) are excluded from S1, S2, S3 and from the screening classes. The analysis set is the **74 PEA-served provinces**.
2. K = 15 is unchanged: **15 of 74 = 20.3%** of units. Rankings for S2 (PAI) and S3 (efficiency-only composite) are the published 77-province scores, with the 3 MEA provinces removed before taking the top 15. Nothing is re-weighted.
3. S1 is renamed **"S1 Population-proportional baseline"** (allocation over all 74 by population). The label "Uniform" is withdrawn.
4. The new denominators are reported: 74 provinces, PEA-area population (WorldPop sum over the 74), and K = 15 of 74.
5. The Section 2 Jenks classes are computed on the 74 provinces (not 77).
6. All other rules of Section 1 are unchanged.

### A3 (2026-10-08): MV variable redefinition. WRITTEN BEFORE ANY MV RESULT WAS COMPUTED
Finding: the variable in Section 2 ("the same input as v2 §4.4 and Table S9") is not one input. v2 §4.4 values come from `gridfinder_distance.json`, which has no producing script and cannot be audited. Table S9 uses `C5_grid_access_90m.tif`, which is a GridFinder **LV-density** index, not MV and not a distance. Approved by the user on 2026-10-08. The claim "the same MV input as v2" is withdrawn and must not appear in the TEJ manuscript.
1. Variable: **"Province mean distance to GridFinder modelled MV lines (km)"**. GridFinder is always called the *modelled MV network*, never the official PEA network.
2. Source: `Energy map\GridFinder_Thailand\gridfinder_mv_lines_thailand.gpkg` (36,027 features, EPSG:4326, file date 2026-06-23). Its SHA-256 is recorded in the QA output.
3. Analysis grid: a new 90 m grid in **EPSG:32647 (WGS 84 / UTM 47N)** covering the GADM 4.1 country extent. Valid cells are those whose cell centre lies inside the union of the 77 GADM 4.1 level-1 polygons (rasterize all_touched = False). Distances are computed in metres in the projected CRS, so the 0.09 km-per-degree-pixel approximation of the v2 C4 raster is avoided. The UTM 47N scale error for the eastern provinces (zone 48 longitudes) is reported in QA.
4. MV lines are reprojected to EPSG:32647 and rasterised with all_touched = True. Distance = Euclidean distance transform × 90 m, from each valid cell to the nearest line cell. Lines outside Thailand are kept, so border cells can be near a line across the border. Cells outside the mask are nodata (−9999).
5. Aggregation: province **mean** of valid cells is the scenario variable. The province median is reported as a descriptive statistic. The number of valid cells per province is reported.
6. Outputs (all in `DER_TEJ\Data\mv_distance\`): the distance raster (GeoTIFF, float32, km), the province table (77 rows; the 74 PEA rows are used), and a QA summary (input hash, CRS, grid size, % of cells within 1, 5 and 10 km, maximum, per-province cell counts, and Spearman ρ against the C4 line distance).
7. Use: a policy-screening and descriptive infrastructure indicator only (metrics 5–6 and the Section 2 classes). It is not a hosting-capacity or connection-feasibility claim.

### Legacy files (recorded 2026-10-08)
`DER\Data\14_Processed_90m\gridfinder_distance.json` and `zone_grid_distance.json` are **legacy, unauditable, not reused in TEJ**. No number from them may enter the TEJ manuscript. Zone distances to lines are recomputed from the C4 raster after its provenance check (`SCENARIO_RUN_LOG.md`).


### A4 (2026-10-09): correction of the C2 poverty input. WRITTEN BEFORE ANY CORRECTED RESULT WAS COMPUTED
Disclosure: all earlier results (scenario runs 1–2, the TEJ manuscript of 2026-10-09) had been computed with the faulty input. The error was found during the reference audit, not by inspecting results.
Finding: `DER\Scripts\02_Preprocessing\build_c2_poverty_province.py` joins NESDC Table 1.5 (poverty incidence by province) to GADM 4.1 on the GADM Thai name `NL_NAME_1`. GADM 4.1 gives Bangkok Metropolis the Thai name of Chiang Mai and Chaiyaphum the Thai name of Chai Nat. Bangkok therefore received 3.0853% (Chiang Mai, 2565) instead of 1.3686%, and Chaiyaphum 15.2575% (Chai Nat, 2565) instead of 1.1748%. An independent join on a Thai-to-English province dictionary (`Scripts\c2_poverty_audit.py`, output `Data\c2_fix\`) finds these two and no other differences among the 77 provinces.
1. The only change is the two corrected C2 values. Source, year rule (2565 first, then nearest year), normalisation, weighting, TOPSIS, k = 5 zones, K = 15, Jenks k = 3, the 74-province scope and every other rule are unchanged. No threshold is changed.
2. The whole province chain is re-run, not patched: C2 raster, province PAI and weights, zones, LISA, sensitivity, bootstrap, validation, spatial permutation, MAUP, LV-density variant, SER check, master results, tables, figures, then the TEJ scenario, zone-distance and policy-table steps.
3. DER is not modified. The re-run happens in a mirror (`DER_TEJ\Rerun_C2fix\`) built from copies of DER data and the portable scripts of `DER_paper_repo`. Before the corrected run, the mirror is run once on the uncorrected input and must reproduce the published DER outputs. Any difference is reported and resolved first.
4. Files with no producing script (`cluster_stability.json`, `lisa_fdr.json`) are recomputed by new TEJ scripts that must first reproduce the existing files on the uncorrected input.
5. The previous outputs are archived, not deleted. The run log records old and new values side by side, including any change in S2/S3 membership, zone membership and headline statistics.

### A5 (2026-10-10): C2 is clipped and scaled once, at province level. WRITTEN AFTER A DIAGNOSTIC OF THE SINGLE-CLIP VARIANT WAS SEEN, BEFORE RUN 4 RESULTS
Disclosure: the independent spot check of the A4 verification (test 7, `Scripts\qa_a4_verification.py`) found that C2 was clipped at the 2nd and 98th percentiles twice: once in `rasterize_c2_poverty.py` (over the 77 province values, written into the raster) and again on the province means in `compute_pai_province_level.py`. The Methods described one clip per criterion. The same diagnostic showed what a single clip gives (equity weight 0.341, S1–S3 membership unchanged, Zone 1 = 6 provinces with Narathiwat in Zone 2). That result was seen before this amendment was written. The decision (author, option B1) rests on the implementation contradicting the stated method and on the first C2 clip repeating the second over the same 77 values, not on the zone result.
Checks made before the decision: C1 and C3 are also scaled at the pixel level (2nd–98th percentile clip in `compute_c1_pvout_90m.py` and `compute_c3_popdens_90m.py`). Their pixel step acts on pixel outliers before aggregation, which is a different operation from the province step, so it is kept and is now described in the Methods. C4 and C5 are formula scores in [0, 1].
1. `rasterize_c2_poverty.py` writes the raw provincial poverty percentage, with tags for unit, scaling = none, years used and the sha256 of the input table. `build_c2_poverty_province.py` writes `year_used` and no longer writes debug files outside the project.
2. `compute_pai_province_level.py` is the only place C2 is clipped and scaled. Its normalisation is unchanged (2nd–98th percentile clip, linear [0, 1], once per criterion). It asserts the C2 raster is unscaled and that each criterion is scaled once, and writes `criterion_scaling.json`.
3. Pixel-level TOPSIS scripts (`sensitivity_analysis.py`, `sensitivity_c3_c4_collinearity.py`, `compute_pai_topsis_poverty.py`) scale C2 explicitly through `_c2_scale.py`, with the transform the raster carried before A5, so pixel-level analyses are not changed by this amendment.
4. New guard `Scripts\guard_c2_scaling.py` (checks G1–G4) runs inside the chain and stops the run on failure.
5. Everything else is unchanged: weighting, TOPSIS, k = 5, K = 15 of 74, Jenks k = 3, thresholds. The whole chain and all TEJ steps are re-run (Run 4). Run 3 outputs are archived in `Data\qa\archive_run3\`. Run 4 becomes the canonical result set, and all eight verification tests are repeated before any freeze.
