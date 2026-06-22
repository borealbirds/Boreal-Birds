# Boreal Birds Dashboard

An interactive dashboard for exploring Boreal Avian Modelling (BAM) bird population and habitat model outputs across boreal North America. The project focuses on improving accessibility and interactivity for BAM model visualizations by replacing static outputs with dynamic maps, charts, filters, and summary metrics.

This initiative is a partnership between Masters of Data Science (MDS) students at the University of British Columbia (UBC), in collaboration and consultation with the Boreal Avian Modelling Centre (BAM).

## Features

- Interactive raster map visualizations
- Bird species and region filters
- Summary charts and tables
- Exploration of BAM model outputs (v4, v5, and future versions)
- Jupyter Notebook based exploratory data analysis (EDA)
- Shiny-based dashboard prototype

---

## Project Structure

```bash
.
├── notebooks/          # Jupyter notebooks for EDA and preprocessing
├── data/               # Local data storage (not included in repo)
├── app/                # Shiny dashboard application
├── environment.yml     # Conda environment file
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

https://www.anaconda.com/download/success

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

### Run Jupyter Lab

```bash
jupyter lab
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

- GeoTIFF raster files (.tif)
- CSV observation datasets
- Excel metadata files

Large raster files may require preprocessing into Cloud Optimized GeoTIFFs (COGs) for improved performance.

## Technologies Used

- Python
- Jupyter Notebook
- Shiny for Python
- Pandas
- GeoPandas
- Rasterio
- Leaflet / Plotly
- Conda

## Acknowledgements

This dashboard was developed in collaboration with the UBC Master of Data Science program during the final capstone project. Members of the team included Wesley Beard, Suryash Chakravarty, Harrison Li, and Joel Peterson.

## References

- Boreal Avian Modelling Centre: [www.github.io/boreal-birds](https://borealbirds.github.io/)
- Cloud Optimized GeoTIFF (COG): https://cogeo.org/
- BAM Shiny Explorer: https://borealbirds.shinyapps.io/bam_landbird_explorer/
- Landbird Models V5: https://github.com/borealbirds/LandbirdModelsV5
