#!/usr/bin/env python3

"""
Plot ICEYE GRD scene footprints over a georeferenced SAR intensity image.

The background TIF is assumed to contain linear SAR intensity/power and
is displayed in dB:

    10 * log10(intensity)

ICEYE footprints are obtained from the corner coordinates in the GRD XML
metadata and transformed to the CRS of the background TIF.

Output is saved as a publication-quality PDF.
"""

from pathlib import Path
import argparse
import xml.etree.ElementTree as ET
from datetime import datetime

import numpy as np
import matplotlib.pyplot as plt
import rasterio
from pyproj import Transformer


def parse_args():

    parser = argparse.ArgumentParser(
        description=(
            "Plot ICEYE GRD scene footprints over a georeferenced "
            "SAR intensity TIF and save as a publication-quality PDF."
        ),
        epilog="""
Example using the Fernandina data:

  python plot_iceye_footprints.py \\
      --xml-dir /nfs/a283/homes/ee16eme/data/fern_iceye_proc/xmls \\
      --tif /nfs/a283/homes/ee16eme/data/fern_iceye_proc/20251102.geo.mli.tif

Specify output PDF:

  python plot_iceye_footprints.py \\
      --xml-dir /nfs/a283/homes/ee16eme/data/fern_iceye_proc/xmls \\
      --tif /nfs/a283/homes/ee16eme/data/fern_iceye_proc/20251102.geo.mli.tif \\
      --output fernandina_iceye_footprints.pdf

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
            "Georeferenced linear SAR intensity TIF used as background. "
            "Example: "
            "/nfs/a283/homes/ee16eme/data/fern_iceye_proc/"
            "20251102.geo.mli.tif"
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path("iceye_footprints.pdf"),
        help=(
            "Output PDF filename "
            "(default: iceye_footprints.pdf)."
        ),
    )

    parser.add_argument(
        "--percentiles",
        type=float,
        nargs=2,
        default=[2.0, 98.0],
        metavar=("LOW", "HIGH"),
        help=(
            "Percentiles used to stretch the SAR background after "
            "conversion to dB (default: 2 98)."
        ),
    )

    return parser.parse_args()


def read_iceye_footprint(xml_file):
    """
    Read four geographic corner coordinates from an ICEYE GRD XML.

    Returns closed polygon coordinates as longitude and latitude.
    """

    tree = ET.parse(xml_file)
    root = tree.getroot()

    # Traverse around the scene perimeter.
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
        # pixel_x pixel_y latitude longitude
        latitude = float(values[2])
        longitude = float(values[3])

        lon.append(longitude)
        lat.append(latitude)

    # Close polygon.
    lon.append(lon[0])
    lat.append(lat[0])

    return lon, lat


def make_legend_label(xml_file):
    """
    Construct a concise publication-style legend label from the
    ICEYE filename.

    Example:
        ICEYE_X42_GRD_SLEA_10079289_20260706T163553.xml

    becomes:
        X42 — 06 Jul 2026 16:35
    """

    parts = xml_file.stem.split("_")

    if len(parts) < 6:
        return xml_file.stem

    satellite = parts[1]
    acquisition_id = parts[4]
    time_string = parts[5]

    try:
        dt = datetime.strptime(
            time_string,
            "%Y%m%dT%H%M%S"
        )

        date_label = dt.strftime(
            "%d %b %Y %H:%M"
        )

    except ValueError:
        date_label = time_string

    return (
        f"{satellite} — {date_label} "
        f"(ID {acquisition_id})"
    )


def main():

    args = parse_args()

    tif_file = args.tif
    xml_dir = args.xml_dir
    output_file = args.output

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
            "--percentiles must satisfy "
            "0 <= LOW < HIGH <= 100"
        )

    # Force PDF extension.
    if output_file.suffix.lower() != ".pdf":
        output_file = output_file.with_suffix(".pdf")

    # Use GRD metadata only.
    xml_files = sorted(
        xml_dir.glob("*_GRD_*.xml")
    )

    if not xml_files:
        raise FileNotFoundError(
            f"No *_GRD_*.xml files found in {xml_dir}"
        )

    print(f"Background TIF: {tif_file}")
    print(f"XML directory:  {xml_dir}")
    print(f"GRD XML files:  {len(xml_files)}")
    print(f"Output PDF:     {output_file}")

    # ------------------------------------------------------------
    # Publication-style Matplotlib settings
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

        # Keep text editable/vectorised in PDF.
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })

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

        intensity = src.read(1).astype(
            np.float32
        )

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
                "No valid positive intensity pixels "
                "found in the TIF."
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
        # Display stretch
        # --------------------------------------------------------

        vmin, vmax = np.nanpercentile(
            intensity_db,
            [
                low_percentile,
                high_percentile
            ],
        )

        print(
            f"SAR display percentiles: "
            f"{low_percentile:g}–"
            f"{high_percentile:g}"
        )

        print(
            f"SAR display range: "
            f"{vmin:.2f} to {vmax:.2f} dB"
        )

        # --------------------------------------------------------
        # Coordinate transformer
        # --------------------------------------------------------

        transformer = Transformer.from_crs(
            "EPSG:4326",
            src.crs,
            always_xy=True,
        )

        # --------------------------------------------------------
        # Figure
        #
        # Map occupies the left-hand portion. Extra width is
        # intentionally provided for the external legend.
        # --------------------------------------------------------

        fig, ax = plt.subplots(
            figsize=(7.2, 5.8)
        )

        # Leave room on right for legend.
        fig.subplots_adjust(
            left=0.10,
            right=0.70,
            bottom=0.12,
            top=0.94,
        )

        # --------------------------------------------------------
        # SAR background
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
        )

        # --------------------------------------------------------
        # Plot ICEYE footprints
        # --------------------------------------------------------

        plotted = 0

        for xml_file in xml_files:

            try:
                lon, lat = read_iceye_footprint(
                    xml_file
                )

            except (
                ET.ParseError,
                ValueError
            ) as error:

                print(
                    f"WARNING: skipping "
                    f"{xml_file.name}: {error}"
                )

                continue

            # Transform WGS84 -> TIF CRS.
            x, y = transformer.transform(
                lon,
                lat
            )

            legend_label = make_legend_label(
                xml_file
            )

            ax.plot(
                x,
                y,
                linewidth=1.5,
                label=legend_label,
                zorder=10,
            )

            plotted += 1

            print(
                f"Plotted: {xml_file.name}"
            )

        # --------------------------------------------------------
        # Map limits
        # --------------------------------------------------------

        ax.set_xlim(
            src.bounds.left,
            src.bounds.right,
        )

        ax.set_ylim(
            src.bounds.bottom,
            src.bounds.top,
        )

        # Maintain correct spatial aspect ratio.
        ax.set_aspect("equal")

        # --------------------------------------------------------
        # Axes
        # --------------------------------------------------------

        ax.set_xlabel("Easting")
        ax.set_ylabel("Northing")

        ax.tick_params(
            top=False,
            right=False,
        )

        # Avoid scientific offset text where practical.
        ax.ticklabel_format(
            style="plain",
            axis="both",
            useOffset=False,
        )

        # --------------------------------------------------------
        # Legend outside map
        # --------------------------------------------------------

        if plotted > 0:

            legend = ax.legend(
                title="ICEYE acquisitions",
                loc="upper left",
                bbox_to_anchor=(1.03, 1.0),
                borderaxespad=0.0,
                frameon=False,
                handlelength=2.5,
                labelspacing=0.8,
            )

            legend.get_title().set_fontsize(8)

        # --------------------------------------------------------
        # SAR intensity colour bar
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
            "SAR intensity (dB)",
            fontsize=8,
        )

        cbar.ax.tick_params(
            labelsize=7,
            width=0.7,
        )

        cbar.outline.set_linewidth(0.7)

        # --------------------------------------------------------
        # Save publication figure
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
