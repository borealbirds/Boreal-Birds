from pathlib import Path
import polars as pl

app_dir = Path(__file__).parent.parent

DATA_DIR = app_dir / "data" / "model_v5"
META_PATH = DATA_DIR / "12_BAMV5-results_noabundance.xlsx"
IMG_DIR = app_dir / "app" / "img"


def get_species_image(species_id: str) -> Path | None:
    path = IMG_DIR / f"{species_id}.jpg"
    return path if path.exists() else None


def get_tif_path(species_id: str, region: str, year: int) -> Path:
    filename = f"{species_id}_{region}_{year}.tif"
    return DATA_DIR / species_id / region / filename


def load_species_metadata() -> pl.DataFrame:
    return pl.read_excel(META_PATH, sheet_name="species")


def available_species() -> list[str]:
    if not DATA_DIR.exists():
        return []

    return sorted(path.name for path in DATA_DIR.iterdir() if path.is_dir())


def available_regions(species_id: str) -> list[str]:
    species_dir = DATA_DIR / species_id

    if not species_dir.exists():
        return []

    return sorted(path.name for path in species_dir.iterdir() if path.is_dir())


def available_years(species_id: str, region: str) -> list[int]:
    region_dir = DATA_DIR / species_id / region

    if not region_dir.exists():
        return []

    years = []

    prefix = f"{species_id}_{region}_"

    for tif_path in region_dir.glob("*.tif"):
        stem = tif_path.stem

        if not stem.startswith(prefix):
            continue

        try:
            year = int(stem.removeprefix(prefix))
            years.append(year)
        except ValueError:
            continue

    return sorted(years)
