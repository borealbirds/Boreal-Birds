"""
Data access layer for the BAM dashboard backend.

Orchestrates data flow between remote data servers, the TiTiler mapping 
gateway, and local disk-backed fallback caches for rasters and tabular files.

Main Capabilities
-----------------
* Monitors the dynamic cloud raster tiler API health status.
* Resolves HTTP URLs for remote Cloud Optimized GeoTIFFs (COGs).
* Extracts and aggregates data tables efficiently using Polars.
* Parses Apache directory listings to scan for available assets.

Notes
-----
All tabular data workflows utilize the high-performance `polars` engine.
"""

import requests
import polars as pl
import yaml
from concurrent.futures import ThreadPoolExecutor

from shared.paths import *


def select_covariate_file(covariate_code: str) -> tuple[str, str]:
    """
    Select csv file for the corresponding covariate code

    Returns
    -------
    tuple of (str, str)
        A tuple of (
            file_url: url linked to the selected covariate file on DRAC, 
            label: continuous/discrete
        )
    """
    base = f"{PREDICTORS_FOLDER}{covariate_code}"

    continuous_url = f"{base}_bootstrap_summary.csv"
    discrete_url = f"{base}_errorbars.csv"

    try:
        r = requests.head(continuous_url, timeout=2)
        if r.status_code == 200:
            return continuous_url, "continuous"
    except Exception:
        pass

    return discrete_url, "discrete"


def load_species_metadata() -> pl.DataFrame:
    """
    Load species taxonomic and descriptive data from the Excel results summary file.

    - lists the species for which results are available
        - id:                   AOU code for the species
        - scientific:           scientific name for the species
        - english:              common name for the species in English
        - french:               common name for the species in French
        - family:               family for the species

    Returns
    -------
    pl.DataFrame
        A Polars DataFrame containing the 'species' sheet metadata.
    """
    return pl.read_excel(LANDBIRD_V5_RESULTS, sheet_name="species")


def load_cog_species(regions: tuple[str, ...] = ("Canada", "Alaska", "Lower48")) -> pl.DataFrame:
    """
    Load the species that have at least one density raster in the cloud cog_species folder.

    The server does not allow directory listings, so the expected raster file
    (cog_species/{id}/{region}/{id}_{region}_{PREDICTION_YEAR}.tif) is checked
    with a HEAD request for each species and region.

    Parameters
    ----------
    regions : tuple of str
        The regions to check for each species.

    Returns
    -------
    pl.DataFrame
        The rows of the 'species' sheet metadata for species with at least one raster.
    """
    species = load_species_metadata()
    session = requests.Session()

    def has_raster(species_id: str) -> bool:
        for region in regions:
            try:
                url = get_tif_path(species_id, region, PREDICTION_YEAR)
                if session.head(url, timeout=10).status_code == 200:
                    return True
            except requests.RequestException:
                pass
        return False

    with ThreadPoolExecutor(max_workers=16) as executor:
        available = list(executor.map(has_raster, species.get_column("id").to_list()))

    return species.filter(pl.Series(available))


def load_covariate_metadata() -> pl.DataFrame:
    """
    Load Covariate metadata and full-form names from the csv file.

    Returns
    -------
    pl.DataFrame
        A Polars DataFrame containing the Covariate metadata.
    """
    return pl.read_csv(COVARIATE_METADATA)


def load_abundance_data() -> pl.DataFrame:
    """
    Load population density estimates from the Excel results summary file.

    - species specific population size (million males) and density estimates (males / ha) by region (density = abundance / area)
        - id:                   AOU code for the species
        - scientific:           scientific name for the species
        - english:              common name for the species in English
        - region:               modelling region
        - year:                 year of prediction, determined by year of covariate prediction layers used
        - population_estimate:  mean population estimate
        - population_lower:     5th percentile of 32 bootstrap population estimate
        - population_upper:     95th percentile of 32 bootstrap population estimate
        - density_estimate:     mean density estimate
        - density_lower:        5th percentile of 32 bootstrap density estimate
        - density_upper:        5th percentile of 32 bootstrap density estimate

    Returns
    -------
    pl.DataFrame
        A Polars DataFrame containing the 'abundances' sheet metadata.
    """
    return pl.read_excel(LANDBIRD_V5_RESULTS, sheet_name="abundances")


def load_importance_data() -> pl.DataFrame:
    """
    Load importance data for each covariate from the Excel results summary file.

    - species specific population size (million males) and density estimates (males / ha) by region (density = abundance / area)
        - id:                   AOU code for the species
        - scientific:           scientific name for the species
        - english:              common name for the species in English
        - region:               modelling region
        - variable:             the covariate of interest, by id
        - importance_mean:      mean importance score for the covariate
        - importance_sd:        std deviation of the importance score for the selected covariate

    Returns
    -------
    pl.DataFrame
        A Polars DataFrame containing the 'importance' sheet metadata.
    """
    return pl.read_excel(LANDBIRD_V5_RESULTS, sheet_name="importance")


def load_region_data() -> pl.DataFrame:
    """
    Load region data from the Excel results summary file.
    
    - lists the individual modelling regions and the mosaiced model regions
        - region:               code for the region (country and bird conservation region number for single model regions)
        - type:                 type of model region (single model vs mosaic of multiple single models)
        - country:              country of the region
        - bcr:                  Bird conservation region (BCR) name
        - area_km2:             area of the region (km2)
        - total_surveys:        total surveys available for the modelling region (including 100km buffer)
        - bootstrap_surveys:    total surveys used for model training per bootsstrap (including 100 km buffer)

    Returns
    -------
    pl.DataFrame
        A Polars DataFrame containing the 'regions' sheet data.
    """

    regions = pl.read_excel(
    LANDBIRD_V5_RESULTS,
    sheet_name="regions",
    columns=["region", "type", "country", "name", "area_km2", "total_surveys", "bootstrap_surveys"]
    )

    regions = regions.with_columns(
        (pl.col("name") + " (" + pl.col("region") + ")").alias("name_adj")
    )
    
    return regions


def read_md(filename) -> str:
    """
    Extract raw text contents out of a localized target Markdown document.

    Parameters
    ----------
    filename : str
        The name of the target file stored under `CONTENT_DIR`.

    Returns
    -------
    str
        The unparsed text content block encoded via UTF-8 rules.
    """
    path = CONTENT_DIR / filename
    return path.read_text(encoding="utf-8")


def read_yaml(filename) -> dict:
    """
    Load and parse a localized target YAML configuration layout file.

    Parameters
    ----------
    filename : str
        The name of the configuration asset stored under `CONTENT_DIR`.

    Returns
    -------
    dict
        A dictionary representation of the parsed YAML document structure.
    """
    path = CONTENT_DIR / filename
    return yaml.safe_load(path.read_text(encoding="utf-8"))
