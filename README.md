# Boreal Birds Dashboard

An interactive dashboard for exploring Boreal Avian Modelling (BAM) bird population and habitat model outputs across boreal North America. The project focuses on improving accessibility and interactivity for BAM model visualizations by replacing static outputs with dynamic maps, charts, filters, and summary metrics.

This initiative is a partnership between Masters of Data Science (MDS) students at the University of British Columbia (UBC), in collaboration and consultation with the Boreal Avian Modelling Centre (BAM).

## Features

- Interactive raster map visualizations
- Bird species and region filters
- Summary charts and tables
- Exploration of BAM Landbird version 5 model outputs
- Shiny-based dashboard

---

## Project Structure

```bash
.
├── app/               # Shiny dashboard application
├── data/              # Local data storage (not included in repo)
├── docs/              # File for GitHub documentation page
├── src/               # Code to retrieve bird sounds and images
├── environment.yml    # Conda environment file
├── Makefile           # Make commands to update and generate .qmd files for documentation
└── README.md
```

## Environment Setup

### Install Miniconda

#### Linux

```bash
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh

bash Miniconda3-latest-Linux-x86_64.sh
```

#### macOS

```bash
curl -O https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-arm64.sh

bash Miniconda3-latest-MacOSX-arm64.sh
```

#### Windows

Download and install Miniconda from:

[https://www.anaconda.com/download/success](https://www.anaconda.com/download/success)

---

### Clone the Repository

```bash
git clone https://github.com/UBC-MDS/Boreal-Birds

cd Boreal-Birds
```

---

### Create and Activate the Conda Environment

```bash
conda env create -f environment.yml

conda activate boreal-birds
```

---

### Run the Shiny Dashboard

```bash
shiny run app/app.py
```

OR

```bash
python app/app.py
```

---

### Deactivate Environment

```bash
conda deactivate
```

## Data Notes

The project uses:

- GeoTIFF raster files (.tif) - optimized into into Cloud Optimized GeoTIFFs (COGs) for improved performance.
- CSV observation datasets
- Excel metadata files

Currently, this data lives and is retrieved from an external server.

## Technologies Used

For a more exhaustive list, please see the environment.yml file.

- Python
- Shiny for Python
- Polars
- GeoPandas
- Rasterio
- Leaflet
- Conda

## Image and Sound Assets

Images and sounds were obtained using APIs from conservation sites.
The images were pulled from iNaturalist using their free API: https://api.inaturalist.org/v1

Sounds were pulled from Xeno-Canto using their free API, and if a suitable sound could not be found within Xeno-Canto, then iNaturalist was used as a fallback. The Xeno-Canto API requires a verified account to be acquired and can be obtained here: https://xeno-canto.org/explore/api

Attributions for the individual images and sounds are displayed with the assets in the image slide modal and spectrogram modal screens. This screen is seen by clicking on an image under the **Info** → **Image** tab for images, and by clicking on the spectrogram under the **Info** → **Sounds** → **Click to expand spectrogram**



## Acknowledgements

This dashboard was developed in collaboration with the UBC Master of Data Science program during the final capstone project.

Members of the team included Wesley Beard, Suryash Chakravarty, Harrison Li, and Joel Nicholas Peterson.

## References

- Boreal Avian Modelling Centre: [Boreal Birds](https://borealbirds.github.io/)
- Cloud Optimized GeoTIFF (COG): [cogeo.org](https://cogeo.org/)
- BAM Shiny Explorer: [BAM Landbird Explorer](https://borealbirds.shinyapps.io/bam_landbird_explorer/)
- Landbird Models V5: [Landbird Models V5](https://github.com/borealbirds/LandbirdModelsV5)
- [Xeno-Canto](https://xeno-canto.org/)
- [iNaturalist](https://www.inaturalist.org/)
- [eBird](https://ebird.org/home)
- [NatureCounts](https://www.naturecounts.ca/nc/default/main.jsp)