"""
Real-world Spatial Validation — OSM Solar Plants vs PAI Zones
==============================================================
Tests whether existing solar farm locations (OSM) concentrate in
high-priority PAI zones more than expected by random placement.

Method:
  1. Extract solar plant points (generator:source=solar) from OSM plants.geojson
  2. Sample PAI zone for each plant location
  3. Compare observed zone distribution to expected (proportional to zone area)
  4. Chi-square test of observed vs. expected distribution
  5. Enrichment factor per zone = observed_fraction / expected_fraction
  6. Spearman rank correlation: province PAI rank vs. solar plant count
"""

import json
import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import rowcol
import geopandas as gpd
import fiona
from rasterstats import zonal_stats
from scipy.stats import spearmanr, chi2_contingency
from shapely.geometry import shape, Point
from pathlib import Path
import os
import warnings
warnings.filterwarnings("ignore")

BASE  = Path(os.environ.get("ENERGY_DATA_ROOT", r"D:\Clude Code GIS\Energy"))
PROC  = BASE / "DER" / "Data" / "14_Processed_90m"
GADM  = BASE / "DER" / "Data" / "01_Admin_Boundaries" / "gadm41_THA.gpkg"
PLANTS_GEOJSON = BASE / "Energy map" / "GridNetwork_OSM" / "plants.geojson"
NODATA = -9999.0

# ── Load solar plant points ───────────────────────────────────────────────────
print("Loading OSM solar plant locations...")
with open(PLANTS_GEOJSON, encoding="utf-8") as fh:
    data = json.load(fh)

solar_pts = []
for ft in data["features"]:
    props = ft.get("properties", {})
    src = (props.get("generator:source") or props.get("plant:source") or
           props.get("power_source") or "")
    if src.lower() != "solar":
        continue
    geom = ft.get("geometry")
    if geom is None:
        continue
    shp = shape(geom)
    # Use centroid for polygon features
    pt = shp.centroid if shp.geom_type != "Point" else shp
    if pt.is_empty or pt.x == 0.0:
        continue
    solar_pts.append({
        "lon": pt.x,
        "lat": pt.y,
        "name": props.get("name", ""),
        "capacity_mw": props.get("plant:output:electricity") or props.get("capacity", ""),
    })

solar_gdf = gpd.GeoDataFrame(
    solar_pts,
    geometry=[Point(p["lon"], p["lat"]) for p in solar_pts],
    crs="EPSG:4326"
)
print(f"  Solar plants with valid geometry: {len(solar_gdf)}")

# Clip to Thailand bbox
solar_gdf = solar_gdf.cx[97.5:106.0, 5.0:21.0]
print(f"  After Thailand bbox clip: {len(solar_gdf)}")

# ── Load PAI zone raster ───────────────────────────────────────────────────────
print("Loading PAI zone raster...")
with rasterio.open(PROC / "DER_zones_90m.tif") as src:
    zone_arr = src.read(1)
    tfm      = src.transform
    crs      = src.crs
    nd       = src.nodata if src.nodata is not None else 0

# Pixel counts per zone (for expected distribution)
zone_counts = {}
for z in range(1, 6):
    zone_counts[z] = int((zone_arr == z).sum())
total_land_px = sum(zone_counts.values())
zone_area_frac = {z: zone_counts[z] / total_land_px for z in range(1, 6)}

print(f"  Land pixels: {total_land_px:,}")
for z in range(1, 6):
    print(f"  Zone {z}: {zone_counts[z]:,} px ({zone_area_frac[z]*100:.1f}%)")

# ── Sample zone for each solar plant ──────────────────────────────────────────
print("\nSampling PAI zones for solar plants...")
plant_zones = []
for _, row in solar_gdf.iterrows():
    try:
        r, c = rowcol(tfm, row.geometry.x, row.geometry.y)
        if 0 <= r < zone_arr.shape[0] and 0 <= c < zone_arr.shape[1]:
            z = int(zone_arr[r, c])
            plant_zones.append(z if z > 0 else np.nan)
        else:
            plant_zones.append(np.nan)
    except Exception:
        plant_zones.append(np.nan)

solar_gdf["zone"] = plant_zones
valid = solar_gdf.dropna(subset=["zone"])
valid["zone"] = valid["zone"].astype(int)
print(f"  Plants with valid zone: {len(valid)} / {len(solar_gdf)}")

# ── Zone distribution analysis ─────────────────────────────────────────────────
print("\n=== Zone Distribution of Solar Plants ===")
obs_counts = valid["zone"].value_counts().sort_index().reindex(range(1, 6), fill_value=0)
n_total    = obs_counts.sum()
exp_counts = pd.Series({z: zone_area_frac[z] * n_total for z in range(1, 6)})

