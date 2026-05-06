from pathlib import Path
import rasterio
from rasterio.shutil import copy as rio_copy
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)

INPUT_DIR = Path("../sample_data/model_predictions")
OUTPUT_DIR = Path("../sample_data/model_predictions_cog")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def convert_to_cog(src_path: Path, dst_path: Path):
    with rasterio.open(src_path) as src:
        profile = src.profile.copy()

        # Update profile for COG
        profile.update(
            driver="COG",
            compress="deflate", 
            blocksize=512, 
            overview_resampling="nearest"
        )

        rio_copy(
            src,
            dst_path,
            **profile
        )


def main():
    tif_files = list(INPUT_DIR.glob("*.tif"))
    print(tif_files)

    for tif in tif_files:
        out_file = OUTPUT_DIR / tif.name

        print(f"Converting {tif.name} to COG")

        convert_to_cog(tif, out_file)

    print("Done.")


if __name__ == "__main__":
    main()