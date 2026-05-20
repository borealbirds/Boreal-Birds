'''
Sort a flat directory of TIF files into a structured hierarchy by species and region.

Expects filenames in the format: {SPECIES}_{REGION}_{YEAR}.tif
e.g. ALFL_Canada_2020.tif → ALFL/Canada/ALFL_Canada_2020.tif

Input:   data/raw/          ← flat directory of TIF files
Output:  data/sorted/     ← structured hierarchy

Run:
  python src/sort_tifs.py                # sort all TIFs
  python src/sort_tifs.py --dry-run      # preview moves without touching files
  python src/sort_tifs.py --copy         # copy instead of move
'''

import argparse
import shutil
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────
_SCRIPT_DIR   = Path(__file__).parent
_PROJECT_ROOT = _SCRIPT_DIR.parent

INPUT_DIR  = _PROJECT_ROOT / "data" / "raw"
OUTPUT_DIR = _PROJECT_ROOT / "data" / "sorted"

# ── CLI ────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(
    description="Sort flat TIF files into {SPECIES}/{REGION}/ hierarchy."
)
parser.add_argument(
    "--dry-run",
    action="store_true",
    help="Preview moves without touching any files.",
)
parser.add_argument(
    "--copy",
    action="store_true",
    help="Copy files instead of moving them.",
)
args = parser.parse_args()

action = "copy" if args.copy else "move"

# ── Collect and sort ───────────────────────────────────────────────────
tif_files = sorted(INPUT_DIR.glob("*.tif"))

if not tif_files:
    print(f"No TIF files found in {INPUT_DIR}")
    raise SystemExit(0)

print(f"Found {len(tif_files)} TIF(s) in {INPUT_DIR}")
print(f"Output  → {OUTPUT_DIR}")
print(f"Action  → {action}")
if args.dry_run:
    print("Dry run — no files will be touched.\n")
print()

moved   = 0
skipped = 0
failed  = []

for src in tif_files:
    # ── Parse filename ────────────────────────────────────────────────
    # Expected: {SPECIES}_{REGION}_{YEAR}.tif
    parts = src.stem.split("_")

    if len(parts) != 3:
        print(f"  [skip] {src.name} — unexpected filename format")
        skipped += 1
        continue

    species, region, year = parts
    dst_dir = OUTPUT_DIR / species / region
    dst     = dst_dir / src.name

    # ── Skip if already in place ──────────────────────────────────────
    if dst.exists():
        print(f"  [skip] {src.name} — already exists at destination")
        skipped += 1
        continue

    print(f"  {src.name}  →  {species}/{region}/")

    if not args.dry_run:
        dst_dir.mkdir(parents=True, exist_ok=True)
        try:
            if args.copy:
                shutil.copy2(src, dst)
            else:
                shutil.move(str(src), dst)
            moved += 1
        except Exception as e:
            print(f"    ERROR: {e}")
            failed.append(src.name)
    else:
        moved += 1

# ── Summary ────────────────────────────────────────────────────────────
verb = "Would move" if args.dry_run else ("Copied" if args.copy else "Moved")
print(f"\n{'='*50}")
print(f"{verb}:  {moved}")
print(f"Skipped: {skipped}")
print(f"Failed:  {len(failed)}")

if failed:
    print("\nFailed files:")
    for f in failed:
        print(f"  - {f}")

if not args.dry_run:
    print(f"\nStructured TIFs → {OUTPUT_DIR}")