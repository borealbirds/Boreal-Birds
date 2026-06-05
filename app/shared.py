import requests
import polars as pl
from io import BytesIO
import geopandas as gpd
from pathlib import Path
from bs4 import BeautifulSoup
from functools import lru_cache
from urllib.parse import urljoin
import yaml


app_dir = Path(__file__).parent.parent

REMOTE_DATA_FOLDER = "dashboard/"
BASE_URL = f"http://206.12.92.143/data/{REMOTE_DATA_FOLDER}"
DATA_DIR = app_dir / "data"
CONTENT_DIR = Path(__file__).parent / "content"
V5_META_PATH = DATA_DIR / "model_v5" / "12_BAMV5-results.xlsx"
BOUNDARIES_PATH = DATA_DIR / "boundaries" / "Subregions_Mosaics_EPSG3978.shp"
COVARIATE_MTDATA = DATA_DIR / "model_v5" / "covariate_metadata_modelevaluation - covariates_label.csv"
MARGINAL_FX_DIR = DATA_DIR / "model_v5" / "marginaleffects"

def get_tif_path(species_id: str, region: str, year: int) -> str:
    """
    Construct the HTTP URL to a specific .tif file.
    """

    filename = f"{species_id}_{region}_{year}.tif"

    return urljoin(
        BASE_URL,
        f"{species_id}/{region}/{filename}"
    )

def get_cov_fx_data(covs: list) -> pl.DataFrame:
    """
    Return the associated marginal effects file for the selected covariates.
    """
    
    filePath = MARGINAL_FX_DIR / covs[0] / "marginalsv5_gampredictions.csv" # "marginalsv5.csv"
    
    df =  pl.read_csv(filePath)

    if len(covs) > 1:
        for i in range(1,len(covs)):
            filePath_1 = MARGINAL_FX_DIR / covs[i] / "marginalsv5_gampredictions.csv" # "marginalsv5.csv"
            df_1 = pl.read_csv(filePath_1)
            df = df.vstack(df_1).rechunk()
    
    return df

@lru_cache(maxsize=1)
def load_subregion_boundaries() -> gpd.GeoDataFrame:
    """
    Load and preprocess ecological subregion boundaries for leaflet rendering.

    Returns
    -------
    gpd.GeoDataFrame
        Simplified subregion polygons in EPSG:4326.
    """

    gdf = gpd.read_file(BOUNDARIES_PATH)

    # convert from EPSG:3978 to EPSG:4326
    gdf = gdf.to_crs(epsg=4326)

    # simplify boundaries to load faster
    gdf["geometry"] = gdf.geometry.simplify(0.01)

    return gdf

def load_species_metadata() -> pl.DataFrame:
    """
    Load species taxonomic and descriptive data from the Excel results summary file.

    Returns
    -------
    pl.DataFrame
        A Polars DataFrame containing the 'species' sheet metadata.
    """
    return pl.read_excel(V5_META_PATH, sheet_name="species")

def load_covariate_metadata() -> pl.DataFrame:
    """
    Load Covariate metadata and full-form names from the csv file.

    Returns
    -------
    pl.DataFrame
        A Polars DataFrame containing the Covariate metadata.
    """
    return pl.read_csv(COVARIATE_MTDATA)

def load_abundance_data() -> pl.DataFrame:
    """
    Load species taxonomic and descriptive data from the Excel results summary file.

    Returns
    -------
    pl.DataFrame
        A Polars DataFrame containing the 'species' sheet metadata.
    """
    return pl.read_excel(V5_META_PATH, sheet_name="abundances")

def load_region_data() -> pl.DataFrame:
    """Load region-level data from the Excel results summary file.

    Returns
    -------
    pl.DataFrame
        A Polars DataFrame containing the 'regions' sheet data.
    """

    regions = pl.read_excel(
    V5_META_PATH,
    sheet_name="regions",
    columns=["region", "type", "country", "name", "area_km2", "total_surveys", "bootstrap_surveys"]
    )

    regions = regions.with_columns(
        (pl.col("name") + " (" + pl.col("region") + ")").alias("name_adj")
    )
    
    return regions

def list_directory(url: str) -> list[str]:
    """
    Parse Apache directory listing and return entries.
    """

    response = requests.get(url, timeout=60)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    entries = []

    for link in soup.find_all("a"):
        href = link.get("href")

        if href not in [None, "../", '/data/', '?C=N;O=D', '?C=M;O=A', '?C=S;O=A', '?C=D;O=A', f'/data/{REMOTE_DATA_FOLDER}']:
            entries.append(href.rstrip("/"))
            continue

    return entries

def species_ids() -> list[str]:
    """
    Scan the data directory for all species with available model results and 
    list available species IDs from remote Apache directory.

    Returns
    -------
    list of str
        Sorted list of species IDs based on existing subdirectories in DATA_DIR.
    """
    try:
        entries = list_directory(BASE_URL)
        return sorted(entries)

    except Exception:
        return []

def available_regions(species_id: str) -> list[str]:
    """
    Identify geographic regions for a specific species and 
    list available regions from remote Apache directory.

    Parameters
    ----------
    species_id : str
        The unique identifier for the species.

    Returns
    -------
    list of str
        Sorted list of region names found within the species' directory.
    """
    species_url = urljoin(BASE_URL, f"{species_id}/")
    try:
        entries = list_directory(species_url)
        if entries:
            return sorted(entries)
    except Exception as e:
        print(f"[available_regions] Remote unavailable for {species_id}: {e}")

    # Local fallback — scan data/model_v5/{species_id}/
    local_dir = DATA_DIR / "model_v5" / species_id
    if local_dir.exists():
        regions = sorted([d.name for d in local_dir.iterdir() if d.is_dir()])
        if regions:
            print(f"[available_regions] Using local data for {species_id}: {regions}")
            return regions

    print(f"[available_regions] No data found for {species_id}")
    return []

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
    region_url = urljoin(BASE_URL, f"{species_id}/{region}/")

    try:
        entries = list_directory(region_url)
        years = []
        prefix = f"{species_id}_{region}_"
        for filename in entries:
            if not filename.endswith(".tif"):
                continue
            stem = filename.removesuffix(".tif")
            if not stem.startswith(prefix):
                continue
            try:
                years.append(int(stem.removeprefix(prefix)))
            except ValueError:
                continue
        if years:
            return sorted(years)
    except Exception as e:
        print(f"[available_years] Remote unavailable for {species_id}/{region}: {e}")

    # Local fallback — scan data/model_v5/{species_id}/{region}/
    local_dir = DATA_DIR / "model_v5" / species_id / region
    if local_dir.exists():
        years = []
        prefix = f"{species_id}_{region}_"
        for tif in local_dir.glob("*.tif"):
            stem = tif.stem
            if not stem.startswith(prefix):
                continue
            try:
                years.append(int(stem.removeprefix(prefix)))
            except ValueError:
                continue
        if years:
            print(f"[available_years] Using local data for {species_id}/{region}: {sorted(years)}")
            return sorted(years)

    print(f"[available_years] No years found for {species_id}/{region}")
    return []

def read_md(filename):
    """
    Read the contents of a markdown file from the content directory.
    """
    path = CONTENT_DIR / filename
    return path.read_text(encoding="utf-8")

def read_yaml(filename):
    """
    Read the contents of a YAML file from the content directory and parse it.
    """
    path = CONTENT_DIR / filename
    return yaml.safe_load(path.read_text(encoding="utf-8"))