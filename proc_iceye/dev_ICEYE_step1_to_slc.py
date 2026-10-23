
from pathlib import Path
import subprocess
import shutil

# Data directory
DATA_DIR = Path("/home/users/ee16eme/data")

# Input ICEYE products
ICEYE_X47_tif = (
    DATA_DIR / "demo_iceye" /
    "ICEYE_3ZYVUU_20251107T213442Z_6951870_X47_SLP2L_SLC.tif"
)

ICEYE_X49_h5 = (
    DATA_DIR / "CS-26350/SLH_10283683_678351" /
    "ICEYE_X49_SLC_SLH_10283683_20260811T011721.h5"
)

# Output directory
working_DIR = DATA_DIR / "fern_iceye"
output_DIR = working_DIR / "slc_data"
working_DIR.mkdir(parents=True, exist_ok=True)
output_DIR.mkdir(parents=True, exist_ok=True)

# Gamma programs in the testing version
TIF_IMPORTER = "par_ICEYE_SLC"
H5_IMPORTER = "par_ICEYE_SLC_HDF5"

# Check input files
for path in (ICEYE_X47_tif, ICEYE_X49_h5):
    if not path.is_file():
        raise FileNotFoundError(path)

# Check Gamma executables
for program in (TIF_IMPORTER, H5_IMPORTER):
    executable = shutil.which(program)
    if executable is None:
        raise RuntimeError(
            f"{program} is not available. "
            "Check that gamma_testing/20260709 is loaded."
        )
    print(f"{program}: {executable}")

def run_gamma(importer, source):
    slc = output_DIR / f"{source.stem}.slc"
    par = output_DIR / f"{source.stem}.slc.par"

    command = [
        importer,
        str(source),
        str(par),
        str(slc),
        "-"
    ]

    print("\nRunning:", " ".join(command), flush=True)

    subprocess.run(command, check=True)

    print("SLC:", slc)
    print("Parameter file:", par)

# Convert ICEYE X47 SLC GeoTIFF
run_gamma(TIF_IMPORTER, ICEYE_X47_tif)

# Convert ICEYE X49 legacy SLC HDF5
run_gamma(H5_IMPORTER, ICEYE_X49_h5)
