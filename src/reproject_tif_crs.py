'''
Reproject GeoTIFF model outputs from any CRS to EPSG:4326 (WGS84 lat/lon)
for use in mapping in the dashboard.

Test data: EPSG:3978 (Statistics Canada Lambert) to EPSG:4326 (WGS84 lat/lon) 

Input:   data/raw/*.tif
Output:  data/processed/reprojected/*.tif  (same filename, reprojected)

Run:
  python src/reproject_tif_crs.py                # process all TIFs in data/raw/
  python src/reproject_tif_crs.py --resume       # skip already-reprojected files
  python src/reproject_tif_crs.py --file CAWA_Canada_2020.tif  # single file
'''

import argparse
import time
from pathlib import Path

import rasterio
from rasterio.warp import (
    calculate_default_transform,
    reproject,
    Resampling,
)

# ── Paths ──────────────────────────────────────────────────────────────
_SCRIPT_DIR   = Path(__file__).parent
_PROJECT_ROOT = _SCRIPT_DIR.parent

RAW_DIR        = _PROJECT_ROOT / "data" / "raw"
REPROJECTED_DIR = _PROJECT_ROOT / "data" / "processed" / "reprojected"

TARGET_CRS = "EPSG:4326"

REPROJECTED_DIR.mkdir(parents=True, exist_ok=True)


# ── CLI ────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(
    description="Reproject GeoTIFF files to EPSG:4326 (WGS84 lat/lon)."
)
parser.add_argument(
    "--resume",
    action="store_true",
    help="Skip TIFs that already exist in the output directory.",
)
parser.add_argument(
    "--file",
    type=str,
    default=None,
    help="Process a single file by name (e.g. CAWA_Canada_2020.tif).",
)
args = parser.parse_args()


# ── Core reproject function ────────────────────────────────────────────
def reproject_tif(src_path: Path, dst_path: Path) -> dict:
    """
    Reproject a single TIF to EPSG:4326 and write to dst_path.

    Returns a dict with timing and file size info.
    """
    t0 = time.perf_counter()

    with rasterio.open(src_path) as src:
        src_crs    = src.crs                
        src_nodata = src.nodata            

        # Calculate the transform, width, and height in the target CRS
        transform, width, height = calculate_default_transform(
            src.crs,                       # <= reads whatever CRS is actually in the file
            TARGET_CRS,                   # <= always reprojects TO EPSG:4326
            src.width,
            src.height,
            *src.bounds,
        )

        profile = src.meta.copy()
        profile.update({
            "crs":       TARGET_CRS,
            "transform": transform,
            "width":     width,
            "height":    height,
            "compress":  "lzw",
            "nodata":    src_nodata if src_nodata is not None else -9999,
        })

        with rasterio.open(dst_path, "w", **profile) as dst:
            for band_idx in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, band_idx),
                    destination=rasterio.band(dst, band_idx),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=TARGET_CRS,
                    resampling=Resampling.bilinear,
                )

    elapsed  = time.perf_counter() - t0
    src_mb   = src_path.stat().st_size / 1e6
    dst_mb   = dst_path.stat().st_size / 1e6

    return {
        "src_crs":  str(src_crs),
        "elapsed":  elapsed,
        "src_mb":   src_mb,
        "dst_mb":   dst_mb,
        "width":    width,
        "height":   height,
    }


# ── Collect files to process ───────────────────────────────────────────
if args.file:
    tif_paths = [RAW_DIR / args.file]
    if not tif_paths[0].exists():
        raise FileNotFoundError(f"File not found: {tif_paths[0]}")
else:
    tif_paths = sorted(RAW_DIR.glob("*.tif"))

if not tif_paths:
    print(f"No TIF files found in {RAW_DIR}")
    raise SystemExit(0)

print(f"Found {len(tif_paths)} TIF(s) in {RAW_DIR}")
print(f"Output → {REPROJECTED_DIR}")
print(f"Target CRS: {TARGET_CRS}\n")

if args.resume:
    print("--resume active: skipping already-reprojected files.\n")


# ── Process ────────────────────────────────────────────────────────────
results   = []
skipped   = 0
failed    = []

for src_path in tif_paths:
    dst_path = REPROJECTED_DIR / src_path.name

    if args.resume and dst_path.exists():
        print(f"  [skip] {src_path.name}")
        skipped += 1
        continue

    print(f"  {src_path.name}")

    try:
        info = reproject_tif(src_path, dst_path)

        print(
            f"    {info['src_crs']} → {TARGET_CRS}  |  "
            f"{info['width']}×{info['height']} px  |  "
            f"{info['src_mb']:.1f} MB → {info['dst_mb']:.1f} MB  |  "
            f"{info['elapsed']:.2f}s"
        )

        results.append({"file": src_path.name, **info})

    except Exception as e:
        print(f"    ERROR: {e}")
        failed.append(src_path.name)


# ── Summary ────────────────────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"Processed:  {len(results)}")
print(f"Skipped:    {skipped}")
print(f"Failed:     {len(failed)}")

if results:
    total_time = sum(r["elapsed"] for r in results)
    print(f"Total time: {total_time:.2f}s")

if failed:
    print("\nFailed files:")
    for f in failed:
        print(f"  - {f}")

print(f"\nReprojected TIFs → {REPROJECTED_DIR}")