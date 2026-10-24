# D: Search criteria for official data (fixed before searching, 2026-10-06), English translation

This is an English translation of `D_SEARCH_PROTOCOL.md`, which was written in Thai and fixed before the
search began on 2026-10-06. The Thai original is kept unchanged and is the authoritative version. Labels in
the right-hand column refer to work items of the authors' revision plan: S = policy scenarios, P = MV-proximity
screen, C = zone-to-policy instrument table, GOV = governance and implementation in Thailand. "[45]" was the
number, in an earlier version of the reference list, of the ERC rooftop regulation of B.E. 2556 (2013), which
the current manuscript no longer cites. Translated 2026-10-24.

## What was searched (four groups, as decided by the authors)

| # | Group | Purpose |
|---|---|---|
| D1 | Installed PV capacity by province (MW) | Main deployment comparison in place of OSM |
| D2 | Interconnection or application records by province (VSPP, SPP, residential rooftop solar for the general public, Thai: โซลาร์รูฟท็อปภาคประชาชน) | Deployment comparison at distribution level |
| D3 | PEA and MEA grid-planning documents (distribution development plans, smart-grid roadmaps) | GOV item and system implications in table C |
| D4 | Publicly released hosting-capacity data | Upgrade or replace item P |
| D5 | Instruments in force: ERC rooftop and net-billing rules, community solar, the administrator of the ENCON Fund, agency roles (Energy Industry Act B.E. 2550, 2007) | Items C and GOV, and to replace or supplement [45] |

## Acceptance criteria for sources

- **Accepted:** websites or documents of the government agency that owns the data (erc.or.th, pea.co.th,
  mea.or.th, egat.co.th, eppo.go.th, dede.go.th, the Royal Gazette), or official open data (data.go.th).
- **Accepted for status or context only:** IEA, IRENA or World Bank reports and peer-reviewed papers (not to
  be used as a source of province-level figures unless they name an official source).
- **Not accepted:** news or blogs as a source of figures (they may only point to the original source), and
  data without a year or an issuing agency.
- **Province-level data are usable when** they cover at least 70 of the 77 provinces, state the year or
  cut-off date, state the unit (MW or number of applications) and can be downloaded or copied in full.
- Every source used is recorded with its URL, access date and the agency named under "Source" (Thai: ที่มา)
  in the authors' findings log.

## Possible outcomes and what follows (set in advance)

- D1 or D2 meets the criteria: use it as the main comparison in Section 4.7 and as one outcome of S, and
  reduce OSM to a descriptive check.
- D1 and D2 do not meet the criteria: keep OSM, state that it records utility-scale plants with
  ascertainment bias, and do not use it as an outcome of S.
- D4 finds area-level data: use it in place of the MV distance in item P. If none is found, use the
  MV-proximity classes as planned.

## Outcome (added with the translation, for readers of the repository)

D1 and D2: no province-level installed-capacity or application dataset meeting the criteria was found, so
OSM was kept as a descriptive comparison (manuscript Section 4.7). D4: PEA publishes remaining generation
capacity per substation (PEA Power Map, which PEA states is for preliminary reference only), but these
records could not be linked reliably to provinces. They therefore inform the utility verification gate,
not the scenarios, and the MV-proximity classes were used as planned (manuscript Section 5.5). The D5
instruments found are recorded in `D5_POLICY_REGISTER.md`.
