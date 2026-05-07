from pathlib import Path
import polars as pl

app_dir = Path(__file__).parent.parent

DATA_DIR = app_dir / "data" / "model_v5"
META_PATH = DATA_DIR / "12_BAMV5-results_noabundance.xlsx"


def get_tif_path(species_code: str, region: str, year: int) -> Path:
    filename = f"{species_code}_{region}_{year}.tif"
    return DATA_DIR / species_code / region / filename


def load_v5_metadata() -> pl.DataFrame:
    return pl.read_excel(META_PATH)


def available_species() -> list[str]:
    if not DATA_DIR.exists():
        return []

    return sorted(
        path.name
        for path in DATA_DIR.iterdir()
        if path.is_dir()
    )


def available_regions(species_code: str) -> list[str]:
    species_dir = DATA_DIR / species_code

    if not species_dir.exists():
        return []

    return sorted(
        path.name
        for path in species_dir.iterdir()
        if path.is_dir()
    )


def available_years(species_code: str, region: str) -> list[int]:
    region_dir = DATA_DIR / species_code / region

    if not region_dir.exists():
        return []

    years = []

    prefix = f"{species_code}_{region}_"

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
