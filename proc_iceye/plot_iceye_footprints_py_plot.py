#!/usr/bin/env python3

"""
Plot ICEYE GRD scene footprints over a georeferenced SAR intensity image.

The background TIF is assumed to contain linear SAR intensity/power.
It is converted to dB using:

    10 * log10(intensity)

The display range is controlled using percentile clipping.
"""

from pathlib import Path
import argparse
import xml.etree.ElementTree as ET

import numpy as np
import matplotlib.pyplot as plt
import rasterio
from pyproj import Transformer


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Plot ICEYE GRD scene footprints from XML metadata over a "
            "georeferenced SAR intensity TIF."
        ),
        epilog="""
Example using the Fernandina data:

  python plot_iceye_footprints.py \\
      --xml-dir /nfs/a283/homes/ee16eme/data/fern_iceye_proc/xmls \\
      --tif /nfs/a283/homes/ee16eme/data/fern_iceye_proc/20251102.geo.mli.tif

Use a different SAR display stretch:

  python plot_iceye_footprints.py \\
      --xml-dir /nfs/a283/homes/ee16eme/data/fern_iceye_proc/xmls \\
      --tif /nfs/a283/homes/ee16eme/data/fern_iceye_proc/20251102.geo.mli.tif \\
      --percentiles 1 99

Only XML files matching *_GRD_*.xml are used.
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--xml-dir",
        type=Path,
        required=True,
        help=(
            "Directory containing ICEYE XML metadata files. "
            "Example: "
            "/nfs/a283/homes/ee16eme/data/fern_iceye_proc/xmls"
        ),
    )

    parser.add_argument(
        "--tif",
        type=Path,
        required=True,
        help=(
            "Georeferenced linear SAR intensity TIF used as the background. "
            "Example: "
            "/nfs/a283/homes/ee16eme/data/fern_iceye_proc/"
            "20251102.geo.mli.tif"
        ),
    )

    parser.add_argument(
        "--percentiles",
        type=float,
        nargs=2,
        default=[2.0, 98.0],
        metavar=("LOW", "HIGH"),
        help=(
            "Percentiles used to stretch the SAR background after conversion "
            "to dB (default: 2 98)."
        ),
    )

    return parser.parse_args()


def read_iceye_footprint(xml_file):
    """
    Read the four geographic corner coordinates from an ICEYE GRD XML.

    Returns
    -------
    lon : list
        Longitude coordinates.
    lat : list
        Latitude coordinates.

    The first coordinate is repeated at the end to close the polygon.
    """

    tree = ET.parse(xml_file)
    root = tree.getroot()

    # Order the coordinates around the perimeter rather than diagonally.
    corner_tags = [
        "coord_first_near",
        "coord_first_far",
        "coord_last_far",
        "coord_last_near",
    ]

    lon = []
    lat = []

    for tag in corner_tags:

        element = root.find(f".//{tag}")

        if element is None or element.text is None:
            raise ValueError(f"Missing {tag}")

        values = element.text.split()

        if len(values) < 4:
            raise ValueError(
                f"Unexpected contents of {tag}: {element.text}"
            )

        # ICEYE format:
        #
        # pixel_x  pixel_y  latitude  longitude
        #
        latitude = float(values[2])
        longitude = float(values[3])

        lon.append(longitude)
        lat.append(latitude)

    # Close polygon.
    lon.append(lon[0])
    lat.append(lat[0])

    return lon, lat


def main():

    args = parse_args()

    tif_file = args.tif
    xml_dir = args.xml_dir

    # ------------------------------------------------------------
    # Check inputs
    # ------------------------------------------------------------

    if not tif_file.is_file():
        raise FileNotFoundError(
            f"TIF file does not exist: {tif_file}"
        )

    if not xml_dir.is_dir():
        raise NotADirectoryError(
            f"XML directory does not exist: {xml_dir}"
        )

    low_percentile, high_percentile = args.percentiles

    if not 0 <= low_percentile < high_percentile <= 100:
        raise ValueError(
            "--percentiles must satisfy 0 <= LOW < HIGH <= 100"
        )

    # Use GRD metadata only.
    xml_files = sorted(xml_dir.glob("*_GRD_*.xml"))

    if not xml_files:
        raise FileNotFoundError(
            f"No *_GRD_*.xml files found in {xml_dir}"
        )

    print(f"Background TIF: {tif_file}")
    print(f"XML directory:  {xml_dir}")
    print(f"GRD XML files:  {len(xml_files)}")

    # ------------------------------------------------------------
    # Read background SAR image
    # ------------------------------------------------------------

    with rasterio.open(tif_file) as src:

        print()
        print(f"TIF CRS:    {src.crs}")
        print(f"TIF bounds: {src.bounds}")
        print(f"TIF shape:  {src.shape}")
        print(f"TIF dtype:  {src.dtypes[0]}")
        print(f"TIF nodata: {src.nodata}")

        if src.crs is None:
            raise ValueError(
                "The TIF does not contain CRS information."
            )

        # Read first raster band as floating point.
        intensity = src.read(1).astype(np.float32)

        # --------------------------------------------------------
        # Mask invalid pixels
        # --------------------------------------------------------

        valid = np.isfinite(intensity)
        valid &= intensity > 0

        if src.nodata is not None:
            valid &= intensity != src.nodata

        n_valid = np.count_nonzero(valid)

        if n_valid == 0:
            raise ValueError(
                "No valid positive intensity pixels found in the TIF."
            )

        print(f"Valid SAR pixels: {n_valid:,}")

        # --------------------------------------------------------
        # Convert linear intensity -> dB
        # --------------------------------------------------------

        intensity_db = np.full(
            intensity.shape,
            np.nan,
            dtype=np.float32,
        )

        intensity_db[valid] = (
            10.0 * np.log10(intensity[valid])
        )

        # --------------------------------------------------------
        # Calculate display stretch
        # --------------------------------------------------------

        vmin, vmax = np.nanpercentile(
            intensity_db,
            [low_percentile, high_percentile],
        )

        print(
            f"SAR display percentiles: "
            f"{low_percentile:g} - {high_percentile:g}"
        )

        print(
            f"SAR display range: "
            f"{vmin:.2f} to {vmax:.2f} dB"
        )

        # --------------------------------------------------------
        # Coordinate transformer
        # --------------------------------------------------------

        # ICEYE corner coordinates are longitude/latitude WGS84.
        #
        # Transform them into the coordinate system used by the
        # background TIF.
        transformer = Transformer.from_crs(
            "EPSG:4326",
            src.crs,
            always_xy=True,
        )

        # --------------------------------------------------------
        # Create plot
        # --------------------------------------------------------

        fig, ax = plt.subplots(
            figsize=(12, 12)
        )

        # Plot the SAR image in map coordinates.
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
        )

        # --------------------------------------------------------
        # Plot ICEYE footprints
        # --------------------------------------------------------

        for xml_file in xml_files:

            try:
                lon, lat = read_iceye_footprint(xml_file)

            except (ET.ParseError, ValueError) as error:

                print(
                    f"WARNING: skipping {xml_file.name}: "
                    f"{error}"
                )

                continue

            # Transform WGS84 lon/lat -> background TIF CRS.
            x, y = transformer.transform(lon, lat)

            # Draw footprint.
            ax.plot(
                x,
                y,
                linewidth=2,
            )

            # ----------------------------------------------------
            # Construct a short label
            # ----------------------------------------------------

            parts = xml_file.stem.split("_")

            # Expected filename:
            #
            # ICEYE_X42_GRD_SLEA_10079289_20260706T163553
            #
            if len(parts) >= 6:

                satellite = parts[1]
                acquisition_id = parts[4]
                acquisition_time = parts[5]

                label = (
                    f"{satellite}\n"
                    f"{acquisition_id}\n"
                    f"{acquisition_time}"
                )

            else:
                label = xml_file.stem

            # Label position = mean of four corners.
            cx = np.mean(x[:-1])
            cy = np.mean(y[:-1])

            ax.text(
                cx,
                cy,
                label,
                fontsize=7,
                ha="center",
                va="center",
                bbox={
                    "facecolor": "white",
                    "alpha": 0.65,
                    "edgecolor": "none",
                    "pad": 2,
                },
            )

            print(f"Plotted: {xml_file.name}")

        # --------------------------------------------------------
        # Final plot configuration
        # --------------------------------------------------------

        ax.set_xlim(
            src.bounds.left,
            src.bounds.right,
        )

        ax.set_ylim(
            src.bounds.bottom,
            src.bounds.top,
        )

        ax.set_title(
            "ICEYE GRD scene footprints"
        )

        ax.set_xlabel("Easting / X")
        ax.set_ylabel("Northing / Y")

        # Add dB colour bar for the background image.
        cbar = fig.colorbar(
            image,
            ax=ax,
            fraction=0.035,
            pad=0.02,
        )

        cbar.set_label(
            "SAR intensity (dB)"
        )

        plt.tight_layout()
        plt.show()


if __name__ == "__main__":
    main()
