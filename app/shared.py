from pathlib import Path
import polars as pl

app_dir = Path(__file__).parent.parent

DATA_DIR = app_dir / "data" / "model_v5"
META_PATH = DATA_DIR / "12_BAMV5-results_noabundance.xlsx"
IMG_DIR = app_dir / "app" / "img"


def get_species_image(species_id: str) -> Path | None:
    """
    Returns the local file path for a species photo.

    Parameters
    ----------
    species_id : str
        The unique identifier for the species (e.g., 'CAWA').

    Returns
    -------
    Path or None
        The path to the .jpg image if it exists, otherwise None.
    """
    path = IMG_DIR / f"{species_id}.jpg"
    return path if path.exists() else None


def get_tif_path(species_id: str, region: str, year: int) -> Path:
    """
    Construct the path to a specific .tif file.

    Parameters
    ----------
    species_id : str
        The unique identifier for the species.
    region : str
        The geographic region identifier.
    year : int
        The specific model year.

    Returns
    -------
    Path
        The path to the corresponding .tif file.
    """
    filename = f"{species_id}_{region}_{year}.tif"
    return DATA_DIR / species_id / region / filename


def load_species_metadata() -> pl.DataFrame:
    """
    Load species taxonomic and descriptive data from the Excel results summary file.

    Returns
    -------
    pl.DataFrame
        A Polars DataFrame containing the 'species' sheet metadata.
    """
    return pl.read_excel(META_PATH, sheet_name="species")


def available_species() -> list[str]:
    """
    Scan the data directory for all species with available model results.

    Returns
    -------
    list of str
        Sorted list of species IDs based on existing subdirectories in DATA_DIR.
    """
    if not DATA_DIR.exists():
        return []

    return sorted(path.name for path in DATA_DIR.iterdir() if path.is_dir())


def available_regions(species_id: str) -> list[str]:
    """
    Identify geographic regions for which a specific species has model data.

    Parameters
    ----------
    species_id : str
        The unique identifier for the species.

    Returns
    -------
    list of str
        Sorted list of region names found within the species' directory.
    """
    species_dir = DATA_DIR / species_id

    if not species_dir.exists():
        return []

    return sorted(path.name for path in species_dir.iterdir() if path.is_dir())


def available_years(species_id: str, region: str) -> list[int]:
    """
    Parse available model years for a specific species and region by scanning filenames.

    This function looks for .tif files following the naming convention 
    '{species}_{region}_{year}.tif' and extracts the integer year.

    Parameters
    ----------
    species_id : str
        The unique identifier for the species.
    region : str
        The geographic region identifier.

    Returns
    -------
    list of int
        Sorted list of years found for the given parameters.
    """
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