print(f"\n  {'Zone':<6} {'Observed':>10} {'Obs%':>8} {'Expected%':>10} {'Enrichment':>11}")
enrich = {}
for z in range(1, 6):
    obs_pct = obs_counts[z] / n_total * 100
    exp_pct = zone_area_frac[z] * 100
    ef      = (obs_counts[z] / n_total) / zone_area_frac[z] if zone_area_frac[z] > 0 else 0
    enrich[z] = ef
    print(f"  Zone {z}    {obs_counts[z]:>10}  {obs_pct:>7.1f}%  {exp_pct:>9.1f}%  {ef:>11.3f}x")

# Chi-square test
chi2, p_chi2, dof, _ = chi2_contingency(
    np.array([[obs_counts[z], max(1, int(exp_counts[z]))] for z in range(1, 6)])
)
print(f"\n  Chi-square = {chi2:.3f}  df={dof}  p={p_chi2:.4f}")

# Zone 1+2 recall
recall_12 = (obs_counts[1] + obs_counts[2]) / n_total * 100
exp_12    = (zone_area_frac[1] + zone_area_frac[2]) * 100
print(f"\n  Solar plants in Zone 1+2 : {obs_counts[1]+obs_counts[2]}/{n_total} ({recall_12:.1f}%)")
print(f"  Expected if random       : {exp_12:.1f}%")
print(f"  Enrichment (Zone 1+2)    : {recall_12/exp_12:.3f}x")

zone1_recall = obs_counts[1] / n_total * 100
print(f"\n  Solar plants in Zone 1   : {obs_counts[1]}/{n_total} ({zone1_recall:.1f}%)")
print(f"  Expected if random       : {zone_area_frac[1]*100:.1f}%")
print(f"  Enrichment (Zone 1)      : {enrich[1]:.3f}x")

# ── Province-level: PAI rank vs solar plant count ─────────────────────────────
print("\n=== Province-level: PAI rank vs Solar Count ===")
layers = fiona.listlayers(str(GADM))
adm1   = next(l for l in layers if l.endswith("_1"))
prov   = gpd.read_file(str(GADM), layer=adm1)[["GID_1","NAME_1","geometry"]].copy()
if prov.crs.to_epsg() != 4326:
    prov = prov.to_crs("EPSG:4326")

# Spatial join solar plants to provinces
joined = gpd.sjoin(valid, prov, how="left", predicate="within")
solar_per_prov = joined.groupby("NAME_1").size().reset_index(name="solar_count")

# Load PAI province summary
pai_df = pd.read_csv(PROC / "province_PAI_summary.csv")
merged = pai_df.merge(solar_per_prov, on="NAME_1", how="left")
merged["solar_count"] = merged["solar_count"].fillna(0).astype(int)

rho, p_rho = spearmanr(merged["PAI"], merged["solar_count"])
print(f"\n  Spearman rho(PAI, solar_count) = {rho:.4f}  p={p_rho:.4f}  n=77")

# Top 10 provinces by solar plant count
top10 = merged.nlargest(10, "solar_count")[["NAME_1","rank","PAI","solar_count","dominant_zone"]]
print("\n  Top 10 provinces by OSM solar plant count:")
print(top10.to_string(index=False))

# Provinces with >10 solar plants and their PAI zone
heavy = merged[merged["solar_count"] >= 5].sort_values("solar_count", ascending=False)
print(f"\n  Provinces with >=5 solar plants: {len(heavy)}")
print(heavy[["NAME_1","rank","PAI","solar_count","dominant_zone"]].to_string(index=False))

# ── Summary for paper ──────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("SUMMARY FOR PAPER")
print("=" * 60)
print(f"  Total solar plants validated : {n_total}")
print(f"  Zone 1 recall                : {zone1_recall:.1f}% (expected {zone_area_frac[1]*100:.1f}%, enrichment {enrich[1]:.2f}x)")
print(f"  Zone 1+2 recall              : {recall_12:.1f}% (expected {exp_12:.1f}%, enrichment {recall_12/exp_12:.2f}x)")
print(f"  Chi-square p-value           : {p_chi2:.4f}")
print(f"  Province-level rho           : {rho:.4f}  (p={p_rho:.4f})")

# ── Save ──────────────────────────────────────────────────────────────────────
out = merged[["NAME_1","rank","PAI","dominant_zone","solar_count"]].copy()
out.to_csv(PROC / "validation_solar_osm.csv", index=False, encoding="utf-8-sig")
print(f"\nSaved: {PROC / 'validation_solar_osm.csv'}")

zone_tbl = pd.DataFrame({
    "zone": list(range(1, 6)),
    "land_pct": [zone_area_frac[z]*100 for z in range(1, 6)],
    "solar_obs": [obs_counts[z] for z in range(1, 6)],
    "solar_obs_pct": [obs_counts[z]/n_total*100 for z in range(1, 6)],
    "enrichment": [enrich[z] for z in range(1, 6)],
})
zone_tbl.to_csv(PROC / "validation_zone_distribution.csv", index=False)
print(f"Saved: {PROC / 'validation_zone_distribution.csv'}")
print("\n=== COMPLETE ===")
