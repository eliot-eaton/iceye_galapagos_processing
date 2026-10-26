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
    print(f"Converting {input_file} to SLC format ({format_type})", flush=True)
    slc = f"{output_DIR}/{name}.slc"
    par = f"{output_DIR}/{name}.slc.par"
    # first check if output files already exist
    if os.path.exists(slc) and os.path.exists(par):
        print(f"Output files {slc} and {par} already exist. Skipping conversion.", flush=True)
        return slc, par
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

# first check if 
# Convert X47 GeoTIFF
X47_slc, X47_par = convert_iceye(
    ICEYE_X47_tif, "tif", ICEYE_X47_json
)

# Convert X49 HDF5
X49_slc, X49_par = convert_iceye(
    ICEYE_X49_h5, "h5"
)

# change directory to output_DIR = f"{DATA_DIR}/fern_iceye/slcs"
# subprocess.run(["cd", output_DIR], check=True)
# # print
os.chdir(output_DIR)
print(f"Changed working directory to {output_DIR}", flush=True)
print('Attempting to convert X47 from fcomplex to scomplex', flush=True)
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
#print 
print('Finished converting X47 from fcomplex to scomplex', flush=True)

# create seperate directories for each SLC date 20251107 and 20260811
os.makedirs(f"{output_DIR}/20251107", exist_ok=True)
os.makedirs(f"{output_DIR}/20260811", exist_ok=True)
# print
print("Created directories for 20251107 and 20260811", flush=True)
# mv the SLCs and their parameter files to their respective directories
subprocess.run([
    "mv",
    "ICEYE_3ZYVUU_20251107T213442Z_6951870_X47_SLP2L_SLC.scomplex.slc",
    "ICEYE_3ZYVUU_20251107T213442Z_6951870_X47_SLP2L_SLC.scomplex.slc.par",
    f"{output_DIR}/20251107/"
], check=True)
# print moved 
print("Moved ICEYE_3ZYVUU_20251107T213442Z_6951870_X47_SLP2L_SLC.scomplex.slc and its parameter file to 20251107 directory", flush=True)
subprocess.run([
    "mv",
    "ICEYE_3ZYVUU_20251107T213442Z_6951870_X47_SLP2L_SLC.slc",
    "ICEYE_3ZYVUU_20251107T213442Z_6951870_X47_SLP2L_SLC.slc.par",
    f"{output_DIR}/20251107/"
], check=True)
print("Moved ICEYE_3ZYVUU_20251107T213442Z_6951870_X47_SLP2L_SLC.slc and its parameter file to 20251107 directory", flush=True)
subprocess.run([
    "mv",
    "ICEYE_X49_SLC_SLH_10283683_20260811T011721.slc",
    "ICEYE_X49_SLC_SLH_10283683_20260811T011721.slc.par",
    f"{output_DIR}/20260811/"
], check=True)
print("Moved ICEYE_X49_SLC_SLH_10283683_20260811T011721.slc and its parameter file to 20260811 directory", flush=True)

#create_offset ICEYE_X49_SLC_SLH_10283683_20260811T011721.slc.par ICEYE_3ZYVUU_20251107T213442Z_6951870_X47_SLP2L_SLC.scomplex.slc.par ICEYE_3ZYVUU_20251107T213442Z_6951870_X47_SLP2L_SLC.scomplex.slc.par ICEYE_3ZYVUU_20251107T213442Z_6951870_X47_SLP2L_SLC.scomplex.re.slc.par