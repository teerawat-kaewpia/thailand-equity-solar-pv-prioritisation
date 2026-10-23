# Scenario run log

## Run 1 (2026-10-08): province inputs + S1–S3 without MV metrics

Scripts: `Scripts\province_metrics.py` → `Data\scenarios\province_inputs.csv` (+ `_checks.json`); `Scripts\scenarios.py` → `Data\scenarios\scenario_tradeoff_noMV.csv`, `scenario_members.json`

### Inputs (all read-only from DER / Energy map)
- Population: `DER\Data\05_Population\worldpop_THA_2020_100m.tif`, the same file as C3 (`compute_c3_popdens_90m.py`). Total 74.94 M.
- PVOUT raw: Global Solar Atlas v2 LTAy `PVOUT.tif`, the same file as C1 before normalisation. Province means range 1,363–1,545 kWh/kWp/yr. (`C1_PVOUT_90m.tif` is normalised to 0–1 and so cannot be used for raw units.)
- Distance to lines: per pixel, d = −5·ln C from `C5_grid_dist_90m.tif`, which `compute_c5_distance_90m.py` builds as exp(−d/5) with d = distance to OSM power lines. Province mean of d.
- Regions: the 6-region grouping from `DER\Scripts\06_Priority_Areas\maup_analysis.py`, parsed with ast (not executed). It asserts 77 provinces.

### Reproduction checks against v2
- Equity vs efficiency-only composite ρ = **−0.391**, identical to master_results. ✔
- Zone mean distance to lines (Table 9 definition: zone mean of province mean pixel distance, d = −5 ln C4):

| Zone | this run | v2 Table 9 (`zone_grid_distance.json`) |
|---|---|---|
| 1 | 12.8 | 12.8 ✔ |
| 2 | 13.2 | 11.7 ✘ |
| 3 | 11.4 | 11.4 ✔ |
| 4 | 16.2 | 15.6 ✘ |
| 5 | 16.9 | 16.4 ✘ |

  The minimum values match in all zones. The differences come from remote provinces only: Mae Hong Son 74.3 km here, while the v2 zone-2 maximum is 55.2. Uthai Thani 58.5 against 46.6. Tested alternatives (excluding C < 1e-4 or C < 1e-3, clipping at 1e-6, −5 ln of the mean C) did not reproduce v2. **`zone_grid_distance.json` has no producing script in DER or DER_paper_repo, so the v2 method cannot be recovered.** The TEJ manuscript should use the reproducible values from this run.

### Result (protocol as locked, K = 15, B shared, population-proportional within set)

| Scenario | Prov. | Regions | Poverty-weighted beneficiary equiv. | Alloc.-wtd mean poverty % | Alloc.-wtd mean PVOUT | Alloc.-wtd median dist. to lines (km) |
|---|---|---|---|---|---|---|
| S1 Uniform | 77 | 6 | 54,979 | 5.50 | 1,469.7 | 8.6 |
| S2 Equity-targeted | 15 | 6 | 87,276 | 8.73 | 1,471.2 | 2.7 |
| S3 Resource-and-infrastructure comparator | 15 | 3 | 21,082 | 2.11 | 1,482.0 | 2.8 |

S2 ∩ S3 = Ang Thong, Bangkok Metropolis, Sing Buri.

### Problem found (protocol design, not code)
**Bangkok Metropolis is PAI rank 14, so it falls inside K = 15. Under population-proportional allocation it takes 58.4% of B in S2** (and 38.8% in S3, with Samut Prakan 11.6% and Nonthaburi 7.8%). The S2 median distance (2.7 km) is Bangkok's own value. S2 is therefore dominated by one low-poverty (3.1%) MEA-served metropolis. This contradicts the decision that the main text is a PEA-province narrative with Bangkok/MEA in the Supplementary.

The fix needs a dated amendment written after this result and a user decision. Nothing was changed.

