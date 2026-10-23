import os
import subprocess

DATA_DIR = "/home/users/ee16eme/data"
output_DIR = f"{DATA_DIR}/fern_iceye/slcs"
os.makedirs(output_DIR, exist_ok=True)

# Input files
ICEYE_X47_tif = f"{DATA_DIR}/demo_iceye/ICEYE_3ZYVUU_20251107T213442Z_6951870_X47_SLP2L_SLC.tif"
ICEYE_X47_json = ICEYE_X47_tif.replace(".tif", ".json")

ICEYE_X49_h5 = f"{DATA_DIR}/CS-26350/SLH_10283683_678351/ICEYE_X49_SLC_SLH_10283683_20260811T011721.h5"


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


# convert X47 from fcomplex to scomlex 
subprocess.run([
    "SLC_copy",
    "ICEYE_3ZYVUU_20251107T213442Z_6951870_X47_SLP2L_SLC.slc",
    "ICEYE_3ZYVUU_20251107T213442Z_6951870_X47_SLP2L_SLC.slc.par",
    "ICEYE_3ZYVUU_20251107T213442Z_6951870_X47_SLP2L_SLC.scomplex.slc",
    "ICEYE_3ZYVUU_20251107T213442Z_6951870_X47_SLP2L_SLC.scomplex.slc.par",
    "2",
    "-",
    "-",
    "-"
], check=True)