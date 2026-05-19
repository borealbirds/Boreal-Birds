# Preprocessing Test Outputs

## Test 1 `reproject_tif_crs.py`

---

```bash
python src/reproject_tif_crs.py
```

Found 5 TIF(s) in /Boreal-Birds/data/raw
Output → /Boreal-Birds/data/processed/reprojected
Target CRS: EPSG:4326

  AMCR_Canada_2000.tif
    EPSG:3978 → EPSG:4326  |  8371×2656 px  |  82.4 MB → 56.3 MB  |  11.11s
  BBMA_Canada_2015.tif
    EPSG:3978 → EPSG:4326  |  8371×2656 px  |  65.9 MB → 46.2 MB  |  10.22s
  CAWA_Canada_2020.tif
    EPSG:3978 → EPSG:4326  |  8371×2656 px  |  72.9 MB → 50.1 MB  |  11.91s
  OVEN_Canada_1990.tif
    EPSG:3978 → EPSG:4326  |  8371×2656 px  |  66.9 MB → 48.2 MB  |  12.41s
  WIPT_Canada_2005.tif
    EPSG:3978 → EPSG:4326  |  8371×2656 px  |  55.9 MB → 42.6 MB  |  10.97s

==================================================
Processed:  5
Skipped:    0
Failed:     0
Total time: 56.62s

Reprojected TIFs → /Boreal-Birds/data/processed/reprojected


## Test 2 `tif_to_cog.py`:
---
```bash
python src/tif_to_cog.py
```
[PosixPath('../data/processed/reprojected/CAWA_Canada_2020.tif'), PosixPath('../data/processed/reprojected/AMCR_Canada_2000.tif'), PosixPath('../data/processed/reprojected/WIPT_Canada_2005.tif'), PosixPath('../data/processed/reprojected/OVEN_Canada_1990.tif'), PosixPath('../data/processed/reprojected/BBMA_Canada_2015.tif')]
Converting CAWA_Canada_2020.tif to COG
Converting AMCR_Canada_2000.tif to COG
Converting WIPT_Canada_2005.tif to COG
Converting OVEN_Canada_1990.tif to COG
Converting BBMA_Canada_2015.tif to COG
Done.

## Test 3 `tif_reproject_crs_to_cog.py`:
---

```bash
python src/tif_reproject_crs_to_cog.py 
```
Input: /Boreal-Birds/data/raw
Reprojected → /Boreal-Birds/data/processed/reprojected
COG         → /Boreal-Birds/data/processed/cog

  AMCR_Canada_2000.tif
    Reproject: EPSG:3978 → EPSG:4326  |  8371×2656 px  |  82.4 MB → 56.3 MB  |  11.88s
    COG:       56.3 MB → 54.5 MB  |  5.36s

  BBMA_Canada_2015.tif
    Reproject: EPSG:3978 → EPSG:4326  |  8371×2656 px  |  65.9 MB → 46.2 MB  |  11.85s
    COG:       46.2 MB → 43.0 MB  |  4.96s

  CAWA_Canada_2020.tif
    Reproject: EPSG:3978 → EPSG:4326  |  8371×2656 px  |  72.9 MB → 50.1 MB  |  11.76s
    COG:       50.1 MB → 47.6 MB  |  5.24s

  OVEN_Canada_1990.tif
    Reproject: EPSG:3978 → EPSG:4326  |  8371×2656 px  |  66.9 MB → 48.2 MB  |  11.53s
    COG:       48.2 MB → 45.3 MB  |  4.87s

  WIPT_Canada_2005.tif
    Reproject: EPSG:3978 → EPSG:4326  |  8371×2656 px  |  55.9 MB → 42.6 MB  |  11.00s
    COG:       42.6 MB → 39.2 MB  |  5.04s

==================================================
Reprojected: 5
COG:         5
Skipped:     0
Failed:      0
Total time:  83.48s

Reprojected → /Boreal-Birds/data/processed/reprojected
COG         → /Boreal-Birds/data/processed/cog
```

## Reprojection and COG Pipeline

*Raw => Reprojected ~ 30% smaller:*
LZW compression applied + reprojection trims edge pixels outside the valid data extent

*Reprojected => COG ~ 5% smaller:*
Deflate compression packs bytes slightly more efficiently than LZW, plus internal tiling reorganises the file layout

*No data is lost:*
both compressions are lossless, every density value is preserved exactly Smaller files are a side effect, not the goal — the goal is EPSG:4326 coordinates and tile-based reading