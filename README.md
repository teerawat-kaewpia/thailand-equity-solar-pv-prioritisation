# Equity-aware spatial prioritisation of distributed solar PV in Thailand

Code and province-level data behind the manuscript "Equity-aware spatial prioritisation of distributed
solar PV in Thailand: Policy scenarios for electricity distribution planning" (submitted to The Electricity
Journal). Authors: Thanapon Saengsuwan and Teerawat Kaewpia, Chiang Rai Rajabhat University.

## What is here

| Folder | Content |
|---|---|
| `scripts/der_chain/` | Province index pipeline (criterion rasters, EWM-TOPSIS PAI, K-means zones, LISA, sensitivity, validation, Bangkok districts), the scripts this release uses from `DER_paper_repo` branch `fix/c2-poverty-join` at commit `db29fac` |
| `scripts/tej/` | Scenario analysis, zone distances, modelled MV distances, policy screen, figures and document assembly |
| `data/province/` | Province-level outputs of the final run (Run 4), 77 provinces |
| `data/master_results.json` | Every headline statistic quoted in the manuscript |
| `data/tej/` | Scenario inputs and results (S1 to S3), zone distances, modelled MV distances, policy instrument screen, corrected C2 table and audit, ERP diagnostic |
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

The scripts were run with Python 3.11 on Windows. Default paths in `scripts/tej/_paths.py` point to the
authors' machine and are overridden by the environment variables above.

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
