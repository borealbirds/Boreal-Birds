# Model Output Preprocessing — Running Instructions

These scripts reproject and/or convert TIF outputs for use in the
interactive dashboard. Run them once whenever new model outputs are received.

---

## 1 · Prerequisites

**Install conda** (if not already installed):
https://docs.conda.io/en/latest/miniconda.html

**Create the environment: (from the environment.yml file)**
```bash
conda env create -f environment.yml
```

**Activate it:**
```bash
conda activate bird
```

---

## 2 · Directory Structure

Place raw TIF files in `data/raw/` before running the scripts.

```
Boreal-Birds/
├── data/
│   ├── raw/                        ← place raw TIFs here
│   │   ├── CAWA_Canada_2020.tif
│   │   ├── AMCR_Canada_2000.tif
│   │   └── ...
│   └── processed/
│       ├── reprojected/            ← auto-created: EPSG:4326 outputs
│       └── cog/                    ← auto-created: Cloud Optimized GeoTIFF outputs
└── src/
    ├── tif_reproject_crs_to_cog.py ← full pipeline (recommended)
    ├── reproject_tif_crs.py        ← step 1 only
    └── tif_to_cog.py               ← step 2 only
```

TIF files must follow the naming convention: `{SPECIES}_{REGION}_{YEAR}.tif`
e.g. `CAWA_Canada_2020.tif`

---

## 3 · Running the Pipeline

### Full pipeline — reproject + COG (recommended)

Process all TIFs in `data/raw/`:
```bash
python src/tif_reproject_crs_to_cog.py
```

Process a single species:
```bash
python src/tif_reproject_crs_to_cog.py --file CAWA_Canada_2020.tif
```

Resume after an interruption (skips already-processed files):
```bash
python src/tif_reproject_crs_to_cog.py --resume
```

COG conversion only (if files are already reprojected):
```bash
python src/tif_reproject_crs_to_cog.py --skip-reproject
```

### Individual steps

Reproject only:
```bash
python src/reproject_tif_crs.py
python src/reproject_tif_crs.py --resume
python src/reproject_tif_crs.py --file CAWA_Canada_2020.tif
```

COG conversion only:
```bash
python src/tif_to_cog.py
```

---

## 4 · Expected Output

Each file prints a summary line as it completes:

```
  CAWA_Canada_2020.tif
    Reproject: EPSG:3978 → EPSG:4326  |  8371×2656 px  |  72.9 MB → 50.1 MB  |  10.3s
    COG:       50.1 MB → 47.6 MB  |  4.5s
```

Final summary:
```
==================================================
Reprojected: 5
COG:         5
Skipped:     0
Failed:      0
Total time:  94.3s
```

Typical processing time is **15–25 seconds per species** depending on file size.

---

## 5 · Verify Outputs

After processing, verify a file is correctly reprojected and COG-formatted:

```bash
python3 -c "
import rasterio
with rasterio.open('data/processed/cog/CAWA_Canada_2020.tif') as src:
    print('Driver:    ', src.driver)
    print('CRS:       ', src.crs)
    print('Block shapes:', src.block_shapes)
    print('Overviews: ', src.overviews(1))
    print('Compression:', src.compression)
"
```

Expected output:
```
Driver:     GTiff
CRS:        EPSG:4326
Block shapes: [(512, 512), (512, 512), (512, 512)]
Overviews:  [2, 4, 8, 16, 32]
Compression: Compression.deflate
```

---

## 6 · Troubleshooting

**`No TIF files found in data/raw/`**
→ Make sure raw TIF files are placed in `data/raw/` before running.

**`Illegal instruction` on startup**
→ Polars CPU compatibility issue. The environment uses `polars-lts-cpu`
  which resolves this. Recreate the environment from `environment.yml`.

**`ModuleNotFoundError`**
→ Make sure the `bird` conda environment is active: `conda activate bird`

**Script runs but CRS is not EPSG:4326**
→ Raw TIFs may already be in a different projection. Check with:
  `python3 -c "import rasterio; src = rasterio.open('data/raw/YOUR.tif'); print(src.crs)"`