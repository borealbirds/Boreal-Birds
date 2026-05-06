from pathlib import Path

app_dir = Path(__file__).parent.parent

DATA_DIR = app_dir / "sample_data" / "model_predictions_cog"

def get_tif_path(species_code: str, region: str, year: int) -> Path:
    filename = f"{species_code}_{region}_{year}.tif"
    print(DATA_DIR / filename)
    return DATA_DIR / filename