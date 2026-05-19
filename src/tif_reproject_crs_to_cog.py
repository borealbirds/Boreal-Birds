'''
Full TIF preprocessing pipeline: reproject CRS => EPSG:4326 | TIF => COG 

Runs both steps in sequence:
Reprojects from EPSG:3978 => EPSG:4326 then converts to Cloud Optimized GeoTIFF (COG).
Both compressions are lossless — files reduce in size as a side effect, no data is lost.
 
Input:   data/raw/*.tif
Output:  data/processed/reprojected/*.tif  (after step 1)
         data/processed/cog/*.tif          (after step 2)
 
Run:
  python src/tif_reproject_crs_to_cog.py                              # all TIFs
  python src/tif_reproject_crs_to_cog.py --resume                     # skip completed
  python src/tif_reproject_crs_to_cog.py --file CAWA_Canada_2020.tif  # single file
  python src/tif_reproject_crs_to_cog.py --skip-reproject             # COG only
'''


import argparse
import time
from pathlib import Path

import rasterio
from rasterio.shutil import copy as rio_copy
from rasterio.warp import calculate_default_transform, reproject, Resampling

# ── Paths ──────────────────────────────────────────────────────────────
_SCRIPT_DIR    = Path(__file__).parent
_PROJECT_ROOT  = _SCRIPT_DIR.parent

RAW_DIR         = _PROJECT_ROOT / "data" / "raw"
REPROJECTED_DIR = _PROJECT_ROOT / "data" / "processed" / "reprojected"
COG_DIR         = _PROJECT_ROOT / "data" / "processed" / "cog"

TARGET_CRS = "EPSG:4326"

REPROJECTED_DIR.mkdir(parents=True, exist_ok=True)
COG_DIR.mkdir(parents=True, exist_ok=True)


# ── CLI ────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(
    description="Reproject GeoTIFF files to EPSG:4326 then convert to COG."
)
parser.add_argument(
    "--resume",
    action="store_true",
    help="Skip files already present in the output directories.",
)
parser.add_argument(
    "--file",
    type=str,
    default=None,
    help="Process a single file by name (e.g. CAWA_Canada_2020.tif).",
)
parser.add_argument(
    "--skip-reproject",
    action="store_true",
    help="Skip step 1 — use already-reprojected files in data/processed/reprojected/.",
)
args = parser.parse_args()


# ── Step 1: Reproject ──────────────────────────────────────────────────
def reproject_tif(src_path: Path, dst_path: Path) -> dict:
    """
    Reproject a single TIF from its source CRS to EPSG:4326.
    Returns a dict with timing and file size info.
    """
    t0 = time.perf_counter()

    with rasterio.open(src_path) as src:
        src_crs    = src.crs
        src_nodata = src.nodata

        transform, width, height = calculate_default_transform(
            src.crs, TARGET_CRS,
            src.width, src.height,
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

    elapsed = time.perf_counter() - t0
    return {
        "src_crs": str(src_crs),
        "elapsed": elapsed,
        "src_mb":  src_path.stat().st_size / 1e6,
        "dst_mb":  dst_path.stat().st_size / 1e6,
        "width":   width,
        "height":  height,
    }


# ── Step 2: Convert to COG ─────────────────────────────────────────────
def convert_to_cog(src_path: Path, dst_path: Path) -> dict:
    """
    Convert a reprojected TIF to Cloud Optimized GeoTIFF (COG).
    Returns a dict with timing and file size info.
    """
    t0 = time.perf_counter()

    with rasterio.open(src_path) as src:
        profile = src.profile.copy()
        profile.update(
            driver="COG",
            compress="deflate",
            blocksize=512,
            overview_resampling="nearest",
        )
        rio_copy(src, dst_path, **profile)

    elapsed = time.perf_counter() - t0
    return {
        "elapsed": elapsed,
        "src_mb":  src_path.stat().st_size / 1e6,
        "dst_mb":  dst_path.stat().st_size / 1e6,
    }


# ── Collect files ──────────────────────────────────────────────────────
if args.file:
    raw_paths = [RAW_DIR / args.file]
    if not args.skip_reproject and not raw_paths[0].exists():
        raise FileNotFoundError(f"File not found: {raw_paths[0]}")
else:
    raw_paths = sorted(RAW_DIR.glob("*.tif"))

if not args.skip_reproject and not raw_paths:
    print(f"No TIF files found in {RAW_DIR}")
    raise SystemExit(0)

print(f"{'Skipping reproject — reading from' if args.skip_reproject else 'Input'}: "
      f"{REPROJECTED_DIR if args.skip_reproject else RAW_DIR}")
print(f"Reprojected → {REPROJECTED_DIR}")
print(f"COG         → {COG_DIR}")
if args.resume:
    print("--resume active: skipping completed files.\n")


# ── Run pipeline ───────────────────────────────────────────────────────
reproject_results = []
cog_results       = []
skipped           = 0
failed            = []

# Determine which files to process
if args.skip_reproject:
    if args.file:
        process_paths = [REPROJECTED_DIR / args.file]
    else:
        process_paths = sorted(REPROJECTED_DIR.glob("*.tif"))
else:
    process_paths = raw_paths

for src_path in process_paths:
    filename     = src_path.name
    reproj_path  = REPROJECTED_DIR / filename
    cog_path     = COG_DIR / filename

    print(f"\n  {filename}")

    # ── Step 1: Reproject ────────────────────────────────────────────
    if not args.skip_reproject:
        if args.resume and reproj_path.exists():
            print(f"    [skip reproject] already exists")
            skipped += 1
        else:
            try:
                info = reproject_tif(src_path, reproj_path)
                reproject_results.append({"file": filename, **info})
                print(
                    f"    Reproject: {info['src_crs']} → {TARGET_CRS}  |  "
                    f"{info['width']}×{info['height']} px  |  "
                    f"{info['src_mb']:.1f} MB → {info['dst_mb']:.1f} MB  |  "
                    f"{info['elapsed']:.2f}s"
                )
            except Exception as e:
                print(f"    Reproject ERROR: {e}")
                failed.append(filename)
                continue

    # ── Step 2: COG ──────────────────────────────────────────────────
    if args.resume and cog_path.exists():
        print(f"    [skip COG] already exists")
    else:
        try:
            info = convert_to_cog(reproj_path, cog_path)
            cog_results.append({"file": filename, **info})
            print(
                f"    COG:       {info['src_mb']:.1f} MB → {info['dst_mb']:.1f} MB  |  "
                f"{info['elapsed']:.2f}s"
            )
        except Exception as e:
            print(f"    COG ERROR: {e}")
            failed.append(filename)


# ── Summary ────────────────────────────────────────────────────────────
total_time = (
    sum(r["elapsed"] for r in reproject_results) +
    sum(r["elapsed"] for r in cog_results)
)

print(f"\n{'='*50}")
print(f"Reprojected: {len(reproject_results)}")
print(f"COG:         {len(cog_results)}")
print(f"Skipped:     {skipped}")
print(f"Failed:      {len(failed)}")
print(f"Total time:  {total_time:.2f}s")

if failed:
    print("\nFailed files:")
    for f in failed:
        print(f"  - {f}")

print(f"\nReprojected → {REPROJECTED_DIR}")
print(f"COG         → {COG_DIR}")