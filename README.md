# Equity-aware spatial prioritisation of distributed solar PV in Thailand

Code and province-level data behind the manuscript "Equity-aware spatial prioritisation of distributed solar PV in Thailand: Policy scenarios for electricity distribution planning" (submitted to The Electricity
Journal). Authors: Thanapon Saengsuwan and Teerawat Kaewpia, Chiang Rai Rajabhat University.

## What is here

| Folder | Content |
|---|---|
| `scripts/der_chain/` | Province index pipeline (criterion rasters, EWM-TOPSIS PAI, K-means zones, LISA, sensitivity, validation, Bangkok districts), the scripts this release uses from `DER_paper_repo` branch `fix/c2-poverty-join` at commit `db29fac` |
| `scripts/tej/` | Scenario analysis, zone distances, modelled MV distances, policy screen, figures and document assembly |
| `scripts/data_download/` | Overpass queries used to download the OpenStreetMap power lines, cables and plants |
| `data/province/` | Province-level outputs of the final run (Run 4), 77 provinces |
| `data/master_results.json` | Every headline statistic quoted in the manuscript |
| `data/tej/` | Scenario inputs and results (S1 to S3), zone distances, modelled MV distances, policy instrument screen, corrected C2 table and audit, ERP diagnostic, cell-area check |
| `data/indices/` | The two author-built composite indices (provincial and Bangkok district): per-unit scores, workbook and methodology (in Thai) |
| `data/bangkok/` | Bangkok district analysis of Supplementary Section S12 (district criteria, vulnerability index and PAI) |
| `figures/` | `main/` Fig. 1 to 6, `supplementary/` Fig. S12 and S13a to S13f, `submission/` journal files, `FIGURES_MANIFEST.csv` |
| `docs/` | Pre-registered scenario protocol with dated amendments A1 to A5, its hash lock, and the run log |

`MANIFEST.csv` lists every file with its size and sha256. `PROVENANCE.csv` lists every dataset, map and
figure, and policy document the study uses, with version, date, source, the analysis stage it serves and
the licence of the source. `DATA_SOURCES.md` repeats the dataset part as printed in Table S10.

## Final results

The canonical result set is Run 4 (`docs/SCENARIO_RUN_LOG.md`). It includes two corrections recorded as
protocol amendments: A4 corrects the provincial poverty input (two provinces had received another
province's value through a wrong Thai name in GADM 4.1), and A5 clips and scales the poverty criterion
once at province level, as stated in the Methods.

## Reproducing the results

1. Download the raw inputs listed in `DATA_SOURCES.md` into a data root with the layout the scripts
   expect (`<root>/DER/Data/...` and `<root>/Energy map/...`).
2. Run the DER chain with `ENERGY_DATA_ROOT=<root>` and `DER_PROJECT_ROOT=<root>/DER`. The order is the
   list `CHAIN` in `scripts/tej/qa_clean_run.py`.
3. Run the TEJ steps with `DER_SOURCE_ROOT=<root>/DER`, in the order of `TEJ_STEPS` in the same file.
4. `scripts/tej/qa_clean_run.py` performs steps 2 and 3 from an empty output state and compares every
   output with the reference run. Its source and work folders are set at the top of the file for the authors' machine and need to be
   edited before it is run elsewhere.

The scripts were run with Python 3.11.9 on Windows. Default paths in `scripts/tej/_paths.py` and
in the DER chain point to the authors' machine and are overridden by the environment variables above.

## Requirements

- The Python packages and versions in `requirements.txt` (`pip install -r requirements.txt`). Geopandas,
  fiona and rasterio need GDAL, which their wheels include on Windows.
- Microsoft Word for the two document assemblers (`assemble_manuscript_tej.py`,
  `assemble_supplementary_tej.py`): equations are converted with Word's `MML2OMML.XSL`. The analysis
  and figure scripts do not need it.
- A Google Earth Engine account only for the raw-data export scripts in `scripts/der_chain/GEE/`. These
  download inputs and are not part of `CHAIN`.

## Differences from the source code

`scripts/der_chain/` is taken from the source branch named above and `scripts/data_download/` from the
authors' download folder, with these changes, none of which changes a computed value (paths below are
relative to `scripts/der_chain/` unless they start with `data_download/`):

- `06_Priority_Areas/validate_zones_province.py` is the version that produced Run 4. It computes the
  chi-square statistic directly because SciPy 1.16 rejects `chisquare` when the rounded expected counts do
  not sum exactly to the observed total.
- `06_Priority_Areas/validate_ser_external.py`: reads ENERGY_DATA_ROOT like the other chain scripts.
- `02_Preprocessing/build_c2_vulnerability_district.py`: diagnostic list of unmatched district names goes to the system temp folder.
- `02_Preprocessing/download_ghsl_building_height.py`: output folder follows ENERGY_DATA_ROOT.
- `data_download/download_grid_osm.py`: output folder follows ENERGY_DATA_ROOT.
- `GEE/02_viirs_nightlights.py`: loads 00_gee_setup.py by file name.
- `GEE/04_hansen_forest.py`: loads 00_gee_setup.py by file name.
- `GEE/05_copernicus_dem.py`: loads 00_gee_setup.py by file name.

## Not included

The manuscript files, raw third-party datasets and rasters, the policy documents themselves (links only),
and the PEA Power Map downloads are not redistributed.

## Licence

Code (`scripts/`) is released under the MIT License, see `LICENSE`. Data, figures and documents (`data/`,
`figures/`, `docs/` and the Markdown files) are released under the Creative Commons Attribution 4.0
International licence (CC BY 4.0), see `LICENSE-DATA`. Raw third-party inputs listed in
`DATA_SOURCES.md` keep their own licences.

## Citation

See `CITATION.cff`. A DOI will be added after the Zenodo release.
