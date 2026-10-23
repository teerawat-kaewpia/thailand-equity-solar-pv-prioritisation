"""Zone-to-policy table, two layers (step C).

Layer 1 (filled now, from the TEJ pipeline only): zone profile, poverty, PVOUT,
distance to OSM-mapped power lines, distance to GridFinder modelled MV lines,
MV-proximity class counts, and the data required before implementation.
Layer 2 (PENDING D5/GOV): candidate policy response, responsible institution,
regulatory basis, official citation. Until D5 is complete the column is named
"candidate policy response", never "recommended instrument".

Zone statistics use the national 77-province base (v2 dominant_zone). MV classes
exist only for the 74 PEA-served provinces (Amendment A2), so class counts are
reported over each zone's PEA members.
"""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import BASE, out_path
from _lineage import load_mv
import pandas as pd

MEA = {"Bangkok Metropolis", "Nonthaburi", "Samut Prakan"}
PENDING = "PENDING D5/GOV"
FOOTNOTES = [
    "MV classes (Jenks, k = 3) are computed for the 74 PEA-served provinces only. Bangkok Metropolis, "
    "Nonthaburi and Samut Prakan (MEA service area) are excluded from the MV classification and from "
    "the PEA policy-allocation scenarios, but remain in the 77-province zone statistics.",
    "Data required before implementation in every zone: feeder-level hosting capacity, time-series "
    "feeder load, existing and queued DER capacity on the feeder, and eligible rooftop or land "
    "availability. PEA publishes substation-level remaining generation capacity (PEA Power Map), "
    "which is record-level and not additive across substations. The zone-specific data gate column "
    "lists only requirements beyond this common set.",
]

inp = pd.read_csv(BASE / "Data" / "scenarios" / "province_inputs.csv")
mv, lineage = load_mv()
cls = pd.read_csv(BASE / "Data" / "scenarios" / "province_scenario_table_74.csv")[["NAME_1", "mv_class"]]
d = inp.merge(mv[["NAME_1", "mv_dist_mean_km"]], on="NAME_1").merge(cls, on="NAME_1", how="left")
assert len(d) == 77 and d.mv_class.isna().sum() == 3 and set(d[d.mv_class.isna()].NAME_1) == MEA

rows = []
for z, g in d.groupby("dominant_zone"):
    pea = g[~g.NAME_1.isin(MEA)]
    c = pea.mv_class.value_counts()
    farther = sorted(pea[pea.mv_class == "farther"].NAME_1)
    extra = []
    if farther:
        extra.append("Farther-MV provinces (" + ", ".join(farther) + "): connection-cost and reinforcement assessment")
    if g.NAME_1.isin(MEA).any():
        extra.append("MEA provinces (" + ", ".join(sorted(g[g.NAME_1.isin(MEA)].NAME_1)) + "): MEA feeder data")
    rows.append({
        "Zone": int(z),
        "Provinces (77 base)": len(g),
        "of which MEA": ", ".join(sorted(g[g.NAME_1.isin(MEA)].NAME_1)) or "none",
        "Poverty incidence %, mean (range)": f"{g.poverty_pct.mean():.1f} ({g.poverty_pct.min():.1f}–{g.poverty_pct.max():.1f})",
        "PVOUT kWh/kWp/yr, mean": f"{g.pvout_kwh_kwp.mean():,.0f}",
        "OSM power lines km, mean (range)": f"{g.dist_line_km.mean():.1f} ({g.dist_line_km.min():.1f}–{g.dist_line_km.max():.1f})",
        "Modelled MV km, mean (range)": f"{g.mv_dist_mean_km.mean():.2f} ({g.mv_dist_mean_km.min():.2f}–{g.mv_dist_mean_km.max():.2f})",
        "MV class among PEA provinces only (nearer/intermediate/farther)": f"{c.get('nearer', 0)}/{c.get('intermediate', 0)}/{c.get('farther', 0)}",
        "Zone-specific data gate": ". ".join(extra) if extra else "common set only (see footnote)",
        "Candidate policy response": PENDING,
        "Responsible institution": PENDING,
        "Regulatory basis": PENDING,
        "Official citation": PENDING,
    })
