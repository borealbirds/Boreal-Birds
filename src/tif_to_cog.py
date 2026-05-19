'''
Convert TIF outputs to Cloud Optimized GeoTIFF (COG) format
for efficient tile-based reading in the dashboard.

COG restructures the TIF with internal tiling and pre-built overviews so
the dashboard only reads the tiles covering the current map extent at the
matching zoom level — rather than decoding the entire file on every render.

Input:   data/processed/reprojected/*.tif  (run reproject_tif_crs.py first)
Output:  data/processed/cog/*.tif          (same filename, COG format)

Run:
  python src/tif_to_cog.py                 # convert all reprojected TIFs
'''

import time
import rasterio
from rasterio.shutil import copy as rio_copy
from pathlib import Path
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)

INPUT_DIR  = Path("../data/processed/reprojected")
OUTPUT_DIR = Path("../data/processed/cog")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def convert_to_cog(src_path: Path, dst_path: Path):
    with rasterio.open(src_path) as src:
        profile = src.profile.copy()

        # Update profile for COG
        profile.update(
            driver="COG",
            compress="deflate",
            blocksize=512,
            overview_resampling="nearest"
        )

        rio_copy(
            src,
            dst_path,
            **profile
        )


def main():
    tif_files = sorted(INPUT_DIR.glob("*.tif"))

    if not tif_files:
        print(f"No TIF files found in {INPUT_DIR}")
        return

    print(f"Found {len(tif_files)} TIF(s) in {INPUT_DIR}\n")

    failed = []
    total_start = time.perf_counter()

    for tif in tif_files:
        out_file = OUTPUT_DIR / tif.name
        print(f"  {tif.name}")
        t0 = time.perf_counter()
        try:
            convert_to_cog(tif, out_file)
            elapsed = time.perf_counter() - t0
            src_mb = tif.stat().st_size / 1e6
            dst_mb = out_file.stat().st_size / 1e6
            print(f"    {src_mb:.1f} MB → {dst_mb:.1f} MB  |  {elapsed:.2f}s")
        except Exception as e:
            print(f"    ERROR: {e}")
            failed.append(tif.name)

    total_time = time.perf_counter() - total_start
    print(f"\n{'='*50}")
    print(f"Converted: {len(tif_files) - len(failed)}")
    print(f"Failed:    {len(failed)}")
    print(f"Total time: {total_time:.2f}s")

    if failed:
        print("\nFailed files:")
        for f in failed:
            print(f"  - {f}")

    print(f"\nCOG outputs → {OUTPUT_DIR}")


if __name__ == "__main__":
    main()