## Pending
- MV variable definition: see D_FINDINGS "MV provenance". Metrics 5–6 are not computed.
- Decision on the Bangkok/MEA issue above.

**Status of run 1: superseded by run 2 (A2). Kept for the record as `Data\scenarios\run1_scenario_tradeoff_noMV_77prov.csv`.**

## Legacy files (2026-10-08)
`DER\Data\14_Processed_90m\gridfinder_distance.json` (§4.4 MV 1.3 km, ρ = −0.448) and `zone_grid_distance.json` (Table 9 zone km) are **legacy, unauditable, not reused in the TEJ manuscript** (no producing script). No number from them enters the TEJ manuscript.

## C4 provenance check (2026-10-08): `Scripts\c4_provenance_check.py` → `Data\qa\c4_provenance_check.json`
- `compute_c5_distance_90m.py` was re-executed in memory on the same inputs (OSM power_lines + power_cables, 3,561 features, SHA-256 recorded). The result is **identical to the published C5_grid_dist_90m.tif in all 61,256,284 valid cells (max |diff| = 0.0, identical nodata mask)**. C4 is reproducible and can serve as the scenario baseline.
- Known approximation: the script uses a constant 0.09 km per pixel on a 0.000833° EPSG:4326 grid. The true pixel height is about 0.092 km and the width is 0.087–0.092 km by latitude, so C4 km values are approximate to within a few percent. The TEJ text must not present C4 distances as more precise than that.
- Side note: 61,256,284 valid cells here, against "60,499,527 valid pixels" in v2 §3.2. They use different masks, and the TEJ text must state the count from the mask actually used.
- Zone distances to lines in TEJ come from `province_inputs.csv` (reproducible), not from Table 9 of v2.