t = pd.DataFrame(rows)
t.to_csv(out_path("Tables", "zone_policy_table_draft.csv"), index=False, encoding="utf-8-sig")
json.dump({"mv_lineage": lineage, "base": "77 provinces for zone statistics; MV classes over 74 PEA provinces",
           "footnotes": FOOTNOTES, "pending_columns": ["Candidate policy response", "Responsible institution", "Regulatory basis", "Official citation"]},
          open(out_path("Tables", "zone_policy_table_draft_meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 60)
print(t[["Zone", "Provinces (77 base)", "MV class among PEA provinces only (nearer/intermediate/farther)", "Zone-specific data gate"]].to_string(index=False))
for i, f in enumerate(FOOTNOTES):
    print(f"Note {i + 1}: {f}")

# ── Layer 2 (revised 2026-10-08): candidate responses from D5-verified instruments ──
# Rules are data-driven from the Layer 1 values above. Instruments and citations
# come from Data/policy/layer2_instruments.json (each cites Docs/D5_POLICY_REGISTER.md).
# "Observed policy gap (study inference)" is this study's inference, limited to the
# instruments examined in D5. It is never a statement about all Thai policy.
L2 = json.loads((BASE / "Data" / "policy" / "layer2_instruments.json").read_text(encoding="utf-8"))
I = L2["instruments"]
zpov = d.groupby("dominant_zone").poverty_pct.mean()
z_high, z_low = int(zpov.idxmax()), int(zpov.idxmin())
GAP_ALL = ("No spatial or poverty-targeting allocation rule was identified among the instruments "
           "examined (household rooftop purchases are allocated first come first served)")
main_rows = []
for r in rows:
    z = r["Zone"]
    zp = d[(d.dominant_zone == z) & ~d.NAME_1.isin(MEA)]
    far = sorted(zp[zp.mv_class == "farther"].NAME_1)
    mea = sorted(d[(d.dominant_zone == z) & d.NAME_1.isin(MEA)].NAME_1)
    resp, gates, inst, basis, cite, gaps = [], [], [], [], [], [GAP_ALL]
    def use(key):
        inst.append(f"{key}: {I[key]['institutions']}")
        basis.append(f"{key}: {I[key]['regulatory_basis']}"); cite.extend(I[key]["citation"])
    resp.append("Household rooftop net billing (I1)"); use("I1")
    gates.append("PEA connection check: transformer export cap 25% of kVA, inverter limits")
    if (zp.mv_class != "farther").any():
        resp.append("Community solar farm (I2)"); use("I2")
        gates.append("utility sizing to feeder grid capacity and load profile")
    if far:
        gates.append("connection-cost and reinforcement assessment for farther-MV provinces (" + ", ".join(far) + ")")
        gaps.append("Connection costs fall on the applicant (I1), and no instrument examined addresses "
                    "connection cost in the farther-MV provinces")
    if z == z_high:
        resp.append("ENCON Fund capital support (I4), conditional candidate")
        cite.extend(I["I4"]["citation"]); inst.append(f"I4: {I['I4']['institutions']}")
        basis.append(f"I4: {I['I4']['regulatory_basis']}")
        resp.append("equity context: progressive residential tariff (I3), a consumer-protection instrument")
        use("I3")
        gaps.append("No instrument examined provides targeted capital support for low-income households' "
                    "solar investment, and ENCON eligibility for solar investment is not confirmed")
    if z == z_low:
        resp.append("ENCON Fund energy-efficiency support (I4)"); use("I4")
    use("G1")
    if mea:
        gates.append("MEA-specific feeder assessment for " + ", ".join(mea) + " (PEA Power Map does not cover them)")
        cite.append("P2")
    r["Observed policy gap (study inference)"] = ". ".join(gaps) + "."
    r["Candidate policy response"] = ". ".join(resp)
    r["Implementation gate"] = ". ".join(gates)
    r["Responsible institution"] = " | ".join(dict.fromkeys(inst))
    r["Regulatory basis"] = " | ".join(dict.fromkeys(basis))
    r["Official citation"] = ", ".join(dict.fromkeys(cite)) + " (D5_POLICY_REGISTER.md)"
    # main-manuscript short version
    cond = (f"Poverty {r['Poverty incidence %, mean (range)'].split(' ')[0]}% (mean). "
            f"MV class among PEA provinces {r['MV class among PEA provinces only (nearer/intermediate/farther)']} "
            f"(nearer/intermediate/farther)" + (f". MEA provinces: {len(mea)}" if mea else ""))
    lead = ["ERC", "PEA"] + (["MEA"] if mea else [])
    if (zp.mv_class != "farther").any(): lead.append("Ministry of Interior (community areas, I2)")
    if z in (z_high, z_low): lead.append("ENCON Fund Committee (I4)")
    main_rows.append({"Zone": z, "Policy-relevant spatial condition": cond,
                      "Observed policy gap (study inference)": r["Observed policy gap (study inference)"],
                      "Candidate response / implementation gate": ". ".join(x[0].upper() + x[1:] for x in resp) + ". Gate: " + ". ".join(x[0].upper() + x[1:] for x in gates) + ".",
                      "Lead institution": ", ".join(lead)})
full = pd.DataFrame(rows)
full.to_csv(out_path("Tables", "zone_policy_table_full_supp.csv"), index=False, encoding="utf-8-sig")
full.to_csv(out_path("Tables", "zone_policy_table_draft.csv"), index=False, encoding="utf-8-sig")
pd.DataFrame(main_rows).to_csv(out_path("Tables", "zone_policy_table_main.csv"), index=False, encoding="utf-8-sig")
print(f"\nhighest-poverty zone = {z_high}, lowest-poverty zone = {z_low}")
for m in main_rows:
    print(f"\nZone {m['Zone']} | {m['Policy-relevant spatial condition']}\n  GAP: {m['Observed policy gap (study inference)']}\n  RESP: {m['Candidate response / implementation gate']}\n  LEAD: {m['Lead institution']}")
