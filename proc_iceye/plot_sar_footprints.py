#!/usr/bin/env python3

"""
Plot ICEYE, TerraSAR-X (TSX1), and TanDEM-X (TDX1) SAR scene footprints
over a georeferenced SAR intensity image.

Background TIF
--------------
The background TIF is assumed to contain linear SAR intensity/power and
is displayed in dB:

    10 * log10(intensity)

ICEYE
-----
ICEYE GRD footprints are read from:

    coord_first_near
    coord_first_far
    coord_last_far
    coord_last_near

TSX / TDX
---------
TerraSAR-X and TanDEM-X SSC footprints are read from the four:

    sceneCornerCoord

elements containing:

    refRow
    refColumn
    lat
    lon

Output
------
The figure is saved as a publication-quality PDF.
"""

from pathlib import Path
import argparse
import xml.etree.ElementTree as ET
from datetime import datetime

import numpy as np
import matplotlib.pyplot as plt
import rasterio
from pyproj import Transformer


# ================================================================
# Command-line arguments
# ================================================================

def parse_args():

    parser = argparse.ArgumentParser(
        description=(
            "Plot ICEYE, TerraSAR-X, and TanDEM-X scene footprints "
            "over a georeferenced SAR intensity TIF."
        ),
        epilog="""
Example using the Fernandina data:

  python plot_sar_footprints.py \\
      --iceye-dir /nfs/a283/homes/ee16eme/data/fern_iceye_proc/xmls \\
      --tsx-dir /nfs/a283/homes/ee16eme/data/fern_iceye_proc/tsx_xml \\
      --tif /nfs/a283/homes/ee16eme/data/fern_iceye_proc/20251102.geo.mli.tif \\
      --output fernandina_sar_footprints.pdf

Use a different SAR display stretch:

  python plot_sar_footprints.py \\
      --iceye-dir /nfs/a283/homes/ee16eme/data/fern_iceye_proc/xmls \\
      --tsx-dir /nfs/a283/homes/ee16eme/data/fern_iceye_proc/tsx_xml \\
      --tif /nfs/a283/homes/ee16eme/data/fern_iceye_proc/20251102.geo.mli.tif \\
      --output fernandina_sar_footprints.pdf \\
      --percentiles 1 99

ICEYE:
    Only *_GRD_*.xml files are used.

TSX / TDX:
    All *.xml files in --tsx-dir are examined.
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--iceye-dir",
        type=Path,
        required=True,
        help=(
            "Directory containing ICEYE GRD XML files. "
            "Example: "
            "/nfs/a283/homes/ee16eme/data/fern_iceye_proc/xmls"
        ),
    )

    parser.add_argument(
        "--tsx-dir",
        type=Path,
        required=True,
        help=(
            "Directory containing TSX1/TDX1 XML files. "
            "Example: "
            "/nfs/a283/homes/ee16eme/data/fern_iceye_proc/tsx_xml"
        ),
    )

    parser.add_argument(
        "--tif",
        type=Path,
        required=True,
        help=(
            "Georeferenced linear SAR intensity TIF. "
            "Example: "
            "/nfs/a283/homes/ee16eme/data/fern_iceye_proc/"
            "20251102.geo.mli.tif"
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path("sar_footprints.pdf"),
        help=(
            "Output PDF filename "
            "(default: sar_footprints.pdf)."
        ),
    )

    parser.add_argument(
        "--percentiles",
        type=float,
        nargs=2,
        default=[2.0, 98.0],
        metavar=("LOW", "HIGH"),
        help=(
            "Percentiles used to stretch the SAR background "
            "after conversion to dB (default: 2 98)."
        ),
    )

    return parser.parse_args()


# ================================================================
# XML helper
# ================================================================

def strip_namespace(tag):
    """
    Remove XML namespace if present.

    Example:
        {namespace}lat

    becomes:
        lat
    """

    return tag.split("}")[-1]


# ================================================================
# ICEYE footprint reader
# ================================================================

def read_iceye_footprint(xml_file):

    tree = ET.parse(xml_file)
    root = tree.getroot()

    corner_tags = [
        "coord_first_near",
        "coord_first_far",
        "coord_last_far",
        "coord_last_near",
    ]

    lon = []
    lat = []

    # Search manually so this also works if namespaces appear.
    elements = {}

    for element in root.iter():

        tag = strip_namespace(element.tag)

        if tag in corner_tags:
            elements[tag] = element

    for tag in corner_tags:

        if tag not in elements:
            raise ValueError(
                f"Missing ICEYE element: {tag}"
            )

        element = elements[tag]

        if element.text is None:
            raise ValueError(
                f"Empty ICEYE element: {tag}"
            )

        values = element.text.split()

        if len(values) < 4:
            raise ValueError(
                f"Unexpected contents of {tag}: "
                f"{element.text}"
            )

        # ICEYE format:
        #
        # pixel_x pixel_y latitude longitude

        latitude = float(values[2])
        longitude = float(values[3])

        lon.append(longitude)
        lat.append(latitude)

    # Close polygon.
    lon.append(lon[0])
    lat.append(lat[0])

    return lon, lat


# ================================================================
# TSX / TDX footprint reader
# ================================================================

def read_tsx_footprint(xml_file):

    tree = ET.parse(xml_file)
    root = tree.getroot()

    corners = []

    # ------------------------------------------------------------
    # Find all sceneCornerCoord elements.
    # ------------------------------------------------------------

    for element in root.iter():

        if strip_namespace(element.tag) != "sceneCornerCoord":
            continue

        values = {}

        for child in element:

            tag = strip_namespace(child.tag)

            if child.text is not None:
                values[tag] = child.text.strip()

        required = [
            "refRow",
            "refColumn",
            "lat",
            "lon",
        ]

        if not all(key in values for key in required):
            continue

        corners.append({
            "row": float(values["refRow"]),
            "column": float(values["refColumn"]),
            "lat": float(values["lat"]),
            "lon": float(values["lon"]),
        })

    if len(corners) != 4:

        raise ValueError(
            f"Expected 4 sceneCornerCoord elements, "
            f"found {len(corners)}"
        )

    # ------------------------------------------------------------
    # Order corners around their geographic centroid.
    #
    # This is safer than assuming that the XML always stores the
    # corners in a particular order.
    # ------------------------------------------------------------

    center_lon = np.mean(
        [corner["lon"] for corner in corners]
    )

    center_lat = np.mean(
        [corner["lat"] for corner in corners]
    )

    for corner in corners:

        corner["angle"] = np.arctan2(
            corner["lat"] - center_lat,
            corner["lon"] - center_lon,
        )

    corners.sort(
        key=lambda corner: corner["angle"]
    )

    lon = [
        corner["lon"]
        for corner in corners
    ]

    lat = [
        corner["lat"]
        for corner in corners
    ]

    # Close polygon.
    lon.append(lon[0])
    lat.append(lat[0])

    return lon, lat


# ================================================================
# ICEYE legend label
# ================================================================

def make_iceye_label(xml_file):

    parts = xml_file.stem.split("_")

    # Expected:
    #
    # ICEYE_X42_GRD_SLEA_10079289_20260706T163553

    if len(parts) < 6:
        return f"ICEYE: {xml_file.stem}"

    satellite = parts[1]
    acquisition_id = parts[4]
    time_string = parts[5]

    try:

        dt = datetime.strptime(
            time_string,
            "%Y%m%dT%H%M%S",
        )

        date_label = dt.strftime(
            "%d %b %Y %H:%M"
        )

    except ValueError:

        date_label = time_string

    return (
        f"ICEYE {satellite} — "
        f"{date_label} "
        f"(ID {acquisition_id})"
    )


# ================================================================
# TSX / TDX legend label
# ================================================================

def make_tsx_label(xml_file):

    parts = xml_file.stem.split("_")

    # Example:
    #
    # TSX1_SAR__SSC______SM_S_SRA_
    # 20221013T115954_20221013T120001

    platform = parts[0]

    # Find timestamp-like elements rather than relying entirely
    # on underscore positions.
    timestamps = []

    for part in parts:

        try:

            dt = datetime.strptime(
                part,
                "%Y%m%dT%H%M%S",
            )

            timestamps.append(dt)

        except ValueError:

            continue

    if timestamps:

        start = timestamps[0]

        date_label = start.strftime(
            "%d %b %Y %H:%M:%S"
        )

        return (
            f"{platform} — {date_label}"
        )

    return f"{platform} — {xml_file.stem}"


# ================================================================
# Main
# ================================================================

def main():

    args = parse_args()

    tif_file = args.tif
    iceye_dir = args.iceye_dir
    tsx_dir = args.tsx_dir
    output_file = args.output

    # ------------------------------------------------------------
    # Check inputs
    # ------------------------------------------------------------

    if not tif_file.is_file():

        raise FileNotFoundError(
            f"TIF file does not exist: {tif_file}"
        )

    if not iceye_dir.is_dir():

        raise NotADirectoryError(
            f"ICEYE directory does not exist: "
            f"{iceye_dir}"
        )

    if not tsx_dir.is_dir():

        raise NotADirectoryError(
            f"TSX directory does not exist: "
            f"{tsx_dir}"
        )

    low_percentile, high_percentile = (
        args.percentiles
    )

    if not (
        0 <= low_percentile
        < high_percentile
        <= 100
    ):

        raise ValueError(
            "--percentiles must satisfy "
            "0 <= LOW < HIGH <= 100"
        )

    if output_file.suffix.lower() != ".pdf":

        output_file = output_file.with_suffix(
            ".pdf"
        )

    # ------------------------------------------------------------
    # Find XML files
    # ------------------------------------------------------------

    iceye_files = sorted(
        iceye_dir.glob("*_GRD_*.xml")
    )

    tsx_files = sorted(
        tsx_dir.glob("*.xml")
    )

    if not iceye_files:

        print(
            f"WARNING: no ICEYE GRD XML files "
            f"found in {iceye_dir}"
        )

    if not tsx_files:

        print(
            f"WARNING: no TSX/TDX XML files "
            f"found in {tsx_dir}"
        )

    print()
    print("Input data")
    print("----------")

    print(
        f"Background TIF : {tif_file}"
    )

    print(
        f"ICEYE directory: {iceye_dir}"
    )

    print(
        f"TSX directory  : {tsx_dir}"
    )

    print(
        f"ICEYE scenes   : {len(iceye_files)}"
    )

    print(
        f"TSX/TDX scenes : {len(tsx_files)}"
    )

    print(
        f"Output PDF     : {output_file}"
    )

    # ------------------------------------------------------------
    # Publication-style Matplotlib configuration
    # ------------------------------------------------------------

    plt.rcParams.update({

        "font.family": "sans-serif",

        "font.size": 8,

        "axes.labelsize": 8,

        "axes.titlesize": 9,

        "xtick.labelsize": 7,

        "ytick.labelsize": 7,

        "legend.fontsize": 7,

        "axes.linewidth": 0.7,

        "xtick.major.width": 0.7,

        "ytick.major.width": 0.7,

        "xtick.direction": "out",

        "ytick.direction": "out",

        # Editable TrueType fonts in PDF.
        "pdf.fonttype": 42,

        "ps.fonttype": 42,
    })

    # ------------------------------------------------------------
    # Open SAR background
    # ------------------------------------------------------------

    with rasterio.open(tif_file) as src:

        print()
        print("Background raster")
        print("-----------------")

        print(
            f"CRS    : {src.crs}"
        )

        print(
            f"Bounds : {src.bounds}"
        )

        print(
            f"Shape  : {src.shape}"
        )

        print(
            f"dtype  : {src.dtypes[0]}"
        )

        print(
            f"nodata : {src.nodata}"
        )

        if src.crs is None:

            raise ValueError(
                "The TIF does not contain "
                "CRS information."
            )

        # --------------------------------------------------------
        # Read SAR intensity
        # --------------------------------------------------------

        intensity = src.read(1).astype(
            np.float32
        )

        valid = np.isfinite(
            intensity
        )

        valid &= intensity > 0

        if src.nodata is not None:

            valid &= (
                intensity != src.nodata
            )

        n_valid = np.count_nonzero(
            valid
        )

        if n_valid == 0:

            raise ValueError(
                "No valid positive intensity "
                "pixels found in the TIF."
            )

        # --------------------------------------------------------
        # Linear intensity -> dB
        # --------------------------------------------------------

        intensity_db = np.full(
            intensity.shape,
            np.nan,
            dtype=np.float32,
        )

        intensity_db[valid] = (
            10.0
            * np.log10(
                intensity[valid]
            )
        )

        # --------------------------------------------------------
        # Display stretch
        # --------------------------------------------------------

        vmin, vmax = np.nanpercentile(
            intensity_db,
            [
                low_percentile,
                high_percentile,
            ],
        )

        print(
            f"Display range: "
            f"{vmin:.2f} to "
            f"{vmax:.2f} dB"
        )

        # --------------------------------------------------------
        # Coordinate transformation
        # --------------------------------------------------------

        transformer = Transformer.from_crs(
            "EPSG:4326",
            src.crs,
            always_xy=True,
        )

        # --------------------------------------------------------
        # Figure
        # --------------------------------------------------------

        fig, ax = plt.subplots(
            figsize=(7.5, 5.8)
        )

        # Space on right for legend.
        fig.subplots_adjust(
            left=0.10,
            right=0.68,
            bottom=0.12,
            top=0.96,
        )

        # --------------------------------------------------------
        # Background SAR
        # --------------------------------------------------------

        image = ax.imshow(
            intensity_db,
            cmap="gray",
            vmin=vmin,
            vmax=vmax,
            extent=[
                src.bounds.left,
                src.bounds.right,
                src.bounds.bottom,
                src.bounds.top,
            ],
            origin="upper",
            interpolation="none",
            zorder=0,
        )

        # ========================================================
        # ICEYE
        # ========================================================

        print()
        print("ICEYE")
        print("-----")

        for xml_file in iceye_files:

            try:

                lon, lat = (
                    read_iceye_footprint(
                        xml_file
                    )
                )

            except (
                ET.ParseError,
                ValueError,
            ) as error:

                print(
                    f"WARNING: skipping "
                    f"{xml_file.name}: "
                    f"{error}"
                )

                continue

            x, y = transformer.transform(
                lon,
                lat,
            )

            label = make_iceye_label(
                xml_file
            )

            ax.plot(
                x,
                y,
                linewidth=1.5,
                linestyle="-",
                label=label,
                zorder=10,
            )

            print(
                f"Plotted: {xml_file.name}"
            )

        # ========================================================
        # TSX / TDX
        # ========================================================

        print()
        print("TSX / TDX")
        print("---------")

        for xml_file in tsx_files:

            try:

                lon, lat = (
                    read_tsx_footprint(
                        xml_file
                    )
                )

            except (
                ET.ParseError,
                ValueError,
            ) as error:

                print(
                    f"WARNING: skipping "
                    f"{xml_file.name}: "
                    f"{error}"
                )

                continue

            x, y = transformer.transform(
                lon,
                lat,
            )

            label = make_tsx_label(
                xml_file
            )

            # ----------------------------------------------------
            # Use line style to distinguish satellite families.
            #
            # Individual acquisitions still receive different
            # colours automatically from Matplotlib.
            # ----------------------------------------------------

            if xml_file.name.startswith(
                "TSX1"
            ):

                linestyle = "--"

            elif xml_file.name.startswith(
                "TDX1"
            ):

                linestyle = "-."

            else:

                linestyle = ":"

            ax.plot(
                x,
                y,
                linewidth=1.6,
                linestyle=linestyle,
                label=label,
                zorder=11,
            )

            print(
                f"Plotted: {xml_file.name}"
            )

        # --------------------------------------------------------
        # Map extent
        # --------------------------------------------------------

        ax.set_xlim(
            src.bounds.left,
            src.bounds.right,
        )

        ax.set_ylim(
            src.bounds.bottom,
            src.bounds.top,
        )

        ax.set_aspect(
            "equal"
        )

        # --------------------------------------------------------
        # Axes
        # --------------------------------------------------------

        ax.set_xlabel(
            "Easting"
        )

        ax.set_ylabel(
            "Northing"
        )

        ax.tick_params(
            top=False,
            right=False,
        )

        ax.ticklabel_format(
            style="plain",
            axis="both",
            useOffset=False,
        )

        # --------------------------------------------------------
        # Legend
        # --------------------------------------------------------

        legend = ax.legend(
            title="SAR acquisitions",
            loc="upper left",
            bbox_to_anchor=(
                1.03,
                1.0,
            ),
            borderaxespad=0.0,
            frameon=False,
            handlelength=3.2,
            labelspacing=0.7,
        )

        legend.get_title().set_fontsize(
            8
        )

        # --------------------------------------------------------
        # Colour bar
        # --------------------------------------------------------

        cbar = fig.colorbar(
            image,
            ax=ax,
            orientation="horizontal",
            fraction=0.045,
            pad=0.09,
            aspect=35,
        )

        cbar.set_label(
            "SAR intensity (dB)"
        )

        cbar.ax.tick_params(
            labelsize=7,
            width=0.7,
        )

        cbar.outline.set_linewidth(
            0.7
        )

        # --------------------------------------------------------
        # Save PDF
        # --------------------------------------------------------

        fig.savefig(
            output_file,
            format="pdf",
            bbox_inches="tight",
            pad_inches=0.05,
            dpi=600,
        )

        plt.close(fig)

    print()
    print(
        f"Saved publication figure: "
        f"{output_file}"
    )


if __name__ == "__main__":
    main()