## MV distance (2026-10-08, A3): `Scripts\mv_distance.py` → `Data\mv_distance\`
- Source gpkg SHA-256 58ddd588…, 36,027 features. Grid EPSG:32647, 90 m, 9,868 × 18,243. 63,536,390 valid cells (about 514,600 km², consistent with Thailand's area).
- 33.9% of cells lie within 1 km of a modelled MV line, 84.1% within 5 km and 94.1% within 10 km. Maximum 66.2 km.
- Province means range from 0.68 to 9.49 km. The smallest province has 50,081 cells.
- Spearman ρ against the C4 line distance = 0.689. UTM 47N scale factor at the east edge (105.57°E) k = 1.0059 (+0.6%).

## Run 2 (2026-10-08): protocol + A2 + A3 → `Data\scenarios\scenario_tradeoff.csv`, `province_scenario_table_74.csv`, `scenario_members.json`
Analysis set: 74 PEA-served provinces. PEA-area population 58,669,402. K = 15 of 74 (20.3%). B = 1,000,000.
MV-proximity classes (FisherJenks k = 3, 74 provinces), upper bounds 2.214 / 4.756 / 9.49 km: nearer 44, intermediate 25, farther 5 (Kanchanaburi, Mae Hong Son, Phetchaburi, Tak, Uthai Thani). The caveat applies to all classes.

| Scenario | Prov. | Regions | Poverty-wtd benef. equiv. | Mean poverty % | Mean PVOUT | Median km to lines | Median km to MV | Largest province share | B in nearer / intermediate / farther (%) |
|---|---|---|---|---|---|---|---|---|---|
| S1 Population-proportional baseline | 74 | 6 | 64,220 | 6.42 | 1,469.9 | 11.8 | 1.77 | 4.4% | 67.4 / 28.4 / 4.2 |
| S2 Equity-targeted support | 15 | 6 | 160,162 | 16.02 | 1,484.3 | 12.8 | 1.70 | 11.0% (Surin) | 68.5 / 22.5 / 9.1 |
| S3 Resource-and-infrastructure comparator | 15 | 4 | 21,241 | 2.12 | 1,491.2 | 3.7 | 1.16 | 16.5% (Pathum Thani) | 100 / 0 / 0 |

S2 ∩ S3 = Ang Thong, Sing Buri. The S2 farther-class members are Mae Hong Son and Tak.

Reading, per protocol 1.4 (no "best" scenario): S2 covers more poverty by construction (16.0% against 6.4% and 2.1%). The trade-off is in grid access. Compared with S3, S2 allocates to provinces whose median distance to the line network is 12.8 km against 3.7 km, whose median distance to the modelled MV network is 1.70 km against 1.16 km, and S2 puts 9.1% of B in the farther MV class against 0%. Compared with the baseline S1, S2's MV proximity is about the same (1.70 against 1.77 km). PVOUT differences are small (1,470–1,491 kWh/kWp), consistent with Thailand's uniform solar resource.

## Legacy cleanup of the TEJ manuscript + 3-layer guard (2026-10-08)

**Status label for the v2 outputs that were removed: "legacy, unauditable, not reused in the TEJ manuscript".** This covers §4.4 MV 1.3 km / ρ = −0.448 (`gridfinder_distance.json`, also embedded as `MR["gridfinder"]`) and the Table 9 zone km (`zone_grid_distance.json`, also `MR["zone_grid_km"]`).

New lineage
- `Scripts\_lineage.py`: `load_mv()` is the only allowed reader of the MV variable. It checks that the QA source hash matches the current gpkg, CRS = EPSG:32647 and res = 90 m, and it returns lineage (producer, QA hash, source hash, CRS, mask, aggregation rule).
- `Scripts\zone_distances.py` → `Data\zone_distances\zone_distances_tej.json`: zone means per v2 dominant_zone (77 provinces) from `province_inputs.csv` (C4, reproduced cell-exact) and `load_mv()`. The assembler aborts if this file was built from a different MV QA record.

**Zone values computed directly (the only basis for any Zone 1 statement):**

| Zone | n | Power lines mean km (range) | Modelled MV mean km (range) |
|---|---|---|---|
| 1 | 6 | 12.8 (2.4–20.3) | 1.32 (0.87–1.70) |
| 2 | 24 | 13.2 (2.2–74.3) | 2.24 (0.68–9.49) |
| 3 | 17 | 11.4 (3.6–25.6) | 1.68 (1.19–3.35) |
| 4 | 18 | 16.2 (6.9–58.5) | 2.91 (1.04–9.00) |
| 5 | 12 | 16.9 (6.2–35.1) | 3.61 (1.55–8.26) |

Spearman, 77 provinces: PAI vs MV mean km ρ = −0.452 (p = 3.7e-5). PAI vs power-line mean km ρ = −0.216 (p = 0.059, n.s.).

**Consequences for the text.** The v2/step-A claim "Zone 1 is far from transmission but close to MV" is NOT supported: Zone 1 is the 2nd-nearest zone to the power-line network. Only "Zone 1 has the lowest mean distance to the modelled MV network" is supported. The v2 claim that Zone 1's north-eastern and southern members are farther from the grid than its central members is also unsupported (Pattani 8.5 km, Chai Nat 18.6 km) and was removed. The C4 network is called "OSM-mapped power lines", not "transmission".

**Grid and pixel counts (distinct, never interchanged):**
- PAI grid: EPSG:4326, 0.000833°, **60,499,527** cells valid in every criterion layer (verified against `PAI_90m.tif` and `DER_zones_90m.tif`). This number is auditable and stays in §3.2. v2 had misstated this grid as "WGS84/UTM Zone 47N", which is corrected.
- C4 reproducibility check: the same EPSG:4326 grid with the C2-raster land mask, **61,256,284** cells.
- MV distance: EPSG:32647, 90 m, GADM-union cell-centre mask, **63,536,390** cells.

**Edits** (backups in `Data\qa\*.pre_legacy_cleanup.py.bak`):
- Main: §3.2 CRS sentence, §4.4 two paragraphs rewritten, the §4.4 S9 paragraph relabelled LV density, Table 9 rebuilt (the hard-coded ordinal "Interconnection convenience" column dropped, MV column added), §3.1/§5.1/§5.3/§5.5 (×2) "far from transmission" removed, Table 2 "GridFinder modelled MV network".
- Supplementary: S9 title, caption, column heads and text now say LV density. The S10 row was corrected: the script is `compute_c5_grid_access_90m.py`, not `08_gridfinder.py`. A new S10 row was added for the modelled MV distance.
- `province_metrics.py` no longer reads `MR["zone_grid_km"]`. `scenarios.py` reads MV through `load_mv()` and records the lineage in `scenario_members.json`. Scenario outputs are byte-identical before and after.

**Guard** `Scripts\guard_legacy.py [--docx]`: PASS (12 scripts, both DOCX).
- Source layer: legacy filenames, `MR["gridfinder"]`, `MR["zone_grid_km"]`, `zone_mv_dist_km`, `pai_corr_rho`.
- Literal layer: "1.3 km", "−0.448", "MV-proximity", "Table S9 … MV", "medium-voltage (MV) proximity", "UTM Zone 47N", "predicted MV network", "far/farther from transmission". It covers the source strings and the DOCX text before the References.
- Lineage layer: `load_mv()` must pass, the zone file must match the current MV QA record, and no script except `mv_distance.py` may read the MV table directly.
- Note: "60,499,527" is NOT in the literal guard, because it was verified as the PAI-grid count. This was a deviation from the reviewer's list and was reported to the user.

## Count-context guard + 77/74 note (2026-10-08)
- The reviewer confirmed that 60,499,527 stays and is not a banned literal. `Scripts\pai_grid_qa.py` → `Data\qa\pai_grid_qa.json` (60,499,527 cells valid in PAI_90m.tif = DER_zones_90m.tif, EPSG:4326, raster hashes). The assembler reads the count from this file and no longer types it.
- `guard_legacy.py` layer 4: each count (PAI grid / C4 check / MV grid) is read from its own QA file, never typed as a literal in the assemblers. In the DOCX, a count may not share a sentence with another grid's CRS or variable (PAI/C4 count with UTM, EPSG:32647, MV distance or modelled MV; MV count with EPSG:4326, PAI grid or C4 raster). The manuscript must state the PAI count from QA. Negative test: the v2 sentence ("UTM Zone 47N … 60,499,527") and a mixed MV sentence are FLAGGED, and the TEJ sentence passes. PASS on the rebuilt DOCX.
- Table 9 caption now ends with: "Zone statistics use the national 77-province analytical base, whereas policy-allocation scenarios are restricted to the 74 provinces in the PEA service area."

## Step C, layer 1 (2026-10-08): `Scripts\zone_policy_table.py` → `Tables\zone_policy_table_draft.csv` (+ `_meta.json` with MV lineage)
Not inserted into the manuscript: layer 2 is pending D5/GOV.
- Layer 1 (filled): provinces (77 base), MEA members, poverty mean (range), PVOUT mean, OSM power-line km, modelled MV km, MV class counts over PEA members, data required before implementation (generic list plus zone-specific flags derived from data).
- Layer 2 (PENDING D5/GOV): **Candidate policy response** (not "recommended instrument"), Responsible institution, Regulatory basis, Official citation.
- All 3 MEA provinces fall in Zone 2, so Zone 2 has 21 PEA members with MV classes.

## Step C + GOV evidence into the manuscript (2026-10-08)
- `zone_policy_table.py` produces `Tables\zone_policy_table_main.csv` (5 columns: Zone, Policy-relevant spatial condition, **Observed policy gap (study inference)**, Candidate response / implementation gate, Lead institution) and `zone_policy_table_full_supp.csv`. Layer 1 columns were verified unchanged.
- Labels: I3 is "equity context, consumer-protection instrument". I4 is a "conditional candidate". Zone 2 states that MEA provinces need an MEA-specific feeder assessment (PEA Power Map does not cover them). EGAT and DEDE roles are not named, per user rule pending P5.
- Manuscript: **Fig. 14 removed and replaced by Table 15** (§5.5). The §5.5 second paragraph was rewritten from D5-verified sources only. The v2 claims about ENCON "competitive grants for renewable" and the ERC 2013 net-metering reference were removed. New references [49]–[53] were appended to the TEJ `references.json` (backup `Data\qa\references.pre_D5.json`) and renumber to [42]–[46] in the build. The ERC 2013 reference is now uncited and dropped.
- Supplementary: new **S11** (Table S11a full screen, Table S11b primary-source index from `Data\policy\source_index.json`). Data Availability now reads S1–S11.
- Found and fixed: the Data Availability text still said "(transmission versus MV) sensitivity (S9)". It now reads "power-line proximity versus LV density". The guard literal list gained `versus MV`. Guard PASS (13 scripts, both DOCX). Build: 13/13 figures.
- **Still v2 text, not D5-grounded (for step B):** the §5.5 first paragraph ("0–3 year horizon", "subsidised community solar with … concessional finance", agrivoltaics, "efficiency-first in Zone 5"). These are study recommendations and must be rewritten or labelled as such.

## Step B: reframe (2026-10-08)
Backups: `Data\qa\assemble_manuscript_tej.pre_B.py.bak`, `assemble_supplementary_tej.pre_S12.py.bak`. Patches: scratchpad `patch_B.py`, `patch_B2.py`, `make_S12.py`.
- Framing: policy allocation trade-offs for distributed solar under equity and network constraints. Title: "…: Policy scenarios for electricity distribution planning". The "Submitted to SCS / ISSN" lines were removed.
- New: highlights (5, ≤ 79 chars), abstract (221 words), keywords (commas), §1 (4 paragraphs, RQ1–RQ3), §3.5 counterfactual allocation scenarios and network screening (states the protocol, hash-locking and the two amendments), §4.9 scenario results and **Table 14** (S1–S3), §5.5 para 1 rebuilt on Tables 14 and 15, §6 (RQ answers, 3 contributions, limitations, closing).
- Removed from §5.5: "0–3 year horizon", "subsidised community solar", concessional finance, agrivoltaics, efficiency-first. Added: "A rule that reserved part of an instrument for high-priority provinces would be a new design. It is not evaluated here."
- Bangkok case moved verbatim to **Supplementary S12** (v2 §3.5, §4.9, §5.7, Fig. 12 → Fig. S12, Table 14 → Table S12a). Cross-references were renumbered and "most remote from transmission" now reads "farthest from the mapped power-line network". Main text now has 12 figures (radar = Fig. 12).
- Other fixes: §3.1 MEA area now reads "Bangkok, Nonthaburi and Samut Prakan" (v2 said "Bangkok and three adjacent provinces" with "remaining 74", internally inconsistent). **This fact has no primary source in D5 yet.** §4.6 and §5.2 Bangkok references were updated. The TOPSIS origin citation [Hwang & Yoon, Behzadian] was re-added in §2.5 after the §1 rewrite dropped it.
- Over-claim caught before reporting: highlight 3 said "not to modelled MV lines", but S2's MV median is also longer than S3's (1.70 vs 1.16 km), so it now reads "much longer power-line distances and smaller MV differences".
- Checks: new prose has 0 em dashes and 0 semicolons. No EGAT or DEDE in the body. Guard PASS (manuscript + supplementary). Body §1–§6 incl. captions is **9,101 words** → F must cut to 4,500–4,800.
- Left for F: legacy v2 prose still contains semicolons and some " — " (converted at build). §2 generalized framework, §4.1–4.8 detail, §5.1–5.4 and §5.6 are long. The moved S12 text keeps v2 semicolons.

## Step F (2026-10-08): float labels + cut to budget
**Mechanism**
- `Scripts\_floats.py` registry. Text refers to floats only through `{T:label}`/`{F:label}`, resolved at build. Main numbering follows the declared order. Supplementary ids are fixed (S1–S12a, S13a–h, Fig. S12, S13a–f).
- The build aborts if caption order ≠ declared order, a label is defined twice, a label is undeclared, or a main float is never cited.
- `tokenize_floats.py` migrated 118 hard-coded references (stage 1 identity check: text identical except 2 intentional edits).
- Guard layer 5 bans hard-coded `Table N` / `Fig. N` / `Table SN` in string literals (negative-tested).
- Main build writes `Data\qa\ref_renumber.json`. The supplementary maps the citations it carries to main numbers and aborts if one is not cited in the main text.
- `_equations.py`: OMML equations shared by both assemblers. Supplementary equations are numbered (S13.1)–(S13.11).

**Moves to Supplementary S13**
- Tables: bounds S13a, transfer S13b, descriptives S13c, correlations/VIF S13d, top-20 S13e, OSM zones S13f, construct check S13g, sensitivity S13h.
- Figures: corr S13a, weights S13b, LISA S13c, ranking S13d, sensitivity S13e, radar S13f.
- Text: the moved text is v2 prose with cross-references renumbered.

**Main text result**
- 6 figures (framework, study region, criteria maps, PAI map, zones, deployment) and 7 tables (criteria, data, weights, zones, grid, allocation, policy).
- Body §1–§6 = **4,021 words** (1: 518, 2: 376, 3: 699, 4: 1,067, 5: 995, 6: 366). Abstract 221, captions 616. References 37.
- Main text has 0 semicolons and 0 em dashes in prose and tables.

**Provenance fixes made during F**
- Table 1 C4 now reads "OSM power lines and cables" (v2 said "+ substations", which the C4 script does not use).
- Table 3 rebuilt: OSM lines June 2026 (not "transmission 2023"), Copernicus GLO-30 (not SRTM), Hansen v1.11 year-2000 layer, GHSL R2023A epoch 2018 at 3 arc-seconds. A GridFinder MV row was added.
- Table S10 GHSL "10 m" corrected to "3 arc-second (about 90 m)" per the download script (`…_4326_3ss`).
- §3.1 claim "Isan PVOUT ≈ 1,700–1,900 kWh/kWp" removed. Province means are 1,363–1,545.
- MEA service area is now cited to the MEA authority page (P12) as reference [54].

**Snapshot:** all 16 protected outputs (scenarios, Layer 1/2 tables, MV/zone/QA files, master_results) are byte-identical to `Data\qa\F_snapshot.json`.

**Open after F**
- Supplementary still has v2 semicolons (42 paragraphs, 56 cells) and 18 em dashes. These need a separate cleanup pass.
- The body is below the 4,500–4,800 target (about 480 words of room).
- The GenAI declaration describes AI use as language editing, code and figures only. In this TEJ revision the assistant also drafted new sections and retrieved and read policy documents. The authors must decide on the wording.

## F3 (2026-10-08): additions, supplementary punctuation, GenAI declaration
- Additions: §4.9 "Three cautions" paragraph (counterfactual reading, no best rule, allocation ≠ installed capacity). §5.4 scope of the observed gap (instruments examined only, allocation only, not a judgement on the instruments' own objectives). Body now **4,213 words**.
- Supplementary cleaned of every semicolon and em dash (paragraphs and cells: 0/0).
  - `Scripts\clean_punct_supp.py` (tokenize-based, context rules: inside parentheses or table cells → comma, between clauses → full stop + capital, em dash → comma). Docstrings, print() and eq() are skipped. Change log in `Data\qa\clean_punct_supp_applied.txt`.
  - S11a cells come from protected files, so separators are converted at render time only.
- Bug from stage-1 tokenisation fixed: NESDC "Table 1.5" (an external report table) had been turned into `{T:criteria}.5`. It is restored as text, and the guard regex now exempts decimal external table numbers.
- 11 stale supplementary cross-references to main-text sections were fixed: 5.4→5.3, 4.9/3.5→S12.2/S12.1, 4.7→S13.8, 2.8→S13.2, 2.3→S13.1, 4.5 local clusters→S13.6, "main text" added where needed.
- **Guard defects found and fixed (the earlier PASS results for these checks were not meaningful):**
  1. The layer-5 regex and the literal `versus MV\b` pattern contained a real backspace character (0x08) instead of `\b`, introduced when they were written through a shell heredoc. Both checks therefore matched nothing until fixed. All scripts were scanned and now contain no control characters.
  2. The guard accepted stale DOCX. A failed build (SyntaxError) still produced "PASS" on 18:23 files. The guard now fails if either DOCX is older than the newest script (tested: FAIL on stale, PASS after rebuild).
- GenAI declaration rewritten. The heading now reads "…in the Manuscript Preparation Process", and the declaration names **Claude (Anthropic) via Claude Code**, the tool actually used. The user's draft named OpenAI Codex (GPT-5). It now states that AI-assisted code was run to compute derived quantities and that source data were not generated or altered. Data Availability adds "All reported quantities are computed by the deposited scripts from the cited data."
- Snapshot: 16/16 protected files byte-identical. Guard PASS on fresh DOCX.

## Run 3 (2026-10-09): amendment A4, corrected C2 input

Chain: `Scripts\rerun_c2fix_chain.py` in the mirror `Rerun_C2fix\` (DER untouched, 0 files modified). Baseline replay on the uncorrected input reproduced every DER output (all CSV/raster/JSON values; LISA FDR differs only in column names; master_results 529/541 leaves identical, the 12 others are the unrecoverable gap statistic and provenance notes; DER_Paper_Tables.xlsx identical). Two run-order and library issues were resolved in the mirror only: `sensitivity_validation_province.py` must precede `validate_zones_province.py` (as in DER), and the chi-square is computed directly on the same rounded expected counts (newer SciPy rejects them).

| Quantity | Before A4 | After A4 |
|---|---|---|
| C2 Bangkok / Chaiyaphum (%) | 3.085 / 15.258 | 1.369 / 1.175 |
| EWM weights C1–C5 | 0.1483, 0.3325, 0.1698, 0.1790, 0.1705 | 0.1460, 0.3425, 0.1673, 0.1763, 0.1679 |
| ρ equity vs efficiency-only (p) | -0.391 (0.0004) | -0.394 (0.0004) |
| PAI range | 0.1831–0.6998 | 0.179–0.707 |
| Zone sizes 1–5 | 6/24/17/18/12 | 7/22/19/17/12 |
| Zone 1 members | Pattani, Ang Thong, Nong Bua Lam Phu, Kalasin, Chai Nat, Si Sa Ket | same six + Narathiwat |
| Chaiyaphum rank / zone | 7 / 2 | 62 / 4 |
| Bangkok rank | 14 | 22 |
| Moran's I (p) | 0.2531 (0.002) | 0.2394 (0.004) |
| LISA unadjusted / FDR significant | 12 / 0 | 15 / 0 |
| Sensitivity ρ equal / expert | 0.7585 / 0.9696 | 0.7403 / 0.9601 |
| ρ PAI vs plant count (p) | 0.003 (0.9765) | -0.042 (0.7157) |
| S2 members | … Chaiyaphum … | Chaiyaphum out, Phatthalung in |
| Mean poverty S1 / S2 / S3 (%) | 6.42/16.02/2.12 | 6.22/15.93/2.12 |
| Median km to power lines S1 / S2 / S3 | 11.8/12.8/3.7 | 11.8/15.7/3.7 |
| Median km to modelled MV S1 / S2 / S3 | 1.77/1.7/1.16 | 1.77/1.7/1.16 |
| Budget in farther MV class S2 (%) | 9.1 | 9.5 |

No threshold, K, class rule or weighting rule changed. Protected-output snapshot re-baselined (9 TEJ outputs and the master results changed, the MV, policy and grid-QA outputs did not). Pre-A4 outputs archived in `Data\qa\archive_pre_A4\`.
Open: the printed ERP VIF (24.98) has no producing script and is not reproduced by any tested specification (VIF 3.2–8.9 on the current criteria, `Scripts\erp_vif_check.py`). Author decision pending.

## Run 4 (2026-10-10): amendment A5, C2 clipped and scaled once at province level

Chain: the fixed builder, then `Scripts\rerun_c2fix_chain.py run4` in the mirror, then the new guard `Scripts\guard_c2_scaling.py` (G1–G4 PASS), the two extras, master results, tables and all TEJ steps (`Scripts\run4_a5.py`). DER untouched. The pixel-level C2 scaled by `_c2_scale.py` equals the pre-A5 raster to within 6e-8 (float32 rounding). The reported sensitivity is province level (`sensitivity_validation_province.py` rewrites the pixel file), so it follows the new matrix.

| Quantity | Run 3 (C2 clipped twice) | Run 4 (C2 clipped once) |
|---|---|---|
| C2 as rasterised | province values clipped 2nd–98th and scaled to [0, 1] | raw poverty percent (scaling = none) |
| C2 clips before the PAI | 2 (raster, then province means) | 1 (province means) |
| EWM weights C1–C5 | 0.1460, 0.3425, 0.1673, 0.1763, 0.1679 | 0.1464, 0.3410, 0.1676, 0.1767, 0.1683 |
| ρ equity vs efficiency-only (p) | -0.394 (0.0003953) | -0.394 (0.0003953) |
| PAI range | 0.179–0.707 | 0.1797–0.706 |
| Zone sizes 1–5 | 7/22/19/17/12 | 6/23/19/17/12 |
| Zone 1 members | Pattani, Nong Bua Lam Phu, Kalasin, Ang Thong, Chai Nat, Si Sa Ket, Narathiwat | Pattani, Nong Bua Lam Phu, Kalasin, Ang Thong, Chai Nat, Si Sa Ket |
| Zone 1 PAI range / land % | 0.567–0.707 / 5.8 | 0.595–0.706 / 4.9 |
| Narathiwat PAI / rank / zone | 0.5672 / 7 / 1 | 0.5581 / 7 / 2 |
| Max change in province PAI / rank |  | 0.0093 / 3 |
| Moran's I (p) | 0.2394 (0.004) | 0.2472 (0.003) |
| LISA unadjusted / FDR significant | 15 / 0 | 13 / 0 |
| Sensitivity ρ equal / expert (province level) | 0.7403 / 0.9601 | 0.7506 / 0.9605 |
| ρ PAI vs plant count (p) | -0.042 (0.7157) | -0.039 (0.7336) |
| Zone 1 share of plants % (χ²) | 2.1 (42.8) | 1.8 (40.2) |
| Zone 1 mean km to lines / modelled MV | 12.6 / 1.38 | 12.8 / 1.32 |
| S1–S3 members |  | identical to Run 3 |
| Scenario trade-off table |  | identical to Run 3 |

Narrative: the Zone 1 entry routes are now described from national ranks (top fifth = rank 15 or better of 77 on raw poverty and on the C1 province mean), which no normalisation choice can move. Under the old 0.7 cut on normalised C2, Si Sa Ket moved from the poverty to the irradiance route between Run 3 (0.715) and Run 4 (0.696) with unchanged data. By rank, Ang Thong enters on irradiance only, Nong Bua Lam Phu and Kalasin on poverty only, and Chai Nat and Si Sa Ket on both (Chai Nat is 4th for irradiance and 9th for poverty, so the earlier text 'Chai Nat entered through irradiance' was incomplete in every run).
No threshold, K, class rule or weighting rule changed. Run 3 outputs archived in `Data\qa\archive_run3\`. Protected-output snapshot re-baselined (8 changed: scenario inputs, zone distances, zone policy tables, master results).
