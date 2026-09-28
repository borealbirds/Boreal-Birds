"""
Paths to files and folders located in the app directory and remote server.
"""

from pathlib import Path

import requests

# Paths to folders and files located within the app structure
APP_DIR = Path(__file__).parent.parent

CONTENT_DIR = APP_DIR / "content"

WWW_DIR = APP_DIR / "www"

# Paths to folders and files located on DRAC
REMOTE_URL = "https://cloud.borealbirds.ca/"

DASHBOARD_FOLDER_URL = f"{REMOTE_URL}dashboard/"

COG_FOLDER = f"{DASHBOARD_FOLDER_URL}cog_species/"

PREDICTORS_FOLDER = f"{DASHBOARD_FOLDER_URL}Predictors/"

LANDBIRD_V5_RESULTS = f"{DASHBOARD_FOLDER_URL}BAMV5-results.xlsx"

PREDICTOR_INFLUENCE = f"{DASHBOARD_FOLDER_URL}PredictorInfluence.csv"

SPECIES_DATA_PATH = f"{DASHBOARD_FOLDER_URL}SpeciesData_Rounded.csv"

BOUNDARIES_PATH = f"{DASHBOARD_FOLDER_URL}gisdata/Subregions_Mosaics_EPSG4326.shp"

COVARIATE_METADATA = f"{DASHBOARD_FOLDER_URL}covariate_metadata_modelevaluation.csv"

# Only publicly released prediction year; 1990-2015 are available upon request
PREDICTION_YEAR = 2020


def get_tif_path(species_id: str, region: str, year: int) -> str:
    """
    Construct the remote HTTP target URL path to a Cloud Optimized GeoTIFF from filter inputs.

    Parameters
    ----------
    species_id : str
        The unique alpha-numeric lookup identifier code for the species.
    region : str
        The regional sub-boundary identifier string (e.g., 'Canada', 'Alaska').
    year : int
        The target modeling year parameter.

    Returns
    -------
    str
        The absolute concatenated URL address location pointing to the raster file.
    """

    return f"{COG_FOLDER}{species_id}/{region}/{species_id}_{region}_{year}.tif"


# assistants
def url_exists(url: str) -> bool:
    """
    Verify the availability of a specific asset URL on the DRAC server.

    Performs a lightweight HEAD request to verify file existence without
    downloading the payload.

    Parameters
    ----------
    url : str
        The full URL string to evaluate.

    Returns
    -------
    bool
        True if the server responds with status code 200, False otherwise.
    """
    try:
        r = requests.head(url, timeout=10)
        return r.status_code == 200
    except Exception:
        return False