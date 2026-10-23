
from pathlib import Path
import subprocess
import shutil
import os

# Data directory
DATA_DIR = Path("/home/users/ee16eme/data")

# Input ICEYE products
ICEYE_X47_tif = (
    DATA_DIR / "demo_iceye" /
    "ICEYE_3ZYVUU_20251107T213442Z_6951870_X47_SLP2L_SLC.tif"
)

ICEYE_X47_json = (
    DATA_DIR / "demo_iceye" /
    "ICEYE_3ZYVUU_20251107T213442Z_6951870_X47_SLP2L_SLC.json"
)

    
ICEYE_X49_h5 = (
    DATA_DIR / "CS-26350/SLH_10283683_678351" /
    "ICEYE_X49_SLC_SLH_10283683_20260811T011721.h5"
)

# Output directory
working_DIR = DATA_DIR / "fern_iceye"
output_DIR = working_DIR / "slcs"
working_DIR.mkdir(parents=True, exist_ok=True)
output_DIR.mkdir(parents=True, exist_ok=True)

def convert_iceye(input_file, format_type, annotation=None):
    name = os.path.splitext(os.path.basename(input_file))[0]

    slc = f"{output_DIR}/{name}.slc"
    par = f"{output_DIR}/{name}.slc.par"

    if format_type == "tif":
        cmd = [
            "par_ICEYE_SLC",
            input_file,
            annotation,
            par,
            slc,
            "0"  # Zero-Doppler geometry
        ]

    elif format_type == "h5":
        cmd = [
            "par_ICEYE_SLC_HDF5",
            input_file,
            par,
            slc,
            "-",  # Default data type
            "-"   # Automatic geometry detection
        ]
    else:
        raise ValueError("format_type must be 'tif' or 'h5'")

    print("Running:", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)

    return slc, par


# Convert X47 GeoTIFF
X47_slc, X47_par = convert_iceye(
    ICEYE_X47_tif, "tif", ICEYE_X47_json
)

# Convert X49 HDF5
X49_slc, X49_par = convert_iceye(
    ICEYE_X49_h5, "h5"
)